"""Safe readback and finalization recovery never repeats a motor or Start request."""
import json
from .transitions import state


async def refresh(lab, session):
    if session["project_id"] == "smart-swarm":
        await project_operations(lab, session)
    elif session["state"] in ("starting", "recording", "saving", "checking", "enabled"):
        pending=[row for row in lab.journal.unresolved() if row['session_id']==session['session_id'] and row['state']=='pending']
        if pending:
            return
        before_state={key:value for key,value in session.items() if key!='recording'}
        original = json.dumps(session, sort_keys=True)
        if session["robot_id"] == "so101":
            await studio(lab, session)
        else:
            await mobile(lab, session)
        if json.dumps(session, sort_keys=True) != original:
            previous = session["revision"]
            after_state={key:value for key,value in session.items() if key!='recording'}
            if after_state!=before_state:
                session["revision"] += 1
            lab.journal.save_session(session, previous)


async def studio(lab, session):
    observed = await lab.native.request("studio", "/api/lab/status")
    recording = observed["recording"]
    session["recording"] = recording
    if session['state']=='enabled' and not observed['teleoperation'].get('active'):
        state(session,'prepared','Native control stopped. Explicitly enable it again before another recording.',['enable_control'])
    if recording.get('session_id') == session['native_ids'].get('native_session_id') and recording.get('episode_id'):
        session['native_ids']['episode_id'] = recording['episode_id']
    if session["state"] == "starting" and recording.get("state") == "recording":
        state(session, "recording", "Perform the task with the native leader arm. Finish when the attempt ends.", ["finish_recording"])
    if session['state']=='recording' and not recording.get('active') and not session['project_state'].get('finish_requested'):
        session['receipts'].append({'source':'Studio stop/partial receipt','native_recording':recording})
        incomplete(session,'Native control or capture stopped before Finish. Partial evidence is retained; do not restart this attempt blindly.')
    if session["state"] == "saving":
        receipt = await lab.studio.saved(session)
        if receipt:
            lab.controls.leases.complete(session["session_id"])
            session["receipts"].append(receipt)
            session["native_ids"]["episode_id"] = receipt["native_episode"]["episode_id"]
            job = await lab.studio.validate(session)
            session["pending_work"] = [{"kind": "native_validation", "native_job": job}]
            if job.get("unknown"):
                state(session, "needs_review", job["message"], ["retry_validation"])
                return
            state(session, "checking", "Raw data saved. Native validation is running.", [])
    if session["state"] == "checking":
        await validation(lab, session, observed)
    if recording.get("state") in ("failed", "error"):
        incomplete(session, recording.get("error", "Native writer failed; partial evidence retained"))


async def validation(lab, session, observed):
    pending = session["pending_work"]
    if not pending:
        return
    job = pending[0]["native_job"]
    identifier = job.get("id", job.get("job_id"))
    latest = await lab.native.request('studio', '/api/lab/jobs/'+identifier) if identifier else None
    if latest and latest["state"] in ("completed", "failed", "cancelled", "stopped", "interrupted"):
        session["receipts"].append({"source": "Studio validation", "native_job": latest})
        session["pending_work"] = []
        session["project_state"]["technical_validation"] = latest
        state(session, "saved" if latest["state"] == "completed" else "needs_review",
            "Saved. Confirm only the outcome you directly observed; technical checks do not establish task success.",
            ["confirm_outcome", "retry_validation"])


