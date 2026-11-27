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


def main():
    facade=HomebrainProject(settings())
    try:
        for line in sys.stdin:
            try:
                message=json.loads(line)
                result=facade.call(message)
                if message['method']=='snapshot':
                    result=enrich(facade,result)
                reply={'id':message.get('id'),'result':result}
            except Exception as error:
                reply={'error':{'code':type(error).__name__,'message':str(error)}}
            sys.stdout.write(json.dumps(reply,allow_nan=False)+'\n')
            sys.stdout.flush()
    finally:
        facade.close()


if __name__=='__main__':
    main()
