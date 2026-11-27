"""Authenticated single-pool model transport with measured streamed-delta latency."""
import json
import time
import httpx
from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse
from ..lab.workload import inspect


class Meter:
    def __init__(self, runtime, identifier):
        self.runtime, self.identifier = runtime, identifier
        self.started = time.monotonic()
        self.first = None

    async def observe(self, line):
        if self.first is None and meaningful(line):
            self.first = time.monotonic()
            scope = self.runtime.requests.get(self.identifier)
            if scope is None:
                return
            record = {'request':self.identifier, 'role':scope['role'],
                      'first_delta_s':self.first-self.started,
                      'request_elapsed_s':self.first-scope.get('started_monotonic',self.started)}
            scope.setdefault('provider_metrics', []).append(record)
            self.runtime.store.audit('model_first_streamed_delta', record)

        if line.startswith('data:') and line[5:].strip()!='[DONE]':
            payload = json.loads(line[5:])
            text = (payload.get('choices') or [{}])[0].get('delta',{}).get('content')
            scope = self.runtime.requests.get(self.identifier, {})
            if text and scope.get('events'):
                await scope['events'].put({'type':'answer','text':text,
                    'elapsed_s':time.monotonic()-scope['started_monotonic']})


def meaningful(line):
    if not line.startswith('data:') or line[5:].strip()=='[DONE]':
        return False
    payload = json.loads(line[5:])
    choices = payload.get('choices') or [{}]
    delta = choices[0].get('delta', {})
    return bool(delta.get('content') or delta.get('tool_calls') or delta.get('reasoning_content'))


async def stream(runtime, identifier, body):
    meter = Meter(runtime, identifier)
    origin = f'http://127.0.0.1:{runtime.config["model_port"]}/v1/chat/completions'
    try:
        async with httpx.AsyncClient(trust_env=False, timeout=360) as client:
            async with client.stream('POST', origin, json=body) as response:
                if response.is_error:
                    detail = (await response.aread()).decode(errors='replace')[:500]
                    raise ValueError('Local provider HTTP '+str(response.status_code)+': '+detail)
                async for line in response.aiter_lines():
                    await meter.observe(line)
                    yield (line+'\n').encode()
    except (httpx.HTTPError,ValueError) as error:
        scope = runtime.requests.get(identifier,{})
        message = 'Shared local inference became unavailable or yielded: '+str(error)
        runtime.store.audit('inference_transport_unavailable',{'request':identifier,'message':message})
        if scope.get('events'):
            await scope['events'].put({'type':'runtime_error','message':message})



def install(app, runtime):
    @app.post('/api/lab/v1/inference/{identifier}/chat/completions')
    async def inference(identifier: str, request: Request):
        if identifier not in runtime.requests:
            raise HTTPException(403,'Unknown or expired inference scope')
        load = await inspect(runtime.lab)
        if not load['inference_permitted']:
            raise HTTPException(503,'Native workload or memory reservation takes priority')
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw)>128000:
                raise HTTPException(413,'Bounded local model context exceeded')
        body = json.loads(raw)
        body.update(stream=True, max_tokens=max(1,min(int(body.get('max_tokens',256)),384)))
        if runtime.config.get('debug_model_shapes'):
            runtime.store.audit('model_request_shape', {
                'request':identifier,'max_tokens':body.get('max_tokens'),'stop':body.get('stop'),
                'last_messages':[{'role':message.get('role'),'content':str(message.get('content'))[:220],
                    'tool_calls':message.get('tool_calls')} for message in body.get('messages',[])[-3:]]})
        return StreamingResponse(stream(runtime,identifier,body), media_type='text/event-stream')
