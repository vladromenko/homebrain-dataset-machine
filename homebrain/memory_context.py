"""Memory has provenance and invalidation; it never owns operational state."""
import json
import time


def initialize(store):
    with store.db() as db:
        db.executescript('''CREATE TABLE IF NOT EXISTS memory_evidence(
            memory_id INTEGER PRIMARY KEY, project_id TEXT, device_id TEXT,
            source_commit TEXT, verification TEXT, confidence REAL, superseded_by INTEGER,
            expires REAL, dependencies TEXT);''')


def attach(store, identifier, project=None, device=None, commit=None, verification='unverified', confidence=.5, dependencies=None):
    initialize(store)
    with store.db() as db:
        db.execute('INSERT OR REPLACE INTO memory_evidence VALUES(?,?,?,?,?,?,NULL,NULL,?)',
                   (identifier,project,device,commit,verification,confidence,json.dumps(dependencies or {})))


def retrieve(store, project=None, device=None, task=None):
    initialize(store)
    with store.db() as db:
        rows = db.execute('''SELECT m.*,e.project_id,e.device_id,e.source_commit,e.verification,e.confidence,e.dependencies
            FROM memory m LEFT JOIN memory_evidence e ON e.memory_id=m.id
            WHERE (e.project_id IS NULL OR e.project_id=?) AND (e.device_id IS NULL OR e.device_id=?)
            AND (m.scope IN ('lab','preference') OR e.project_id=?)
            AND e.superseded_by IS NULL AND (e.expires IS NULL OR e.expires>?)
            ORDER BY m.verified DESC,m.id DESC LIMIT 8''', (project,device,project,time.time())).fetchall()
    return [dict(row) for row in rows
            if not json.loads(row['dependencies'] or '{}').get('task_id')
            or json.loads(row['dependencies']).get('task_id')==task]


def supersede(store, old, new):
    initialize(store)
    with store.db() as db:
        db.execute('UPDATE memory_evidence SET superseded_by=? WHERE memory_id=?', (new,old))
    store.audit('memory_superseded', {'old':old, 'new':new})


def invalidate_device(store, device, reason):
    initialize(store)
    with store.db() as db:
        db.execute('UPDATE memory_evidence SET expires=? WHERE device_id=? AND dependencies != ?', (time.time(),device,'{}'))
    store.audit('dependent_memory_invalidated', {'device':device,'reason':reason})


def invalidate_source(store, path, revision, digest=None):
    initialize(store)
    invalid = []
    with store.db() as db:
        for row in db.execute('SELECT memory_id,dependencies FROM memory_evidence WHERE expires IS NULL'):
            dependencies = json.loads(row['dependencies'])
            if dependencies.get('source_path')==str(path):
                expected_hash = dependencies.get('source_sha256')
                changed = expected_hash != digest if expected_hash else dependencies.get('source_commit') != revision
                if changed or revision=='deleted':
                    invalid.append(row['memory_id'])
        db.executemany('UPDATE memory_evidence SET expires=? WHERE memory_id=?',
                       [(time.time(),identifier) for identifier in invalid])
    if invalid:
        store.audit('source_memory_invalidated',{'path':str(path),'revision':revision,'memory_ids':invalid})
