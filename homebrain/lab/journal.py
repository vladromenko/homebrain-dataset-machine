"""Persist intent before effects; uncertainty is never retried blindly."""
import hashlib
import json
import sqlite3
import time
import uuid


class Conflict(ValueError):
    pass


class Journal:
    def __init__(self, path):
        self.path = str(path)
        with self.db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, revision INTEGER, data TEXT, updated REAL);
            CREATE TABLE IF NOT EXISTS operations(id TEXT PRIMARY KEY, request_key TEXT UNIQUE, fingerprint TEXT,
                session_id TEXT, action TEXT, state TEXT, request TEXT, result TEXT, created REAL);
            CREATE TABLE IF NOT EXISTS events(sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT, kind TEXT, revision INTEGER, created REAL, payload TEXT);
            CREATE TABLE IF NOT EXISTS tickets(digest TEXT PRIMARY KEY, expires REAL, used REAL, launcher TEXT);
            CREATE TABLE IF NOT EXISTS profiles(id TEXT PRIMARY KEY, data TEXT, updated REAL);
            """)

    def db(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def session(self, identifier):
        with self.db() as db:
            row = db.execute("SELECT data FROM sessions WHERE id=?", (identifier,)).fetchone()
        if row is None:
            raise KeyError("Session not found")
        return json.loads(row[0])

    def sessions(self):
        with self.db() as db:
            rows = db.execute("SELECT data FROM sessions ORDER BY updated DESC LIMIT 100").fetchall()
        return [json.loads(row[0]) for row in rows]

    def save_session(self, data, expected=None):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT revision FROM sessions WHERE id=?", (data["session_id"],)).fetchone()
            if expected is not None and (row is None or row[0] != expected):
                raise Conflict("Session revision changed; refresh the authoritative snapshot")
            db.execute("INSERT OR REPLACE INTO sessions VALUES(?,?,?,?)",
                       (data["session_id"],data["revision"],json.dumps(data),time.time()))
        self.event(data["session_id"], "session", data["revision"], data)

    def intent(self, request):
        payload = request.model_dump()
        fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM operations WHERE request_key=?", (request.idempotency_key,)).fetchone()
            if row:
                if row["fingerprint"] != fingerprint:
                    raise Conflict("Idempotency key was reused with different arguments")
                return dict(row), False
            identifier = uuid.uuid4().hex
            db.execute("INSERT INTO operations VALUES(?,?,?,?,?,?,?,?,?)", (identifier,request.idempotency_key,
                fingerprint,request.session_id,request.action,"pending",json.dumps(payload),None,time.time()))
        return {"id":identifier,"state":"pending","result":None}, True

    def complete(self, operation, result):
        with self.db() as db:
            db.execute("UPDATE operations SET state=?,result=? WHERE id=?", (result["status"],json.dumps(result),operation))
        self.event(None, "operation", result["revision"], result)

    def unresolved(self):
        with self.db() as db:
            rows = db.execute("SELECT * FROM operations WHERE state IN ('pending','unknown') ORDER BY created").fetchall()
        return [dict(row) for row in rows]

    def event(self, session, kind, revision, payload):
        with self.db() as db:
            db.execute("INSERT INTO events VALUES(NULL,?,?,?,?,?)", (session,kind,revision,time.time(),json.dumps(payload)))
            db.execute("DELETE FROM events WHERE sequence < (SELECT COALESCE(MAX(sequence),0)-2000 FROM events)")

    def events(self, after=0):
        with self.db() as db:
            rows = db.execute("SELECT * FROM events WHERE sequence>? ORDER BY sequence LIMIT 100", (after,)).fetchall()
        return [{**dict(row),"payload":json.loads(row["payload"])} for row in rows]

    def profile(self, identifier, data=None):
        with self.db() as db:
            if data is not None:
                db.execute("INSERT OR REPLACE INTO profiles VALUES(?,?,?)", (identifier,json.dumps(data),time.time()))
            row = db.execute("SELECT data FROM profiles WHERE id=?", (identifier,)).fetchone()
        return json.loads(row[0]) if row else None

    def operations(self, session):
        with self.db() as db:
            rows = db.execute("SELECT result FROM operations WHERE session_id=? AND result IS NOT NULL ORDER BY created DESC LIMIT 10", (session,)).fetchall()
        return [json.loads(row[0]) for row in rows]
