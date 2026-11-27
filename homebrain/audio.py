"""Local CPU speech avoids contention with scientific GPU workloads."""
import io
import subprocess
import threading
import re
import wave
from pathlib import Path

TERMS = "Homebrain, LeRobot, SO101, ROSMASTER, Tank, MuJoCo, ACT, SmolVLA, calibration, gripper, dataset, checkpoint, episode, joint position."


def wake_command(text, phrase="Hey, Homebrain"):
    words = re.findall(r"[a-z0-9]+",phrase.lower())
    prefix = r"[,\s]+".join(re.escape(w) for w in words).replace("homebrain",r"home\s*brain")
    match = re.match(r"^\s*"+prefix+r"[\s,:.!-]+(.+)$",text,re.IGNORECASE) if prefix else None
    return match.group(1).strip() if match else None


class Audio:
    def __init__(self, work, wake_phrase="Hey, Homebrain"):
        self.work = Path(work)
        self.asr = None
        self.voice = None
        self.lock = threading.Lock()
        self.recording = None
        self.wake_phrase = wake_phrase

    def transcribe(self, data):
        from faster_whisper import WhisperModel
        with self.lock:
            if self.asr is None:
                self.asr = WhisperModel(str(self.work/"models/whisper-tiny.en"),device="cpu",compute_type="int8",cpu_threads=2)
            segments,info = self.asr.transcribe(io.BytesIO(data),language="en",beam_size=3,
                                              vad_filter=True,initial_prompt=TERMS,condition_on_previous_text=False)
            text = " ".join(segment.text.strip() for segment in segments)
        return {"text":text,"wake_command":wake_command(text,self.wake_phrase),"language":info.language,"runtime":"faster-whisper CPU int8","input_provenance":"caller supplied; not automatically verified"}

    def speak(self, text, speed=1.0):
        from piper import PiperVoice,SynthesisConfig
        with self.lock:
            if self.voice is None:
                self.voice = PiperVoice.load(str(self.work/"models/piper/en_US-lessac-medium.onnx"))
            output = io.BytesIO()
            with wave.open(output,"wb") as wav:
                self.voice.synthesize_wav(text[:1800],wav,syn_config=SynthesisConfig(length_scale=1/max(.65,min(speed,1.5))))
        return output.getvalue()

    def capture(self, microphone, seconds=8):
        microphone.refresh()
        if microphone.state != "Ready" or microphone.selected["id"] != microphone.authorized:
            raise PermissionError("Explicit microphone permission is required")
        microphone.state = "Listening"
        try:
            args = ["arecord","-q","-D",microphone.selected["alsa"],"-f","S16_LE","-r","16000","-c","1","-d",str(min(seconds,20)),"-t","wav","-"]
            self.recording = subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            output,error = self.recording.communicate(timeout=min(seconds,20)+3)
            if self.recording.returncode or microphone.authorized is None:
                raise OSError("Microphone disconnected or unavailable")
            return output
        finally:
            self.recording = None
            microphone.state = "Recovering"
            microphone.refresh()

    def stop_capture(self):
        if self.recording is not None and self.recording.poll() is None:
            self.recording.terminate()
