"""Envelope counters use retained native receipts; scientific counters stay project-owned."""
import json
from .contracts import Progress


def technically_valid(session):
    result = session['project_state'].get('technical_validation', {})
    if session['robot_id'] == 'so101':
        return result.get('state') == 'completed'
    return (result.get('quality') or {}).get('status') == 'pass'


def successful_motor(session):
    technical = session['project_state'].get('technical_validation', {})
    attempt = technical.get('attempt', {})
    observed = session['project_state'].get('outcome', {})
    if session['robot_id']=='so101':
        hardware = any(receipt.get('source')=='Studio' and receipt.get('native_episode',{}).get('source')=='hardware'
                       and receipt['native_episode'].get('test_only') is False for receipt in session['receipts'])
        return bool(hardware and technically_valid(session) and observed.get('label')=='success' and observed.get('assisted') is False)
    return bool(technically_valid(session) and attempt.get('outcome')=='success'
                and not attempt.get('user_excluded',True) and observed.get('label')=='success' and observed.get('assisted') is False)


def demonstrations(journal):
    with journal.db() as db:
        rows = db.execute("SELECT data FROM sessions WHERE json_extract(data,'$.project_id')='demonstrations'").fetchall()
    sessions = [json.loads(row[0]) for row in rows]
    attempts = [row for row in sessions if row['project_state'].get('started_at')]
    outcomes = [row['project_state'].get('outcome', {}) for row in attempts]
    saved = lambda row: any(receipt.get('source') in ('Studio','Explorer') for receipt in row['receipts'])
    return Progress(scope='Homebrain native development attempts',attempts=len(attempts),
        saved_raw=sum(saved(row) for row in attempts),technically_valid=sum(technically_valid(row) for row in attempts),
        successful_unassisted_motor=sum(successful_motor(row) for row in attempts),
        assisted=sum(outcome.get('assisted') is True for outcome in outcomes),
        valid_failures=sum(technically_valid(row) and row['project_state'].get('outcome',{}).get('label')=='failure' for row in attempts),
        unknown=sum(outcome.get('label')=='unknown' for outcome in outcomes),
        incomplete=sum(row['state']=='incomplete' for row in attempts),
        pending=sum(row['state'] in ('starting','recording','saving','checking') for row in attempts),
        source_groups={'purpose':'development','scientific_admission':'not_assessed'}).model_dump()
