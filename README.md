# Homebrain Dataset Machine

**A local AI workstation for guided robotics dataset collection.**

Homebrain Dataset Machine helps an operator prepare a recording, follow the approved demonstration procedure, and check whether the native recorder actually saved and admitted the episode. It combines local language models, English voice interaction, a laboratory camera, project documentation, and read-only project adapters.

The application is independent from the robot projects it assists. SO101 Studio and other native applications remain responsible for raw recording, motor control, labels, calibration, and STOP. Homebrain adds an operator and verification layer; stopping it does not stop those applications.

## The problem it solves

Recording a useful robotics dataset involves more than pressing Record. The operator needs to know:

- Which approved demonstration comes next and why it is needed.
- Which native dataset to select and what equipment must be ready.
- Whether the camera view is fresh and whether moving the camera invalidated geometry.
- Whether an episode was saved, validated, rejected, or admitted for motor training.
- Whether a failed manipulation is still useful evidence without being labeled a successful motor demonstration.

Homebrain connects these questions to the project's actual cards, manifests and receipts. It does not create a competing recording plan or infer successful recording from a chat message.

## The collection workflow

```text
Approved project card and native status
                 ↓
      Readiness and attended preflight
                 ↓
  One physical instruction at a time
                 ↓
   Operator records in the native app
                 ↓
  Read saved episode + admission receipt
                 ↓
Explain acceptance, rejection, or missing evidence
```

For the Smart Swarm pilot, the assistant reads the existing SO101 card, native dataset binding and admission receipt. `pause`, `resume`, `next instruction` and repeat preserve the assistant's workflow state. Native attended preflight cannot be cleared by conversational confirmation alone.

## Technologies and how they serve the goal

| Technology | What it does here | Why it helps dataset collection |
|---|---|---|
| **Python 3.12 + FastAPI + Uvicorn** | Modular local service, typed HTTP endpoints and streaming responses. | Keeps the interface and project readers in one small service on the Jetson. |
| **HTML/CSS/JavaScript** | Chat, overview preview, device indicators, voice controls and next-step panel. | Lets the operator use a Mac browser while working with the robots. |
| **llama.cpp + replaceable GGUF models** | Local inference; the measured default is Qwen3.5-2B Q4_K_M on two CPU threads. | Provides explanations without sending lab prompts to a cloud inference API and leaves the GPU available to research workloads. |
| **faster-whisper + CTranslate2 + Silero VAD** | English speech recognition, int8 CPU inference and speech filtering. | Turns bounded microphone utterances into commands and questions while reducing silence processing. |
| **Piper + ONNX Runtime** | Local English speech synthesis with browser playback. | Gives short spoken instructions without requiring the operator to read the screen. |
| **ALSA + udev + persistent USB identities** | Discovers and associates video/audio devices; tracks approved microphones across reconnection. | Avoids hard-coded device indices and separates device connection from permission to listen. |
| **OpenCV ORB + RANSAC homography** | Checks distributed reference features and detects significant viewpoint changes. | Suspends stale spatial assumptions after camera movement; brightness or blur alone is insufficient movement evidence. |
| **ArUco + PnP** | Detects markers and supports pose recovery from supplied calibration and fixed marker coordinates. | Enables traceable geometry checks when calibration exists, without inventing metric coordinates from an image. |
| **SmolVLM2 500M, on demand** | Optional image interpretation, with a matched vision projector. | Adds advisory visual descriptions without running a large VLM on every frame. Dark inputs are refused because the measured dark-scene test was unreliable. |
| **SQLite FTS5 + BGE-small ONNX** | Persistent source retrieval with paths, hashes, revisions and timestamps. | Grounds guidance in approved operator documentation and code. Full-text is the measured default; semantic fusion is available explicitly. |
| **Versioned JSON project adapters + HTTPX + Pydantic** | Declares approved paths, read-only endpoints, capabilities and typed tool arguments. | Connects existing native applications without modifying their backends or moving their datasets. |
| **Deterministic workflow + scoped specialist roles** | Maintains procedure state while sharing one model server. | Prevents a fresh recording plan being invented after each question and avoids a separate large model for every role. |
| **psutil + resource governor** | Monitors memory, native recording/training state and shared-compute lease conflicts. | Unloads only Homebrain's inference process when a primary recording or training workflow needs resources. |
| **pytest + pinned dependencies + SHA-256 asset locks** | Software regression tests and repeatable runtime/model installation. | Makes behavior and model identity auditable, including failed development probes. |
| **Loopback binding + authentication + SSH forwarding** | Restricts access to the UI, model server and laboratory media. | Allows Mac microphone/camera access through localhost without publicly exposing lab streams. |

Runtime inference and speech processing are local. Installation downloads pinned dependencies and weights; no trained weights or raw laboratory media are stored in this Git repository. See [third-party notices](THIRD_PARTY_NOTICES.md) for software and model licenses.

## Implemented in this version

- English web chat with streaming model output and grounded readers for volatile facts.
- Local ASR and TTS, push-to-talk, and an optional default-off ASR-gated “Hey, Homebrain” half-duplex loop.
- C920 video/audio discovery, microphone authorization, configurable preferred input and recovery logic.
- Shared-camera acquisition that preserves the native application's ownership and settings.
- Bounded frame buffering, timestamp checks, camera-change handling and optional calibrated marker pose.
- Read-only Smart Swarm pilot integration, plus Explorer, SO101 Studio, ROSMASTER and historical MuJoCo adapter examples.
- Persistent conversation, inspectable memory, source retrieval and citations.
- Advisory laboratory events with deduplication, cooldown and acknowledgement.
- No motor, unrestricted shell, scientific-policy export or dataset mutation tool.

