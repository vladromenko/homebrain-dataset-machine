"""Fixed loopback destinations; paths never come directly from the model."""
import httpx


class Native:
    def __init__(self, studio="http://127.0.0.1:8020", explorer="http://127.0.0.1:8030"):
        self.origins = {"studio": studio, "explorer": explorer}
        self.client = httpx.AsyncClient(trust_env=False, timeout=httpx.Timeout(12, connect=2), follow_redirects=False)

    async def request(self, service, path, body=None, method=None, headers=None):
        origin = self.origins[service]
        if service == "studio" and path == "/api/status":
            path = "/api/lab/status"
        if service == 'explorer' and path == '/api/status':
            path = '/api/lab/capabilities'
        response = await self.client.request(method or ("POST" if body is not None else "GET"),
            origin + path, json=body, headers={"Origin": origin, **(headers or {})})
        if response.is_error:
            if response.status_code >= 500:
                raise OSError(f'Native {service} outcome unknown after HTTP {response.status_code}; reconcile before retrying')
            raise ValueError(f"Native {service} returned {response.status_code}: {response.text[:1200]}")
        return response.json()

    async def observed(self, service, path="/api/status"):
        try:
            return {"available": True, "data": await self.request(service, path)}
        except (httpx.HTTPError, ValueError, OSError) as error:
            return {"available": False, "error": str(error), "data": {}}

    async def frame(self, service, path):
        origin = self.origins[service]
        response = await self.client.get(origin + path, headers={"Origin": origin})
        response.raise_for_status()
        return response.content, response.headers.get("content-type", "image/jpeg")

    async def stop(self, robot):
        paths = {"so101": ("studio", "/api/teleoperation/stop"),
                 "tank": ("explorer", "/api/lab/stop"),
                 "rosmaster": ("explorer", "/api/rosmaster/stop")}
        service, path = paths[robot]
        return await self.request(service, path, {})

    async def tank_frame(self):
        status = await self.request('explorer', '/api/lab/status')
        sample = status.get('sample', {})
        image = sample.get('images', {}).get('front', {})
        age = status.get('sample_age_ms')
        age = age+image.get('age_at_agent_response_ns',0)/1e6+image.get('request_duration_ns',0)/1e6 if age is not None else None
        if status.get('robot')!='tank' or age is None or age>500 or sample.get('camera_missing'):
            raise OSError('Tank has no verified fresh front-camera frame. The SO101 view is not a substitute.')
        origin = self.origins['explorer']
        async with self.client.stream('GET', origin+'/api/live/camera.mjpg',headers={'Origin':origin}) as response:
            response.raise_for_status()
            buffer = bytearray()
            async for chunk in response.aiter_bytes():
                buffer.extend(chunk)
                start, end = buffer.find(b'\xff\xd8'), buffer.find(b'\xff\xd9')
                if start>=0 and end>start:
                    return bytes(buffer[start:end+2]), 'image/jpeg', {'age_ms':age,'sequence':image.get('sequence'),'reused':image.get('reused')}
                if len(buffer)>2_000_000:
                    raise OSError('Native preview frame exceeds the bounded reader')
        raise OSError('Native preview disconnected before a frame arrived')
