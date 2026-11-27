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


def retrieve(store, project=None, device=None):
    initialize(store)
    with store.db() as db:
        rows = db.execute('''SELECT m.*,e.project_id,e.device_id,e.source_commit,e.verification,e.confidence
            FROM memory m LEFT JOIN memory_evidence e ON e.memory_id=m.id
            WHERE (e.project_id IS NULL OR e.project_id=?) AND (e.device_id IS NULL OR e.device_id=?)
            AND (m.scope IN ('lab','preference') OR e.project_id=?)
            AND e.superseded_by IS NULL AND (e.expires IS NULL OR e.expires>?)
            ORDER BY m.verified DESC,m.id DESC LIMIT 8''', (project,device,project,time.time())).fetchall()
    return [dict(row) for row in rows]


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
