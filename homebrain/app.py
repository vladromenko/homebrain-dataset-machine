"""Private loopback web application for an authenticated SSH-forwarded browser."""
import asyncio
import json
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse
from fastapi import FastAPI,Request,HTTPException
from fastapi.responses import FileResponse,Response,StreamingResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field,ConfigDict
from .config import load,ROOT
from .store import Store
from .adapters import Adapter,approved
from .audio import Audio
from .backend import Backend
from .devices import Microphones,video_devices
from .vision import Vision
from .supervisor import Supervisor
from .tools import Registry,ToolRequest
from .events import Events
from .readiness import readiness
from .governor import Governor
from .lab.service import Lab
from .lab.api import router as lab_router
from .native_adapters.control import Controls
from .agent_runtime.runtime import Runtime
from .agent_runtime.api import install as install_agents
from .local_voice import LocalVoice

config = load()
runtime = Path(config["runtime"])
token_path = runtime/"access-token"
if not token_path.exists():
    token_path.write_text(secrets.token_urlsafe(32))
    token_path.chmod(0o600)
TOKEN = token_path.read_text().strip()
store = Store(str(runtime/"memory.sqlite"))
adapters = {a["id"]:Adapter(a) for a in [json.loads((ROOT/p).read_text()) for p in config["adapters"]]}
vision = Vision(config)
vision.scene.calibration = store.state("camera_calibration")
microphones = Microphones(store.state("microphone_preferred",config["microphone_preferred"]),config["microphone_fallback"])
audio = Audio(config["work"],config.get("wake_phrase","Hey, Homebrain"))
backend = Backend(config)
supervisor = Supervisor(adapters,store,backend,vision)
registry = Registry(adapters,store,vision)
events = Events(store)
media_lock = asyncio.Lock()
governor = Governor(config,adapters["smart-swarm"],store)
lab = Lab(config)
lab.vision = vision
governor.lab = lab
lab.controls = Controls(lab)
agent_runtime = Runtime(config,store,lab,TOKEN)
agent_runtime.perception = supervisor.perception
microphones.approved = set(store.state("microphone_approved",[]))
local_voice = LocalVoice(audio,microphones,agent_runtime,store,media_lock)
lab.memory_store = store
lab.on_selection = lambda identifier: setattr(local_voice,"selection",identifier)


def index_sources():
    from .indexing import index_root
    roots = {str(ROOT)} | {root for adapter in adapters.values() for root in adapter.spec['approved_roots']}
    peer = lab.swarm.registration()
    if peer:
        roots.add(peer['repository_path'])
    for root in roots:
        index_root(store,Path(root))


def source_revision(path, spec):
    mirror = spec.get("repository_mirror")
    if mirror:
        import subprocess
        relative = path.relative_to(spec["approved_roots"][0])
        mirrored = Path(mirror)/relative
        revision = subprocess.check_output(["git","-C",mirror,"rev-parse","HEAD"],text=True).strip()
        if mirrored.exists() and mirrored.read_bytes()==path.read_bytes():
            return revision
        return "installed snapshot differs from mirror "+revision
    return "unversioned installed snapshot; mtime="+str(path.stat().st_mtime)


@asynccontextmanager
async def lifespan(app):
    indexing = asyncio.create_task(index_when_idle())
    task = asyncio.create_task(vision.run())
    monitor = asyncio.create_task(monitor_events())
    resources = asyncio.create_task(governor.run())
    lab_recovery = asyncio.create_task(lab.recover())
    local_voice.restore()
    yield
    local_voice.shutdown()
    vision.enabled = False
    task.cancel()
    monitor.cancel()
    resources.cancel()
    indexing.cancel()
    lab_recovery.cancel()
    await lab.swarm.close()
    audio.stop_capture()
    vision.close()