## Measured status and limits

The original deployment was tested on a **Jetson Orin NX with 16 GB unified memory, Ubuntu 24.04, Python 3.12 and L4T 39.2.1**. These are deployment measurements, not minimum requirements or a claim of universal Jetson compatibility.

| Check | Actual result |
|---|---|
| Python software suite | 25 tests passed in the original deployment; rerun results for this repository are recorded with publication verification. |
| Requested English acceptance phrases | 14 live HTTP requests exercised grounded handling, with physical visibility/readiness claims kept separate. |
| Selected CPU model | Approximately 1.82 GiB peak process RSS and 8.93 median generated tokens/s on the small sequential probe. |
| Model comparison | Liquid LFM2.5, Gemma4 E2B and Qwen3.5 were measured. Hallucinations and scope errors were retained in the reports. |
| Local speech | Synthetic Piper-to-Whisper phrases tested; this does not establish physical operator speech accuracy. |
| C920 | Actual video preview and bounded mono/stereo microphone captures worked simultaneously with native previews. |
| Camera ownership | Studio already owned the C920. Its 640×480 stream was preserved; direct 720p/5-fps code awaits coordinated exclusive ownership. |
| Retrieval | Expected source document appeared in the top four for 4/5 full-text questions and 3/5 hybrid questions in a small development probe. |

Free-form model reasoning remains fallible. The application uses direct project readers for counts, native readiness, geometry validity and documented paper limits. A low training loss is not evidence of successful grasping; a saved episode is not automatically an admitted motor demonstration.

**Still awaiting physical verification:** actual spoken-English recognition accuracy, physical USB unplug/replug, camera repositioning and calibrated recovery, external microphone hot-plug, Mac browser permissions/playback, and recording a valid scientific episode under simultaneous load. Full-duplex echo handling and the requested 300–500 reviewed specialization examples are unfinished. See [acceptance results](ACCEPTANCE.md), [benchmarks](BENCHMARKS.md) and [adaptation status](evaluation/ADAPTATION.md).

The evaluation snapshots use normalized paths and device identifiers. Their measurements are historical evidence, not live status on a new installation.

## Install and run

Existing system requirements: Python 3.12, Git, CMake, a C++ compiler, NumPy/OpenCV, ALSA `arecord`, `udevadm` and `fuser`. The installer does not upgrade the OS, change drivers or modify another robotics environment.

```bash
git clone https://github.com/vladromenko/homebrain-dataset-machine.git
cd homebrain-dataset-machine
./install.sh /absolute/private/homebrain-work
```

Before using lab hardware, configure `config.local.json` with the actual persistent camera/microphone IDs. Set the approved roots and endpoint URLs in your local adapter manifests. The tracked manifests under `adapters/` use example paths under `/srv/robotics/`; they are not a promise that these paths exist on another computer. Keep host-specific adapters in the ignored `adapters.local/` directory and reference them from `config.local.json`.

```bash
./homebrain.sh start
./homebrain.sh status
./homebrain.sh unload   # stop Homebrain inference; keep the web tools available
./homebrain.sh stop
```

Open `http://localhost:8090` on the host. The private login token is created in `runtime/access-token`; no token is committed. Model files, memory, transcripts and logs remain in private local storage.

The first start can take longer than a warm request. General model answers may take tens of seconds on the tested CPU and are bounded at 60 seconds. Grounded recording/status instructions use the direct readers and responded in under a second in the final deployment probe.

### Use a Mac browser

Forward the private UI and native Studio with SSH:

```bash
ssh -N -o ExitOnForwardFailure=yes \
  -L 8090:127.0.0.1:8090 \
  -L 8020:127.0.0.1:8020 \
  USER@JETSON_HOST
```

Then open `http://localhost:8090`, sign in with the local token and grant the browser's normal microphone permission if needed. Never expose the model server or laboratory media ports publicly. The optional [Mac launcher](Mac_Homebrain.command) accepts the host, SSH user and installation directory through environment variables.

## Example operator interaction

1. Ask **“What should I record next?”**
2. Read the actual approved card and dataset binding.
3. Complete the existing project's attended preflight in its native interface.
4. Follow one instruction at a time; ask questions, pause or repeat without losing the session.
5. Record through the native application.
6. Ask **“Has my last demonstration been saved?”**
7. Check the separate validation/admission receipt before counting it as motor-training data.

No physical success or current dataset count is implied by this example. The project records remain authoritative.

## Repository map

```text
homebrain/        supervisor, tools, adapters, speech, vision, retrieval and web UI
adapters/         versioned example project manifests
scripts/          pinned installation helper
assets.lock.json  weight URLs, revisions, sizes and hashes; no weights
requirements.lock exact isolated Python dependencies
evaluation/       measured probes, failures, synthetic examples and held-out cases
tests/            software tests; no automatic robot movement
docs/             detailed operator guide
```

- [Detailed operator guide](docs/OPERATOR_GUIDE.md)
- [Acceptance and physical verification](ACCEPTANCE.md)
- [Measured benchmarks](BENCHMARKS.md)
- [Implementation research and reuse decisions](RESEARCH_REVIEW.md)
- [Third-party licenses and attribution](THIRD_PARTY_NOTICES.md)

## Verify changes

```bash
.venv/bin/python -m pytest -q
node --check homebrain/static/app.js
```

The current test boundary uses an installation's local configuration. Tests do not start native recording, change calibration or command robot motors. Keep real observations separate from synthetic development examples. The application is advisory; native controls and STOP mechanisms remain authoritative.

## License

Application source: **GPL-3.0-or-later**. Third-party components and model weights retain their own licenses. See [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
