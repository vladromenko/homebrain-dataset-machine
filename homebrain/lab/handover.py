"""Atomic deployment and launcher descriptors contain no credentials."""
import hashlib
import json
import os
import subprocess
from pathlib import Path


def directory():
    path = Path(os.environ.get("HOMEBRAIN_LAB_HANDOVER_DIR",Path.home()/".local/share/homebrain-lab/handover"))
    path.mkdir(mode=0o700,parents=True,exist_ok=True)
    return path


def atomic(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value,indent=2))
    temporary.replace(path)


def launcher_descriptor(root, origin, deployed=False):
    script = root/"scripts/homebrain-lab-launcher"
    revision = subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
    operations = {name:{"argv":[str(script),name],"sha256":hashlib.sha256(script.read_bytes()).hexdigest(),
                        "cwd":str(root)} for name in ("start","status","handoff")}
    return {"descriptor_version":"homebrain.lab.v1","compatible_contract_version":"homebrain.lab.v1",
        "source_commit":revision,"supported_launcher_versions":["0.2.0"],"deployed":deployed,
        "repository":"https://github.com/vladromenko/homebrain-dataset-machine",
        "service":{"id":"homebrain-lab","origin":origin,"workspace_path":"/lab",
                   "health_path":"/api/health","health_expected":{"service_id":"homebrain-lab"}},
        "operations":operations,"authentication":{"method":"ssh-once-form-post-v1","operation":"handoff",
            "post_path":"/api/launcher/handoff","field":"ticket","expires_in":60,
            "resume_method":"Existing cookie and durable task selection reused. SSH issues a new one-use POST ticket after expiry."},
        "browsers":[{"bundle_id":"com.google.Chrome","viewer":"pending","gamepad":"pending","audio":"pending"}],
        "installation_instructions":"Use the saved SSH locator; start and handoff are fixed allowlisted operations. No tokens in URLs."}
