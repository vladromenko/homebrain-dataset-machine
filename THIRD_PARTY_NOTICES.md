# Attribution and licenses

Homebrain application source is GPL-3.0-or-later. The included `LICENSE` contains GPLv3. This choice accounts for the directly imported Piper GPL component. This repository does not relicense third-party components or model weights.

- llama.cpp: ggml contributors, MIT. Full source and license retained in the isolated `work/vendor/llama.cpp` checkout; pinned revision recorded in `evaluation/environment.json`.
- NVIDIA Reachy Mini Jetson Assistant: NVIDIA, Apache-2.0; inspected as an architecture/software-only configuration reference. No robot-control source is imported or launched.
- OpenCV: Apache-2.0, installed system version 4.8.0. NumPy: BSD-3-Clause.
- FastAPI: MIT. Starlette: BSD-3-Clause. Uvicorn: BSD-3-Clause. HTTPX: BSD-3-Clause. Pydantic: MIT. psutil: BSD-3-Clause.
- faster-whisper and CTranslate2: MIT; Whisper weights retain their upstream notices. Silero VAD is bundled by faster-whisper.
- Piper 1.3.0: GPL-3.0; upstream source: <https://github.com/OHF-Voice/piper1-gpl>. Its wheels include native eSpeak NG components and corresponding license materials. Preserve source availability and all notices if redistributing a packaged environment.
- Piper lessac medium: voice card and original dataset license URL retained in `licenses/Piper-lessac-MODEL_CARD.txt`. Do not infer permission to redistribute voice data beyond its actual terms.
- LFM2.5 model: Liquid AI, LFM Open License v1.0, retained in `licenses/LiquidAI-LFM.txt`. Review its revenue/commercial conditions for organizational deployments.
- Gemma4 GGUF: Google model, ggml conversion. See the downloaded license in `licenses/Gemma4.txt`.
- BGE small: BAAI, MIT; ONNX conversion by Xenova. Model card retained with its license metadata.

Runtime wheels remain installed in `.venv` with upstream `.dist-info` license files; they are excluded from Git. `requirements.lock` records the exact local Python packages. Third-party source has not been rewritten to follow Homebrain's function-length rule.
