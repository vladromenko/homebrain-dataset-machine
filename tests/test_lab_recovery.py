"""Integration fault injection exercises durable intent, receipt fencing and scope."""
import asyncio
from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from homebrain.lab.service import Lab
from homebrain.lab.contracts import ActionRequest
from homebrain.native_adapters.studio import Studio


def selected(lab):
    return asyncio.run(lab.select('demonstrations', 'so101-placement'))


def test_wrong_contract_and_cross_session_scope_reject_before_effect(tmp_path):
    with pytest.raises(ValidationError):
        ActionRequest(contract_version='wrong', action='start_recording', project_id='x', expected_revision=0, idempotency_key='fixture-key')
    lab = Lab({'runtime':str(tmp_path)})
    session = selected(lab)
    request = ActionRequest(action='prepare_session', project_id='smart-swarm', session_id=session['session_id'],
        expected_revision=0, idempotency_key='scope-mismatch')
    with pytest.raises(ValueError):
        asyncio.run(lab.action(request))
    assert lab.journal.operations(session['session_id']) == []


def test_timeout_and_repeated_start_do_not_repeat_effect(tmp_path):
    lab = Lab({'runtime':str(tmp_path)})
    session = selected(lab)
    session.update(state='enabled', permitted_actions=['start_recording'])
    lab.journal.save_session(session)
    calls = []
    async def unknown(*args):
        calls.append('start')
        raise OSError('Native response lost after acceptance')
    lab.controls = SimpleNamespace(require=lambda scope: {})
    lab.studio = SimpleNamespace(start=unknown)
    async def observed(*args):
        return {'hardware_stop_generation':7}
    lab.native = SimpleNamespace(request=observed)
    request = ActionRequest(action='start_recording', project_id='demonstrations', session_id=session['session_id'],
        expected_revision=0, idempotency_key='same-start-intent')
    async def exercise():
        first = await lab.action(request)
        await asyncio.gather(*lab.workers)
        duplicate = await lab.action(request)
        snapshot = await lab.snapshot(session['session_id'])
        return first, duplicate, snapshot
    first, duplicate, snapshot = asyncio.run(exercise())
    assert first['operation_id'] == duplicate['operation_id']
    assert duplicate['status'] == 'unknown' and calls == ['start']
    assert snapshot['permitted_actions'] == ['reconcile']


def test_native_saved_receipt_cannot_bind_foreign_session(tmp_path):
    calls = []
    async def request(service, path):
        if path == '/api/lab/status':
            return {'recording':{'state':'idle','dataset_id':'ours','session_id':'ours-session'}}
        return [{'storage':'episodes','metadata':{'dataset_id':'ours','session_id':'foreign-session','status':'complete'}}]
    studio = Studio(SimpleNamespace(request=request), None)
    async def stop_owned(session):
        calls.append('stop')
    studio.stop_owned = stop_owned
    session = {'native_ids':{'dataset_id':'ours','native_session_id':'ours-session','episode_id':'ep-native'}, 'project_state':{}}
    assert asyncio.run(studio.saved(session)) is None
    assert calls == []


def test_late_old_completion_cannot_replace_new_dataset_fence(tmp_path, monkeypatch):
    from homebrain.lab.native_lease import NativeLeases
    monkeypatch.setenv('HOMEBRAIN_LAB_HANDOVER_DIR', str(tmp_path/'handover'))
    leases = NativeLeases()
    old = leases.issue('old-session', 1, 'ds_'+'a'*16)
    new = leases.issue('new-session', 2, 'ds_'+'a'*16)
    leases.complete('old-session')
    import json
    active = json.loads((leases.folder/('dataset-ds_'+'a'*16+'.json')).read_text())
    assert active['operation_id'] == new and active['operation_id'] != old


def test_stop_between_admission_and_enable_rejects_before_native_effect(tmp_path):
    from homebrain.lab.transitions import enable
    lab = Lab({'runtime':str(tmp_path)})
    session = selected(lab)
    calls = []
    async def observed(*args):
        return {'hardware_stop_generation':8,'teleoperation':{'active':False}}
    async def effect(*args):
        calls.append('enable')
    lab.native = SimpleNamespace(request=observed)
    lab.controls = SimpleNamespace(require=lambda scope:{},permit=lambda *args:'proof')
    lab.studio = SimpleNamespace(enable=effect)
    with pytest.raises(PermissionError,match='STOP generation changed'):
        asyncio.run(enable(lab,session,{'expected_native_generation':7}))
    assert calls == []


def test_unresolved_project_intent_blocks_second_side_effect(tmp_path):
    lab = Lab({'runtime':str(tmp_path)})
    session = selected(lab)
    session['project_id']='smart-swarm'
    lab.journal.save_session(session)
    first = ActionRequest(action='start_recording',project_id='smart-swarm',session_id=session['session_id'],
                          expected_revision=0,idempotency_key='first-intent')
    lab.journal.intent(first)
    second = first.model_copy(update={'idempotency_key':'second-intent'})
    result = asyncio.run(lab.action(second))
    assert result['status']=='rejected' and 'Reconcile' in result['message']


def test_idle_reconcile_preserves_unknown_effect(tmp_path):
    from homebrain.lab.recovery import reconcile_unknown
    lab = Lab({'runtime':str(tmp_path)})
    session = selected(lab)
    request = ActionRequest(action='start_recording',project_id='demonstrations',session_id=session['session_id'],
                            expected_revision=0,idempotency_key='lost-response')
    operation,_ = lab.journal.intent(request)
    lab.journal.complete(operation['id'],lab.result(operation['id'],'unknown',0))
    async def observed(*args):
        return {'recording':{'active':False},'teleoperation':{'active':False}}
    lab.native = SimpleNamespace(request=observed)
    asyncio.run(reconcile_unknown(lab,session))
    result = lab.journal.operations(session['session_id'])[0]
    assert result['status']=='unknown' and result['native_acknowledgement']['reconciled']
    assert lab.journal.unresolved()==[]


