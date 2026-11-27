"""Bind delayed human actions to the STOP generation visible before admission."""
import httpx


async def decorate(lab, session):
    robot = session['robot_id']
    owner = 'studio' if robot == 'so101' else 'explorer'
    path = '/api/lab/rosmaster/status' if robot == 'rosmaster' else '/api/lab/status'
    try:
        observed = await lab.native.request(owner, path)
    except (OSError,ValueError,httpx.HTTPError) as error:
        session['readiness'].update(native_stop_generation=None,native_observation_available=False)
        session['blockers'].append('Native service unavailable: '+str(error)+'. Reconnect it and refresh; movement will not resume.')
        session['permitted_actions'] = [action for action in session['permitted_actions'] if action in ('stop','reconcile','next_task')]
        return session
    key = 'hardware_stop_generation' if robot == 'so101' else 'generation'
    session['readiness']['native_stop_generation'] = observed[key]
    return session


def expected(arguments, observed):
    generation = arguments.get('expected_native_generation')
    if type(generation) is not int or generation != observed:
        raise PermissionError('Native STOP generation changed. Refresh and explicitly enable control again.')
    return generation


def project_request(request):
    payload = request.model_dump() if hasattr(request, 'model_dump') else dict(request)
    payload['arguments'] = {key:value for key,value in payload.get('arguments', {}).items()
                            if key != 'expected_native_generation'}
    return payload
