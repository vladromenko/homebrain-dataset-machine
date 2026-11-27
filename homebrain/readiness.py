"""Conservative advisory readiness from native live status and attended receipts."""
from pathlib import Path


def readiness(status):
    if status["project"] not in ("smart-swarm","so101-studio"):
        return {"ready":False,"blocking_issues":["This adapter has no approved recording workflow; use its native interface"],"authority":"Project-specific native controls"}
    live = status["live"].get("data",{})
    receipt = status.get("attended",{}).get("data",{})
    reasons = []
    if status["live"].get("kind")!="live":
        reasons.append("Native Studio status is unavailable")
    if not receipt:
        reasons.append("No native attended setup and STOP receipt is available")
    if receipt and receipt.get("homebrain_boot_id")!=Path("/proc/sys/kernel/random/boot_id").read_text().strip():
        reasons.append("Attended receipt belongs to another boot")
    if live.get("recording",{}).get("active") or live.get("teleoperation",{}).get("active"):
        reasons.append("Native controls are active; follow the current native session")
    for role in ("top","wrist"):
        camera = live.get("preview",{}).get("cameras",{}).get(role,{})
        if not camera.get("connected") or camera.get("last_frame_age_ms",1e9)>1500:
            reasons.append(role+" camera has no verified fresh native preview")
    if receipt:
        after = receipt.get("after",{})
        if live.get("hardware_stop_generation",-1)<after.get("native_stop_generation",1e12):
            reasons.append("Current native STOP evidence does not match the attended receipt")
        identities = {k:v.get("resolved_path") for k,v in live.get("resources",{}).get("device_inventory",{}).items()}
        if identities!=after.get("native_device_identities"):
            reasons.append("Device identities require native revalidation")
    return {"ready":not reasons,"blocking_issues":reasons,"authority":"Native project preflight remains authoritative"}
