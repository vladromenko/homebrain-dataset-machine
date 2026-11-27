"""Allowlisted SSH operations: one JSON object on stdout, diagnostics on stderr."""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from .config import load


def request(config, operation, launcher):
    endpoint = '/api/health' if operation == 'status' else '/api/lab/v1/auth/ticket'
    headers = {'Content-Type': 'application/json'}
    body = None
    if operation == 'handoff':
        headers['Authorization'] = 'Bearer '+(Path(config['runtime'])/'access-token').read_text().strip()
        body = json.dumps({'launcher_id': launcher}).encode()
    call = urllib.request.Request(f'http://127.0.0.1:{config["port"]}'+endpoint, data=body, headers=headers)
    with urllib.request.urlopen(call, timeout=5) as response:
        return json.load(response)


def start(config):
    unit = config.get('service_unit')
    if unit:
        environment = {**os.environ, 'XDG_RUNTIME_DIR': '/run/user/'+str(os.getuid()),
                       'DBUS_SESSION_BUS_ADDRESS': 'unix:path=/run/user/'+str(os.getuid())+'/bus'}
        subprocess.run(['systemctl', '--user', 'start', unit], env=environment, check=True,
                       stdout=sys.stderr, stderr=sys.stderr, timeout=25)
    else:
        from .process import main as launch
        from contextlib import redirect_stdout
        sys.argv = [sys.argv[0], 'start']
        with redirect_stdout(sys.stderr):
            launch()
    deadline = time.monotonic()+25
    while time.monotonic() < deadline:
        try:
            return request(config, 'status', None)
        except OSError:
            time.sleep(.25)
    raise TimeoutError('Homebrain did not become ready within 25 seconds')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=['handoff', 'status', 'start'])
    parser.add_argument('--launcher-id', default='mac-homebrain')
    args = parser.parse_args()
    try:
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', args.launcher_id):
            raise ValueError('Invalid launcher identity')
        config = load()
        result = start(config) if args.operation == 'start' else request(config, args.operation, args.launcher_id)
        print(json.dumps(result))
    except Exception as error:
        print(str(error), file=sys.stderr)
        print(json.dumps({'status': 'unavailable', 'message': str(error)}))
        raise SystemExit(1) from error


if __name__ == '__main__':
    main()