async def index_when_idle():
    from .lab.workload import inspect
    while True:
        try:
            load = await inspect(lab)
            if load['profile'] == 'Idle' and load['inference_permitted'] and not agent_runtime.queue.locked():
                await asyncio.to_thread(index_sources)
        except (OSError, ValueError) as error:
            store.audit('index_deferred', {'reason': str(error)})
        await asyncio.sleep(60)


async def build_semantics(hybrid):
    try:
        await asyncio.to_thread(hybrid.index)
        store.hybrid = hybrid
    except Exception as error:
        store.audit("semantic_index_unavailable",{"error":str(error)})


async def monitor_events():
    previous = None
    admitted = None
    while True:
        status = vision.status()
        revision = status["scene"].get("revision",0)
        if store.state("active_session",False):
            if status["state"] != "Ready":
                events.emit("camera_missing","The overview camera is unavailable. Visual guidance is suspended.",1)
            if previous is not None and revision!=previous:
                from .memory_context import invalidate_device
                invalidate_device(store,config['camera_id'],'Camera viewpoint changed')
                lab.journal.profile('camera_geometry',{'requires_recheck':True,'revision':revision})
                guidance = 'The C920 viewpoint changed. '+status['scene'].get('guidance','Keep the pickup, release and fixed reference areas fully visible, then recheck the workspace.')
                events.emit('viewpoint_changed',guidance,1)
                local_voice.announce(guidance)
            if status["scene"].get("quality",{}).get("dark"):
                alert = events.emit("dark_view",status["scene"]["guidance"],2,90)
                if alert:
                    local_voice.announce(alert['text'])
            if governor.latest:
                native = governor.latest["live"].get("data",{})
                recording = native.get("recording",{})
                if recording.get("error") or recording.get("state") in ("failed","error"):
                    events.emit("recording_failed","Native Studio reports a recording failure. Check its error before another attempt.",1)
                count = governor.latest["intake"].get("data",{}).get("counts",{}).get("accepted_motor")
                if count is not None and admitted is not None and count>admitted:
                    events.emit("episode_admitted",f"The native intake receipt now reports {count} accepted motor demonstrations in its pilot scope.",2)
                admitted = count
        previous = revision
        await asyncio.sleep(3)


app = FastAPI(title="Homebrain Lab",version="0.2.0",lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)


@app.middleware("http")
async def guard(request, call_next):
    if request.url.hostname not in ("localhost","127.0.0.1","testserver"):
        return JSONResponse({"error":"Untrusted host"},403)
    origin = request.headers.get("origin")
    handoff = request.url.path == "/api/launcher/handoff" and request.method == "POST"
    if origin and origin != str(request.base_url).rstrip("/") and not (handoff and origin == "null"):
        return JSONResponse({"error":"Cross-origin request denied"},403)
    provided = request.headers.get("authorization","").removeprefix("Bearer ") or request.cookies.get("homebrain","")
    public = request.url.path in ("/","/lab","/api/login","/api/health","/api/launcher/handoff") or request.url.path.startswith(("/static/","/lab-assets/"))
    if not public and not secrets.compare_digest(provided,TOKEN):
        return JSONResponse({"error":"Authentication required"},401)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' blob: data:; media-src 'self' blob:; style-src 'self' 'unsafe-inline'; script-src 'self' 'wasm-unsafe-eval'; connect-src 'self' blob:; worker-src 'self' blob:; frame-ancestors 'none'"
    return response


class Login(BaseModel):
    token: str = Field(max_length=200)


@app.post("/api/login")
def login(body:Login):
    if not secrets.compare_digest(body.token,TOKEN):
        raise HTTPException(401,"Invalid access token")
    response = JSONResponse({"authenticated":True})
    response.set_cookie("homebrain",TOKEN,httponly=True,samesite="strict",max_age=28800)
    return response


@app.get("/")
@app.get("/lab")
def index():
    built = ROOT/"homebrain/static/lab/index.html"
    return FileResponse(built if built.exists() else ROOT/"homebrain/static/index.html")


