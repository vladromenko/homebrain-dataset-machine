"""A requested robot view never falls back to another robot's camera."""
import json
import time


async def frame(native, robot, role):
    if robot == 'so101' and role in ('top','wrist'):
        status = await native.request('studio','/api/lab/status')
        camera = status.get('preview',{}).get('cameras',{}).get(role,{})
        age = camera.get('last_frame_age_ms')
        if age is None or age>500 or not camera.get('connected'):
            raise OSError('Studio '+role+' camera has no verified fresh shared frame')
        content,kind = await native.frame('studio','/api/frame/'+role)
        return content,kind,{'robot':robot,'role':role,'age_ms':age,'sequence':camera.get('stream',{}).get('capture_frames'),
            'clock':'Homebrain capture read end; exposure timestamp unavailable'}
    if robot not in ('tank','rosmaster') or role!='front':
        raise ValueError('Unsupported authorized robot/camera pairing')
    origin = native.origins['explorer']
    response = await native.client.get(origin+'/api/lab/'+robot+'/frame.jpg',headers={'Origin':origin})
    if response.status_code != 200:
        raise OSError('No fresh '+robot.upper()+' front view. Check its native read-only observer and connection; another robot view is not a substitute.')
    age = float(response.headers['X-Frame-Age-Ms'])
    return response.content,'image/jpeg',{'robot':robot,'role':role,'age_ms':age,
        'sequence':response.headers.get('X-Frame-Sequence'),'clock':response.headers.get('X-Frame-Clock')}
