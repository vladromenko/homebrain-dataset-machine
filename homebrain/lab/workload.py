"""Measured qualification gates inference; existing native reservations remain binding."""
import asyncio
import psutil


async def inspect(lab):
    studio, explorer, ros = await asyncio.gather(
        lab.native.request('studio', '/api/lab/status'),
        lab.native.request('explorer', '/api/health'),
        lab.native.request('explorer', '/api/lab/rosmaster/status'))
    training = explorer.get('compute_job') or any(job.get('state') in
        ('running', 'starting', 'queued', 'waiting_resources') for job in studio.get('jobs', []))
    training = training or any(row['action']=='submit_job' for row in lab.journal.unresolved())
    recording = studio['recording'].get('active') or studio['teleoperation'].get('active')
    recording = recording or explorer.get('armed') or explorer['session']['thread_active'] or ros['armed'] or ros['recording']['thread_active']
    profile = 'Training' if training else 'Recording' if recording else 'Idle'
    qualification = lab.journal.profile('concurrency') or {}
    available = psutil.virtual_memory().available/2**30
    permitted = profile == 'Idle' or (profile == 'Recording' and qualification.get('status') == 'qualified_native_recording')
    return {'profile': profile, 'inference_permitted': bool(permitted and available >= lab.config['min_available_gb']),
            'available_gib': round(available, 2), 'reservation_gib': lab.config['min_available_gb'],
            'qualification': qualification.get('status', 'pending_attended_native_recording')}
