"""Native catalogs are read on demand, outside the live camera/control poll."""
import re
import uuid
from fastapi import HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from pydantic import BaseModel, ConfigDict
from .contracts import SessionSnapshot


class Inspect(BaseModel):
    model_config = ConfigDict(extra='forbid')
    dataset_id: str
    episode_id: str


def install(api, lab):
    @api.get('/api/lab/v1/project-media/{project}/{relative:path}')
    def media(project: str, relative: str):
        registration=lab.swarm.registration()
        if project!='smart-swarm' or not registration or not relative.startswith('docs/setup/'):
            raise HTTPException(404)
        root=Path(registration['repository_path']).resolve()
        path=(root/relative).resolve()
        if not path.is_relative_to(root/'docs/setup') or path.suffix not in ('.svg','.png','.jpg') or not path.is_file():
            raise HTTPException(404)
        return FileResponse(path)

    @api.get('/api/lab/v1/catalog')
    async def catalog():
        studio = await lab.native.request('studio', '/api/status?catalog=1')
        explorer = await lab.native.request('explorer', '/api/status?catalog=1')
        return {'studio':studio,'explorer':explorer}

    @api.get('/api/lab/v1/datasets/{identifier}/episodes')
    async def episodes(identifier: str):
        if not re.fullmatch('ds_[a-f0-9]{16}',identifier):
            raise HTTPException(404)
        return await lab.native.request('studio','/api/episodes/'+identifier+'?include_frames=false')

    @api.post('/api/lab/v1/inspect')
    async def inspect(body: Inspect):
        if not re.fullmatch('ds_[a-f0-9]{16}',body.dataset_id) or not re.fullmatch('[A-Za-z0-9_-]{1,100}',body.episode_id):
            raise HTTPException(422,'Invalid native recording identity')
        records = await lab.native.request('studio',f'/api/episodes/{body.dataset_id}?include_frames=false&episode_id={body.episode_id}')
        if len(records) != 1:
            raise HTTPException(404,'Native episode receipt unavailable')
        snapshot = SessionSnapshot(session_id=uuid.uuid4().hex,project_id='demonstrations',task_id='so101-placement',
            robot_id='so101',domain='physical',state='needs_review',instruction='Inspect the selected native recording receipt. No control was enabled.',
            native_ids={'dataset_id':body.dataset_id,'episode_id':body.episode_id},
            receipts=[{'source':'Studio native receipt','native_episode':records[0]}],permitted_actions=[]).model_dump()
        lab.journal.save_session(snapshot)
        return snapshot
