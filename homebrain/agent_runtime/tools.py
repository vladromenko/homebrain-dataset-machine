"""Server-issued scope overrides every model-supplied identity."""
import hashlib
import subprocess
from pathlib import Path
from .configuration import ROLES
from .permissions import ROLE_TOOLS
from .evidence import compact, status, receipts
from ..adapters import approved
from ..config import ROOT
from ..lab.contracts import ActionRequest


async def invoke(runtime, identifier, tool, arguments, adapters):
    scope = runtime.requests.get(identifier)
    if scope is None:
        raise PermissionError('Unknown or expired agent request')
    if tool not in ROLE_TOOLS.get(scope['role'], set()):
        raise PermissionError('Tool is outside this role capability')
    session = await runtime.lab.snapshot(scope['selection']) if scope['selection'] else None
    if tool == 'delegate':
        role = arguments.get('role')
        if role not in ROLES or role == 'coordinator':
            raise PermissionError('Unknown specialist')
        return await runtime.delegate(identifier, role, str(arguments['question'])[:1500])
    if tool == 'status':
        result = await status(runtime.lab, session)
    elif tool == 'receipt':
        result = receipts(session)
    elif tool == 'search':
        result = [dict(row, text=row['text'][:1200]) for row in runtime.store.retrieve(str(arguments['query'])[:500])[:2]]
    elif tool == 'read':
        result = read(runtime, arguments['path'], adapters, arguments.get('start_line',1))
    elif tool == 'vision':
        from .vision import inspect
        result = await inspect(runtime,arguments)
    elif tool == 'memory':
        from ..memory_context import retrieve
        result = {'memory':compact(retrieve(runtime.store,session.get('project_id') if session else None))}
    elif tool in ('git', 'check'):
        from .investigation import investigate
        result = await investigate(runtime, tool, arguments, adapters)
    elif tool == 'operation':
        result = await operation(runtime, scope, session, arguments['action'], identifier)
    else:
        raise PermissionError('Unknown typed tool')
    runtime.store.audit('agent_tool', {'request': identifier, 'tool': tool, 'arguments': arguments, 'result': result})
    scope['sources'].append({'tool': tool, 'result': result})
    return result


def read(runtime, path, adapters, start_line=1):
    roots = [str(ROOT)] + [root for adapter in adapters.values() for root in adapter.spec['approved_roots']]
    peer = runtime.lab.swarm.registration()
    if peer:
        roots.append(peer['repository_path'])
    candidate = approved(path, roots)
    with runtime.store.db() as db:
        indexed = db.execute('SELECT revision FROM documents WHERE path=? LIMIT 1', (str(candidate),)).fetchone()
    if indexed is None:
        raise PermissionError('Source must be in the approved index before reading')
    start_line=max(1,min(int(start_line),100000))
    lines=candidate.read_text(errors='replace').splitlines()
    content='\n'.join(lines[start_line-1:start_line+39])[:5000]
    return {'path': str(candidate), 'revision': indexed[0], 'sha256': hashlib.sha256(candidate.read_bytes()).hexdigest(), 'start_line':start_line,'text':content}


async def operation(runtime, scope, session, action, identifier):
    if scope['role'] != 'coordinator':
        raise PermissionError('Specialists only investigate; the coordinator owns typed operations')
    if session is None:
        raise ValueError('Choose a task in the workspace first')
    allowed = {'prepare_session', 'retry_validation', 'reconcile', 'refresh', 'review'}
    from .intents import authorized
    allowed |= authorized(scope['text'])
    if action not in allowed:
        return {'operator_action_required': action, 'message': 'Use the visible typed task action. Direct motor authority is not granted to this agent.'}
    request = ActionRequest(action=action, project_id=session['project_id'], session_id=session['session_id'],
        target_id=session['task_id'], expected_revision=session['revision'], idempotency_key=identifier+':'+action)
    return await runtime.lab.action(request)
