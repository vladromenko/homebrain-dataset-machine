"""Transport-only fence around the peer's original native Finish operation."""
import json
from urllib.request import Request, ProxyHandler, build_opener


def call(facade, message, binding):
    from smart_swarm import studio
    original = studio.native_request

    def request(config, path, body=None):
        if path != '/api/record/end':
            return original(config,path,body)
        if config['studio_origin'] != 'http://127.0.0.1:8020':
            raise ValueError('Unexpected native Studio origin')
        payload = {key:binding[key] for key in ('dataset_id','session_id')}
        from smart_swarm.platform_client import NoRedirect
        command = Request(config['studio_origin']+'/api/lab/record/finish',
            data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        with build_opener(ProxyHandler({}),NoRedirect()).open(command,timeout=5) as response:
            return json.load(response)

    studio.native_request = request
    try:
        return facade.call(message)
    finally:
        studio.native_request = original
