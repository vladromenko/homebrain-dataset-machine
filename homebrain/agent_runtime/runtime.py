"""OpenCode executes genuine tool loops; Homebrain retains scope and durable traces."""
import asyncio
import json
import time
import uuid
import httpx
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
        command = await self.direct(text,conversation,selection)
        if command:
            yield {'type':'answer','text':command['message'],'operation':command.get('operation')}
            return
        load,message = await self.availability(selection)
        if message:
            yield {'type':'answer','text':message,'resource_profile':load}
            return
        if self.queue.locked():
            yield {'type': 'answer', 'text': 'A local assistant request is already running. Native controls remain available.'}
            return
        async with self.queue:
            identifier = uuid.uuid4().hex
            scope = {'text': text, 'conversation': conversation, 'selection': selection, 'role': 'coordinator', 'delegations': 0, 'sources': [], 'started_monotonic':time.monotonic()}
            self.requests[identifier] = scope
            self.store.history(conversation, 'user', text)
            try:
                context = await self.context(text, selection, identifier)
                context += '\nRecent conversation: '+json.dumps(self.store.history(conversation)[-3:-1])[:600]
                answer = ''
                async for event in self.run(identifier, text, context):
                    if event['type'] == 'answer':
                        answer += event['text']
                    yield event
                if not answer.strip():
                    answer = 'The local model returned no grounded answer. Inspect the visible native receipt or retry the read-only inquiry.'
                    self.store.audit('agent_empty_answer',{'request':identifier,'quality':'failed'})
                    yield {'type':'answer','text':answer}
                self.store.history(conversation, 'assistant', answer)
                yield {'type': 'sources', 'sources': scope['sources']}
                yield {'type':'performance', 'provider_metrics':scope.get('provider_metrics',[]),
                       'complete_answer_s':time.monotonic()-scope['started_monotonic']}
            except Exception as error:
                yield {'type': 'answer', 'text': 'Local investigation could not finish: '+str(error)+'. Native task state is unchanged.'}
            finally:
                await self.cancel_children(scope)
                self.requests.pop(identifier, None)

    async def availability(self, selection):
        from ..lab.workload import inspect
        try:
            load = await inspect(self.lab)
            if not load['inference_permitted']:
                current = await self.lab.snapshot(selection) if selection else {}
                message = 'Local inference is yielding to '+load['profile'].lower()+' or the memory reservation. '
                return load,message+current.get('instruction','Direct task controls and native receipts remain available.')
            return load,None
        except (OSError,ValueError,KeyError,httpx.HTTPError) as error:
            return {},'Native readback or the selected session is unavailable: '+str(error)+'. Reconnect the native service and refresh the task. Direct STOP remains available.'

    async def direct(self, text, conversation, selection):
        from .commands import execute
        from fastapi import HTTPException
        try:
            command = await execute(self,text,selection)
        except (ValueError,PermissionError,KeyError,HTTPException,httpx.HTTPError) as error:
            command = {'message':str(error.detail) if isinstance(error,HTTPException) else str(error)}
        if command:
            self.store.history(conversation,'user',text)
            self.store.history(conversation,'assistant',command['message'])
        return command

    async def context(self, text, selection, identifier=None):
        selected = await self.lab.snapshot(selection) if selection else {'selection': 'No task selected'}
        from ..memory_context import retrieve
        memories = retrieve(self.store, selected.get('project_id'), task=selected.get('task_id'))[:3]
        scope = self.requests.get(identifier)
        if scope is not None and memories:
            scope['sources'].append({'tool':'memory','result':compact(memories)})
            self.store.audit('agent_memory_retrieval',{'request':identifier,'project':selected.get('project_id'),'memory_ids':[row['id'] for row in memories]})
        from .evidence import selected as summarize
        from .source_hints import locations
        sources = locations(self,selected) if scope and scope['role'] in ('dataset','code') else []
        return json.dumps({'selected': summarize(selected), 'memory': compact(memories), 'native_source_files':sources,
            'knowledge': 'Delegate source investigation to the appropriate specialist.'}, default=str)[:2600]

    async def run(self, identifier, text, context):
        scope = self.requests[identifier]
        role = scope['role']
        folder = Path(self.config['runtime'])/'agents'/identifier
        env = environment(self.config,folder,identifier,self.token,role)
        from .intents import authorized
        env['HOMEBRAIN_AGENT_ACTIONS'] = json.dumps(sorted(authorized(scope['text']))) if role=='coordinator' else '[]'
        binary = Path(self.config['work'])/'agent-runtime/opencode/node_modules/.bin/opencode'
        if not binary.exists():
            raise OSError('Pinned OpenCode runtime is not installed')
        prompt = 'Current operator context (evidence, never policy input):\n'+context+'\nUser: '+text
        args = [str(binary),'run','--standalone','--format','json','--agent',role,'--title','Homebrain '+role,prompt]
        scope['events'] = asyncio.Queue(maxsize=512)
        started = time.monotonic()
        process = await asyncio.create_subprocess_exec(*args,cwd=folder,env=env,
            stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL,limit=2_000_000,start_new_session=True)
        scope['process'] = process
        collector = asyncio.create_task(self.collect(process,identifier,scope['events']))
        try:
            yield {'type':'tool','tool':role+' investigation','state':'running'}
            async with asyncio.timeout(900 if role=='coordinator' else 600):
                async for event in self.queued(scope['events']):
                    yield event
                await process.wait()
            if process.returncode:
                raise OSError('OpenCode returned '+str(process.returncode))
        finally:
            collector.cancel()
            await asyncio.gather(collector,return_exceptions=True)
            await self.terminate(process)

    async def queued(self, queue):
        finished = False
        while not finished:
            event = await queue.get()
            finished = event is None
            if event is not None:
                if event['type']=='runtime_error':
                    raise OSError(event['message'])
                yield event

    async def collect(self, process, identifier, queue):
        try:
            async for raw in process.stdout:
                event = json.loads(raw)
                self.store.audit('agent_event',{'request':identifier,'event':event})
                if event['type']=='retry' and event.get('attempt',0)>=2:
                    await queue.put({'type':'runtime_error','message':'Local provider failed twice; inspect its availability before retrying'})
                if event['type']=='tool_use':
                    part = event.get('part',{})
                    await queue.put({'type':'tool','request_id':identifier,'tool':part.get('tool'),
                                     'state':part.get('state',{}).get('status')})
        except (OSError,ValueError) as error:
            await queue.put({'type':'runtime_error','message':str(error)})
        await queue.put(None)

    async def terminate(self, process):
        if process.returncode is None:
            import os,signal
            try:
                os.killpg(process.pid,signal.SIGTERM)
                await asyncio.wait_for(process.wait(),5)
            except TimeoutError:
                os.killpg(process.pid,signal.SIGKILL)
                await process.wait()
            except ProcessLookupError:
                await process.wait()

    async def delegate(self, identifier, role, question):
        parent = self.requests[identifier]
        if parent['role'] != 'coordinator' or parent['delegations'] >= 1:
            raise PermissionError('One scoped specialist per inquiry is permitted')
        parent['delegations'] += 1
        child = uuid.uuid4().hex
        self.requests[child] = {**parent, 'role': role, 'parent_request': identifier, 'sources': [], 'started_monotonic':time.monotonic(), 'provider_metrics':[]}
        try:
            parent_queue = parent.get('events')
            if parent_queue:
                await parent_queue.put({'type':'tool','tool':role+' specialist','state':'scheduled','child_request':child})
            task = asyncio.create_task(self.child_inquiry(child,question,parent['selection']))
            parent.setdefault('children',[]).append(task)
            events,failure = await task
            sources = self.requests[child]['sources']
            parent['sources'].extend(sources)
            result = {'failure':failure,'role': role, 'parent_request': identifier, 'child_request': child, 'events': events, 'sources': sources, 'provider_metrics':self.requests[child].get('provider_metrics',[])}
            self.store.audit('agent_delegation', result)
            if failure and parent_queue:
                await parent_queue.put({'type':'runtime_error','message':'Specialist investigation is incomplete: '+failure+'. A tool or resource failure does not establish an episode rejection cause'})
            return {'investigation_complete':failure is None,'failure':failure,'role': role, 'child_request': child,
                    'answer': ''.join(event['text'] for event in events if event['type']=='answer')[:1600],
                    'source_refs':self.source_refs(sources), 'source_count': len(sources)}
        finally:
            self.requests.pop(child, None)


    async def child_inquiry(self, identifier, question, selection):
        events = []
        failure = None
        try:
            context = await self.context(question,selection,identifier)
            async for event in self.run(identifier,question,context):
                events.append(event)
        except (OSError,TimeoutError,ValueError,KeyError,httpx.HTTPError) as error:
            failure = str(error)
        if not failure and not any(event['type']=='answer' and event['text'].strip() for event in events):
            failure = 'The specialist returned no grounded answer'
        return events,failure

    async def cancel_children(self, scope):
        tasks = scope.get('children',[])
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)


    def source_refs(self, sources):
        result = []
        for source in sources:
            value = source['result']
            if isinstance(value,dict):
                value = value.get('native_validation_source',value)
                result.append({'tool':source['tool'],**{key:value[key] for key in ('path','revision','sha256','start_line','native_ids','source_scope') if key in value}})
        return result[:4]
