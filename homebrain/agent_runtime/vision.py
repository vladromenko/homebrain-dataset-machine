"""Bounded optional visual interpretation, separate from all research-policy inputs."""
import time
from collections import deque
from types import SimpleNamespace
import cv2
import numpy as np
import psutil
from ..native_adapters.camera import frame


class Snapshot:
    def __init__(self, content, age):
        self.content = content
        self.frames = deque([(None,time.time()-age/1000)],maxlen=1)
        image = cv2.imdecode(np.frombuffer(content,np.uint8),cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError('Invalid native image')
        self.scene = SimpleNamespace(state={'quality':{'dark':float(image.mean())<45},
            'guidance':'Increase workspace lighting. I cannot reliably identify objects in this dark view.'})

    def status(self):
        return {'state':'Ready'}

    def jpeg(self):
        return self.content


async def inspect(runtime, arguments):
    robot,role = arguments['robot_id'],arguments['role']
    content,kind,metadata = await frame(runtime.lab.native,robot,role)
    studio = await runtime.lab.native.request('studio','/api/lab/status')
    explorer = await runtime.lab.native.request('explorer','/api/health')
    busy = studio['recording'].get('active') or studio['teleoperation'].get('active') or explorer.get('armed')
    if busy or psutil.virtual_memory().available/2**30 < runtime.config['min_available_gb']+1:
        return {**metadata,'interpretation':'Visual inference deferred by native workload or memory reservation. The authorized source view remains available.','policy_input':False}
    snapshot = Snapshot(content,metadata['age_ms'])
    interpretation = await runtime.perception.describe(snapshot,str(arguments['question'])[:800])
    return {**metadata,'interpretation':interpretation,'policy_input':False,'metric_calibration':False}
