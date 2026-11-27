"""Software acceptance: permissions, grounding, state and provenance."""
import asyncio
import ast
import json
from pathlib import Path
import pytest
from homebrain.adapters import Adapter,approved
from homebrain.store import Store
from homebrain.devices import Microphones
from homebrain.workflow import Workflow
from homebrain.tools import Registry,ToolRequest
from homebrain.backend import Backend
from homebrain.supervisor import busy


@pytest.fixture
def store(tmp_path):
    return Store(str(tmp_path/"memory.sqlite"))


def test_no_microphone_and_hotplug():
    mic = Microphones("external","c920")
    assert mic.refresh([])["state"]=="Not connected"
    device = {"id":"c920","alsa":"fixture"}
    assert mic.refresh([device])["state"]=="Permission required"
    mic.authorized = "c920"
    assert mic.refresh([device])["state"]=="Ready"
    assert mic.refresh([])["state"]=="Disconnected"
    assert mic.refresh([device])["state"]=="Ready"
    mic.mute()
    assert mic.authorized is None


def test_external_priority_does_not_grant_listening():
    mic = Microphones("external","c920")
    mic.authorized = "c920"
    result = mic.refresh([{"id":"c920"},{"id":"external"}])
    assert result["selected"]["id"]=="external"
    assert result["state"]=="Permission required"


def test_path_isolation(tmp_path):
    allowed = tmp_path/"project"
    allowed.mkdir()
    assert approved(allowed/"guide.md",[allowed]).is_relative_to(allowed)
    with pytest.raises(PermissionError):
        approved(allowed/"../outside",[allowed])
    with pytest.raises(PermissionError):
        approved(allowed/"DogFleet/model",[allowed])
    with pytest.raises(PermissionError):
        approved(allowed/".env",[allowed])
    (allowed/"escape").symlink_to(tmp_path)
    with pytest.raises(PermissionError):
        approved(allowed/"escape/file",[allowed])


def test_memory_survives_restart_and_has_unverified_origin(store):
    store.remember("preference","English","operator")
    again = Store(store.path)
    assert again.memories()[0]["verified"]==0
    again.forget(again.memories()[0]["id"])
    assert again.memories()==[]


def test_retrieval_provenance_and_reindex(store,tmp_path):
    source = tmp_path/"manual.md"
    source.write_text("ACT grasping failed despite optimizer loss decreasing.")
    store.index(source,"commit-123")
    result = store.search("ACT grasping")[0]
    assert result["revision"]=="commit-123" and len(result["hash"])==64
    source.write_text("SmolVLA changed")
    store.index(source,"commit-456")
    assert store.search("grasping")==[]


def test_guidance_question_preserves_state(store):
    flow = Workflow(store)
    card = {"preflight":["Verify native STOP","Verify camera identity"],"setup":["Place cube"]}
    flow.action("operator","next",card)
    assert flow.current("operator")["step"]==1
    flow.action("operator","pause",card)
    flow.action("operator","next",card)
    assert flow.current("operator")["step"]==1
    flow.action("operator","resume",card)
    flow.action("operator","next",card)
    assert flow.current("operator")["phase"]=="setup"


def test_model_cannot_call_motor_or_export_to_policy(store):
    registry = Registry({},store,None)
    with pytest.raises(PermissionError):
        asyncio.run(registry.call(ToolRequest(role="supervisor",tool="motor"),"smart-swarm"))
    with pytest.raises(PermissionError):
        asyncio.run(registry.call(ToolRequest(role="perception",tool="camera",audience="robot_policy"),"smart-swarm"))


def test_unavailable_endpoint_is_not_simulated():
    adapter = Adapter({"version":1,"id":"missing","files":{},"endpoints":{"status":"http://127.0.0.1:1/"}})
    status = asyncio.run(adapter.status())
    assert status["live"]["kind"]=="unavailable"
    assert status["live"]["data"]=={}


def test_busy_recording_and_training():
    assert busy({"live":{"data":{"recording":{"active":True}}}})
    assert busy({"live":{"data":{"jobs":[{"state":"running"}]}}})
    assert not busy({"live":{"data":{"recording":{"active":False}}}})


def test_project_source_constraints():
    for path in Path("homebrain").glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            assert not isinstance(node,(ast.Break,ast.Continue)),(path,node.lineno)
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                assert node.end_lineno-node.lineno+1<=40,(path,node.name)
