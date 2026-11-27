"""Exact actuator utterances are an authorization guard, never the agent supervisor."""
import re


def authorized(text):
    words = ' '.join(re.findall(r'[a-z]+', text.lower()))
    phrases = {'start recording': 'start_recording', 'finish recording': 'finish_recording',
               'enable control': 'enable_control', 'stop': 'stop', 'prepare session':'prepare_session',
               'retry validation':'retry_validation', 'reconcile native state':'reconcile',
               'refresh project state':'refresh', 'review admission receipts':'review','submit reviewed job':'submit_job'}
    stripped = words.removeprefix('please ').removesuffix(' please')
    return {phrases[stripped]} if stripped in phrases else set()
