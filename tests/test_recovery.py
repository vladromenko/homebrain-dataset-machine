"""Deterministic recovery and resource tests; no devices are opened."""
import asyncio
import time
import cv2
import numpy as np
import pytest
from homebrain.backend import Backend
from homebrain.geometry import calibration,pose
from homebrain.events import Events
from homebrain.store import Store
from homebrain.vision import Vision


def test_calibrated_marker_pose_and_missing_reference():
    data = calibration({"camera_id":"fixture","intrinsics":[[500,0,400],[0,500,300],[0,0,1]],"resolution":[800,600],
                        "fixed_marker_world_corners":{"7":[[-.05,-.05,0],[.05,-.05,0],[.05,.05,0],[-.05,.05,0]]}})
    markers = [{"id":7,"corners":[[350,250],[450,250],[450,350],[350,350]]}]
    result = pose(data,markers,[800,600])
    assert result["geometry_valid"]
    assert abs(result["pose"]["translation_m"][2]-.5)<.001
    assert not pose(data,[],[800,600])["geometry_valid"]
    assert not pose(data,markers,[640,480])["geometry_valid"]


def test_event_deduplication_and_acknowledgement(tmp_path):
    events = Events(Store(str(tmp_path/"memory.sqlite")))
    events.emit("disconnect","Camera disconnected",1)
    events.emit("disconnect","Camera disconnected",1)
    assert len(events.pending())==1
    events.acknowledge(events.pending()[0]["id"])
    assert events.pending()==[]


def test_busy_gpu_uses_explicit_configured_cpu_fallback():
    backend = Backend({"threads":2,"gpu_layers":0,"model":"qwen","min_available_gb":0})
    assert backend.resources()["gpu_layers"]==0
    async def collect():
        return "".join([part async for part in backend.stream([],busy=True)])
    assert "yielding" in asyncio.run(collect())


def test_stale_buffer_does_not_present_live_image():
    vision = Vision({})
    vision.frames.append((np.zeros((20,20,3),np.uint8),time.time()-30))
    assert vision.status()["state"]=="Stale"
    with pytest.raises(OSError):
        vision.jpeg()


def test_camera_disconnection_and_reconnection(monkeypatch):
    vision = Vision({"camera_id":"fixture","camera_fps":2,"camera_shared_url":"http://native/frame"})
    attempts = []
    async def shared():
        attempts.append(1)
        if len(attempts)==1:
            raise OSError("fixture USB disconnect")
        vision.enabled = False
        return np.zeros((40,40,3),np.uint8)
    monkeypatch.setattr("homebrain.vision.owners",lambda device:[99999999])
    monkeypatch.setattr(vision,"shared",shared)
    asyncio.run(vision.run())
    assert len(attempts)==2 and vision.status()["state"]=="Ready"


def test_configured_native_owner_is_not_replaced_during_service_gap(monkeypatch):
    vision = Vision({'camera_id':'fixture', 'camera_fps':2, 'camera_shared_url':'http://native/frame'})
    attempts = []
    async def unavailable():
        attempts.append('shared')
        vision.enabled = False
        raise OSError('Native owner restarting')
    monkeypatch.setattr('homebrain.vision.owners', lambda device: [])
    monkeypatch.setattr(vision, 'shared', unavailable)
    monkeypatch.setattr(vision, 'direct', lambda: pytest.fail('Must never acquire native camera'))
    asyncio.run(vision.run())
    assert attempts == ['shared'] and vision.capture is None
