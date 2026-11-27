"""One acquisition owner, bounded latest-frame buffer and recovery."""
import asyncio
import time
from collections import deque
from pathlib import Path
import cv2
import httpx
import numpy as np
from .devices import owners
from .scene import Scene


class Vision:
    def __init__(self, config):
        self.config,self.scene = config,Scene()
        self.frames = deque(maxlen=3)
        self.capture = None
        self.state = "Not connected"
        self.source = None
        self.enabled = True
        self.browser_until = 0

    def direct(self):
        if self.capture is None:
            self.capture = cv2.VideoCapture(self.config["camera_id"],cv2.CAP_V4L2)
            self.capture.set(cv2.CAP_PROP_FOURCC,cv2.VideoWriter_fourcc(*"MJPG"))
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT,720)
            self.capture.set(cv2.CAP_PROP_FPS,5)
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE,1)
        ok,image = self.capture.read()
        if not ok:
            self.close()
            raise OSError("C920 video unavailable; recovering")
        self.source = "dedicated_uvc"
        return image

    async def shared(self):
        self.close()
        async with httpx.AsyncClient(timeout=3,trust_env=False) as client:
            status = (await client.get(self.config["camera_shared_status"])).json()
            preview = status.get("preview",{}).get("cameras",{}).get("top",{})
            device = preview.get('stream', {}).get('device')
            expected = Path(self.config['camera_id'])
            if not device or not expected.exists() or Path(device).resolve() != expected.resolve():
                raise OSError('Native overview camera identity differs from the configured C920')
            age = preview.get("last_frame_age_ms")
            if age is None or age>1500 or not preview.get("connected"):
                raise OSError("Native camera has no verified fresh timestamp")
            response = await client.get(self.config["camera_shared_url"])
            response.raise_for_status()
        image = cv2.imdecode(np.frombuffer(response.content,np.uint8),cv2.IMREAD_COLOR)
        if image is None:
            raise OSError("Invalid native camera image")
        self.source = "studio_read_only"
        return image

    async def run(self):
        while self.enabled:
            try:
                if time.time()>=self.browser_until:
                    foreign = await asyncio.to_thread(owners,self.config["camera_id"])
                    import os
                    foreign = [pid for pid in foreign if pid != os.getpid()]
                    image = await self.shared() if self.config.get("camera_shared_url") or foreign else await asyncio.to_thread(self.direct)
                    self.accept(image,self.config["camera_id"])
            except (OSError,ValueError,AttributeError,cv2.error,httpx.HTTPError) as error:
                if self.state == 'Ready':
                    self.scene.invalidate('Overview stream interrupted; workspace references require recheck')
                self.state = str(error)
                self.scene.state["geometry_valid"] = False
            await asyncio.sleep(1/max(1,self.config["camera_fps"]))

    def accept(self, image, identity, timestamp=None):
        stamp = time.time() if timestamp is None else timestamp
        if image.shape[0]>1080 or image.shape[1]>1920:
            raise ValueError("Frame too large")
        self.frames.append((image,stamp))
        self.scene.observe(image,identity,stamp)
        self.state = "Ready"

    def jpeg(self):
        if not self.frames or time.time()-self.frames[-1][1]>3:
            raise OSError("No fresh overview frame")
        return cv2.imencode(".jpg",self.frames[-1][0],[cv2.IMWRITE_JPEG_QUALITY,78])[1].tobytes()

    def status(self):
        stale = not self.frames or time.time()-self.frames[-1][1]>3
        return {"state":"Stale" if stale else self.state,"source":self.source,
                "scene":{**self.scene.state,"geometry_valid":False if stale else self.scene.state["geometry_valid"]},
                "requested_dedicated_resolution":[1280,720],"shared_resolution_control":"native owner"}

    def close(self):
        if self.capture is not None:
            self.capture.release()
            self.capture = None
