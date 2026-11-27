# Homebrain AI

Independent, local, English robotics laboratory assistant. This is a deployed first version with measured limitations, not a completed claim of every requested P3 feature. See `ACCEPTANCE.md` and `evaluation/` for evidence.

## Start and stop on Homebrain

```bash
cd /srv/homebrain-dataset-machine
./homebrain.sh start
./homebrain.sh status
./homebrain.sh unload   # release only Homebrain inference; keep text tools and camera monitoring
./homebrain.sh stop
```

Web: `http://localhost:8090`. Model server: loopback `127.0.0.1:8091`, never publicly exposed. The optional visual worker uses loopback port 8093 and exits after a request. Ports 8090, 8091 and 8093 were unoccupied before installation. Existing lab ports were preserved.

Logs and private local memory are in `runtime/`; model weights are under the private work directory configured in `config.local.json`. On this host, `work/models` points to `/srv/homebrain-models`, keeping several GB off the nearly full system disk. No foreign files were removed.

## Open from the Mac

Copy `Mac_Homebrain.command` to the Mac and run it, or open this SSH tunnel:

```bash
ssh -N -o ExitOnForwardFailure=yes -L 8090:127.0.0.1:8090 -L 8020:127.0.0.1:8020 jetsonnx@JETSON_HOST
```

Then open **http://localhost:8090**. Homebrain's LAN SSH address is also `JETSON_LAN_HOST` when the Mac is on that network. SSH access and, for the 100.x address, a working authorized Tailscale connection are prerequisites. This session could not verify the actual Mac connection. Localhost forwarding provides the browser secure context required for Mac microphone/camera access without untrusted HTTPS bypasses.

Retrieve the private access token from `runtime/access-token` on Homebrain and paste it into the login form. Do not publish the token or model/media ports. `access-url.txt`, excluded from Git and mode 0600, contains a convenient local URL with a fragment token. The fragment is removed after login. Authentication uses an HttpOnly SameSite cookie; cross-origin requests are rejected.

The native Studio interface is available through the same tunnel at **http://localhost:8020**. Native recording, labels, control, calibration and STOP remain there.

## First Smart Swarm demonstration

1. Ask **“What should I record next?”** The assistant reads the actual installed card and native dataset binding.
2. The inspected current card is the SO101 **development pilot**, bound to Studio dataset `ds_0000000000000000`. This is not the complete research dataset or a new collection plan.
3. The latest pilot receipt reports zero accepted motor demonstrations. The live native episode reader returned an empty list for that binding. The attended setup/STOP receipt is absent, so Homebrain does not declare recording readiness.
4. Complete the existing project's attended preflight in its native interface. Preserve its saved calibration, camera assignments, source group, development split and STOP procedure.
5. Guidance advances one assistant step at a time. `next instruction`, `pause`, `resume` and repeat preserve session state. The preflight gate cannot be cleared by conversational confirmation alone.
6. After native recording and admission, ask whether the episode was saved. Saving and successful motor admission are separate facts. Labels and outcomes are never written by the model.

The physical lab arrangement is user-reported: SO101 on the table, Tank and ROSMASTER on the floor. No automatic workspace transfer or protocol change is made.

## Camera and microphone

The C920 video and audio interfaces share USB serial **EXAMPLE_CAMERA_SERIAL**. Persistent IDs:

```text
/dev/v4l/by-id/usb-046d_HD_Pro_Webcam_C920_EXAMPLE_CAMERA_SERIAL-video-index0
/dev/snd/by-id/usb-046d_HD_Pro_Webcam_C920_EXAMPLE_CAMERA_SERIAL-02
```

Studio already owns the C920 as its top camera. Homebrain reads the authorized `/api/frame/top` endpoint and validates Studio's capture-age report. It does not reopen the camera, change autofocus/exposure, or change Studio's resolution. The current stream is **640×480**, with approximately 15 observed frames/s despite a nominal 30-fps device setting. Homebrain samples at 2 fps. Its dedicated acquisition path requests **1280×720 at 5 fps** when the device has no other owner. Dedicated 720p and 1080p detail capture are not claimed as physically verified while Studio owns the camera.

The current image is very dark. The UI reports measured brightness and asks for more workspace lighting. It does not claim the gripper and two containers are verified. Ask **“Describe the scene”** for request-driven SmolVLM assistance when image quality permits. This small model's real dark-image test was unreliable; its interpretations are labeled unverified and are never admission or safety evidence.

ORB/RANSAC background agreement detects significant changes; poor texture, focus breathing and missing references suspend geometry. ArUco corners and optional PnP support versioned operator calibration. No metric coordinates are available without matching camera identity, resolution, intrinsics and known fixed-marker world corners. Physical camera-motion and calibrated-marker recovery still require operator testing.

