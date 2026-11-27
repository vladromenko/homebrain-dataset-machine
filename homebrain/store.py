"""Local memory and provenance-bearing full-text retrieval."""
import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path

STOP_WORDS = set("what which why how when where should would could can has have had the this that these those are was were did does for from with into about still next new current please explain help tell provide find need any all and not our your my been kept".split())


class Store:
    def __init__(self, path):
        self.path = path
        self.hybrid = None
        with self.db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS memory(id INTEGER PRIMARY KEY,scope TEXT,
              text TEXT,verified INTEGER,source TEXT,created REAL);
            CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY,session TEXT,
              role TEXT,text TEXT,created REAL);
            CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY,value TEXT);
            CREATE VIRTUAL TABLE IF NOT EXISTS documents USING fts5(
              text,path UNINDEXED,hash UNINDEXED,revision UNINDEXED,indexed UNINDEXED);
            CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,event TEXT,
              data TEXT,created REAL);
            """)

    def db(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def state(self, key, default=None):
        with self.db() as db:
            row = db.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def put(self, key, value):
        with self.db() as db:
            db.execute("INSERT OR REPLACE INTO state VALUES (?,?)", (key,json.dumps(value)))

    def audit(self, event, data):
        with self.db() as db:
            db.execute("INSERT INTO audit VALUES(NULL,?,?,?)", (event,json.dumps(data),time.time()))

    def history(self, session, role=None, text=None):
        with self.db() as db:
            if role:
                db.execute("INSERT INTO history VALUES(NULL,?,?,?,?)", (session,role,text,time.time()))
            rows = db.execute("SELECT role,text,created FROM history WHERE session=? ORDER BY id DESC LIMIT 24", (session,)).fetchall()
        return [dict(row) for row in reversed(rows)]

    def memories(self):
        with self.db() as db:
            return [dict(r) for r in db.execute("SELECT * FROM memory ORDER BY id DESC LIMIT 200")]

    def remember(self, scope, text, source):
        with self.db() as db:
            db.execute("INSERT INTO memory VALUES(NULL,?,?,0,?,?)", (scope,text,source,time.time()))

    def forget(self, identifier):
        with self.db() as db:
            db.execute("DELETE FROM memory WHERE id=?", (identifier,))

    def index(self, path, revision="unknown"):
        content = Path(path).read_text(errors="replace")[:100000]
        digest = hashlib.sha256(content.encode()).hexdigest()
        with self.db() as db:
            db.execute("DELETE FROM documents WHERE path=?", (str(path),))
            for offset in range(0,len(content),2200):
                db.execute("INSERT INTO documents VALUES(?,?,?,?,?)", (content[offset:offset+2600],str(path),digest,revision,time.time()))

    def search(self, query):
        terms = [t for t in re.findall(r"[A-Za-z0-9_]{3,}",query) if t.lower() not in STOP_WORDS][:10]
        match = " OR ".join('"'+t+'"' for t in terms)
        with self.db() as db:
            rows = db.execute("SELECT *,bm25(documents) rank FROM documents WHERE documents MATCH ? ORDER BY rank LIMIT 20", (match,)).fetchall() if match else []
        result = {}
        for row in rows:
            if row["path"] not in result:
                result[row["path"]] = dict(row)
        return list(result.values())[:4]

    def retrieve(self, query, mode="lexical"):
        return self.hybrid.search(query) if mode=="hybrid" and self.hybrid else self.search(query)
