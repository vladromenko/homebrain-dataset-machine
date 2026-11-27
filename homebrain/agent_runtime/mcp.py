"""Private stdio MCP transport; scope is issued by Homebrain, never by the model."""
import json
import os
import sys
import urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from homebrain.agent_runtime.permissions import ROLE_TOOLS

TOOLS = [
    ('status', 'Read the selected task and current native status', {}),
    ('receipt', 'Read the selected native episode and validation receipts', {}),
    ('search', 'Search approved code/docs with revision and file hash', {'query': {'type': 'string'}}),
    ('read', 'Read an approved indexed source file', {'path': {'type': 'string'}, 'start_line': {'type':'integer','minimum':1,'default':1}}),
    ('vision', 'Inspect only the requested native robot view. SO101 uses top/wrist; Tank and ROSMASTER use front.', {'robot_id':{'type':'string','enum':['so101','tank','rosmaster']},'role':{'type':'string','enum':['top','wrist','front']},'question':{'type':'string'}}),
    ('memory', 'Retrieve scoped durable lab memory', {'query': {'type': 'string'}}),
    ('git', 'Inspect approved repository version or tracked diff', {'operation': {'type':'string','enum':['version','diff']}, 'path': {'type':'string'}}),
    ('check', 'Run a fixed small check in the isolated Homebrain checkout when idle', {'check': {'type':'string','enum':['contracts','memory','recovery']}}),
    ('delegate', 'Ask a scoped specialist to investigate evidence', {'role': {'type': 'string', 'enum': ['dataset', 'hardware', 'code', 'learning', 'knowledge']}, 'question': {'type': 'string'}}),
    ('operation', 'Request a permitted typed operation; motor enable/start requires the visible operator action', {'action': {'type': 'string'}}),
]


def call(name, arguments):
    body = json.dumps({'request_id': os.environ['HOMEBRAIN_AGENT_REQUEST'], 'tool': name, 'arguments': arguments}).encode()
    request = urllib.request.Request(os.environ['HOMEBRAIN_AGENT_ORIGIN']+'/api/lab/v1/agent/tool', data=body,
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer '+os.environ['HOMEBRAIN_AGENT_TOKEN']})
    with urllib.request.urlopen(request, timeout=240) as response:
        return json.load(response)


def answer(message):
    method = message.get('method')
    if method == 'initialize':
        return {'protocolVersion': '2024-11-05', 'capabilities': {'tools': {}},
                'serverInfo': {'name': 'homebrain', 'version': '1.0.0'}}
    if method == 'tools/list':
        names = ROLE_TOOLS.get(os.environ.get('HOMEBRAIN_AGENT_ROLE'), set())
        allowed = [tool for tool in TOOLS if tool[0] in names]
        return {'tools': [{'name': name, 'description': description, 'inputSchema': {
            'type': 'object', 'properties': properties, 'required': [key for key,value in properties.items() if 'default' not in value], 'additionalProperties': False}}
            for name, description, properties in allowed]}
    if method == 'tools/call':
        params = message['params']
        result = call(params['name'], params.get('arguments', {}))
        return {'content': [{'type': 'text', 'text': json.dumps(result)}]}
    return {}


def main():
    for line in sys.stdin:
        try:
            message = json.loads(line)
            if 'id' in message:
                try:
                    result = {'jsonrpc': '2.0', 'id': message['id'], 'result': answer(message)}
                except Exception as error:
                    result = {'jsonrpc': '2.0', 'id': message['id'], 'error': {'code': -32000, 'message': str(error)}}
                sys.stdout.write(json.dumps(result)+'\n')
                sys.stdout.flush()
        except ValueError:
            pass


if __name__ == '__main__':
    main()
