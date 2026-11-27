"""A single persistent peer process, using its own environment and wire contract."""
import asyncio
import json
import os
import uuid
from ..lab.handover import directory
from ..config import ROOT


class Swarm:
    def __init__(self):
        self.process = None
        self.lock = asyncio.Lock()
        self.manifest = None

    def registration(self):
        path = directory()/"smart-swarm.json"
        return json.loads(path.read_text()) if path.exists() else None

    async def start(self):
        descriptor = self.registration()
        if descriptor is None:
            raise ValueError("Smart Swarm project handover has not been published")
        if self.process and self.process.returncode is None:
            return
        argv = descriptor["entrypoint_argv"]
        if len(argv) != 3 or argv[1:] != ["-m", "smart_swarm.lab_facade"]:
            raise ValueError("Unsupported project facade entrypoint")
        env = {**os.environ, **descriptor.get("environment", {})}
        self.process = await asyncio.create_subprocess_exec(argv[0],str(ROOT/"homebrain/project_adapters/swarm_host.py"), cwd=descriptor["working_directory"],
            env=env, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL)
        self.manifest = descriptor

    async def call(self, method, params=None):
        async with self.lock:
            await self.start()
            identifier = uuid.uuid4().hex
            request = {"id": identifier, "method": method, "params": params or {}}
            self.process.stdin.write((json.dumps(request)+"\n").encode())
            await self.process.stdin.drain()
            line = await asyncio.wait_for(self.process.stdout.readline(), timeout=20)
            if not line:
                raise OSError("Project facade disconnected; reconcile pending operations before retrying")
            reply = json.loads(line)
            if reply.get("error"):
                raise ValueError(reply["error"]["message"])
            if reply.get("id") != identifier:
                raise OSError("Project response correlation failed")
            return reply["result"]

    async def close(self):
        if self.process and self.process.returncode is None:
            self.process.stdin.close()
            try:
                await asyncio.wait_for(self.process.wait(), 5)
            except TimeoutError:
                pass
