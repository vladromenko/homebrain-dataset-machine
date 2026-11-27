"""Versioned read-only project contract with explicit file and endpoint allowlists."""
import hashlib
import json
import time
from pathlib import Path
import httpx

DENIED = ("dogfleet", "dog-fleet", ".env", "credential", "secret", "token", "id_rsa")


def approved(path, roots):
    resolved = Path(path).resolve()
    if any(word in str(resolved).lower() for word in DENIED):
        raise PermissionError("Source is outside Homebrain permissions")
    if not any(resolved.is_relative_to(Path(root).resolve()) for root in roots):
        raise PermissionError("Source is outside approved roots")
    return resolved


class Adapter:
    def __init__(self, manifest):
        if manifest["version"] != 1:
            raise ValueError("Unsupported adapter contract")
        self.spec = manifest

    def read(self, name):
        path = approved(self.spec["files"][name], self.spec["approved_roots"])
        if path.stat().st_size > 4_000_000:
            raise ValueError("Source exceeds bounded read size")
        raw = path.read_bytes()
        return {"data":json.loads(raw),"source":str(path),"mtime":path.stat().st_mtime,
                "sha256":hashlib.sha256(raw).hexdigest(),"observed_at":time.time(),"kind":"historical_record"}

    async def live(self, name):
        if name not in self.spec.get("endpoints",{}):
            raise ValueError("This adapter does not declare the requested live endpoint")
        url = self.spec["endpoints"][name]
        async with httpx.AsyncClient(timeout=4, trust_env=False) as client:
            response = await client.get(url)
            response.raise_for_status()
        data = response.json()
        if not isinstance(data,(dict,list)):
            raise ValueError("Endpoint returned invalid structured status")
        return {"data":data,"source":url,"observed_at":time.time(),"kind":"live"}

    def optional(self, name):
        try:
            return self.read(name)
        except (OSError,ValueError,KeyError) as error:
            return {"unavailable":str(error),"data":{},"kind":"unavailable"}

    async def status(self):
        try:
            live = await self.live("status")
        except (httpx.HTTPError,ValueError) as error:
            live = {"unavailable":str(error),"data":{},"kind":"unavailable"}
        return {"project":self.spec["id"],"live":live,
                "card":self.optional("card"),"progress":self.optional("progress"),
                "intake":self.optional("intake"),"binding":self.optional("binding"),"attended":self.optional("attended")}

    async def episodes(self):
        binding = self.read("binding")["data"]
        identifier = binding["dataset_id"]
        import re
        if not re.fullmatch(r"ds_[a-f0-9]{16}",identifier):
            raise ValueError("Invalid native dataset identifier")
        url = self.spec["episode_base"] + identifier + "?include_frames=false"
        async with httpx.AsyncClient(timeout=5,trust_env=False) as client:
            response = await client.get(url)
            response.raise_for_status()
        return {"data":response.json(),"source":url,"observed_at":time.time(),"kind":"live"}
