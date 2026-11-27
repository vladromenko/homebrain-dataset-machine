"""Native collection series and readback; no admission rule is reimplemented."""


async def prepare(lab, session, task):
    health = await lab.native.request('explorer', '/api/health')
    ros = await lab.native.request('explorer', '/api/lab/rosmaster/status')
    if health.get('armed') or health['session']['thread_active'] or ros['armed'] or ros['recording']['thread_active']:
        raise ValueError('A native controller or writer is active. Finish it before preparation.')
    series = await lab.native.request('explorer', '/api/lab/collections/prepare', {
        'task': task['control_profile'], 'profile': task['control_profile'],
        'binding': 'development-'+task['task_id'], 'instruction': task['title']})
    session['project_state']['native_series'] = series
    session['native_ids']['collection_id'] = series['id']
    session['readiness'] = {'native_series': series, 'physical_checks': 'Native Enable enforces live checks'}
    return {'nonactuating': True, 'native_series': series}


def parameters(session):
    series = session['project_state']['native_series']
    return {'profile': series['profile'], 'scene': series['layout'], 'collection': series['id']}


async def validation(lab, session):
    from ..lab.transitions import state
    identifier = session['native_ids']['episode_id']
    receipt = await lab.native.request('explorer', '/api/lab/quality/'+identifier)
    if receipt['state'] == 'checking':
        session['pending_work'] = [{'kind': 'native_collection_readback', 'episode_id': identifier}]
        return
    quality = receipt.get('quality') or {}
    session['project_state']['technical_validation'] = receipt
    session['pending_work'] = []
    session['receipts'].append({'source': 'Explorer native collection quality', 'native_quality': receipt})
    passed = quality.get('status') == 'pass'
    message = 'Saved. Native technical checks passed.' if passed else 'Saved; native quality needs review: '+ '; '.join(quality.get('problems', ['No completed quality receipt']))
    state(session, 'saved' if passed else 'needs_review', message+' Confirm only the outcome directly observed.', ['confirm_outcome'])
