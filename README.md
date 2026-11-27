# Homebrain Lab — robotics dataset workstation

Homebrain Lab is one local operator workspace over the existing SO101 Studio and Explorer robotics backends. It brings task selection, human control, native recording, validation, evidence review, simulation and an English assistant into the same application. It extends this repository's original independent Homebrain assistant; it is the same project.

**Operator entry:** open the Homebrain Mac icon, then use `/lab` through its authenticated SSH connection. The Homebrain service listens only at `http://127.0.0.1:8090/lab`. Opening that address on a different computer requires the launcher tunnel; the application does not expose an anonymous LAN control endpoint.

[Mac launcher download](https://github.com/vladromenko/robot-lab-menu/releases/download/v0.2.0/Homebrain_Mac_0.2.0.zip) · [Russian operator guide](docs/OPERATOR_RU.md) · [Acceptance evidence and remaining attended checks](docs/ACCEPTANCE.md) · [Deployment and rollback](docs/DEPLOYMENT.md)

## First recording

1. Open **Projects → Robot demonstrations → Place a cube in the marked box**.
2. Put the cube and box inside the **top** and **wrist** views. Keep the physical workspace clear.
3. Choose **Prepare session**. The application checks native device identities and camera freshness and creates/reuses the native development dataset.
4. At the robot, explicitly choose **Enable control** and follow the existing native leader/follower procedure. Startup and task selection do not enable motors.
5. Choose **Start recording**, perform the placement, then **Finish recording**. Raw data is saved by Studio, including source timestamps and native calibration provenance.
6. Wait for **Checking**, inspect the retained result, choose the directly observed outcome and assistance status, then **Confirm outcome → Next task**.

The same shell provides native Tank docking and ROSMASTER docking/placement tasks. Smart Swarm adds its own staged instructions, timed observations, witness cameras, decision sealing and evaluator reveal. Its facade remains the authority for allocations, scientific gates, admission and splits. Study tasks remain gated until its actual development and station qualification requirements are met.

A raw save, technical integrity, successful unassisted motor demonstration and admitted scientific story are different results. The UI and journal retain these distinctions. An interrupted attempt is retained for inspection; reconnection never resumes movement automatically.

## Technology and purpose

| Technology | Contribution to the workstation |
| --- | --- |
| React 19, TypeScript, Vite 7 | One static, typed operator application served by FastAPI; no permanent frontend development server. |
| shadcn/ui, Radix, Tailwind 4, Lucide | Consistent controls, dialogs, keyboard focus, task layout and visible STOP. |
| assistant-ui custom runtime | Embedded text and voice conversation connected to the actual local agent runtime. |
| FastAPI, Pydantic, generated JSON Schema/TypeScript | `homebrain.lab.v1` contracts shared by buttons, orchestration and permissioned tools. The frozen `robot-platform/1.0.0` scientific contract remains separate. |
| SQLite WAL | Durable UI sessions, idempotent operation intents, uncertain outcomes, event cursors, one-use launch tickets and common memory. Native services still own actuator/writer state. |
| Existing SO101 Studio and Explorer | Original controllers, leader mappings, watchdogs, STOP, LeRobot writers/exporters and validation. Additive adapters do not instantiate another recorder or hardware owner. |
| Native ROS2 / MCAP and Rerun 0.44 | Namespaced sensor observations and a locally served replay/3D viewer. RRD is a derived diagnostic view; original MCAP stays in its native store. Unknown world transforms remain unknown. |
| Existing individual/shared MuJoCo workers | Original CAD/models, simulation ownership and supported controls. Simulation namespaces and datasets remain distinct from physical robots; dynamics are not hardware calibrated. |
| OpenCode V2 2.4.2 + llama.cpp + Qwen CPU | Real local model/tool loops, bounded roles and server-issued specialist sessions sharing one model pool. Shell/edit/web permissions are denied. No cloud model is required. |
| SQLite FTS5 + incremental approved-source indexing | Revision/hash-bearing repository evidence and scoped memory retrieval; changed/deleted files update the index. Credentials and raw datasets are excluded. |
| faster-whisper tiny.en int8, VAD, Piper | Local English push-to-talk, robotics vocabulary hints and spoken responses in the Mac browser or an explicitly selected local output. Server voice mode is opt-in and half duplex. |
| Linux udev, sysfs, ALSA, V4L2 | Persistent USB video/audio identities, physical USB parent association, ownership checks, discovery, fallback input and reconnect recovery. |
| OpenCV ORB/CLAHE/RANSAC, ArUco/PnP | Conservative stationary-reference checks, exposure/focus ambiguity handling and measured-marker geometry. No metric workspace is invented from an uncalibrated image. |

Versions are pinned in [frontend/package-lock.json](frontend/package-lock.json), [requirements.lock](requirements.lock) and the optional runtime manifests. Optional inference/viewer environments are separate from the native robot environments. OpenClaw was inspected as an alternative; it is not installed as a competing Homebrain supervisor. OpenCode's native built-in delegation did not pass the bounded local-model probe; Homebrain issues actual bounded child runtime sessions instead of trusting model-invented session IDs.

## Camera and audio

The connected Logitech C920's video and microphone interfaces were associated with the same physical USB parent and serial using Linux discovery. A real eight-second ALSA capture ran while both native camera previews continued. This establishes video acquisition, microphone availability and concurrent transport, **not English speech accuracy**: no attended reference utterance was present in that capture.

C920 video is currently owned by Studio. Homebrain consumes its read-only top view and preserves the native stream configuration. Its standalone acquisition profile requests 1280×720 at 5 fps; a shared native owner's resolution remains authoritative. Higher-resolution detail capture must use an authorized owner profile, rather than silently opening another device handle or changing an active scientific recording.

Audio selection uses persistent `/dev/snd/by-id` identities and discovers the actual ALSA PCM interface. Authorized external microphones can take priority; the authorized C920 remains a fallback. A newly discovered input is visible before permission is granted. **Settings → English robotics speech test** measures word error rate against a real spoken reference, including SO101, ROSMASTER, LeRobot, MuJoCo and ACT terminology. No fabricated accuracy score is shipped.

Camera movement invalidates dependent geometry and triggers English guidance and a framing recheck. Focus breathing or insufficient stationary texture suspends geometry without asserting physical movement. The current implementation detects ArUco markers; AprilTag is discussed in [camera geometry notes](docs/CAMERA_GEOMETRY.md). Markers are optional for initial recording. Metric geometry requires actual intrinsics, marker dimensions and fixed reference coordinates.

## Ownership, recovery and resources

- Studio and Explorer remain authoritative hardware owners. Starting Homebrain does not acquire actuators. Camera ownership is never taken over during a native service restart.
- Focused browser packets extend native control leases. Chat focus/modal entry clears held inputs; blur, tab hiding, target change, gamepad loss and disconnect release owned control. There is no synthetic backend heartbeat.
- Operation intents are persisted before effects. Duplicate keys return the same operation. A lost response becomes **unknown** and requires authoritative reconciliation; Start is never blindly repeated.
- A Finish accepted by the native writer continues finalization after browser loss. Earlier connection loss follows native watchdogs and retains partial evidence.
- USB recovery reopens only the previously authorized camera identity at an idle native boundary. It does not resume recording or control.
- Idle / Recording / Training resource profiles retain the existing 8 GiB available-memory reservation. Conversational inference during physical recording remains gated until an attended recording-under-assistant-load qualification passes. Optional indexing, visual inference, replay derivation and checks yield first.
- Raw datasets remain in their native locations. Shared catalogs contain references and receipts. There is no bulk migration or new raw dataset format.

See [acceptance status](docs/ACCEPTANCE.md) for the difference between implemented paths, native read-only checks, replay/synthetic tests and physical checks still awaiting an operator.

## Source layout

```text
frontend/                    React operator workspace and assistant-ui
homebrain/lab/               common contract, journal, workflow and recovery
homebrain/native_adapters/   fixed native transports and browser control bridge
homebrain/project_adapters/  real Smart Swarm facade transport/presentation
homebrain/agent_runtime/     OpenCode adapter, scoped MCP tools and investigation
homebrain/{audio,vision,...} reused local media, memory and resource modules
contracts/                  canonical schemas and launcher descriptor schema
native_patches/             narrow tested native backend adapters
handover/                   portable descriptor examples, never credentials
```

## Development and installation

The deployed Homebrain installation is configured once with private native service/device profiles. Operators do not enter paths, ports or camera indices for each attempt. A new installation must supply its own native station profiles and model locations; workstation-specific configuration, credentials, media, model weights and runtime databases are excluded from Git.

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.lock
npm ci --prefix frontend
npm run build --prefix frontend
.venv/bin/python scripts/generate-contracts.py
.venv/bin/python -m pytest -q
node --check homebrain/static/app.js
```

Linux OpenCV/NumPy and the installed native robotics environments are prerequisites on the Jetson. Do not upgrade the OS, JetPack or native environments to install this UI. Apply only the reviewed matching-baseline native adapter patches at an idle boundary; [deployment instructions](docs/DEPLOYMENT.md) describe verification and rollback.

Homebrain Lab is independent of the scientific recording pipelines. Its assistant knowledge, voice and diagnostic derived views are operator aids, never automatic scientific-policy inputs. DogFleet source, data, environments and compute are excluded entirely.
