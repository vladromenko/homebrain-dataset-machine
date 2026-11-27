"""Opt-in server-side half duplex; browser presence is not required."""
import asyncio
import subprocess
import time
import uuid
from pathlib import Path
from .devices import audio_devices


def outputs():
    return [device for device in audio_devices(playback=True)]


class LocalVoice:
    def __init__(self, audio, microphones, runtime, store, media_lock):
        self.audio, self.microphones, self.runtime, self.store = audio, microphones, runtime, store
        self.media_lock = media_lock
        self.alerts = asyncio.Queue(maxsize=4)
        self.enabled = False
        self.output = None
        self.selection = None
        self.task = None
        self.state = 'Muted'
        self.error = None

    def configure(self, enabled, output=None, selection=None):
        if enabled:
            self.microphones.refresh()
            if self.microphones.state != 'Ready':
                raise PermissionError('Authorize the selected local microphone first')
            if output and not any(device['id'] == output for device in outputs()):
                raise ValueError('Selected playback device is unavailable')
        self.enabled, self.output, self.selection = enabled, output, selection
        self.store.put("local_voice_mode", {"enabled":enabled,"output":output,"selection":selection})
        if enabled and (self.task is None or self.task.done()):
            self.task = asyncio.create_task(self.run())
        if not enabled:
            self.audio.stop_capture()
            self.state = 'Muted'
        return self.status()

    def restore(self):
        saved = self.store.state('local_voice_mode', {})
        if saved.get('enabled'):
            self.enabled = True
            self.output, self.selection = saved.get('output'), saved.get('selection')
            self.task = asyncio.create_task(self.run())

    def status(self):
        return {'enabled': self.enabled, 'state': self.state, 'output': self.output,
                'error': self.error, 'mode': 'half_duplex_asr_gated_wake_phrase',
                'input': self.microphones.refresh(), 'outputs': outputs(),
                'selection': self.selection, 'browser_required': False}

    async def run(self):
        while self.enabled:
            try:
                self.state = 'Listening for wake phrase'
                async with self.media_lock:
                    data = await asyncio.to_thread(self.audio.capture, self.microphones, 6)
                    self.state = 'Transcribing'
                    transcript = await asyncio.to_thread(self.audio.transcribe, data)
                command = transcript.get('wake_command')
                if command:
                    await self.respond(command)
                if not self.alerts.empty():
                    await self.play(await self.alerts.get())
                self.error = None
            except Exception as error:
                self.error = str(error)
                self.state = 'Recovering; no motion resumes automatically'
                await asyncio.sleep(2)
        self.state = 'Muted'

    async def respond(self, command):
        self.state = 'Assistant working; microphone paused'
        answer = ''
        async for event in self.runtime.answer(command, 'operator', self.selection):
            if event['type'] == 'answer':
                answer += event['text']
        self.store.audit('local_voice_turn', {'command': command, 'selection': self.selection, 'answer': answer})
        await self.play(answer[:1800])

    async def play(self, text):
        if self.output and self.enabled:
            device = next((item for item in outputs() if item['id']==self.output),None)
            if device is None:
                raise OSError('Authorized speaker disconnected; reconnect it to resume speech output')
            async with self.media_lock:
                self.state = 'Speaking; microphone paused'
                wave = await asyncio.to_thread(self.audio.speak,text)
                await asyncio.to_thread(subprocess.run,['aplay','-q','-D',device['alsa'],'-t','wav','-'],
                                        input=wave,check=True,timeout=90)

    def announce(self, text):
        if self.enabled and not self.alerts.full():
            self.alerts.put_nowait(text)

    def shutdown(self):
        self.enabled = False
        self.audio.stop_capture()
        if self.task:
            self.task.cancel()
