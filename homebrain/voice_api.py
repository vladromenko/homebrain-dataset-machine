"""Explicit local listening and output authorization."""
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict


class LocalMode(BaseModel):
    model_config = ConfigDict(extra='forbid')
    enabled: bool
    output: str | None = None
    selection: str | None = None


def install(app, voice):
    @app.get('/api/lab/v1/voice')
    def status():
        return voice.status()

    @app.post('/api/lab/v1/voice')
    async def configure(body: LocalMode):
        try:
            return voice.configure(body.enabled, body.output, body.selection)
        except (PermissionError, ValueError) as error:
            raise HTTPException(409, str(error)) from error
