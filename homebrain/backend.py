"""Replaceable local inference with declared, measured capabilities."""
import asyncio
import json
import time
import httpx
import psutil


class Backend:
    def __init__(self, config):
        self.config = config
        self.lock = asyncio.Lock()
        self.capabilities = {"text":True,"vision":config["model"]=="gemma",
                             "audio_input":False,"audio_output":False,"tools":"validated_read_only"}

    def resources(self):
        memory = psutil.virtual_memory()
        return {"available_gb":round(memory.available/2**30,2),"total_gb":round(memory.total/2**30,2),
                "cpu_percent":psutil.cpu_percent(),"cpu_threads":self.config["threads"],
                "gpu_layers":self.config["gpu_layers"],"model":self.config["model"],
                "capabilities":self.capabilities,"available":memory.available>self.config["min_available_gb"]*2**30}

    async def stream(self, messages, busy=False):
        if busy or not self.resources()["available"]:
            yield "Local inference is yielding to the laboratory workload. Live read-only status and recording instructions remain available."
            return
        if self.lock.locked():
            yield "Another assistant request is running. Please retry when it finishes."
            return
        async with self.lock:
            async for token in self.generate(messages):
                yield token

    async def generate(self, messages):
        url = f'http://127.0.0.1:{self.config["model_port"]}/v1/chat/completions'
        body = {"messages":messages,"max_tokens":self.config["max_tokens"],"temperature":.2,
                "stream":True,"chat_template_kwargs":{"enable_thinking":False}}
        try:
            async with asyncio.timeout(60),httpx.AsyncClient(timeout=55,trust_env=False) as client:
                async with client.stream("POST",url,json=body) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: ") and line[6:] != "[DONE]":
                            data = json.loads(line[6:])
                            delta = data.get("choices",[{}])[0].get("delta",{}) if data.get("choices") else {}
                            yield delta.get("content") or ""
        except (httpx.HTTPError,ValueError,TimeoutError) as error:
            yield f"Local model unavailable ({type(error).__name__}). Live project tools remain available."
