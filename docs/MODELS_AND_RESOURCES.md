# Local model selection and resource evidence

Homebrain uses one pinned OpenCode V2 2.4.2 runtime and one llama.cpp pool. Specialists are bounded OpenCode child sessions with server-issued identities, shared local memory and restricted MCP tools. They are not simultaneously loaded models. OpenCode's built-in delegation did not pass the local probe; the wrapper retains actual parent/child tool traces instead of accepting model-generated session IDs. OpenClaw was inspected and is not a second supervisor.

The CPU candidate is Qwen3-4B-Instruct-2507 Q4_K_M, four threads, 6144-token context, memory-mapped weights without repacking, one inference slot and no GPU layers. The quantized file is 2,497,281,120 bytes, SHA-256 `3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597`. Its acquisition is pinned to `unsloth/Qwen3-4B-Instruct-2507-GGUF` revision `a06e946bb6b655725eafa393f4a9745d460374c9`. The original smaller local model remains on disk as a fallback; retaining weights is not a claim that it passed specialist investigation quality.

The installed llama.cpp source is `15fcfc7357f8de73671d39e7d8c594e1beb3052d`. Source weights can be memory-mapped with the explicit `model_load_mode` profile setting. Loading mode, repacking, context and process memory matter on unified-memory Jetson hardware; file size alone is not the complete budget.

| Real local probe | Observation |
| --- | --- |
| Original smaller CPU model, long context | Timed out; not qualified |
| Original smaller model, reduced context | Read native status but attempted an unrequested operation; authorization denied it and no motion occurred |
| 4B, two CPU threads, two runner steps | Read native status, then ended without a useful answer; not qualified |
| 4B, four CPU threads, four runner steps | Native next-step inquiry passed: first provider delta 54.91 s, first natural-language delta 83.67 s, complete answer 105.9 s |
| Direct 4B provider diagnostic | Correctly interpreted an actual tool result in 36.36 s; this is not a full agent test |
| Initial rejection inquiry | Actual specialist read the selected hardware receipt; excessive unscoped retrieval caused a provider timeout. Retained as a failed measurement |
| 4B memory-mapped weights, real delegation | Specialist read the actual native receipt, saved dataset configuration and source file; correct operator-rejection answer. First parent answer 369.47 s, complete 393.77 s, minimum available memory 8.36 GiB, maximum model RSS 5.28 GiB. This probe read the source header and did not qualify validation-body grounding. |
| 4B no-repack, undersized 4096 context | Actual native tool evidence exceeded the context budget; failed. The final candidate uses 6144 tokens and preserves Unicode source text without escape expansion. |
| Broad validator inquiry | Failed answer quality: the model inferred a calibration failure from current predicates without historical evidence, then timed out after 857 s. Source selection now follows the selected receipt reason and explicitly separates operator disposition from technical failure. |
| Final 4B CPU4, 6144 context, no repacking | Actual selected receipt + saved configuration + native quarantine procedure read by a real delegated specialist. Correct operator-rejection finding, no inferred calibration fault. First provider delta 126.52 s from request, first parent natural-language text 639.51 s, complete 665.51 s; minimum available memory 9.97 GiB, maximum model RSS 3.26 GiB. This bounded development inquiry passed grounding; latency remains a material limitation. |
| Saved preference after service restart | Actual persisted operator language preference was retrieved, quoted correctly and attributed to its document. First text about 108 s, complete 117.97 s. No invented preference was seeded. |
| Tank current view | Hardware specialist called the actual Tank front-view reader and correctly reported no fresh Tank frame. No SO101 image was substituted; complete answer 342.14 s. This is an availability result, not verification of a working Tank camera. |
| Did the selected episode save? | Actual selected receipt read afresh: raw hardware episode retained in quarantine, superseded by operator, admission not established; saved wrist-only configuration preserved. Complete answer 168.63 s. |
| Resource-interrupted inquiry | The existing governor unloaded inference during competing work; not counted as successful investigation or concurrency qualification |

The transport now streams real provider text, returns partial scoped specialist evidence on failure, caps retries, and distinguishes empty answers from successful answers. Dataset investigation retrieves the selected native configuration and searches the relevant native source tree. English Piper synthesis was exercised on Homebrain: a real 6.23-second, 22,050 Hz WAV was generated in 1.77 seconds using two CPU threads. Speaker playback and spoken-reference ASR accuracy remain attended checks.

Exact operator commands use the same typed task operations and bypass inference; STOP bypasses the assistant queue.

## Workload policy

Idle, Recording and Training are derived from authoritative Studio/Explorer controller, writer and job states. The existing 8 GiB available-memory reservation is retained. Optional work backs off first. A model server can unload and recover; no robot movement or recording resumes automatically.

Recording-time inference remains gated until an attended native comparison qualifies it. The installation did not perform physical motion or a new physical demonstration. Idle tool quality, native camera preview, fake-agent writers and MCAP replay do not establish recording quality under AI load.

The attended comparison must use the native recorder's actual profile and integrity requirements, with a baseline and assistant-load attempt. Compare raw frame periods/gaps, camera age/reuse/drop counters, camera pair skew, state-to-action delay, writer backlog, controller watchdog/STOP, available unified memory, disk I/O and thermal behavior. Retain native receipts and source/configuration identity. Record numerical budgets from that profile and baseline before enabling a recording-time conversational profile. Status and direct controls remain independent of inference throughout.

## References

[Qwen model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507), [pinned quantization repository](https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF), [OpenCode agents](https://opencode.ai/docs/agents/), [OpenCode MCP](https://opencode.ai/docs/mcp-servers/). Exact installed package manifests take precedence over examples for a different OpenCode generation.