async def mobile(lab, session):
    native = await lab.controls.observed(session)
    recording = native if session["robot_id"] == "tank" else native.get("recording", {})
    session["recording"] = recording
    phase = recording.get("phase")
    if session["state"] == "starting" and phase in ("recording", "following", "teleoperating", "paused"):
        state(session, "recording", "Operate only the selected robot. Finish when the attempt ends.", ["finish_recording"])
    if recording.get("error"):
        incomplete(session, recording["error"])
    if session['state'] == 'recording' and phase in ('idle', 'error') and not session['project_state'].get('finish_requested'):
        session['receipts'].append({'source': 'Explorer interrupted capture', 'native_recording': recording})
        incomplete(session, 'Native capture ended before Finish. Partial evidence is retained; reconcile before a new attempt.')
    if session["state"] == "saving" and phase in ("idle", "error"):
        identifier = recording.get("last_episode_id", recording.get("episode"))
        previous = session["project_state"].get("previous_episode")
        if identifier and identifier != previous and not recording.get("thread_active"):
            rows = await lab.native.request("explorer", "/api/lab/recordings")
            receipt = next((row for row in rows["episodes"] if row["id"] == identifier), None)
            if receipt and receipt['session'] == session['native_ids'].get('collection_id'):
                entry = lab.controls.connections.get(session['session_id'])
                if entry:
                    await lab.controls.release(session, entry)
                session["native_ids"]["episode_id"] = identifier
                session["receipts"].append({"source": "Explorer", "native_episode": receipt, "collections": rows["collections"]})
                state(session, 'checking', 'Raw data saved. Native collection readback is running.', [])
    if session['state'] == 'checking':
        from ..native_adapters.collection import validation as collection_validation
        await collection_validation(lab, session)


def incomplete(session, message):
    session["blockers"] = [str(message)]
    session["recovery"] = "Retain the native attempt, use STOP, and inspect its receipt before preparing again."
    state(session, "incomplete", str(message), ["reconcile"])


async def project_operations(lab, session):
    await project_finalize(lab, session)
    for row in lab.journal.unresolved():
        if row["session_id"] == session["session_id"] and row.get("result"):
            result = json.loads(row["result"])
            identifier = result["native_acknowledgement"].get("project_operation_id")
            if identifier:
                observed = await lab.swarm.call("operation", {"identifier": identifier})
                observed["native_acknowledgement"]["project_operation_id"] = identifier
                observed["operation_id"] = row["id"]
                lab.journal.complete(row["id"], observed)


async def project_finalize(lab, session):
    intent = lab.journal.profile('finalize:'+session['session_id'])
    if not intent or not intent.get('finish_intent'):
        return
    observed = await lab.native.request('studio', '/api/lab/status')
    recording = observed['recording']
    last = recording.get('last_episode') or {}
    if recording.get('dataset_id') != intent['dataset_id']:
        return
    if recording.get('state') in ('ready', 'stopped', 'idle') and last.get('episode_id') == intent['episode_id'] and last.get('status') == 'complete':
        acknowledgement = await lab.stop_owned(session)
        lab.controls.leases.complete(session['session_id'])
        lab.journal.profile('finalize:'+session['session_id'], {'finish_intent': False, 'saved': last, 'stop': acknowledgement})
        lab.journal.event(session['session_id'], 'project_native_saved_stopped', session['revision'], {'episode': last, 'stop': acknowledgement})


async def reconcile_unknown(lab, session):
    if session["robot_id"] == "so101":
        observed = await lab.native.request("studio", "/api/lab/status")
        session["recording"] = observed["recording"]
        active = observed["recording"].get("active") or observed["teleoperation"].get("active")
    else:
        observed = await lab.controls.observed(session)
        active = observed.get("thread_active") or observed.get("armed")
    if active:
        raise ValueError("Native activity remains. Use STOP or complete its native finish; Start will not be repeated.")
    for row in lab.journal.unresolved():
        if row["session_id"] == session["session_id"]:
            lab.journal.complete(row["id"], lab.result(row["id"], "accepted", session["revision"],
                "Native readback is idle. Original effect is not asserted; retained evidence requires review.", {"reconciled_idle": True}))
    state(session, "needs_review", "Native service is idle. Review retained evidence; select a new attempt explicitly.", ["next_task"])
    return {"native_readback": observed, "original_effect": "not_asserted"}
