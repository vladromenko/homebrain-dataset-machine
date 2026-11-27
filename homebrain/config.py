"""Explicit local configuration; no project environment imports."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load():
    path = Path(os.environ.get("HOMEBRAIN_CONFIG", ROOT / "config.local.json"))
    config = json.loads(path.read_text())
    config.setdefault("runtime",str(ROOT / "runtime"))
    Path(config["runtime"]).mkdir(mode=0o700, exist_ok=True)
    return config
