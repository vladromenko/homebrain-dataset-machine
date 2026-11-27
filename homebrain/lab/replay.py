"""Explicit optional derivation jobs; fixed native artifact identities only."""
import asyncio
import json
import re
from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import FileResponse
import psutil
from ..config import ROOT


class Replay:
    def __init__(self, lab):
        self.lab = lab
        self.tasks = set()
        self.folder = Path(lab.config['runtime'])/'views'
        self.folder.mkdir(exist_ok=True)

    async def derive(self, identifier):
        if not re.fullmatch('[0-9a-f]{32}', identifier):
            raise ValueError('Invalid native capture identity')
        if self.tasks:
            raise ValueError('One optional replay derivation is already running')
        from .workload import inspect
        load = await inspect(self.lab)
        if load['profile'] != 'Idle' or not load['inference_permitted']:
            raise ValueError('Replay derivation waits for an idle native station and its existing memory reservation')
        record = self.lab.journal.profile('replay:'+identifier)
        if record and record['state'] in ('pending', 'ready'):
            return record
        catalog = await self.lab.native.request('explorer', '/api/fleet/captures')
        source = next((row for row in catalog['records'] if row['id'] == identifier), None)
        if not source or source['phase'] != 'complete':
            raise ValueError('Wait for the native MCAP capture to finish')
        if psutil.virtual_memory().available/2**30 < self.lab.config['min_available_gb']:
            raise ValueError('Replay derivation deferred by the existing memory reservation')
        native_root = Path(self.lab.config['native_data_root']).resolve()
        files = list((native_root/'fleet-captures'/identifier/'bag').glob('bag_*.mcap'))
        if len(files) != 1 or files[0].is_symlink() or not files[0].resolve().is_relative_to(native_root):
            raise ValueError('Expected one finalized native MCAP; the raw artifact is retained')
        record = {'id': identifier, 'state': 'pending', 'kind': 'derived_view', 'training_eligible': False}
        self.lab.journal.profile('replay:'+identifier, record)
        task = asyncio.create_task(self.run(identifier, files[0]))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return record

    async def run(self, identifier, source):
        destination = self.folder/(identifier+'.rrd')
        process = None
        try:
            interpreter = self.lab.config['view_python']
            process = await asyncio.create_subprocess_exec(interpreter, str(ROOT/'homebrain/lab/derive.py'),
                str(source), str(destination), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await asyncio.wait_for(process.communicate(), 120)
            if process.returncode:
                raise ValueError(stderr.decode()[-1500:])
            result = {'id': identifier, 'state': 'ready', 'kind': 'derived_view', 'training_eligible': False,
                'provenance': json.loads(stdout), 'url': '/api/lab/v1/replays/'+identifier+'/view.rrd'}
        except Exception as error:
            result = {'id': identifier, 'state': 'failed', 'message': str(error), 'raw_retained': True}
        if process is not None and process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), 5)
            except TimeoutError:
                process.kill()
                await process.wait()
        self.lab.journal.profile('replay:'+identifier, result)


def install(api, lab):
    replay = Replay(lab)

    @api.get('/api/lab/v1/replays')
    async def catalog():
        native = await lab.native.request('explorer', '/api/fleet/captures')
        keys = ('id', 'phase', 'created_at', 'kind', 'training_eligible', 'requested_seconds')
        return {'captures': [{key: row.get(key) for key in keys} for row in native['records']]}

    @api.post('/api/lab/v1/replays/{identifier}')
    async def derive(identifier: str):
        try:
            return await replay.derive(identifier)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error

    @api.get('/api/lab/v1/replays/{identifier}')
    def status(identifier: str):
        return lab.journal.profile('replay:'+identifier) or {'state': 'not_requested'}

    @api.get('/api/lab/v1/replays/{identifier}/view.rrd')
    def artifact(identifier: str):
        if not re.fullmatch('[0-9a-f]{32}', identifier):
            raise HTTPException(404)
        path = replay.folder/(identifier+'.rrd')
        if not path.is_file() or (lab.journal.profile('replay:'+identifier) or {}).get('state') != 'ready':
            raise HTTPException(404)
        return FileResponse(path, media_type='application/octet-stream')