@app.get("/api/status")
async def status(project:str="smart-swarm"):
    if project not in adapters:
        raise HTTPException(404,"Project unavailable")
    project_status = await adapters[project].status()
    return {"project":project_status,"readiness":readiness(project_status),
            "guidance":supervisor.workflow.instruction("operator",project_status["card"]["data"]),"camera":vision.status(),
            "microphones":await asyncio.to_thread(microphones.refresh),"resources":{**backend.resources(),"governor":governor.state},
            "projects":list(adapters),"roles":list(__import__('homebrain.tools',fromlist=['ROLES']).ROLES),
            "audio":{"asr":"local faster-whisper tiny.en int8","tts":"local Piper lessac medium","hands_free":"opt-in ASR-gated half-duplex; acoustic activation unverified","wake_phrase":audio.wake_phrase}}


class Chat(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1,max_length=4000)
    session: str = Field(default="operator",pattern=r"^[A-Za-z0-9_-]{1,64}$")
    project: str = "smart-swarm"


@app.post("/api/chat")
async def chat(body:Chat):
    if body.project not in adapters:
        raise HTTPException(404,"Project unavailable")
    async def events():
        async for event in agent_runtime.answer(body.text,body.session,store.state('selected_session')):
            yield json.dumps(event)+"\n"
    return StreamingResponse(events(),media_type="application/x-ndjson")


@app.post("/api/tool")
async def tool(body:ToolRequest,project:str="smart-swarm"):
    try:
        return await asyncio.wait_for(registry.call(body,project),timeout=8)
    except PermissionError as error:
        store.audit("denied_tool",body.model_dump())
        raise HTTPException(403,str(error)) from error
    except (ValueError,KeyError,OSError,TimeoutError) as error:
        raise HTTPException(409,str(error)) from error


@app.get("/api/camera.jpg")
def camera():
    try:
        return Response(vision.jpeg(),media_type="image/jpeg")
    except OSError as error:
        raise HTTPException(503,str(error)) from error


@app.post("/api/browser-frame")
async def browser_frame(request:Request):
    import cv2,numpy as np,time
    raw = await bounded_body(request,2_000_000)
    image = cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(400,"Invalid image")
    stamp = float(request.headers.get("x-captured-at",0))/1000
    if abs(time.time()-stamp)>3:
        raise HTTPException(409,"Stale browser frame")
    vision.accept(image,"authorized-browser-camera",stamp)
    vision.browser_until = time.time()+3
    vision.source = "authorized_browser"
    return vision.status()


async def bounded_body(request, limit):
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data)>limit:
            raise HTTPException(413,"Media limit exceeded")
    return bytes(data)


class Permission(BaseModel):
    device: str = Field(max_length=300)
    confirmed: bool


@app.post("/api/microphone/authorize")
def authorize_microphone(body:Permission):
    if not body.confirmed:
        raise HTTPException(403,"Explicit listening permission is required")
    microphones.authorize(body.device)
    store.put("microphone_preferred",microphones.preferred)
    store.put("microphone_approved",list(microphones.approved))
    store.audit("microphone_permission",{"device":body.device})
    return microphones.refresh()


@app.post("/api/microphone/mute")
def mute():
    local_voice.configure(False)
    store.put("microphone_approved",[])
    microphones.mute()
    audio.stop_capture()
    return {"state":"Muted"}


class Confirmation(BaseModel):
    confirmed: bool


@app.post("/api/session/active")
def active_session(body:Confirmation):
    store.put("active_session",body.confirmed)
    return {"active":body.confirmed}


@app.get("/api/events")
def pending_events():
    return events.pending()


@app.post("/api/events/{identifier}/acknowledge")
def acknowledge_event(identifier:str):
    events.acknowledge(identifier)
    return {"acknowledged":identifier}


