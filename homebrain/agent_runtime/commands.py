"""Exact visible action names bypass inference and use the same typed native boundary."""
import asyncio
import hashlib
import json
from .intents import authorized
from ..lab.contracts import ActionRequest


async def execute(runtime, text, selection):
    actions = authorized(text)
    if not actions:
        return None
    action = next(iter(actions))
    session = await runtime.lab.snapshot(selection) if selection else None
    if action == 'stop':
        robots = [session['robot_id']] if session else ['so101','tank','rosmaster']
        results = await asyncio.gather(*(runtime.lab.emergency_stop(robot) for robot in robots),return_exceptions=True)
        missing = [robot for robot,result in zip(robots,results) if isinstance(result,Exception)]
        return {'message':'Native STOP requested.'+(' Acknowledgement unavailable: '+', '.join(missing) if missing else ' Controller acknowledgements received.'),
                'physical_stop_confirmed':False}
    if action == 'submit_job':
        from ..lab.project_jobs import Submission, submit
        review = runtime.lab.journal.profile('reviewed-job') or {}
        if not session or review.get('session_id') != session['session_id']:
            raise PermissionError('Review a project-approved job in Jobs before voice submission')
        result = await submit(runtime.lab,Submission(**{key:review[key] for key in ('recipe_id','corpus_sha256','idempotency_key')}))
    else:
        if session is None:
            raise ValueError('Select the task before this command')
        arguments = {'explicit_user_start':True} if action=='start_recording' else {}
        if action in ('enable_control','start_recording'):
            arguments['expected_native_generation'] = session['readiness']['native_stop_generation']
        key = hashlib.sha256(json.dumps([session['session_id'],session['revision'],action]).encode()).hexdigest()
        request = ActionRequest(action=action,project_id=session['project_id'],session_id=session['session_id'],
            target_id=session['task_id'],expected_revision=session['revision'],idempotency_key='utterance-'+key,
            arguments=arguments)
        result = await runtime.lab.action(request)
    runtime.store.audit('typed_operator_command', {'action':action,'result':result})
    return {'message':result['status'].capitalize()+': '+result['message'],'operation':result}
