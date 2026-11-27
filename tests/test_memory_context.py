"""Memory correction and device invalidation must preserve unrelated knowledge."""
from homebrain.store import Store
from homebrain.memory_context import attach, retrieve, supersede, invalidate_device
from homebrain.voice_benchmark import score


def test_restart_scope_correction_and_geometry_invalidation(tmp_path):
    path = str(tmp_path/'memory.sqlite')
    store = Store(path)
    preference = store.remember('preference', 'Use English', 'operator')
    attach(store, preference, verification='operator_confirmed', confidence=1)
    old = store.remember('project', 'Old procedure', 'receipt-old')
    attach(store, old, project='swarm', commit='old', verification='verified')
    new = store.remember('project', 'Corrected procedure', 'receipt-new')
    attach(store, new, project='swarm', commit='new', verification='verified')
    supersede(store, old, new)
    geometry = store.remember('lab', 'Camera workspace geometry', 'measured-marker')
    attach(store, geometry, device='camera-usb', dependencies={'geometry_revision':1})
    restarted = Store(path)
    assert {row['id'] for row in retrieve(restarted, 'other')} == {preference}
    assert {row['id'] for row in retrieve(restarted, 'swarm')} == {preference, new}
    assert geometry in {row['id'] for row in retrieve(restarted, 'swarm', 'camera-usb')}
    invalidate_device(restarted, 'camera-usb', 'viewpoint changed')
    assert {row['id'] for row in retrieve(restarted, 'swarm', 'camera-usb')} == {preference, new}


def test_speech_score_counts_real_errors_without_a_fake_accuracy_floor():
    assert score('check gripper calibration', 'check gripper calibration')['word_error_rate'] == 0
    assert score('check gripper calibration', '')['word_error_rate'] == 1
    assert score('check gripper calibration', 'check calibration')['word_errors'] == 1


def test_source_change_and_task_scope_expire_only_dependent_summary(tmp_path):
    from homebrain.memory_context import invalidate_source
    store = Store(str(tmp_path/'memory.sqlite'))
    procedure = store.remember('project','Validated source summary','source')
    attach(store,procedure,project='demonstrations',dependencies={
        'source_path':'/approved/validator.py','source_sha256':'old','source_commit':'same-commit','task_id':'placement'})
    preference = store.remember('preference','Use English','operator')
    attach(store,preference)
    assert procedure not in {row['id'] for row in retrieve(store,'demonstrations',task='docking')}
    assert procedure in {row['id'] for row in retrieve(store,'demonstrations',task='placement')}
    invalidate_source(store,'/approved/validator.py','same-commit','new-hash')
    assert {row['id'] for row in retrieve(store,'demonstrations',task='placement')}=={preference}
