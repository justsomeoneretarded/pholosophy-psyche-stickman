"""Observed Groq OTPM limits must not produce impossible repeated retries."""
import pytest
from pipeline.writing.llm import Groq, WriterError

class TooLarge(Exception):
    status_code = 429
    body = 'Request too large on output tokens per minute (OTPM): Limit 1000, Requested 3000.'

def client():
    c = Groq.__new__(Groq)
    c.model = 'test-model'
    c.optional = {}
    return c

def test_reported_output_cap_is_respected_and_remembered():
    c = client()
    budgets = []
    def call(payload):
        budgets.append(payload['max_tokens'])
        if len(budgets) == 1:
            raise TooLarge()
        return {'choices': [{'finish_reason': 'stop', 'message': {'content': '{"ok": true}'}}]}
    c._call = call
    assert c.complete('system', 'user', max_tokens=3000) == '{"ok": true}'
    assert budgets == [3000, 968]
    c.complete('system', 'another request', max_tokens=3000)
    assert budgets[-1] == 968

def test_truncated_cap_limited_reply_falls_back_instead_of_requesting_impossible_budget():
    c = client()
    c._output_cap = 968
    c._call = lambda payload: {'choices': [{'finish_reason': 'length', 'message': {'content': '{"partial":'}}]}
    with pytest.raises(WriterError, match='968-token output cap'):
        c.complete('system', 'user', max_tokens=6500)
