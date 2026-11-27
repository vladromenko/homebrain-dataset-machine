"""Private runtime tools and authenticated durable conversation stream."""
import json
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from .tools import invoke


class Chat(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: str = Field(min_length=1, max_length=4000)
    conversation: str = Field(default='operator', pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    selection: str | None = None


class Tool(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    tool: str
    arguments: dict = {}


def install(app, runtime, adapters):
    @app.post('/api/lab/v1/chat')
    async def chat(body: Chat):
        async def stream():
            async for event in runtime.answer(body.text, body.conversation, body.selection):
                yield json.dumps(event)+'\n'
        return StreamingResponse(stream(), media_type='application/x-ndjson')

    @app.post('/api/lab/v1/agent/tool')
    async def tool(body: Tool):
        try:
            return await invoke(runtime, body.request_id, body.tool, body.arguments, adapters)
        except (PermissionError, ValueError, KeyError) as error:
            raise HTTPException(403, str(error)) from error
