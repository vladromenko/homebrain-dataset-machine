"""Measure existing native camera continuity; never start a scientific recording."""
import json
import time
from pathlib import Path
import httpx


def probe(seconds=8):
    rows = []
    started = time.monotonic()
    with httpx.Client(timeout=4,trust_env=False) as client:
        while time.monotonic()-started<seconds:
            status = client.get("http://127.0.0.1:8020/api/status").json()
            rows.append({"time":time.monotonic(),"recording_active":status["recording"]["active"],
                         "cameras":{k:{"frames":v["frames_received"],"fps":v["observed_fps"],"age_ms":v["last_frame_age_ms"]} for k,v in status["preview"]["cameras"].items()}})
            time.sleep(.5)
    return {"kind":"native_live_preview_continuity","physical_scientific_recording":False,"samples":rows}


if __name__=="__main__":
    Path("evaluation/camera-impact.json").write_text(json.dumps(probe(),indent=2))
