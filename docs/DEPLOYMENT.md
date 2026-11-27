# Deployment and rollback

The integration is one user service, `homebrain-lab.service`, bound to loopback port 8090. The Mac launcher forwards the connection and obtains a short-lived single-use POST ticket over SSH. Native Studio/Explorer services and their original data roots remain separate.

Private `config.local.json` holds persistent camera/audio identities, approved repository adapters, local model directory, runtime directory and optional viewer interpreter. Private descriptors live in `$HOMEBRAIN_LAB_HANDOVER_DIR` or `~/.local/share/homebrain-lab/handover`:

- `integration-owner.json`: shared deployment ownership and exact source revision.
- `smart-swarm.json`: peer-owned project facade and its environment.
- `homebrain-lab.json`: deployed common service and pinned allowlisted launcher operations.
- `launcher.json`: Mac packaging provenance and attended test status.

The canonical launcher schema is in `contracts/launcher-descriptor.schema.json`. A launcher operation emits one JSON object to stdout; diagnostics go to stderr. Secrets belong only in private SSH output/POST bodies/cookies, never URLs, Git or descriptors. Health captures the source commit when the process starts, rather than reporting a newer on-disk commit as already running.

## Native compatibility patches

| Owner | Audited baseline | Additive adapter branch |
| --- | --- | --- |
| Explorer | `89bba26780619ddec7355da60c7b57a006711daf` | `codex/homebrain-lab-api` in an isolated checkout |
| SO101 Studio | `5c5c8043668db08601b68f1c0fa11a0c77e3dbc2` | `codex/homebrain-lab-fence` in an isolated checkout |

`native_patches/` contains the source patches and exact adapter revisions in `versions.json`. The latest deployed adapters are Explorer `3317849` and Studio `d74597f`; their baseline repository HEADs are preserved. Preserve unrelated local modifications. Run `git apply --check` against the installed source and inspect active native controller, recorder, finalizer, fleet capture and compute-job state before applying/restarting. Do not restart an active native service. Reopen only an already-authorized preview using its native settings; never resume actuators or recording.

The station configures the individual MuJoCo viewer at port 8036 through a narrow user-service environment override; the pre-existing service at 8031 is retained. Shared-world native ports remain unchanged. Remove only this integration-owned override when rolling back that setting.

Browser leases carry captured STOP generation, operation/session/dataset binding, a short monotonic deadline and boot identity. The UI and direct voice boundary capture the native STOP generation before admission. A delayed worker cannot replace it with a fresh post-STOP generation. New Homebrain native routes are loopback-only behind the authenticated app; original native Host/Origin checks remain. Finishing an older attempt cannot overwrite the next dataset lease. Finish additionally binds the original native dataset and recording session under Studio’s existing controller lock. The Smart Swarm transport applies the same fence around its original Finish request without altering scientific decisions. A stale Finish was rejected against the actual idle native service; the synthetic regression also covers a replacement owner. The independent native STOP remains outside the normal queued action path.

## Release and rollback procedure

Build/test the integration separately. Keep a known-good checkout, built frontend and private configuration snapshot. Switch the user service only after authoritative idle checks, verify `/api/health`, authenticated handoff, native read-only status and retained journal, then atomically publish the launcher descriptor. The running service and descriptor must agree on the deployed commit.

To roll back, stop only the Homebrain Lab user service, restore the previous known-good service working directory/configuration and start it. Keep the same persistent journal/memory when schema-compatible. Native services continue independently. If reverting a native adapter, wait for idle, check the exact reverse patch, revert only its files, restart only the affected native service and restore its previously authorized preview. Do not reset a dirty native repository or remove datasets.

The installed workstation keeps private baseline source backups, pre-change status and deployment receipts in the integration runtime directory. Optional agent/viewer dependencies and model weights are outside the native virtual environments. No global OS/JetPack upgrade is part of this deployment.
