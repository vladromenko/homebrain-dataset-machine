"""Durable diagnostic capture intent; an unknown acknowledgement never repeats Start."""
import asyncio
from typing import Literal
import httpx
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field


class Capture(BaseModel):
    model_config = ConfigDict(extra='forbid')
    seconds: Literal[15,30,60]
    idempotency_key: str = Field(pattern=r'^[A-Za-z0-9_-]{8,100}$')


async def start(lab, body, lock):
    key = 'observation-capture:'+body.idempotency_key
    async with lock:
        prior = lab.journal.profile(key)
        if prior:
            if prior['seconds']!=body.seconds:
                raise HTTPException(409,'Capture key reused for a different duration')
            return prior
        intent = {'status':'unknown','seconds':body.seconds,'message':'Native acknowledgement unavailable. Inspect Sensor archives before another capture.'}
        lab.journal.profile(key,intent)
        try:
            result = await lab.native.request('explorer','/api/lab/observation/capture',{'seconds':body.seconds})
            intent.update(status='accepted',native=result,message='Existing native observation capture started. No motion command was sent.')
        except (OSError,TimeoutError,httpx.TransportError) as error:
            intent['message'] += ' '+str(error)
        except ValueError as error:
            intent.update(status='rejected',message=str(error))
        lab.journal.profile(key,intent)
        return intent


def install(api, lab):
    lock = asyncio.Lock()
    @api.post('/api/lab/v1/observation-capture')
    async def capture(body: Capture):
        return await start(lab,body,lock)
