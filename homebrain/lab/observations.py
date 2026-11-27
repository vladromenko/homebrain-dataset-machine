"""Read-only native observations and explicitly separate simulation commands."""
import time
import httpx
from fastapi import HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict


class Simulation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    command: str
    arguments: dict = {}


def install(api, lab):
    from .capture import install as install_capture
    install_capture(api, lab)
    @api.get('/api/lab/v1/sensors')
    async def sensors():
        value = await lab.native.observed('explorer', '/api/fleet/live')
        return {**value,'controller_readbacks':await controller_readbacks(lab)}

    @api.get('/api/lab/v1/simulation/{kind}')
    async def simulation(kind: str):
        if kind not in ('individual', 'shared'):
            raise HTTPException(404)
        return await simulation_native(lab,kind)

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
        return await simulation_native(lab,kind,body.model_dump())


async def simulation_native(lab, kind, body=None):
    try:
        result = await lab.native.request('explorer','/api/lab/simulation/'+kind,body)
        if body and body['command']!='close':
            state = await lab.native.request('explorer','/api/lab/simulation/'+kind)
            return {**state,'native_acknowledgement':result,'domain':'simulation'}
        return {**result,'domain':'simulation'}
    except ValueError as error:
        raise HTTPException(409,str(error)) from error
    except (OSError,httpx.HTTPError) as error:
        raise HTTPException(503,'Native simulation unavailable: '+str(error)) from error


async def controller_readbacks(lab):
    readings = {robot:{'data':value['data'],'cache_age_ms':max(0,time.monotonic()-value['received_monotonic'])*1000,
                       'source':'Native controller telemetry','sensor_clock':'Retained source metadata; reception age is separate'}
                for robot,value in lab.controls.latest.items()}
    studio = await lab.native.observed('studio','/api/lab/status')
    readings['so101'] = {'data':studio.get('data',{}).get('teleoperation',{}),
                         'source':'Studio canonical owner','available':studio['available'],
                         'sensor_clock':'Native sample age is unknown unless explicitly supplied'}
    return readings
