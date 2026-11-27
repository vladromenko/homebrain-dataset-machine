"""Read-only Git and fixed isolated checks; no arbitrary command execution."""
import asyncio
import subprocess
from pathlib import Path
from .tools import read
from ..config import ROOT

CHECKS = {'contracts': ['tests/test_lab_journal.py'], 'memory': ['tests/test_memory_context.py'],
          'recovery': ['tests/test_recovery.py']}


async def investigate(runtime, tool, arguments, adapters):
    if tool == 'check':
        return await check(runtime, arguments['check'])
    evidence = read(runtime, arguments['path'], adapters)
    path = Path(evidence['path'])
    root = subprocess.check_output(['git', '-C', str(path.parent), 'rev-parse', '--show-toplevel'], text=True, timeout=5).strip()
    operation = arguments['operation']
    if operation not in ('version', 'diff'):
        raise PermissionError('Unsupported Git inspection')
    argv = ['git', '-C', root, 'rev-parse', 'HEAD'] if operation == 'version' else ['git', '-C', root, 'diff', 'HEAD', '--', str(path)]
    result = await asyncio.to_thread(subprocess.run, argv, capture_output=True, text=True, timeout=10)
    return {**{key:evidence[key] for key in ('path','revision','sha256')},
            'operation': operation, 'output': result.stdout[:6000], 'returncode': result.returncode}


async def check(runtime, name):
    from ..lab.workload import inspect
    load = await inspect(runtime.lab)
    if load['profile'] != 'Idle' or not load['inference_permitted']:
        raise PermissionError('Optional checks wait for an idle qualified resource profile')
    folder = Path(runtime.config['investigation_checkout']).resolve()
    if folder == ROOT.resolve() or not (folder/'.git').exists():
        raise PermissionError('A separate approved investigation checkout is required')
    approved = runtime.config.get('investigation_checkout')
    if str(folder) != str(Path(approved).resolve()) or name not in CHECKS:
        raise PermissionError('Unknown isolated check')
    argv = [str(ROOT/'.venv/bin/python'), '-m', 'pytest', '-q', *CHECKS[name]]
    result = await asyncio.to_thread(subprocess.run, argv, cwd=folder, capture_output=True, text=True, timeout=25)
    revision = subprocess.check_output(['git','-C',str(folder),'rev-parse','HEAD'],text=True,timeout=5).strip()
    return {'check':name, 'source_commit':revision, 'checkout':str(folder), 'returncode':result.returncode,
            'output':(result.stdout+result.stderr)[-5000:], 'scope':'isolated synthetic checks; no physical qualification'}
