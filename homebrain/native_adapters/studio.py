"""Studio remains the only SO101 controller, camera owner and dataset writer."""
import asyncio
import time


class Studio:
    def __init__(self, native, journal):
        self.native, self.journal = native, journal

    async def prepare(self, session, task):
        status = await self.native.request("studio", "/api/status?preparation=resources")
        if status["recording"].get("active") or status["teleoperation"].get("active"):
            raise ValueError("Studio is active. Finish its current session before preparing another.")
        await self.check_preview(status)
        profile = self.journal.profile("so101-demonstrations")
        if profile is None:
            dataset = await self.native.request("studio", "/api/datasets", {
                "name": "Homebrain Lab / development demonstrations", "task": task["title"],
                "source": "hardware", "camera_mode": "two_camera", "target_episodes": 1})
            profile = {"dataset_id": dataset["dataset_id"], "purpose": "development", "camera_roles": ["top", "wrist"]}
            self.journal.profile("so101-demonstrations", profile)
        session["native_ids"]["dataset_id"] = profile["dataset_id"]
        session["readiness"] = {"hardware_stop_generation": status["hardware_stop_generation"],
            "preview": status.get("preview"), "resources": status.get("resources"),
            "calibration": "Native live readback required on Enable control"}
        return {"profile": profile, "nonactuating": True}

    async def check_preview(self, status):
        inventory = status.get('resources',{}).get('device_inventory',{})
        missing = [name for name in ('leader','follower','top','wrist') if not inventory.get(name,{}).get('present')]
        if missing:
            raise ValueError('Reconnect the configured native devices: '+', '.join(missing)+'. Their persistent identities will be checked again.')
        if not status.get('preview',{}).get('active'):
            await self.native.request('studio','/api/preview/start',{})
            status['preview'] = (await self.native.request('studio','/api/lab/status'))['preview']
        cameras = status['preview'].get('cameras',{})
        stale = [name for name in ('top','wrist') if not cameras.get(name,{}).get('connected') or (cameras.get(name,{}).get('last_frame_age_ms') is None or cameras[name]['last_frame_age_ms']>500)]
        if stale:
            raise ValueError('Native camera view unavailable or stale: '+', '.join(stale)+'. Reconnect it and wait for native camera recovery; other recording owners are preserved.')

    async def enable(self, generation, operation):
        return await self.native.request("studio", f"/api/teleoperation/start?expected_stop_generation={generation}", {},
            headers={'X-Homebrain-Operation':operation})

    async def start(self, session, authorize):
        status = await self.native.request("studio", "/api/lab/status")
        if status["recording"].get("active"):
            raise ValueError("An active native recording already exists; reconcile it before Start.")
        if not status['teleoperation'].get('active'):
            raise PermissionError('Native control is stopped. Explicitly enable it before starting a new recording.')
        operation = await authorize(status)
        session["project_state"]["previous_episode"] = status["recording"].get("last_episode")
        result = await self.native.request("studio", "/api/record/start", {
            "dataset_id": session["native_ids"]["dataset_id"], "episode_count":1, "auto_advance":False, "keep_open":False,
            "expected_stop_generation": status["hardware_stop_generation"]}, headers={"X-Homebrain-Operation":operation})
        if result.get('session_id'):
            session['native_ids']['native_session_id'] = result['session_id']
        return result

    async def finish(self, session):
        result = await self.native.request("studio", "/api/record/end", {})
        session["project_state"]["finish_requested"] = True
        return result

    async def saved(self, session):
        status = await self.native.request('studio', '/api/lab/status')
        recording = status['recording']
        dataset = session['native_ids']['dataset_id']
        native_session = session['native_ids'].get('native_session_id')
        belongs = recording.get('dataset_id') == dataset and recording.get('session_id') == native_session
        if belongs:
            session['recording'] = recording
            if recording.get('state') in ('saving', 'recording', 'preparing', 'starting'):
                return None
            if recording.get('state') in ('failed', 'error'):
                raise ValueError(recording.get('error') or 'Native writer failed; partial evidence retained')
        identifier = session['native_ids'].get('episode_id')
        last = recording.get('last_episode') or {}
        if not identifier and last.get('session_id') == native_session:
            identifier = last.get('episode_id')
        if not identifier:
            return None
        rows = await self.native.request('studio', f'/api/episodes/{dataset}?include_frames=false&episode_id={identifier}')
        verified = [row for row in rows if row.get('metadata', {}).get('session_id') == native_session
                    and row['metadata'].get('dataset_id') == dataset and row['metadata'].get('status') == 'complete']
        if len(verified) != 1 or verified[0].get('storage') != 'episodes':
            return None
        await self.stop_owned(session)
        return {'native_episode': verified[0]['metadata'], 'readback': verified,
                'source': 'Studio', 'admission': 'not_assessed'}

    async def validate(self, session, retry=False):
        dataset = session["native_ids"]["dataset_id"]
        key = 'validation:'+session['session_id']
        previous = self.journal.profile(key)
        if previous and retry and previous.get('job'):
            identifier = previous['job'].get('id', previous['job'].get('job_id'))
            job = await self.native.request('studio', '/api/lab/jobs/'+identifier)
            if job['state'] in ('failed', 'stopped', 'interrupted', 'cancelled'):
                previous = None
        if previous:
            if previous.get('job'):
                return previous['job']
            status = await self.native.request('studio', '/api/status?catalog=validation-reconcile')
            matches = [job for job in status['jobs'] if job['kind']=='validate'
                       and job['dataset'].rstrip('/').endswith('/'+dataset) and job['created_at']>=previous['created']-.5]
            return matches[0] if len(matches)==1 else {'unknown':True,'message':'Native validation submission needs receipt reconciliation'}
        intent = {'created':time.time(), 'dataset':dataset, 'state':'intent'}
        self.journal.profile(key, intent)
        result = await self.native.request("studio", f"/api/datasets/{dataset}/validate", {"allow_test_data": False})
        self.journal.profile(key, {**intent,'state':'acknowledged','job':result})
        return result
