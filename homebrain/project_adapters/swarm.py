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
            stderr=asyncio.subprocess.DEVNULL,limit=2_000_000)
        self.manifest = descriptor

    async def call(self, method, params=None):
        async with self.lock:
            await self.start()
            identifier = uuid.uuid4().hex
            request = {"id": identifier, "method": method, "params": params or {}}
            self.process.stdin.write((json.dumps(request)+"\n").encode())
            await self.process.stdin.drain()
            return await self.receive(identifier)

    async def receive(self, identifier):
        deadline = asyncio.get_running_loop().time()+20
        result = None
        while result is None:
            remaining = deadline-asyncio.get_running_loop().time()
            if remaining <= 0:
                raise TimeoutError('Project response unknown; reconcile the persisted request key')
            line = await asyncio.wait_for(self.process.stdout.readline(),timeout=remaining)
            if not line:
                raise OSError('Project facade disconnected; reconcile before retrying')
            reply = json.loads(line)
            if reply.get('id') == identifier:
                if reply.get('error'):
                    raise ValueError(reply['error']['message'])
                result = reply
        return result['result']

    async def close(self):
        if self.process and self.process.returncode is None:
            self.process.stdin.close()
            try:
                await asyncio.wait_for(self.process.wait(), 5)
            except TimeoutError:
                pass
