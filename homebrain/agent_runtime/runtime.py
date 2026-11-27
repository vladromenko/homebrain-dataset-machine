"""OpenCode executes genuine tool loops; Homebrain retains scope and durable traces."""
import asyncio
import json
import time
import uuid
from pathlib import Path
from .configuration import environment
from .evidence import selected, compact
from ..config import ROOT


class Runtime:
    def __init__(self, config, store, lab, token):
        self.config, self.store, self.lab, self.token = config, store, lab, token
        self.queue = asyncio.Lock()
        self.requests = {}

    async def answer(self, text, conversation, selection):
        from .intents import authorized
        if 'stop' in authorized(text):
            current = await self.lab.snapshot(selection) if selection else {}
            for robot in [current['robot_id']] if current else ['so101', 'tank', 'rosmaster']:
                await self.lab.emergency_stop(robot)
            yield {'type': 'answer', 'text': 'Native STOP requested. The controller acknowledgement does not confirm physical standstill.'}
            return
        from ..lab.workload import inspect
        load = await inspect(self.lab)
        if not load['inference_permitted']:
            current = await self.lab.snapshot(selection) if selection else {}
            yield {'type': 'answer', 'text': 'Local inference is yielding to '+load['profile'].lower()+
                   ' or the memory reservation. '+current.get('instruction', 'Direct task controls and native receipts remain available.'), 'resource_profile': load}
            return
        if self.queue.locked():
            yield {'type': 'answer', 'text': 'A local assistant request is already running. Native controls remain available.'}
            return
        async with self.queue:
            identifier = uuid.uuid4().hex
            scope = {'text': text, 'conversation': conversation, 'selection': selection, 'role': 'coordinator', 'delegations': 0, 'sources': []}
            self.requests[identifier] = scope
            self.store.history(conversation, 'user', text)
            try:
                context = await self.context(text, selection)
                context += '\nRecent conversation: '+json.dumps(self.store.history(conversation)[-3:-1])[:600]
                answer = ''
                async for event in self.run(identifier, text, context):
                    if event['type'] == 'answer':
                        answer += event['text']
                    yield event
                self.store.history(conversation, 'assistant', answer)
                yield {'type': 'sources', 'sources': scope['sources']}
            except Exception as error:
                yield {'type': 'answer', 'text': 'Local investigation could not finish: '+str(error)+'. Native task state is unchanged.'}
            finally:
                self.requests.pop(identifier, None)

    async def context(self, text, selection):
        selected = await self.lab.snapshot(selection) if selection else {'selection': 'No task selected'}
        from ..memory_context import retrieve
        memories = retrieve(self.store, selected.get('project_id'))[:3]
        from .evidence import selected as summarize
        return json.dumps({'selected': summarize(selected), 'memory': compact(memories),
            'knowledge': 'Use lab_search and lab_read for approved source evidence.'}, default=str)[:2600]

    async def run(self, identifier, text, context):
        scope = self.requests[identifier]
        role = scope['role']
        folder = Path(self.config['runtime'])/'agents'/identifier
        env = environment(self.config, folder, identifier, self.token, role)
        binary = Path(self.config['work'])/'agent-runtime/opencode/node_modules/.bin/opencode'
        if not binary.exists():
            raise OSError('Pinned OpenCode runtime is not installed')
        prompt = 'Server-scoped current context (operator-only; not policy input):\n'+context+'\nUser: '+text
        args = [str(binary), 'run', '--standalone', '--format', 'json', '--agent', role, '--title', 'Homebrain '+role, prompt]
        started = time.monotonic()
        process = await asyncio.create_subprocess_exec(*args, cwd=folder, env=env,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, limit=2_000_000)
        try:
            async with asyncio.timeout(300 if role == 'coordinator' else 180):
                async for event in self.stream(process, identifier, started):
                    yield event
                await process.wait()
            if process.returncode:
                raise OSError('OpenCode returned '+str(process.returncode))
        finally:
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), 5)
                except TimeoutError:
                    process.kill()
                    await process.wait()

    async def stream(self, process, identifier, started):
        async for raw in process.stdout:
            event = json.loads(raw)
            self.store.audit('agent_event', {'request': identifier, 'event': event})
            converted = self.event(event, identifier, started)
            if converted:
                yield converted

    def event(self, event, identifier, started):
        part = event.get('part', {})
        if event['type'] == 'text':
            return {'type': 'answer', 'text': part.get('text', ''), 'elapsed_s': round(time.monotonic()-started, 2)}
        if event['type'] == 'tool_use':
            return {'type': 'tool', 'request_id': identifier, 'tool': part.get('tool'), 'state': part.get('state', {}).get('status')}
        return None

    async def delegate(self, identifier, role, question):
        parent = self.requests[identifier]
        if parent['role'] != 'coordinator' or parent['delegations'] >= 1:
            raise PermissionError('One scoped specialist per inquiry is permitted')
        parent['delegations'] += 1
        child = uuid.uuid4().hex
        self.requests[child] = {**parent, 'role': role, 'parent_request': identifier, 'sources': []}
        try:
            context = await self.context(question, parent['selection'])
            events = [event async for event in self.run(child, question, context)]
            sources = self.requests[child]['sources']
            parent['sources'].extend(sources)
            result = {'role': role, 'parent_request': identifier, 'child_request': child, 'events': events, 'sources': sources}
            self.store.audit('agent_delegation', result)
            return {'role': role, 'child_request': child,
                    'answer': ''.join(event['text'] for event in events if event['type']=='answer')[:1600],
                    'source_count': len(sources)}
        finally:
            self.requests.pop(child, None)
