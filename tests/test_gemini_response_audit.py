"""Keep final output and termination evidence without retaining thought parts."""
import json
import pytest

from campusai.llm.client import GeminiClient, LLMResponseError
from evaluation.reranker.collect_paired_answers import recording_generate


def provider(monkeypatch, parts, reason='STOP'):
    monkeypatch.setattr('campusai.llm.client._request_json', lambda *_args, **_kwargs:
        {'candidates': [{'content': {'parts': parts}, 'finishReason': reason}],
         'usageMetadata': {'promptTokenCount': 7, 'candidatesTokenCount': 2, 'thoughtsTokenCount': 3},
         'modelVersion': 'gemini-3.8-flash-001'})
    return GeminiClient('synthetic-test-key', cache=None, max_retries=0)


def test_final_response_audit_excludes_thoughts_and_keeps_finish_reason(monkeypatch):
    client = provider(monkeypatch, [{'text': 'private reasoning', 'thought': True},
                                   {'text': '{"answer":'}, {'text': '"public"}'}])
    calls = []
    client.generate = recording_generate(client.generate, calls)
    assert client.generate_json('question')['answer'] == 'public'
    assert calls[0]['finish_reason'] == 'STOP'
    assert calls[0]['response_text'] == '{"answer":"public"}'
    assert 'private reasoning' not in json.dumps(calls)
    assert calls[0]['usage']['thoughtsTokenCount'] == 3


def test_truncated_final_response_is_saved_before_json_parse_failure(monkeypatch):
    client = provider(monkeypatch, [{'text': '{"answer":'}], reason='MAX_TOKENS')
    calls = []
    client.generate = recording_generate(client.generate, calls)
    with pytest.raises(LLMResponseError):
        client.generate_json('question')
    assert calls[0]['response_text'] == '{"answer":'
    assert calls[0]['finish_reason'] == 'MAX_TOKENS'
    assert calls[0]['provider_status'] == 'completed'


def test_thought_only_response_cannot_become_application_answer(monkeypatch):
    client = provider(monkeypatch, [{'text': '{"answer":"private"}', 'thought': True}])
    with pytest.raises(LLMResponseError, match='no final text'):
        client.generate_json('question')


def test_provider_model_version_is_retained_for_cross_window_acceptance(monkeypatch):
    client = provider(monkeypatch, [{'text': 'answer'}])
    try:
        assert client.complete('question').model_version == 'gemini-3.8-flash-001'
    finally:
        client.close()
