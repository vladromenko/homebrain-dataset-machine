# Acceptance and remaining verification

27 November 2026. **Passed** below describes the stated behavior and evidence only. A conservative “unavailable” response is not a successful physical experiment.

| English request | Status | Actual observed behavior |
|---|---|---|
| What should I record next? | Passed | Reads installed SO101 development pilot card, dataset binding and pending attended preflight. |
| Show me the laboratory camera. | Passed | Authenticated current C920 preview through Studio; reports measured dark image. UI browser rendering remains unverified. |
| Can you see the gripper and both containers? | Awaiting physical verification | Refuses to confirm object identities in the current dark image. No positive visibility claim. |
| Has the camera moved? | Awaiting physical verification | Actual current view has insufficient reference evidence; reports geometry suspended. Synthetic translation detection passes. |
| Is the new camera position suitable? | Awaiting physical verification | Gives measured lighting guidance; cannot certify workspace geometry without references. |
| Which dataset should I select? | Passed | Reads `ds_0000000000000000` for the pilot and preserves its development scope. |
| Has my last demonstration been saved? | Passed | Live native episode endpoint returned no episodes for the pilot binding; does not invent a saved demonstration. |
| Why was this episode rejected? | Passed | No pilot rejection or attempt exists in the receipt; asks for a real selected episode instead of inventing a reason. A real rejection explanation awaits an episode. |
| How many accepted demonstrations do I have? | Passed | Reports the historical pilot admission receipt, with scope and provenance; does not extrapolate to the full corpus. |
| Why did ACT fail to grasp the object? | Passed | Recognizes the missing episode/checkpoint and refuses a specific physical causal claim. Detailed diagnosis awaits a linked record. |
| What evidence is still missing for my paper? | Passed | Reads the current claims table's physical, motor, selection and supervision limits. The earlier unsupported model answer is preserved as a failed development result. |
| Explain this function in the project. | Passed | Requests the unspecified function; approved source files are indexed and searchable. |
| Switch to the Explorer project. | Passed | Switch event selects the actual independent Explorer adapter. |
| Repeat the previous instruction. | Passed | Repeats persisted previous output without changing workflow state. |

Raw final HTTP results: `evaluation/acceptance-live.json`. Original failed research answer: `evaluation/acceptance-before-research-fix.json`.

| Additional test | Status | Evidence / limit |
|---|---|---|
| No microphone at startup | Passed | Simulated empty inventory; app does not open any microphone on startup. Physical C920 is present, so a physically unplugged startup remains unverified. |
| Simulated microphone connection/disconnection | Passed | Stable-ID permission, disconnection, same-device return and preferred input tests. |
| Physical C920 video/audio association | Passed | Matching udev USB serial EXAMPLE_CAMERA_SERIAL on video and audio interfaces. |
| Physical C920 microphone function | Passed | Bounded mono 16-kHz capture and native stereo capture negotiated to 32 kHz; no clipping in the initial mono probe. |
| C920 spoken-English recognition accuracy | Awaiting physical verification | No known operator-spoken reference was available. Synthetic ASR results are separate. |
| Physical USB microphone hot-plug | Awaiting physical verification | No cable disconnection or reconnection was performed. |
| New external microphone priority | Awaiting physical verification | Discovery and priority logic pass simulated events; external hardware not available. |
| Simultaneous video and authorized audio | Passed | Studio preview frames advanced during a bounded C920 audio capture. |
| Camera reconnection | Passed | Simulated acquisition failure and recovery; physical USB recovery awaits operator test. |
| Physical camera movement / new view | Awaiting physical verification | No camera was physically repositioned by the agent. |
| Missing markers | Passed | Actual scene has no verified reference markers; geometry remains unavailable. Synthetic marker detection and PnP tests pass. |
| Object movement without camera movement | Passed | Synthetic localized foreground change does not trigger global camera motion. |
| Focus and exposure changes | Passed | Synthetic blur/brightness changes do not become measured motion; scale ambiguity suspends geometry. Physical C920 autofocus test awaits verification. |
| Stale frames | Passed | Buffer age and native capture-age validation reject stale images. |
| Busy GPU / recording reservation | Passed | CPU profile selected; simulated active jobs/recording cause inference to yield. Governor reads native shared-compute lease conflicts. No foreign process is stopped. |
| Unavailable project endpoints | Passed | Explicit unavailable result; no synthetic live status. |
| Application restart | Passed | Actual owned web/model stop and restart succeeded repeatedly; memory/session persistence also tested. |
| Unauthorized tool use | Passed | Motor/shell/unknown tools and non-operator audiences denied; typed arguments reject undeclared fields. |
| Scientific observation isolation | Passed | No policy write or media injection endpoint; registry rejects evaluated-policy audience. No end-to-end scientific policy was executed. |
| Actual scientific recording under load | Awaiting physical verification | Native live-preview continuity measured; no scientific recording or motor action initiated. |
| Half-duplex push-to-talk and local speech software | Passed | Actual Piper generation, faster-whisper recognition and Silero filtering on synthetic speech files. |
| Hands-free wake phrase | Awaiting physical verification | Optional ASR-gated software mode and transcript/synthetic tests; acoustic false activation, echo and browser behavior unmeasured. |
| Mac camera/microphone/playback | Awaiting physical verification | Secure localhost forwarding route supplied; this session has no available browser-control surface. |
| First valid physical demonstration and admission | Awaiting physical verification | Native attended preflight is absent and no pilot attempt exists. |
| Pinned installer re-check | Passed | Pinned asset hashes and existing pinned CPU build verified by the installer. |
| Clean second-machine installation | Awaiting physical verification | A clean second machine was not available. |

The Python suite and JavaScript syntax check cover software paths only. `runtime/tests-final.log` records the latest test run. All project-owned functions satisfy the 40-line rule; no `break` or `continue` is present in project-owned code.

## Explicitly unfinished

- 300–500 reviewed specialization examples, model-specific validated LoRA training configuration and adaptation experiment. Twelve focused seed examples and separate held-out cases are provided; no training was run.
- Validated full-duplex/echo handling and a measured acoustic wake-word engine.
- Reliable object identity/event recognition in this dark, uncalibrated laboratory view. The request-driven small VLM remains advisory and failed a dark-image description probe.
- Dedicated 720p/high-resolution capture while C920 is assigned to Studio. The shared stream is preserved at its native owner's settings; direct 720p code is awaiting coordinated exclusive ownership.
- Live MuJoCo control/status service and richer project-specific workflows beyond the actual Smart Swarm pilot. The generic adapters accurately report their available read-only scope.
- End-to-end scientific recording, physical calibration recovery, actual operator speech accuracy and Mac UI verification.

These limits are not reported as completed features or successful physical tests.
