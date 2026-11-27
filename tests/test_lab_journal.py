import asyncio
import json
import sqlite3
import time
import pytest
from homebrain.lab.journal import Journal, Conflict
from homebrain.lab.contracts import ActionRequest
from homebrain.lab.tickets import issue, consume


def request(**values):
    return ActionRequest(action='start_recording', project_id='demonstrations', session_id='one',
                         expected_revision=0, idempotency_key='unique-request', **values)


def test_durable_intent_and_duplicate_collision(tmp_path):
    journal = Journal(tmp_path/'lab.sqlite')
    operation, fresh = journal.intent(request())
    duplicate, again = Journal(journal.path).intent(request())
    assert fresh and not again and operation['id'] == duplicate['id']
    with pytest.raises(Conflict):
        journal.intent(request(arguments={'changed': True}))
    assert len(journal.unresolved()) == 1


def test_revision_fence_does_not_overwrite_other_result(tmp_path):
    journal = Journal(tmp_path/'lab.sqlite')
    journal.save_session({'session_id':'one', 'revision':0})
    journal.save_session({'session_id':'one', 'revision':1}, 0)
    with pytest.raises(Conflict):
        journal.save_session({'session_id':'one', 'revision':2}, 0)
    assert journal.session('one')['revision'] == 1


def test_ticket_consumed_once_and_expired_rejected(tmp_path):
    journal = Journal(tmp_path/'lab.sqlite')
    ticket = issue(journal, 'test-mac')['ticket']
    assert consume(journal, ticket) == 'test-mac'
    with pytest.raises(PermissionError):
        consume(journal, ticket)
    other = issue(journal, 'test-mac')['ticket']
    with journal.db() as db:
        db.execute('UPDATE tickets SET expires=?', (time.time()-1,))
    with pytest.raises(PermissionError):
        consume(journal, other)
    assert ticket not in str(sqlite3.connect(journal.path).execute('SELECT * FROM tickets').fetchall())
