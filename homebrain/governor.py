"""Yield only Homebrain-owned inference processes to native workloads."""
import asyncio
import time
from pathlib import Path
import psutil
from .process import start,stop,model_args,identity


class Governor:
    def __init__(self, config, adapter, store):
        self.config,self.adapter,self.store = config,adapter,store
        self.state = "Monitoring"
        self.latest = None

    async def run(self):
        while True:
            try:
                if not self.config.get("manage_models",True):
                    self.state = "External shared inference pool; existing resource guards retained"
                else:
                    await self.observe()
            except Exception as error:
                self.state = "Resource observation unavailable: "+type(error).__name__
            await asyncio.sleep(2)

    async def observe(self):
        from .lab.workload import inspect
        load = await inspect(self.lab)
        self.store.put('resource_profile', load)
        available = load['available_gib']
        yielding = not load['inference_permitted']
        self.state = load['profile']+' · '+load['qualification']
        disabled = (Path(self.config["runtime"])/"model-disabled").exists()
        process = identity(Path(self.config["runtime"])/"model.json")
        if yielding and process:
            await asyncio.to_thread(stop,self.config,'perception')
            await asyncio.to_thread(stop,self.config,"model")
            self.state = "Yielding to native recording, training or memory reservation"
        if not yielding and not disabled and not process and available>self.config["min_available_gb"]+1.5:
            args = model_args(self.config)
            if Path(args[0]).exists():
                start("model",["nice","-n","15"]+args,self.config)
                self.state = "Local CPU fallback available"
