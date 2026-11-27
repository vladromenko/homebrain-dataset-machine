"""One explicit native transition for each common action."""
from . import catalog


def state(session, name, instruction, actions):
    session.update(state=name, instruction=instruction, permitted_actions=actions)


async def transition(lab, session, request):
    handlers = {"prepare_session": prepare, "enable_control": enable, "start_recording": start,
                "finish_recording": finish, "confirm_outcome": outcome, "next_task": next_task,
                "retry_validation": validate, "reconcile": reconcile, "stop": stop, 'review_viewpoint': review_viewpoint}
    return await handlers[request.action](lab, session, request.arguments)


def card(session):
    return next(item for item in catalog.tasks() if item["task_id"] == session["task_id"])


async def prepare(lab, session, arguments):
    task = card(session)
    if session["robot_id"] == "so101":
        receipt = await lab.studio.prepare(session, task)
    else:
        from ..native_adapters.collection import prepare as prepare_collection
        receipt = await prepare_collection(lab, session, task)
    state(session, "prepared", "Check the views and motion area, then explicitly enable native control.", ["enable_control"])
    return {"prepared": True, "actuation": "none", "native": receipt}


async def enable(lab, session, arguments):
    entry = lab.controls.require(session)
    entry["owned"] = True
    if session["robot_id"] == "so101":
        observed = await lab.native.request('studio', '/api/lab/status')
        if observed['teleoperation'].get('active'):
            raise PermissionError('Native control is already active. Reconcile its owner first.')
        generation = observed['hardware_stop_generation']
        operation = lab.controls.permit(session, generation)
        receipt = await lab.studio.enable(generation, operation)
    elif session["robot_id"] == "tank":
        receipt = await tank_start(lab, session, False)
    else:
        profile = session['project_state']['native_series']['profile'].replace('_rgbd_lidar', '')
        receipt = await lab.controls.command(session, {"action": "enable", "profile": profile, "observing": True})
    state(session, "enabled", "Use the selected native control. Start recording when the scene is ready.", ["start_recording"])
    return receipt


async def tank_start(lab, session, recording):
    from ..native_adapters.collection import parameters
    entry = lab.controls.require(session)
    native = await lab.native.request("explorer", "/api/lab/status")
    session["project_state"]["previous_episode"] = native.get("last_episode_id")
    result = await lab.native.request("explorer", "/api/lab/record/start", {
        **{key: value for key, value in parameters(session).items() if key != 'collection'},
        'collection_id': session['native_ids']['collection_id'],
        "owner": entry["owner"], "record": recording, "expected_generation": native["generation"]})
    session["native_ids"]["native_session_id"] = result["session_id"]
    entry["owned"] = True
    return result


async def start(lab, session, arguments):
    geometry = lab.journal.profile('camera_geometry') or {}
    if geometry.get('requires_recheck') and geometry.get('generic_reviewed_revision') != geometry.get('revision'):
        raise ValueError('The overview camera moved. Review the reframed workspace before recording a new attempt.')
    lab.controls.require(session)
    if session["robot_id"] == "so101":
        receipt = await lab.studio.start(session, lambda status: lab.controls.record_permit(session, status, session['native_ids']['dataset_id']))
    elif session["robot_id"] == "tank":
        receipt = await tank_start(lab, session, True)
    else:
        from ..native_adapters.collection import parameters
        observed = await lab.controls.observed(session)
        session['project_state']['previous_episode'] = observed.get('recording', {}).get('episode')
        receipt = await lab.controls.command(session, {"action": "record_start", **parameters(session),
            "category": "demonstration", "observing": True})
    session["project_state"]["started_at"] = __import__("time").time()
    state(session, "starting", "Waiting for the native writer to report recording. Keep control focused.", [])
    return receipt


async def finish(lab, session, arguments):
    result = arguments.get("outcome", "aborted")
    if result not in ("success", "failure", "aborted"):
        raise ValueError("Choose success, failure or unknown/aborted")
    if session["robot_id"] == "so101":
        lab.controls.leases.finalize(session['session_id'])
        receipt = await lab.studio.finish(session)
    elif session["robot_id"] == "tank":
        owner = lab.controls.require(session)["owner"]
        receipt = await lab.native.request("explorer", "/api/lab/record/finish", {"owner": owner, "outcome": result})
    else:
        receipt = await lab.controls.command(session, {"action": "record_finish", "outcome": result})
    session["project_state"]["finish_requested"] = True
    state(session, "saving", "Saving raw evidence through the native writer. Finalization continues if this page closes.", [])
    return receipt


async def outcome(lab, session, arguments):
    label = arguments.get("outcome")
    if label not in ("success", "failure", "unknown") or not isinstance(arguments.get("assisted"), bool):
        raise ValueError("Choose an observed outcome and whether assistance was used")
    session["project_state"]["outcome"] = {"label": label, "assisted": arguments["assisted"], "source": "operator_observation"}
    state(session, "reviewed", "Raw data and your observation are retained. Native technical validation governs eligibility.", ["next_task", "retry_validation"])
    return {"observation_saved": True, "scientific_admission": "not_assessed"}


async def next_task(lab, session, arguments):
    state(session, "complete", "Attempt retained. Select the next task or repeat with a new attempt.", [])
    return {"next": "task_queue"}


async def validate(lab, session, arguments):
    if session["robot_id"] == "so101":
        result = await lab.studio.validate(session, retry=True)
        session["pending_work"] = [{"kind": "native_validation", "native_job": result}]
        state(session, "checking", "Native validation is checking the saved evidence.", [])
        return result
    raise ValueError("Explorer validates through its native collection audit; inspect the retained receipt")


async def reconcile(lab, session, arguments):
    from .recovery import reconcile_unknown
    return await reconcile_unknown(lab, session)


async def stop(lab, session, arguments):
    receipt = await lab.native.stop(session["robot_id"])
    state(session, "incomplete", "STOP requested. Partial evidence is retained; physical stop requires native confirmation.", ["reconcile"])
    return receipt


async def review_viewpoint(lab, session, arguments):
    status = lab.vision.status()
    if status['state'] != 'Ready' or status['scene'].get('quality', {}).get('dark'):
        raise ValueError('A fresh, well-lit overview is required. Reconnect the camera and illuminate the pickup, release and reference areas.')
    if arguments.get('framing_checked') is not True:
        raise ValueError('Check that the pickup, release, target and stationary references are visible')
    geometry = lab.journal.profile('camera_geometry') or {}
    lab.journal.profile('camera_geometry', {**geometry, 'generic_reviewed_revision': geometry.get('revision')})
    receipt = {'source': 'operator_framing_review', 'revision': geometry.get('revision'),
               'metric_geometry_valid': False, 'scientific_station_qualification': False}
    session['receipts'].append(receipt)
    return receipt
