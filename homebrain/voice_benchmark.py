"""Attended English reference tests keep recognition accuracy separate from signal presence."""
import re
import time
from pydantic import BaseModel, ConfigDict, Field
from fastapi import HTTPException

PHRASES = [
    'Homebrain, check the SO101 gripper calibration before recording the next episode.',
    'The ROSMASTER joint position and the Tank camera timestamps must stay aligned.',
    'Validate the LeRobot dataset, then inspect the MuJoCo replay and the ACT checkpoint.',
]


def score(reference, recognized):
    expected = re.findall(r'[a-z0-9]+', reference.lower())
    heard = re.findall(r'[a-z0-9]+', recognized.lower())
    previous = list(range(len(heard)+1))
    for i, word in enumerate(expected, 1):
        current = [i]
        for j, actual in enumerate(heard, 1):
            current.append(min(current[-1]+1, previous[j]+1, previous[j-1]+(word != actual)))
        previous = current
    return {'word_error_rate': previous[-1]/max(1,len(expected)), 'word_errors': previous[-1],
            'reference_words': len(expected), 'recognized_words': len(heard)}


class Trial(BaseModel):
    model_config = ConfigDict(extra='forbid')
    reference: str = Field(min_length=4, max_length=400)


def install(app, capture, audio_task, voice, microphones, store):
    @app.get('/api/lab/v1/voice/benchmark')
    def status():
        return {'phrases': PHRASES, 'latest': store.state('speech_benchmark'),
                'conditions': 'Read the selected English reference aloud during the eight-second capture.'}

    @app.post('/api/lab/v1/voice/benchmark')
    async def benchmark(body: Trial):
        if voice.enabled:
            raise HTTPException(409, 'Mute local voice mode before the attended speech test')
        started = time.monotonic()
        result = await audio_task(capture)
        report = {**score(body.reference, result['text']), 'reference': body.reference,
                  'recognized': result['text'], 'elapsed_s': time.monotonic()-started,
                  'device_id': microphones.selected['id'], 'runtime': result['runtime'],
                  'created_at': time.time(), 'scope': 'single attended utterance; no population accuracy claim'}
        store.put('speech_benchmark', report)
        return report
