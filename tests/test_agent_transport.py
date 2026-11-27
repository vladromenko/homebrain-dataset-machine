"""Native non-English evidence stays readable inside the MCP text payload."""
import json
from homebrain.agent_runtime import mcp


def test_native_source_is_not_expanded_into_unicode_escape_sequences(monkeypatch):
    source={'text':'Quarantine сохранён и исключён из train','reason':'operator_rejected_first_episode'}
    monkeypatch.setattr(mcp,'call',lambda *args:source)
    reply=mcp.answer({'method':'tools/call','params':{'name':'receipt','arguments':{}}})
    payload=reply['content'][0]['text']
    assert json.loads(payload)==source
    assert 'сохранён' in payload and '\\u04' not in payload


def test_optional_visual_inference_yields_to_native_ros_manual_control(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from homebrain.agent_runtime import vision
    async def frame(*args):
        return b'unused-jpeg','image/jpeg',{'robot_id':'rosmaster','role':'front','age_ms':20}
    async def workload(*args):
        return {'profile':'Recording','available_gib':12,'reservation_gib':8}
    monkeypatch.setattr(vision,'frame',frame)
    monkeypatch.setattr('homebrain.lab.workload.inspect',workload)
    perception=SimpleNamespace(describe=AsyncMock())
    runtime=SimpleNamespace(lab=SimpleNamespace(native=None),perception=perception)
    result=asyncio.run(vision.inspect(runtime,{'robot_id':'rosmaster','role':'front','question':'Describe'}))
    assert 'deferred' in result['interpretation']
    perception.describe.assert_not_called()