def test_mobile_readback_cannot_attach_another_operator_episode():
    from homebrain.lab.recovery import mobile_binding
    tank={'robot_id':'tank','native_ids':{'native_session_id':'our-native-session'}}
    recording,belongs=mobile_binding(tank,{'session_id':'foreign-native-session','episode_id':'foreign'})
    assert not belongs
    ros={'robot_id':'rosmaster','native_ids':{'recording_owner':'our-browser'}}
    recording,belongs=mobile_binding(ros,{'recording':{'native_owner':'foreign-browser','episode':'foreign'}})
    assert not belongs
    recording,belongs=mobile_binding(ros,{'recording':{'native_owner':'our-browser','episode':'ours'}})
    assert belongs and recording['episode']=='ours'


def test_simulation_ack_keeps_authoritative_owner_and_hardware_namespace_separate():
    from homebrain.lab.observations import simulation_native
    calls=[]
    async def request(service,path,body=None):
        calls.append((service,path,body))
        return {'ok':True} if body else {'owner':'sim-owner','paused':False}
    lab=SimpleNamespace(native=SimpleNamespace(request=request))
    result=asyncio.run(simulation_native(lab,'shared',{'command':'heartbeat','arguments':{'operator':'sim-owner'}}))
    assert result['owner']=='sim-owner' and result['domain']=='simulation'
    assert len(calls)==2 and all(path=='/api/lab/simulation/shared' for _,path,_ in calls)


def test_specialist_failure_stops_coordinator_inference_without_inventing_cause(tmp_path):
    from homebrain.agent_runtime.runtime import Runtime
    audit=[]
    runtime=Runtime({},SimpleNamespace(audit=lambda *args:audit.append(args)),None,'token')
    runtime.requests['parent']={'role':'coordinator','delegations':0,'selection':None,'sources':[],
                                 'events':asyncio.Queue(),'text':'Why rejected?'}
    async def context(*args):
        return '{}'
    async def run(*args):
        yield {'type':'tool','tool':'dataset investigation'}
        raise OSError('Native resource reservation')
    runtime.context=context
    runtime.run=run
    result=asyncio.run(runtime.delegate('parent','dataset','Investigate the selected receipt'))
    assert not result['investigation_complete']
    events=[]
    queue=runtime.requests['parent']['events']
    while not queue.empty():
        events.append(queue.get_nowait())
    assert events[-1]['type']=='runtime_error' and 'does not establish' in events[-1]['message']
    assert set(runtime.requests)=={'parent'} and audit[0][0]=='agent_delegation'


def test_ros_manual_control_keeps_unqualified_inference_out_of_recording_profile(monkeypatch):
    from homebrain.lab.workload import inspect
    async def request(service,path):
        if path.endswith('/rosmaster/status'):
            return {'armed':True,'recording':{'thread_active':False}}
        if service=='studio':
            return {'recording':{'active':False},'teleoperation':{'active':False},'jobs':[]}
        return {'armed':False,'session':{'thread_active':False},'compute_job':None}
    monkeypatch.setattr('homebrain.lab.workload.psutil.virtual_memory',lambda:SimpleNamespace(available=16*2**30))
    lab=SimpleNamespace(native=SimpleNamespace(request=request),config={'min_available_gb':8},
                        journal=SimpleNamespace(profile=lambda key:None,unresolved=lambda:[]))
    result=asyncio.run(inspect(lab))
    assert result['profile']=='Recording' and not result['inference_permitted']


def test_observed_so_success_requires_real_source_and_unassisted_native_validation():
    from homebrain.lab.progress import successful_motor
    session={'robot_id':'so101','project_state':{'technical_validation':{'state':'completed'},
             'outcome':{'label':'success','assisted':False}},'receipts':[
             {'source':'Studio','native_episode':{'source':'hardware','test_only':False}}]}
    assert successful_motor(session)
    session['project_state']['outcome']['assisted']=True
    assert not successful_motor(session)
    session['project_state']['outcome']['assisted']=False
    session['receipts'][0]['native_episode']['source']='synthetic_test'
    assert not successful_motor(session)


def test_parent_cancellation_releases_its_specialist_task():
    from homebrain.agent_runtime.runtime import Runtime
    runtime=Runtime({},None,None,'token')
    async def exercise():
        ended=asyncio.Event()
        async def specialist():
            try:
                await asyncio.Event().wait()
            finally:
                ended.set()
        task=asyncio.create_task(specialist())
        await asyncio.sleep(0)
        await runtime.cancel_children({'children':[task]})
        return task.cancelled(),ended.is_set()
    assert asyncio.run(exercise())==(True,True)


def test_replaced_studio_owner_is_not_attached_as_our_partial_receipt():
    from homebrain.lab.recovery import studio
    async def request(*args):
        return {'recording':{'dataset_id':'foreign','session_id':'foreign-session','active':True,'episode_id':'foreign-episode'},
                'teleoperation':{'active':False}}
    session={'state':'recording','native_ids':{'dataset_id':'ours','native_session_id':'our-session'},
             'project_state':{},'receipts':[]}
    asyncio.run(studio(SimpleNamespace(native=SimpleNamespace(request=request)),session))
    assert session['state']=='incomplete'
    assert session['receipts'][0]['native_recording']=={'state':'ownership_changed','session_id':'our-session'}
    assert 'episode_id' not in session['native_ids']
