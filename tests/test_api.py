"""HTTP boundary tests avoid hardware and external project mutation."""
from fastapi.testclient import TestClient
from homebrain.app import app,TOKEN

client = TestClient(app)
AUTH = {"Authorization":"Bearer "+TOKEN}


def test_http_authentication_and_origin():
    assert client.get("/").status_code==200
    assert client.get("/api/status").status_code==401
    assert client.get("/api/status",headers={**AUTH,"Host":"evil.example"}).status_code==403
    assert client.post("/api/microphone/mute",json={},headers={**AUTH,"Origin":"https://evil.example"}).status_code==403


def test_no_motion_or_policy_export_endpoints():
    assert client.post("/api/motor",json={},headers=AUTH).status_code==404
    result = client.post("/api/tool",headers=AUTH,json={"role":"hardware","tool":"motor"})
    assert result.status_code==403
    result = client.post("/api/tool",headers=AUTH,json={"role":"perception","tool":"camera","audience":"policy"})
    assert result.status_code==403


def test_memory_write_requires_confirmation():
    result = client.post("/api/memory",headers=AUTH,json={"scope":"lab","text":"fixture","confirmed":False})
    assert result.status_code==403


def test_unknown_fields_and_invalid_calibration_denied():
    result = client.post("/api/chat",headers=AUTH,json={"text":"hello","shell":"rm"})
    assert result.status_code==422
    result = client.post("/api/calibration",headers=AUTH,json={"confirmed":False})
    assert result.status_code==403
