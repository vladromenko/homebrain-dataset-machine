"""Single-use POST browser handoff issued to authenticated launchers."""
import hashlib
import secrets
import time


def issue(journal, launcher):
    ticket = secrets.token_urlsafe(32)
    digest = hashlib.sha256(ticket.encode()).hexdigest()
    with journal.db() as db:
        db.execute("DELETE FROM tickets WHERE expires<?", (time.time()-60,))
        db.execute("INSERT INTO tickets VALUES(?,?,NULL,?)", (digest,time.time()+60,launcher[:100]))
    return {"ticket":ticket,"expires_in_s":60,"method":"POST","path":"/api/launcher/handoff","field":"ticket"}


def consume(journal, ticket):
    digest = hashlib.sha256(ticket.encode()).hexdigest()
    with journal.db() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM tickets WHERE digest=?", (digest,)).fetchone()
        if row is None or row["used"] is not None or row["expires"]<time.time():
            raise PermissionError("Launcher ticket expired or already used; reopen Homebrain")
        db.execute("UPDATE tickets SET used=? WHERE digest=?", (time.time(),digest))
    return row["launcher"]
