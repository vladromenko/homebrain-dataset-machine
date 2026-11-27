"""Read-only native observations and explicitly separate simulation commands."""
import time
from fastapi import HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict


class Simulation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    command: str
    arguments: dict = {}


def install(api, lab):
    @api.get('/api/lab/v1/sensors')
    async def sensors():
        return await lab.native.observed('explorer', '/api/fleet/live')

    @api.get('/api/lab/v1/simulation/{kind}')
    async def simulation(kind: str):
        if kind not in ('individual', 'shared'):
            raise HTTPException(404)
        return await lab.native.request('explorer', '/api/lab/simulation/'+kind)

    @api.post('/api/lab/v1/simulation/{kind}')
    async def simulation_action(kind: str, body: Simulation):
        if kind not in ('individual', 'shared'):
            raise HTTPException(404)
        if body.command == 'start':
            studio = await lab.native.request('studio', '/api/lab/status')
            explorer = await lab.native.request('explorer', '/api/health')
            if studio['recording'].get('active') or studio['teleoperation'].get('active') or explorer.get('armed') or explorer['session']['thread_active']:
                raise HTTPException(409, 'Finish physical control/recording before opening simulation.')
        lab.journal.event(None, 'simulation_intent', 0, {'domain': 'simulation', 'kind': kind, **body.model_dump()})
        return await lab.native.request('explorer', '/api/lab/simulation/'+kind, body.model_dump())
