"""Wire presentation in the peer's own process; scientific decisions stay in its facade."""
import json
import sys
import time
from pathlib import Path
from smart_swarm.cli import settings
from smart_swarm.lab_api import HomebrainProject


def enrich(facade, snapshot):
    from smart_swarm.lab_domain import session_state, relocation_readiness
    from smart_swarm.physical_story_operator import archived_rgb_started
    state = session_state(facade.domain.config,snapshot['task_id'])
    if state and 'markers' in state:
        from smart_swarm.physical_story_source import story_phases
        phases=story_phases(state)
        index=len(state['markers'])
        snapshot['project_state']['required_phase']=phases[index] if index<len(phases) else None
        snapshot['project_state']['phase_family']=state.get('card',{}).get('family')
    if state and state.get('fleet_acknowledgement'):
        snapshot['project_state']['phase_timing'] = relocation_readiness(state,time.monotonic_ns(),
            archived_rgb_started(facade.domain.config,state))
        snapshot['project_state']['timing_authority']='smart_swarm.lab_domain.relocation_readiness'
    progress = facade.domain.config['data_root']/'lab/corpus-progress.json'
    if progress.is_file():
        snapshot['project_state']['admission_progress']=json.loads(progress.read_text())
    return snapshot


def dispatch(facade, message):
    binding = message.get('params',{}).pop('_native_finish_binding',None)
    if binding is not None:
        from swarm_finish import call
        return call(facade,message,binding)
    if message['method'] == 'find_operation':
        return find_operation(facade,message['params'])
    if message['method'] == 'task_card':
        from smart_swarm.lab_api import wire_card
        return wire_card(facade.domain.present_card(message['params']['target']))
    result = facade.call(message)
    return job_evidence(facade,result) if message['method']=='jobs' else result


def find_operation(facade, request):
    task = request.get('target_id') or request['session_id']
    digest = facade.domain.store.revision_digest(task, request['expected_revision'])
    raw = {key:request[key] for key in ('project_id','action','idempotency_key')}
    raw.update(session_id=task,target_id=task,expected_revision=digest,arguments={key:value for key,value in request.get('arguments',{}).items() if key!='expected_native_generation'})
    result = facade.domain.store.existing(raw)
    return facade.result(result,task) if result else None


def job_evidence(facade, result):
    from hashlib import sha256
    from smart_swarm.lab_jobs import motor_eligibility
    root = facade.domain.config['data_root'].resolve()
    progress = root/'lab/corpus-progress.json'
    review = json.loads(progress.read_text()) if progress.is_file() else {}
    manifest = Path(review['motor_manifest']).resolve() if review.get('motor_manifest') else None
    result['eligibility'] = {'eligible':False,'reason':'Review admitted native motor evidence first. Ten independent train groups and separate validation are required.'}
    if manifest and manifest.is_relative_to(root) and manifest.is_file():
        try:
            result['eligibility'] = motor_eligibility(json.loads(manifest.read_text()))
        except ValueError as error:
            result['eligibility'] = {'eligible':False,'reason':str(error)}
        result['corpus_sha256'] = sha256(manifest.read_bytes()).hexdigest()
        result['review_source'] = str(progress)
    return result


def main():
    facade=HomebrainProject(settings())
    try:
        for line in sys.stdin:
            message={}
            try:
                message=json.loads(line)
                result=dispatch(facade,message)
                if message['method']=='snapshot':
                    result=enrich(facade,result)
                reply={'id':message.get('id'),'result':result}
            except Exception as error:
                reply={'id':message.get('id'),'error':{'code':type(error).__name__,'message':str(error)}}
            sys.stdout.write(json.dumps(reply,allow_nan=False)+'\n')
            sys.stdout.flush()
    finally:
        facade.close()


if __name__=='__main__':
    main()
