"""Recovered transient faults clear without accepting a changed camera geometry."""
from homebrain.events import Events
from homebrain.store import Store


def test_recovered_camera_clears_only_matching_pending_fault(tmp_path):
    store = Store(str(tmp_path/'memory.sqlite'))
    events = Events(store)
    events.emit('camera_missing','No current frame')
    events.emit('viewpoint_changed','Recheck workspace geometry')
    events.resolve('camera_missing')
    assert [event['key'] for event in events.pending()]==['viewpoint_changed']
    events.resolve('camera_missing')
    with store.db() as db:
        assert db.execute("SELECT count(*) FROM audit WHERE event='advisory_resolved'").fetchone()[0]==1
