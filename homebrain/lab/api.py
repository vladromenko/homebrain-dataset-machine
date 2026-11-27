"""Same authenticated boundary for buttons, speech and agent tools."""
import asyncio
import json
import subprocess
from fastapi import APIRouter, Request, HTTPException, WebSocket
from fastapi.responses import Response, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field
from .contracts import ActionRequest
from .tickets import issue, consume
from ..config import ROOT


class Selection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str
    task_id: str


class Launcher(BaseModel):
    model_config = ConfigDict(extra="forbid")
    launcher_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")


def router(lab, token):
    api = APIRouter()
    commit = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = bool(subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain', '--untracked-files=no'], text=True).strip())

    @api.get("/api/health")
    def health():
        return {"service_id": "homebrain-lab", "contract_version": "homebrain.lab.v1", "source_commit": commit, 'source_dirty': dirty, "status": "ready"}

    @api.post("/api/lab/v1/auth/ticket")
    def ticket(body: Launcher):
        return issue(lab.journal, body.launcher_id)

    @api.post("/api/launcher/handoff")
    async def handoff(request: Request):
        form = await request.form()
        try:
            consume(lab.journal, str(form.get("ticket", "")))
        except PermissionError as error:
            raise HTTPException(401, str(error)) from error
        response = RedirectResponse("/lab", status_code=303)
        response.set_cookie("homebrain", token, httponly=True, samesite="lax", max_age=28800)
        return response

    from .catalog_api import install as install_catalog
    install_catalog(api, lab)
    from .project_jobs import install as install_project_jobs
    install_project_jobs(api, lab)
    from .replay import install as install_replay
    install_replay(api, lab)
    from .observations import install
    install(api, lab)
    install_read_routes(api, lab)
    install_action_routes(api, lab, token)
    return api


def install_read_routes(api, lab):
    @api.get("/api/lab/v1/overview")
    async def overview():
        return await lab.overview()

    @api.get("/api/lab/v1/tasks")
    async def tasks(project_id: str = "demonstrations", group: str | None = None, offset: int = 0, limit: int = 50):
        return await lab.tasks(project_id, group, offset, limit)

    @api.get("/api/lab/v1/sessions/{identifier}")
    async def snapshot(identifier: str):
        return await lab.snapshot(identifier)

    @api.get("/api/lab/v1/events")
    def events(after: int = 0):
        return {"events": lab.journal.events(after), "snapshot_resync": "/api/lab/v1/overview"}

    @api.get("/api/lab/v1/operations/{identifier}")
    def operation(identifier: str):
        with lab.journal.db() as db:
            row = db.execute("SELECT state,result FROM operations WHERE id=?", (identifier,)).fetchone()
        if row is None:
            raise HTTPException(404)
        return json.loads(row["result"]) if row["result"] else {"status": row["state"]}

    @api.get("/api/lab/v1/frame/{robot}/{role}")
    async def frame(robot: str, role: str):
        from ..native_adapters.camera import frame as shared_frame
        try:
            content, content_type, metadata = await shared_frame(lab.native,robot,role)
            return Response(content,media_type=content_type,headers={'X-Frame-Age-Ms':str(metadata['age_ms']),
                'X-Frame-Robot':robot,'X-Frame-Role':role,'X-Frame-Sequence':str(metadata['sequence'])})
        except (ValueError,OSError) as error:
            raise HTTPException(503,str(error)) from error


def install_action_routes(api, lab, token):
    @api.post("/api/lab/v1/select")
    async def select(body: Selection):
        return await lab.select(body.project_id, body.task_id)

    @api.post("/api/lab/v1/actions")
    async def action(body: ActionRequest):
        try:
            return await lab.action(body)
        except (KeyError, ValueError) as error:
            raise HTTPException(409, str(error)) from error

    @api.post("/api/lab/v1/stop/{robot}")
    async def stop(robot: str):
        if robot not in ("so101", "tank", "rosmaster"):
            raise HTTPException(404)
        return await lab.emergency_stop(robot)

    @api.websocket("/api/lab/v1/control/{identifier}")
    async def control(socket: WebSocket, identifier: str):
        import secrets
        origin = socket.headers.get("origin")
        expected = str(socket.url).replace("ws://", "http://").split("/api/")[0]
        if origin != expected or not secrets.compare_digest(socket.cookies.get("homebrain", ""), token):
            await socket.close(code=4403)
            return
        await lab.controls.open(socket, await lab.snapshot(identifier))
