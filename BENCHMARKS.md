# Measured model and retrieval results

Measurements are from this Jetson on 27 November 2026. CPU percentages use one core = 100%. RSS is process memory, not an isolated GPU allocation. These are small development probes, not a statistical ranking.

| Model/profile | Peak RSS GiB | Median decode tokens/s | Median first useful token s | Decision |
|---|---:|---:|---:|---|
| liquid | 1.47 | 18.31 | 1.47 | Rejected for hallucinated hardware, scope and coordinates |
| gemma | 4.55 | 8.48 | 1.03 | Better uncertainty/tool behavior; too large for native reservation guard |
| qwen | 1.82 | 8.93 | 1.43 | Selected CPU profile, with grounded status/science fast paths |

Liquid and Gemma used the initial default repacking/mmap profile. Qwen was additionally tuned: initial peak 3.02 GiB; disabling repacking reduced memory but slowed prefill; repacking with non-mmap loading and zero prompt RAM cache retained a 1.82-GiB peak while improving prefill. Raw settings, outputs and tuning variants are retained. Comparisons include concurrent system activity, so they are deployment decisions rather than controlled speed claims.

Gemma image first-response latency was 14.51 s on an actual authorized lab image. The small SmolVLM image path completed in 13.41 s including startup, but hallucinated a door in the dark scene. Dark views are now refused for object identification. Object detection accuracy and physical event understanding remain unverified.

The 14 live acceptance prompts returned HTTP 200 with grounded handling after corrections, approximately 0.07–0.55 s in the final run. These paths read tools or enforce evidence limits. A separate actual model-generated greeting took 21.22 s including a cold/idle start and context overhead. General model answers may take tens of seconds and are bounded at 60 s.

The first paper-gap answer was wrong (it asserted no missing evidence from an incomplete excerpt). The original response is preserved in `evaluation/acceptance-before-research-fix.json`; the final route reads the current claims table directly. Model scientific judgment has not been validated generally.

Synthetic Piper-to-Whisper speech: five phrases; word error rates 0.0%, 10.0%, 16.7%, 6.2%, 7.7%. All specified robotics names appeared in the synthetic transcripts. This does not measure the C920 acoustic speech-recognition accuracy.

C920 physical acquisition: 16-kHz mono software path and negotiated 32-kHz stereo hardware path passed bounded captures. Simultaneous native video preview continued during microphone capture. In the 8-second preview continuity probe, mean top/wrist rates were 15.57/30.05 fps with maximum sampled frame ages 65.70/30.48 ms. No scientific recording was launched, so actual native recording impact remains awaiting physical verification.

Retrieval development probe: fts 4/5 expected source documents in top four, hybrid 3/5 expected source documents in top four. Full-text is the default because it performed better on this small suite. Local semantic fusion remains explicitly available with `retrieval_mode=hybrid` in the typed search tool. These source-hit checks are not answer-quality scores.