@app.post("/api/calibration")
async def set_calibration(request:Request):
    from .geometry import calibration
    data = json.loads(await bounded_body(request,20000))
    if data.pop("confirmed",False) is not True:
        raise HTTPException(403,"Confirm calibration import")
    vision.scene.calibration = calibration(data)
    store.put("camera_calibration",vision.scene.calibration)
    vision.scene.invalidate("New operator-supplied calibration; reacquiring references")
    return {"calibration_revision":vision.scene.calibration["revision"]}


@app.post("/api/microphone/capture")
async def microphone_capture():
    try:
        return await audio_task(capture_and_transcribe)
    except (OSError,PermissionError) as error:
        raise HTTPException(409,str(error)) from error


def capture_and_transcribe():
    data = audio.capture(microphones,8)
    return audio.transcribe(data)


async def audio_task(function, *args):
    if media_lock.locked():
        raise HTTPException(429,"A voice request is already active")
    async with media_lock:
        try:
            return await asyncio.to_thread(function,*args)
        except (RuntimeError,ValueError) as error:
            raise HTTPException(400,"Local speech could not process this audio") from error


from .voice_benchmark import install as install_voice_benchmark
install_voice_benchmark(app, capture_and_transcribe, audio_task, local_voice, microphones, store)


@app.post("/api/transcribe")
async def transcribe(request:Request):
    raw = await bounded_body(request,4_000_000)
    return await audio_task(audio.transcribe,raw)


class Speech(BaseModel):
    text: str = Field(max_length=1800)
    speed: float = Field(default=1,ge=.65,le=1.5)


@app.post("/api/speak")
async def speak(body:Speech):
    data = await audio_task(audio.speak,body.text,body.speed)
    return Response(data,media_type="audio/wav")


@app.get("/api/history")
def history(session:str="operator"):
    return store.history(session)


@app.get("/api/source")
def source(path:str):
    roots = [root for adapter in adapters.values() for root in adapter.spec["approved_roots"]]
    try:
        file = approved(path,roots)
    except PermissionError as error:
        raise HTTPException(403,str(error)) from error
    with store.db() as db:
        record = db.execute("SELECT path,hash,revision,indexed FROM documents WHERE path=? LIMIT 1",(str(file),)).fetchone()
    if record is None:
        raise HTTPException(404,"Source is not in the approved knowledge index")
    return {**dict(record),"text":file.read_text(errors="replace")[:100000],"scope":"approved operator knowledge; never a scientific policy feed"}


@app.get("/api/memory")
def memories():
    return store.memories()


class Memory(BaseModel):
    scope: str = Field(pattern=r"^(lab|project|session|preference|task|decision)$")
    text: str = Field(max_length=2000)
    confirmed: bool
    project_id: str | None = None
    device_id: str | None = None
    supersedes: int | None = None


@app.post("/api/memory")
def remember(body:Memory):
    if not body.confirmed:
        raise HTTPException(403,"Confirm the memory write")
    from .memory_context import attach, supersede
    identifier = store.remember(body.scope,body.text,"operator-confirmed")
    attach(store, identifier, project=body.project_id, device=body.device_id,
           verification='operator_confirmed', confidence=1)
    if body.supersedes is not None:
        supersede(store, body.supersedes, identifier)
    return store.memories()


@app.delete("/api/memory/{identifier}")
def forget(identifier:int,confirmed:bool=False):
    if not confirmed:
        raise HTTPException(403,"Confirm memory removal")
    store.forget(identifier)
    return {"removed":identifier}


@app.get("/api/export")
def export_memory():
    return {"memory":store.memories(),"conversation":store.history("operator")}


app.mount("/static",StaticFiles(directory=ROOT/"homebrain/static"),name="static")
app.include_router(lab_router(lab,TOKEN))
install_agents(app,agent_runtime,adapters)
from .voice_api import install as install_voice
install_voice(app,local_voice)
app.mount("/lab-assets",StaticFiles(directory=ROOT/"homebrain/static/lab",check_dir=False),name="lab-assets")
