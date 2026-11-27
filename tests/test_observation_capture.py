"""A lost native reader acknowledgement must not start a duplicate capture."""
import asyncio
from types import SimpleNamespace
from homebrain.lab.capture import Capture, start
from homebrain.lab.journal import Journal


def test_unknown_capture_is_durable_and_duplicate_never_repeats(tmp_path):
    calls=[]
    async def request(*args):
        calls.append(args)
        raise OSError('Acknowledgement lost after native acceptance')
    lab=SimpleNamespace(journal=Journal(tmp_path/'lab.sqlite'),native=SimpleNamespace(request=request))
    body=Capture(seconds=15,idempotency_key='same-capture')
    async def exercise():
        lock=asyncio.Lock()
        return await start(lab,body,lock),await start(lab,body,lock)
    first,second=asyncio.run(exercise())
    assert first==second and first['status']=='unknown' and len(calls)==1