The C920 microphone successfully captured 16-kHz mono PCM through ALSA conversion and native stereo PCM at the negotiated 32-kHz rate. Discovery runs without listening. Select the input and click **Authorize selected mic**, then **C920 · 8 sec** for a bounded utterance. Mute cancels capture. A new external microphone is discovered automatically; select and authorize it once to make it preferred. The previously authorized C920 can remain the fallback within the same listening session. Authorization is not restored silently after application restart.

For the Mac microphone, click **Mac push-to-talk** and grant the browser's normal permission. Click again to finish, or the 20-second bound ends capture. All transcription runs on Homebrain, not browser cloud speech recognition. Enable **Speak responses on this browser** for local Piper audio returned to the Mac. Speed, volume and interruption controls are present. Browser permissions, playback and actual operator speech accuracy await physical verification.

An optional **Hands-free C920** checkbox runs bounded half-duplex utterances after microphone authorization. Only a transcript beginning with the configured wake phrase, initially “Hey, Homebrain”, becomes a command. The same browser waits for its spoken response before recording again. This ASR-gated mode is off by default; transcript and synthetic-speech tests do not establish physical false-activation or echo performance. Full duplex remains disabled. There is no ambient recording on startup.

## Models and resource isolation

The selected conversational model is **Qwen3.5-2B Q4_K_M**, using the pinned Unsloth GGUF and the embedded llama.cpp chat template. The deployed profile uses ARM CPU inference, two threads, 4096 context, one request, no RAM prompt cache, repacking with non-mmap loading, and idle sleep after 30 seconds. Model files and hashes are recorded in `assets.lock.json` and `evaluation/models.json`.

Liquid LFM2.5 and Gemma4 E2B were tested sequentially. Liquid invented hardware status and invalid coordinates; it was rejected for those duties. Gemma handled uncertainty better but its approximately 4.55-GiB measured process peak exceeds the existing native process reservation threshold. The tuned Qwen profile measured approximately 1.82 GiB, but still made a dataset-scope mistake. Tool-grounded answers protect volatile counts, readiness, geometry and documented paper limits. General AI explanations remain fallible.

The governor reads native recording/training state and shared compute-lease conflicts, preserves an 8-GiB available-memory threshold, and unloads only Homebrain's identified model process when it must yield. It never stops a foreign process or modifies a foreign resource lock. Existing Explorer GPU ownership remains visible; Homebrain uses CPU. CUDA 13.2/SM87 source configuration was verified, but the optional CUDA build was stopped and no CUDA inference performance is claimed.

`RESEARCH_REVIEW.md` explains the bounded primary-source review and reusable components.

## Knowledge, memory and adapters

SQLite FTS5 plus local BGE-small quantized ONNX embeddings index approved Smart Swarm documents and bounded source files. Full-text is the measured default (4/5 source-document hits in the small probe); explicit hybrid semantic search scored 3/5. Source paths, content hashes, mirror revision comparisons and indexing times are retained. No credentials or unrelated project directories are indexed. DogFleet is excluded by an explicit path deny rule and was not inspected.

All eight logical specialist roles share the model backend. The registry grants read-only tools per role; there is no shell, actuation or policy-export tool. Documents, tool responses and camera-visible text cannot grant permissions. Persistent memory supports inspection, explicit writes, removal and export; operator entries remain marked unverified. No fine-tuned weights contain volatile lab state.

Adapters are versioned JSON manifests in `adapters/`. Smart Swarm has live Studio status, pilot cards/bindings, native episodes, historical admission and approved research/code retrieval. Explorer, SO101 Studio and ROSMASTER provide read-only native health integrations. MuJoCo exposes an approved historical status source and explicitly reports no live endpoint. Explorer is the reusable adapter example: another project is connected by a new manifest and configuration entry, without changing core code or the project itself.

Optional active laboratory sessions provide deduplicated, acknowledged advisory events for camera loss, viewpoint changes, dark views, native recording errors and increased pilot admission counts. They never publish into evaluated robot observations.

## Reproduce on this Jetson

Requirements already present: Python 3.12, Git, CMake, C++ compiler, system OpenCV 4.8/NumPy 1.26, ALSA `arecord`, `udevadm`, `fuser`. The installer does not change system packages, drivers or another environment.

```bash
./install.sh /absolute/private/homebrain/work-directory
./homebrain.sh start
```

The installer creates a private venv with explicit system OpenCV access, installs `requirements.lock`, verifies pinned model asset SHA-256 values, checks the pinned llama.cpp source revision and builds only the CPU server with two low-priority compilation jobs. Existing valid assets/builds are reused. Configuration paths in project manifests describe this inspected host; update them deliberately for another machine. GPU wheels are not required.

Tests: `.venv/bin/python -m pytest -q`. Measured model probes: `.venv/bin/python -m evaluation.benchmark` (this temporarily stops only Homebrain's model server and sequentially evaluates the compared families). Live request audit: `.venv/bin/python -m evaluation.acceptance`.

See `evaluation/ADAPTATION.md` for the reviewed seed and held-out cases. The requested 300–500 reviewed specialization examples, validated adaptation recipe and any LoRA experiment remain unfinished. No training or unrelated compute access was launched.
