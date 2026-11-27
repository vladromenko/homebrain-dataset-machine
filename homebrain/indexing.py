"""Incremental approved tracked-code index with revision, hash and deletion handling."""
import hashlib
import subprocess
import time
from pathlib import Path

SUFFIXES = {'.py', '.md', '.rst', '.txt', '.toml', '.json', '.yaml', '.yml', '.ts', '.tsx'}
EXCLUDED = {'runtime', 'local-data', 'datasets', 'node_modules', '.venv', 'data', 'work', 'secrets'}


def sources(root):
    result = subprocess.run(['git', '-C', str(root), 'ls-files', '-z'], capture_output=True, timeout=10)
    paths = [root/value.decode() for value in result.stdout.split(b'\0') if value] if result.returncode == 0 else []
    return [path for path in paths if path.is_file() and path.resolve().is_relative_to(root.resolve()) and path.suffix in SUFFIXES
            and not EXCLUDED.intersection(path.relative_to(root).parts)
            and not any(word in path.name.lower() for word in ('secret', 'token', '.local.', 'credential'))
            and path.stat().st_size < 200000]


def revision(root):
    result = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True, timeout=5)
    if result.returncode != 0:
        return 'unversioned-approved-source'
    dirty = subprocess.run(['git','-C',str(root),'status','--porcelain','--untracked-files=no'],capture_output=True,timeout=5)
    return result.stdout.strip()+('; modified working tree' if dirty.stdout else '')


def index_root(store, root):
    paths = sources(root)
    commit = revision(root)
    active = set(map(str, paths))
    with store.db() as db:
        indexed = {row['path']: row['hash'] for row in db.execute('SELECT path,hash FROM documents WHERE path LIKE ?', (str(root)+'/%',))}
        for path in set(indexed)-active:
            db.execute('DELETE FROM documents WHERE path=?', (path,))
    from .memory_context import invalidate_source
    for path in set(indexed)-active:
        invalidate_source(store,path,'deleted')
    for path in paths:
        digest = hashlib.sha256(path.read_text(errors='replace')[:100000].encode()).hexdigest()
        if indexed.get(str(path)) != digest:
            invalidate_source(store,path,commit,digest)
            store.index(path, commit+'; file_sha256='+digest)
    return len(paths)
