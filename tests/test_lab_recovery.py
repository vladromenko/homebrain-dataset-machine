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
