import io
import json
import time
import urllib.error

import pytest

from finrag.llm.cache import SQLiteLLMCache
from finrag.llm.client import (
    LLMAuthenticationError,
    LLMResponseError,
    OpenAICompatibleClient,
)
from finrag.llm.rate_limiter import RateLimiter


def _response(payload):
    return io.BytesIO(json.dumps(payload).encode())


def test_cache_keeps_original_metadata(tmp_path):
    cache = SQLiteLLMCache(str(tmp_path / "cache.sqlite"))
    cache.put("k", "answer", {"total_tokens": 3}, 12.5)
    hit = cache.get("k")
    assert hit and hit.text == "answer" and hit.usage["total_tokens"] == 3
    assert hit.latency_ms == 12.5

def test_client_uses_cache_without_network(tmp_path):
    cache = SQLiteLLMCache(str(tmp_path / "cache.sqlite"))
    client = OpenAICompatibleClient("http://invalid", "key", "model", cache=cache)
    cache_key_payload = '{"messages": [{"content": "hi", "role": "user"}], "model": "model"}'
    import hashlib
    cache.put(hashlib.sha256(cache_key_payload.encode()).hexdigest(), "cached", {}, 9)
    response = client.complete("hi")
    assert response.cached and response.text == "cached"


def test_cache_miss_then_hit_makes_one_provider_call(tmp_path, monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, timeout))
        response = _response({"choices": [{"message": {"content": "live"}}], "usage": {"total_tokens": 7}})
        response.__enter__ = lambda: response
        response.__exit__ = lambda *args: None
        return response

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    cache = SQLiteLLMCache(str(tmp_path / "cache.sqlite"))
    client = OpenAICompatibleClient("http://provider", "key", "model", cache=cache, max_retries=0)
    first = client.complete("hello")
    second = OpenAICompatibleClient("http://provider", "key", "model", cache=SQLiteLLMCache(str(tmp_path / "cache.sqlite")), max_retries=0).complete("hello")
    assert len(calls) == 1
    assert first.text == second.text == "live"
    assert second.cached and second.usage == first.usage and second.latency_ms == first.latency_ms


def test_cache_key_changes_with_generation_parameters(tmp_path, monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(json.loads(request.data))
        response = _response({"choices": [{"message": {"content": str(len(calls))}}]})
        response.__enter__ = lambda: response
        response.__exit__ = lambda *args: None
        return response

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = OpenAICompatibleClient("http://provider", "key", "model", cache=SQLiteLLMCache(str(tmp_path / "cache.sqlite")), max_retries=0)
    client.complete("same", temperature=0)
    client.complete("same", temperature=1)
    assert len(calls) == 2


def test_4xx_is_not_retried(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(1)
        raise urllib.error.HTTPError(request.full_url, 400, "bad request", {}, io.BytesIO(b"{}"))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = OpenAICompatibleClient("http://provider", "key", "model", max_retries=3)
    with pytest.raises(Exception):
        client.complete("bad")
    assert len(calls) == 1


def test_auth_error_is_classified(monkeypatch):
    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 401, "unauthorized", {}, io.BytesIO(b"{}"))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(LLMAuthenticationError):
        OpenAICompatibleClient("http://provider", "key", "model", max_retries=2).complete("bad")


def test_malformed_json_is_safe(monkeypatch):
    response = io.BytesIO(json.dumps({"choices": [{"message": {"content": "{bad"}}]}).encode())
    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: response)
    with pytest.raises(LLMResponseError):
        OpenAICompatibleClient("http://provider", "key", "model", max_retries=0).generate_json("ignored")


def test_rate_limiter_spaces_requests(monkeypatch):
    sleeps = []
    now = [0.0]
    monkeypatch.setattr(time, "monotonic", lambda: now[0])
    monkeypatch.setattr(time, "sleep", lambda delay: sleeps.append(delay))
    limiter = RateLimiter(120)
    limiter.wait()
    now[0] = 0.1
    limiter.wait()
    assert sleeps == [0.4]
