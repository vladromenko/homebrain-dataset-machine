"""Low-memory visual inference is request driven and never a policy input."""
import asyncio
import base64
import time
from pathlib import Path
import httpx
from .process import start,model_args,stop


class Perception:
    def __init__(self, config):
        self.config = config
        self.lock = asyncio.Lock()

    async def describe(self, vision, question):
        if vision.status()["state"]!="Ready":
            return "No fresh overview observation is available."
        if vision.scene.state.get("quality",{}).get("dark"):
            return vision.scene.state["guidance"]+" I cannot reliably identify laboratory objects in this view."
        if self.lock.locked():
            return "Another visual request is running."
        async with self.lock:
            configuration = {**self.config,"model":"smolvlm","model_port":8093,"context":2048,"gpu_layers":0}
            args = model_args(configuration)+["--mmproj",str(Path(configuration["work"])/"models/smolvlm/mmproj.gguf"),"--no-mmproj-offload"]
            start("perception",["nice","-n","15"]+args,configuration)
            try:
                return await self.query(vision,question,configuration)
            finally:
                stop(configuration,"perception")

    async def query(self, vision, question, config):
        url = f'http://127.0.0.1:{config["model_port"]}'
        async with httpx.AsyncClient(timeout=70,trust_env=False) as client:
            ready,attempt = False,0
            while not ready and attempt<30:
                try:
                    ready = (await client.get(url+"/health")).status_code==200
                except httpx.HTTPError:
                    pass
                attempt += 1
                if not ready:
                    await asyncio.sleep(.5)
            if not ready:
                return "Visual inference is unavailable. Current framing metrics remain available."
            captured = vision.frames[-1][1]
            image = base64.b64encode(vision.jpeg()).decode()
            body = {"messages":[{"role":"user","content":[{"type":"text","text":"Describe the visible scene in two sentences. Be cautious about uncertainty. "+question},{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,"+image}}]}],"max_tokens":100,"temperature":0}
            response = await client.post(url+"/v1/chat/completions",json=body)
            response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"]
            return f"AI interpretation of the image captured {time.time()-captured:.1f} seconds ago: {text} Object identities and physical success require operator verification."
