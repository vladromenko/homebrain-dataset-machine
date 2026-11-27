"""Typed read-only registry; there is no shell or policy write tool."""
import time
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field

ROLES = {
    "supervisor":["status","card","episodes","search"],
    "perception":["camera"],"dataset":["status","card","episodes"],
    "learning":["status","search"],"hardware":["status","camera"],
    "software":["search"],"research":["search"],"knowledge":["search"]}


class ToolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str = Field(max_length=30)
    tool: str = Field(max_length=30)
    query: str = Field(default="",max_length=500)
    audience: str = "operator"
    retrieval_mode: Literal["lexical","hybrid"] = "lexical"


class Registry:
    def __init__(self, adapters, store, vision):
        self.adapters,self.store,self.vision = adapters,store,vision

    async def call(self, request, project):
        if request.audience != "operator":
            raise PermissionError("Assistant observations cannot be exported to scientific policies")
        if request.tool not in ROLES.get(request.role,[]):
            raise PermissionError("This role does not have this tool permission")
        adapter = self.adapters[project]
        self.store.audit("tool",{"role":request.role,"tool":request.tool,"project":project,"time":time.time()})
        if request.tool == "status":
            return await adapter.status()
        if request.tool == "episodes":
            return await adapter.episodes()
        if request.tool == "card":
            return adapter.read("card")
        if request.tool == "camera":
            return self.vision.status()
        if request.tool == "search":
            return self.store.retrieve(request.query,request.retrieval_mode)
        raise PermissionError("Unavailable tool")
