"""Durable UI envelopes; native and project authorities retain their own state."""
import asyncio
import json
import time
import uuid
import httpx
from .contracts import SessionSnapshot, ActionResult
from .journal import Journal, Conflict
from . import catalog
from .fencing import decorate, expected, project_request
from ..native_adapters.http import Native
from ..native_adapters.studio import Studio
from ..project_adapters.swarm import Swarm


class Lab:
    def __init__(self, config):
        self.config = config
        self.journal = Journal(config["runtime"]+"/lab.sqlite")
        self.native = Native()
        self.studio = Studio(self.native, self.journal)
        self.studio.stop_owned = self.stop_owned
        self.swarm = Swarm()
        self.controls = None
        self.locks = {}
        self.workers = set()

    async def overview(self):
        studio, explorer = await asyncio.gather(self.native.observed("studio"), self.native.observed("explorer"))
        projects = [catalog.descriptor()]
        registration = self.swarm.registration()
        if registration:
            try:
                projects.append(await self.swarm.call("descriptor"))
            except (OSError, ValueError, TimeoutError) as error:
                registration = {**registration, 'unavailable': str(error)}
        return {"contract_version": "homebrain.lab.v1", "projects": projects,
            "robots": catalog.capabilities(studio["data"], explorer["data"]),
            "sessions": self.journal.sessions(), "native": {"studio": studio, "explorer": explorer},
            "project_handover": {"smart_swarm": bool(registration), 'error': (registration or {}).get('unavailable')},
            'camera_geometry': self.journal.profile('camera_geometry') or {},
            "qualification": self.journal.profile("concurrency") or {"status": "pending_attended_native_recording"}}

    async def tasks(self, project, group=None, offset=0, limit=50):
        if project == "demonstrations":
            cards = catalog.tasks()
            return {"tasks": cards, "total": len(cards)}
        if project != "smart-swarm":
            raise KeyError("Unknown project")
        options = {"offset": offset, "limit": max(1, min(limit, 50))}
        options["group"] = group or "station_setup"
        return await self.swarm.call("tasks", options)

    async def select(self, project, task):
        if project not in ('demonstrations', 'smart-swarm'):
            raise ValueError('Unknown project')
        if project == "smart-swarm":
            snapshot = await self.swarm.call("snapshot", {"target": task})
        else:
            card = next(item for item in catalog.tasks() if item["task_id"] == task)
            snapshot = SessionSnapshot(session_id=uuid.uuid4().hex, project_id=project, task_id=task,
                robot_id=card["robot_id"], domain="physical", instruction="Check the setup, then prepare the native session.",
                permitted_actions=["prepare_session"]).model_dump()
        self.journal.save_session(snapshot)
        self.remember_selection(snapshot)
        return snapshot

    def remember_selection(self, snapshot):
        if hasattr(self,'memory_store'):
            self.memory_store.put('active_session',True)
            self.memory_store.put('selected_session',snapshot['session_id'])
            self.on_selection(snapshot['session_id'])

    async def snapshot(self, identifier):
        saved = self.journal.session(identifier)
        if saved["project_id"] == "smart-swarm":
            current = await self.swarm.call("snapshot", {"target": saved["task_id"]})
            if current != saved:
                self.journal.save_session(current)
            native=await self.native.request('studio','/api/lab/status')
            dataset=current['native_ids'].get('studio_dataset_id') or current['readiness'].get('component',{}).get('native_dataset_id')
            current['recording']=native['recording'] if dataset and native['recording'].get('dataset_id')==dataset else {'state':'No native recording bound','active':False}
            current["project_state"]["homebrain_operations"] = self.journal.operations(identifier)
            self.pending(current)
            current['project_state']['overview_geometry'] = self.journal.profile('camera_geometry') or {}
            return await decorate(self, current)
        unresolved = [row for row in self.journal.unresolved() if row['session_id'] == identifier]
        if unresolved:
            saved['pending_work'] += [{'operation_id': row['id'], 'action': row['action'], 'status': row['state']} for row in unresolved]
            saved['permitted_actions'] = ['reconcile'] if any(row['state'] == 'unknown' for row in unresolved) else []
        saved['project_state']['overview_geometry'] = self.journal.profile('camera_geometry') or {}
        return await decorate(self, saved)

    async def action(self, request):
        session = self.journal.session(request.session_id)
        if request.project_id != session['project_id'] or request.target_id not in (None, session['task_id']):
            raise ValueError('Action scope does not match the selected session')
        operation, fresh = self.journal.intent(request)
        if not fresh:
            return json.loads(operation["result"]) if operation["result"] else self.result(operation["id"], "pending", request.expected_revision)
        if request.project_id == "smart-swarm":
            return await self.project_action(operation["id"], request)
        lock = self.locks.setdefault(request.session_id, asyncio.Lock())
        async with lock:
            session = self.journal.session(request.session_id)
            if session["revision"] != request.expected_revision:
                return self.reject(operation["id"], session, "STALE_REVISION", "Refresh the session before acting.")
            pending = [row for row in self.journal.unresolved() if row["session_id"] == request.session_id and row["id"] != operation["id"]]
            if pending and request.action != "reconcile":
                return self.reject(operation["id"], session, "RECONCILE_REQUIRED", "An earlier operation has an unresolved outcome.")
            if request.action not in session["permitted_actions"] + ["stop", "reconcile", 'review_viewpoint']:
                return self.reject(operation["id"], session, "ACTION_NOT_PERMITTED", "This action is not available in the current state.")
            worker = asyncio.create_task(self.execute(operation["id"], request))
            self.workers.add(worker)
            worker.add_done_callback(self.workers.discard)
        return self.result(operation["id"], "pending", session["revision"])

    def pending(self, session):
        rows = [row for row in self.journal.unresolved() if row['session_id']==session['session_id']]
        if rows:
            session['pending_work'] += [{'operation_id':row['id'],'action':row['action'],'status':row['state']} for row in rows]
            session['permitted_actions'] = ['reconcile'] if any(row['state']=='unknown' for row in rows) else []

    async def project_action(self, operation, request):
        try:
            unresolved = [row for row in self.journal.unresolved() if row['session_id']==request.session_id and row['id']!=operation]
            if unresolved and request.action not in ('reconcile','stop'):
                raise PermissionError('Reconcile the unresolved operation before another action')
            if request.action == 'reconcile':
                from .recovery import reconcile_project
                return await reconcile_project(self, operation, request)
            geometry = self.journal.profile('camera_geometry') or {}
            if request.action in ('start_recording', 'start_mobile', 'mark', 'grant_relocation', 'predict', 'reveal') and geometry.get('requires_recheck'):
                raise PermissionError('The C920 references require recheck. Capture and confirm the station again before starting.')
            await self.project_control(request)
            if request.action == 'enable_control':
                response = self.result(operation, 'accepted', request.expected_revision, 'Native control transition acknowledged.')
                self.journal.complete(operation, response)
                return response
            else:
                outgoing = project_request(request)
                if request.action=='finish_recording':
                    outgoing['_native_finish_binding'] = self.journal.profile('finalize:'+request.session_id)
                response = await self.swarm.call('action',outgoing)
            response["native_acknowledgement"]["project_operation_id"] = response["operation_id"]
            response["operation_id"] = operation
            if request.action == 'confirm_station' and response['status'] == 'accepted':
                self.journal.profile('camera_geometry', {'requires_recheck': False, 'station_receipts': response['receipts']})
            self.journal.complete(operation, response)
            return response
        except (ValueError, PermissionError, KeyError) as error:
            result = self.result(operation, 'rejected', request.expected_revision, str(error))
            self.journal.complete(operation, result)
            return result
        except (OSError, TimeoutError, httpx.TransportError) as error:
            result = self.result(operation, "unknown", request.expected_revision, str(error))
            self.journal.complete(operation, result)
            return result

    async def project_control(self, request):
        if request.action not in ('enable_control', 'start_recording', 'finish_recording'):
            return
        session = await self.snapshot(request.session_id)
        if session['revision'] != request.expected_revision:
            raise ValueError('Project revision changed; refresh before acting')
        entry = self.controls.require(session)
        if request.action in ('enable_control', 'start_recording'):
            entry['owned'] = True
        if request.action == 'enable_control':
            native = await self.native.request('studio', '/api/lab/status')
            if native['teleoperation'].get('active'):
                raise PermissionError('Native control is already active. Reconcile its owner first.')
            generation = expected(request.arguments, native['hardware_stop_generation'])
            proof = self.controls.permit(session, generation)
            await self.studio.enable(generation, proof)
        if request.action == 'start_recording':
            native = await self.native.request('studio', '/api/lab/status')
            if not native['teleoperation'].get('active'):
                raise PermissionError('Explicitly enable native control before recording this project task.')
            dataset = session['native_ids'].get('studio_dataset_id') or session['readiness'].get('component', {}).get('native_dataset_id')
            if not dataset:
                raise ValueError('Prepare the project task before native recording')
            await self.controls.record_permit(session, native, dataset, request.arguments)
        if request.action == 'finish_recording':
            native = await self.native.request('studio', '/api/lab/status')
            dataset = session['native_ids'].get('studio_dataset_id') or session['readiness'].get('component',{}).get('native_dataset_id')
            if not dataset or native['recording'].get('dataset_id')!=dataset or not native['recording'].get('session_id'):
                raise PermissionError('Native recording ownership changed; refresh the retained attempt before Finish')
            self.controls.leases.finalize(session['session_id'])
            self.journal.profile('finalize:'+request.session_id, {'dataset_id':dataset,'session_id':native['recording']['session_id'],
                'episode_id': native['recording'].get('episode_id'), 'finish_intent': True})

    def result(self, identifier, state, revision, message="Reconcile the authoritative snapshot before retrying.", acknowledgement=None):
        return ActionResult(status=state, operation_id=identifier, revision=revision,
            reason_code=state.upper(), message=message, native_acknowledgement=acknowledgement or {}).model_dump()

    def reject(self, identifier, session, code, message):
        result = self.result(identifier, "rejected", session["revision"], message)
        result["reason_code"] = code
        self.journal.complete(identifier, result)
        return result

    async def execute(self, identifier, request):
        from .transitions import transition
        session = self.journal.session(request.session_id)
        expected = session["revision"]
        try:
            acknowledgement = await transition(self, session, request)
            session["revision"] += 1
            self.journal.save_session(session, expected)
            result = self.result(identifier, "accepted", session["revision"], "Native acknowledgement received.", acknowledgement)
        except (httpx.TransportError, OSError, TimeoutError, Conflict) as error:
            result = self.result(identifier, "unknown", expected, str(error))
        except (ValueError, PermissionError, KeyError) as error:
            result = self.result(identifier, "rejected", expected, str(error))
        except Exception as error:
            result = self.result(identifier, "unknown", expected, type(error).__name__+': '+str(error))
        self.journal.complete(identifier, result)

    async def recover(self):
        for row in self.journal.unresolved():
            if row["state"] == "pending":
                self.journal.complete(row["id"], self.result(row["id"], "unknown", 0, "Service restarted. Native readback required; no action was repeated."))
        while True:
            from .recovery import refresh
            for session in self.journal.sessions():
                try:
                    await refresh(self, session)
                except (ValueError, OSError, httpx.HTTPError, KeyError) as error:
                    self.journal.event(session["session_id"], "readback_unavailable", session["revision"], {"message": str(error)})
            await asyncio.sleep(2)

    async def stop_owned(self, session):
        native = await self.native.request('studio', '/api/lab/lease')
        active = native.get('active') or {}
        operation = active.get('operation_id')
        proof = self.controls.leases.entries.get(operation, {})
        if proof.get('session_id') != session['session_id']:
            return {'requested':False, 'reason':'Native control belongs to another owner or is already stopped'}
        return await self.native.request('studio', '/api/lab/lease/stop', {'operation_id':operation})

    async def emergency_stop(self, robot):
        self.journal.event(None, 'independent_stop_intent', 0, {'robot_id': robot})
        result = await self.native.stop(robot)
        self.journal.event(None, 'independent_stop_acknowledgement', 0, {'robot_id': robot, 'native': result})
        return result
