"""Reviewed project recipes retain owner eligibility, corpus identity and idempotency."""
import json
import time
import uuid
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from fastapi import HTTPException
from .contracts import ActionRequest
from .workload import inspect


class Submission(BaseModel):
    model_config = ConfigDict(extra='forbid')
    recipe_id: Literal['native-act-fit-v1','native-smolvla-fit-v1']
    corpus_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    idempotency_key: str = Field(min_length=8, max_length=128)


def prior(lab, body):
    with lab.journal.db() as db:
        row = db.execute('SELECT * FROM operations WHERE request_key=?',(body.idempotency_key,)).fetchone()
    if row is None:
        return None
    arguments = json.loads(row['request'])['arguments']
    if arguments != {'recipe_id':body.recipe_id,'corpus_sha256':body.corpus_sha256}:
        raise HTTPException(409,'Reviewed job key was reused for a different corpus or recipe')
    return json.loads(row['result']) if row['result'] else lab.result(row['id'],'pending',0)


async def submit(lab, body):
    existing = prior(lab, body)
    if existing:
        return existing
    load = await inspect(lab)
    if load['profile'] != 'Idle' or not load['inference_permitted']:
        raise HTTPException(409,'Project jobs wait for native idle and the existing resource reservation')
    evidence = await lab.swarm.call('jobs')
    if not evidence['eligibility']['eligible'] or evidence.get('corpus_sha256') != body.corpus_sha256:
        raise HTTPException(409,evidence['eligibility'].get('reason') or 'Corpus changed; review the current project evidence')
    review = lab.journal.profile('reviewed-job') or {}
    if any(review.get(key)!=value for key,value in body.model_dump().items()) or review.get('expires',0)<time.time():
        raise HTTPException(409,'Open the current project job review before submitting')
    session = await lab.swarm.call('snapshot', {'target':'station-setup'})
    lab.journal.save_session(session)
    request = ActionRequest(action='submit_job',project_id='smart-swarm',session_id=session['session_id'],
        target_id=session['task_id'],expected_revision=session['revision'],idempotency_key=body.idempotency_key,
        arguments={'recipe_id':body.recipe_id,'corpus_sha256':body.corpus_sha256})
    return await lab.action(request)


def install(api, lab):
    @api.post('/api/lab/v1/project-jobs')
    async def submit_job(body: Submission):
        return await submit(lab, body)

    @api.post('/api/lab/v1/project-jobs/review')
    async def review_job(body: Submission):
        evidence = await lab.swarm.call('jobs')
        if not evidence['eligibility']['eligible'] or evidence.get('corpus_sha256') != body.corpus_sha256:
            raise HTTPException(409,'Project eligibility or corpus changed; refresh the job evidence')
        session = await lab.swarm.call('snapshot', {'target':'station-setup'})
        lab.journal.save_session(session)
        review = {**body.model_dump(), 'session_id':session['session_id'], 'expires':time.time()+900}
        lab.journal.profile('reviewed-job',review)
        return {'review':review,'session':session}
