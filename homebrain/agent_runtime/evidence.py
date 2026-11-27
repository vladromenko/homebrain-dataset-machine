"""Bound model context while retaining identities, reasons and source revisions."""


def compact(value, depth=0):
    if depth > 4:
        return '[deeper native evidence available on demand]'
    if isinstance(value, dict):
        return {key:compact(item,depth+1) for key,item in list(value.items())[:18]}
    if isinstance(value, list):
        return [compact(item,depth+1) for item in value[:3]]
    return value[:1000] if isinstance(value,str) else value


def selected(session):
    if not session:
        return {'selection':'No task selected'}
    keys = ('project_id','task_id','robot_id','state','instruction','permitted_actions','blockers')
    if session.get('project_state',{}).get('archive_inspection'):
        keys = tuple(key for key in keys if key!='task_id')
    return {**{key:session.get(key) for key in keys}, 'recording':recording(session.get('recording',{})),
            'receipt_count':len(session.get('receipts',[]))}


def recording(value):
    keys = ('state','phase','active','hardware_open','episode_id','session_id','dataset_id','frames','error','writer_queue','writer_pending','hardware_stop_state','stop_errors')
    return {key:value[key] for key in keys if key in value}


async def status(lab, session):
    studio = await lab.native.observed('studio')
    explorer = await lab.native.observed('explorer','/api/health')
    data = studio['data']
    preview = {name:{key:camera.get(key) for key in ('connected','error','last_frame_age_ms','observed_fps')}
               for name,camera in data.get('preview',{}).get('cameras',{}).items()}
    return {'selected':{key:session.get(key) for key in ('state','instruction','permitted_actions')} if session else None,'studio':{'recording':recording(data.get('recording',{})),
            'teleoperation':recording(data.get('teleoperation',{})),'preview':preview},
            'explorer':{key:explorer.get('data',{}).get(key) for key in ('armed','selected_robot','session','compute_job')},
            'availability':{'studio':{'available':studio['available'],'error':studio.get('error')},
                            'explorer':{'available':explorer['available'],'error':explorer.get('error')}},
            'authority':'Current native readback when available; operator-only'}


async def receipts(lab, session):
    if not session:
        return {'error':'No task selected'}
    result = []
    evidence = await current_receipts(lab,session)
    for receipt in evidence[-4:]:
        value = receipt.get('native_episode',receipt.get('native_recording',receipt))
        metadata = value.get('metadata',value)
        keys = ('episode_id','session_id','task','status','source','test_only','frames','reason','error','abort_reason','stop_reason','termination','outcome','timing','quality','validation')
        selected_metadata = {key:compact(metadata[key]) for key in keys if key in metadata}
        result.append({'source':receipt.get('source'),'storage':value.get('storage'),'receipt':selected_metadata or compact(value)})
    configuration = {}
    if session['robot_id']=='so101' and session['native_ids'].get('dataset_id'):
        catalog = await lab.native.request('studio','/api/status?catalog=selected-episode')
        dataset = next((row for row in catalog.get('datasets',[]) if row.get('dataset_id')==session['native_ids']['dataset_id']),{})
        configuration.update({key:compact(dataset[key]) for key in ('source','camera_mode','cameras','settings','test_only') if key in dataset})
    return {'native_ids':session['native_ids'],'selected_receipts':result,'native_configuration':configuration,
            'scope':'Operator evidence, never policy input'}


async def current_receipts(lab, session):
    identifiers = session['native_ids']
    if session['robot_id']=='so101' and identifiers.get('dataset_id') and identifiers.get('episode_id'):
        records = await lab.native.request('studio',f"/api/episodes/{identifiers['dataset_id']}?include_frames=false&episode_id={identifiers['episode_id']}")
        if len(records)!=1:
            raise ValueError('Selected native receipt is unavailable; refresh the native archive')
        retained = [row for row in session['receipts'] if row.get('source')=='Studio validation']
        return retained+[{'source':'Studio current native receipt','native_episode':records[0]}]
    return session['receipts']
