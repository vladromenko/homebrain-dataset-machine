"""Stable USB discovery. Discovery never grants listening permission."""
import glob
import os
import subprocess
from pathlib import Path


def properties(device):
    result = subprocess.run(["udevadm","info","--query=property","--name="+device],capture_output=True,text=True,timeout=3)
    return dict(line.split("=",1) for line in result.stdout.splitlines() if "=" in line)


def owners(device):
    result = subprocess.run(["fuser",str(Path(device).resolve())],capture_output=True,text=True,timeout=3)
    return [int(x) for x in result.stdout.split() if x.isdigit()]


def video_devices():
    result = []
    for path in sorted(glob.glob("/dev/v4l/by-id/*video-index0")):
        prop = properties(path)
        result.append({"id":path,"serial":prop.get("ID_SERIAL"),"name":prop.get("ID_MODEL"),
                       "owners":owners(path),"connected":True})
    return result


def audio_devices():
    result = []
    for path in sorted(glob.glob("/dev/snd/by-id/*")):
        prop = properties(path)
        control = Path(path).resolve().name.removeprefix("controlC")
        identity = Path("/proc/asound/card"+control+"/id")
        if identity.exists():
            card = identity.read_text().strip()
            result.append({"id":path,"serial":prop.get("ID_SERIAL"),"name":prop.get("ID_MODEL"),
                           "alsa":"plughw:CARD="+card+",DEV=0","state":"Available"})
    return result


class Microphones:
    def __init__(self, preferred, fallback):
        self.preferred, self.fallback = preferred, fallback
        self.authorized = None
        self.state = "Not connected"
        self.selected = None
        self.muted = False
        self.approved = set()

    def refresh(self, devices=None):
        devices = audio_devices() if devices is None else devices
        ranked = sorted(devices,key=lambda d: (d["id"] != self.preferred,d["id"] == self.fallback,d["id"]))
        known = next((d for d in ranked if d["id"] in (self.preferred,self.fallback)),None)
        self.selected = known
        if known and known["id"] in self.approved:
            self.authorized = known["id"]
        if self.state != "Listening":
            self.state = "Muted" if self.muted else "Ready" if known and known["id"] == self.authorized else "Permission required" if known else "Disconnected" if self.authorized else "Not connected"
        return {"devices":devices,"selected":known,"state":self.state,"authorized":bool(self.authorized)}

    def authorize(self, identity):
        device = next((d for d in audio_devices() if d["id"] == identity),None)
        if device is None:
            raise ValueError("Microphone is not available")
        self.authorized, self.selected, self.state = identity,device,"Ready"
        self.approved.add(identity)
        if identity != self.fallback:
            self.preferred = identity
        self.muted = False

    def mute(self):
        self.authorized = None
        self.approved.clear()
        self.state = "Muted"
        self.muted = True
