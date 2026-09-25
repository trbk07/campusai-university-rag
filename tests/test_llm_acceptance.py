import io
import json
import builtins
import threading
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from email.utils import formatdate

import pytest

from campusai.llm.cache import SQLiteLLMCache
from campusai.llm.client import (
    GeminiClient,
    LLMAuthenticationError,
    LLMProviderError,
    LLMRateLimitError,
    OpenAICompatibleClient,
    LLMResponseError,
    _request_json,
    _sleep_backoff,
    _validate_schema,
    _gemini_schema,
    _retry_after_seconds,
    build_cache_key,
)
from campusai.llm.factory import (
    _fallback_yaml,
    _integer,
    _read_config,
    _scalar,
    create_llm,
)
from campusai.llm.rate_limiter import RateLimiter


def _response(payload):
    response = io.BytesIO(json.dumps(payload).encode())
    response.__enter__ = lambda: response
    response.__exit__ = lambda *args: None
    return response


def test_memory_cache_persists_between_operations():
    cache = SQLiteLLMCache(":memory:")
    cache.put("key", "value", {"total": 2}, 4.5)
    assert cache.get("key") == cache.get("key")
    assert cache.get("key").text == "value"
    assert cache.get("key").usage == {"total": 2}
    cache.close()


def test_identical_concurrent_requests_are_single_flight(tmp_path, monkeypatch):
    calls = 0
    call_lock = threading.Lock()
    started = threading.Event()
    release = threading.Event()

    def fake_urlopen(request, timeout):
        nonlocal calls
        with call_lock:
            calls += 1
        started.set()
        assert release.wait(2), "provider call did not finish"
        return _response({"choices": [{"message": {"content": "shared"}}]})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    cache = SQLiteLLMCache(str(tmp_path / "single-flight.sqlite"))
    client = OpenAICompatibleClient(
        "https://provider.test/chat", "secret", "model", cache=cache, max_retries=0
    )
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(client.complete, "same prompt") for _ in range(8)]
        assert started.wait(2)
        release.set()
        responses = [future.result(timeout=2) for future in futures]

    assert calls == 1
    assert {response.text for response in responses} == {"shared"}
    assert sum(response.cached for response in responses) == 7


def test_gemini_offline_contract_uses_header_and_safe_cache_key(tmp_path, monkeypatch):
    seen = []

    def fake_urlopen(request, timeout):
        seen.append((request.full_url, dict(request.headers), json.loads(request.data)))
        return _response(
            {
                "candidates": [{"content": {"parts": [{"text": "OK"}]}}],
                "usageMetadata": {"totalTokenCount": 3},
            }
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    secret = "gemini-secret-value"
    client = GeminiClient(
        secret,
        model="gemini-test",
        endpoint="https://provider.test/generate?key=secret&region=test",
        cache=SQLiteLLMCache(str(tmp_path / "gemini.sqlite")),
        max_retries=0,
    )
    first = client.complete("hello", system_prompt="be concise")
    second = client.complete("hello", system_prompt="be concise")

    assert first.text == "OK"
    assert second.cached is True
    assert len(seen) == 1
    url, headers, body = seen[0]
    assert secret not in url
    assert "region=test" in url
    assert "key=" not in url
    assert headers["X-goog-api-key"] == secret
    assert body["systemInstruction"]["parts"][0]["text"] == "be concise"
    assert secret not in build_cache_key(
        provider="gemini",
        endpoint=client.endpoint,
        request=body,
    )


@pytest.mark.parametrize("status", [408, 429, 500, 502, 503, 504])
def test_transient_http_errors_retry_then_succeed(status, monkeypatch):
    calls = 0

    def fake_urlopen(request, timeout):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise urllib.error.HTTPError(
                request.full_url, status, "temporary", {"Retry-After": "0"}, io.BytesIO()
            )
        return _response({"choices": [{"message": {"content": "recovered"}}]})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("campusai.llm.client._sleep_backoff", lambda *args: None)
    response = OpenAICompatibleClient(
        "https://provider.test/chat", "key", "model", max_retries=1
    ).complete("retry")
    assert response.text == "recovered"
    assert calls == 2


def test_timeout_retries_then_succeeds(monkeypatch):
    calls = 0

    def fake_urlopen(request, timeout):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TimeoutError("temporary timeout")
        return _response({"choices": [{"message": {"content": "recovered"}}]})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("campusai.llm.client._sleep_backoff", lambda *args: None)
    assert OpenAICompatibleClient(
        "https://provider.test/chat", "key", "model", max_retries=1
    ).complete("retry").text == "recovered"
    assert calls == 2


def test_retry_exhaustion_and_429_classification(monkeypatch):
    calls = 0

    def fake_urlopen(request, timeout):
        nonlocal calls
        calls += 1
        raise urllib.error.HTTPError(
            request.full_url, 429, "busy", {}, io.BytesIO()
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("campusai.llm.client._sleep_backoff", lambda *args: None)
    with pytest.raises(LLMRateLimitError):
        OpenAICompatibleClient(
            "https://provider.test/chat", "key", "model", max_retries=2
        ).complete("retry")
    assert calls == 3


def test_retry_after_http_date_is_supported(monkeypatch):
    monkeypatch.setattr("campusai.llm.client.time.time", lambda: 1_000.0)
    value = formatdate(1_003.0, usegmt=True)
    assert 2.0 <= _retry_after_seconds(value) <= 3.0


def test_retry_helpers_cover_limiter_and_invalid_date(monkeypatch):
    monkeypatch.setattr("campusai.llm.client.parsedate_to_datetime", lambda value: None)
    assert _retry_after_seconds("invalid-but-parseable") is None

    class FakeLimiter:
        def __init__(self):
            self.calls = []

        def backoff(self, *args):
            self.calls.append(args)

    limiter = FakeLimiter()
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: (_ for _ in ()).throw(
            urllib.error.HTTPError("https://provider.test", 500, "busy", {}, io.BytesIO())
        ),
    )
    request = __import__("urllib.request", fromlist=["Request"]).Request(
        "https://provider.test"
    )
    with pytest.raises(LLMProviderError):
        _request_json(request, 1, limiter, 1)
    assert len(limiter.calls) == 1
    with pytest.raises(LLMProviderError):
        _request_json(request, 1, None, -1)


def test_factory_reads_bom_nested_config_and_validates(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\ufeffllm:\n"
        "  provider: openai-compatible\n"
        "  model: test-model\n"
        "  endpoint: https://provider.test/v1/chat\n"
        "  timeout_seconds: 7\n"
        "  requests_per_minute: 0\n"
        "  max_retries: 2\n"
        f"  cache_path: {tmp_path / 'cache.sqlite'}\n",
        encoding="utf-8",
    )
    assert _read_config(config_path)["llm"]["timeout_seconds"] == 7
    client = create_llm(config_path, {"OPENAI_API_KEY": "secret"})
    assert isinstance(client, OpenAICompatibleClient)
    assert client.timeout == 7
    assert client.max_retries == 2


@pytest.mark.parametrize(
    ("body", "environment", "message"),
    [
        ("llm:\n  provider: unknown\n  model: m\n", {"KEY": "x"}, "unsupported"),
        ("llm:\n  provider: gemini\n", {"GEMINI_API_KEY": "x"}, "model"),
        ("llm:\n  provider: gemini\n  model: m\n  timeout_seconds: 0\n", {"GEMINI_API_KEY": "x"}, "timeout"),
    ],
)
def test_factory_rejects_invalid_config(tmp_path, body, environment, message):
    path = tmp_path / "bad.yaml"
    path.write_text(body, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        create_llm(path, environment)


def test_auth_error_does_not_expose_provider_details(monkeypatch):
    secret = "super-secret"

    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(
            request.full_url, 401, f"bad key {secret}", {}, io.BytesIO()
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(LLMAuthenticationError) as error:
        GeminiClient(secret, max_retries=0).complete("hello")
    assert secret not in str(error.value)


def test_retry_and_schema_edge_cases(monkeypatch):
    assert _retry_after_seconds(None) is None
    assert _retry_after_seconds("not-a-date") is None
    sleeps = []
    monkeypatch.setattr("campusai.llm.client.time.sleep", sleeps.append)
    _sleep_backoff(0)
    _sleep_backoff(0, 1000)
    assert sleeps == [0.75, 60.0]

    schema = {
        "type": "object",
        "required": ["name", "items"],
        "additionalProperties": False,
        "properties": {
            "name": {"type": "string", "minLength": 2, "maxLength": 5, "pattern": "^[A-Z]"},
            "items": {
                "type": "array",
                "items": {"type": "integer", "minimum": 1, "maximum": 3},
            },
        },
    }
    _validate_schema({"name": "OK", "items": [1, 3]}, schema)
    invalid_values = [
        ({"items": [1]}, schema),
        ({"name": "x", "items": [1]}, schema),
        ({"name": "ok", "items": [1]}, schema),
        ({"name": "OK", "items": [0]}, schema),
        ({"name": "OK", "items": [1], "extra": True}, schema),
    ]
    for value, invalid_schema in invalid_values:
        with pytest.raises(LLMResponseError):
            _validate_schema(value, invalid_schema)


def test_transport_error_classification_and_json_shapes(monkeypatch):
    def invalid_json(request, timeout):
        return io.BytesIO(b"{bad")

    monkeypatch.setattr("urllib.request.urlopen", invalid_json)
    with pytest.raises(LLMResponseError, match="malformed JSON"):
        OpenAICompatibleClient("https://provider.test", "key", "model", max_retries=0).complete("x")

    def non_object(request, timeout):
        return _response(["not", "object"])

    monkeypatch.setattr("urllib.request.urlopen", non_object)
    with pytest.raises(LLMResponseError, match="JSON object"):
        OpenAICompatibleClient("https://provider.test", "key", "model", max_retries=0).complete("x")

    def network_error(request, timeout):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr("urllib.request.urlopen", network_error)
    monkeypatch.setattr("campusai.llm.client._sleep_backoff", lambda *args: None)
    with pytest.raises(LLMProviderError):
        OpenAICompatibleClient("https://provider.test", "key", "model", max_retries=1).complete("x")

    def forbidden(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 403, "forbidden", {}, io.BytesIO())

    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    with pytest.raises(LLMAuthenticationError):
        OpenAICompatibleClient("https://provider.test", "key", "model", max_retries=2).complete("x")


def test_client_validation_and_response_validation(monkeypatch):
    with pytest.raises(ValueError):
        OpenAICompatibleClient("", "key", "model")
    with pytest.raises(ValueError):
        OpenAICompatibleClient("https://provider.test", "key", "", timeout=0)
    with pytest.raises(ValueError):
        OpenAICompatibleClient("https://provider.test", "key", "model", timeout=0)
    with pytest.raises(LLMAuthenticationError):
        OpenAICompatibleClient("https://provider.test", "", "model")
    with pytest.raises(ValueError):
        OpenAICompatibleClient("https://provider.test", "key", "model", max_retries=-1)

    responses = [
        {},
        {"choices": [{"message": {"content": 1}}]},
        {"choices": [{"message": {"content": "{}"}}], "usage": []},
    ]
    for payload in responses:
        monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout, payload=payload: _response(payload))
        if payload == {"choices": [{"message": {"content": "{}"}}], "usage": []}:
            assert OpenAICompatibleClient("https://provider.test", "key", "model", max_retries=0).complete("x").usage == {}
        else:
            with pytest.raises(LLMResponseError):
                OpenAICompatibleClient("https://provider.test", "key", "model", max_retries=0).complete("x")


def test_json_generation_and_gemini_error_shapes(monkeypatch):
    payloads = iter([
        {"choices": [{"message": {"content": "```json\n{\"ok\": true}\n```"}}]},
        {"choices": [{"message": {"content": "[]"}}]},
    ])
    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: _response(next(payloads)))
    client = OpenAICompatibleClient("https://provider.test", "key", "model", max_retries=0)
    assert client.generate_json("x", {"type": "object"}) == {"ok": True}
    with pytest.raises(LLMResponseError):
        client.generate_json("y")

    payloads = iter([
        {"candidates": [{"content": {"parts": [{"text": "{\"ok\": true}"}]}}]},
        {"candidates": [{"content": {"parts": [{"text": "not-json"}]}}]},
        {"candidates": [{}]},
    ])
    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: _response(next(payloads)))
    gemini = GeminiClient("key", max_retries=0)
    assert gemini.generate_json("x", {"type": "object"}) == {"ok": True}
    with pytest.raises(LLMResponseError):
        gemini.generate_json("y")
    with pytest.raises(LLMResponseError):
        gemini.complete("z")


def test_gemini_schema_projects_unsupported_json_schema_keywords():
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "answer": {"type": "string", "minLength": 1, "maxLength": 10},
            "items": {
                "type": "array",
                "items": {"type": "string", "pattern": "x"},
            },
        },
    }

    projected = _gemini_schema(schema)

    assert "additionalProperties" not in projected
    assert "minLength" not in projected["properties"]["answer"]
    assert "maxLength" not in projected["properties"]["answer"]
    assert "pattern" not in projected["properties"]["items"]["items"]
    assert projected["type"] == "OBJECT"
    assert projected["properties"]["answer"]["type"] == "STRING"


def test_limiter_paths_and_provider_response_types(monkeypatch):
    class FakeLimiter:
        def __init__(self):
            self.waits = 0

        def wait(self):
            self.waits += 1

        def backoff(self, *args):
            pass

    limiter = FakeLimiter()
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: _response({"choices": [{"message": {"content": "ok"}}]}),
    )
    client = OpenAICompatibleClient(
        "https://provider.test", "key", "model", limiter=limiter, max_retries=0
    )
    assert client.complete("x", system_prompt="system").text == "ok"
    assert limiter.waits == 1

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: _response({"candidates": [{"content": {"parts": [{"text": 1}]}}]}),
    )
    with pytest.raises(LLMResponseError):
        GeminiClient("key", limiter=limiter, max_retries=0).complete("x")
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: _response({"candidates": [{"content": {"parts": [{"text": "ok"}]}}], "usageMetadata": []}),
    )
    assert GeminiClient("key", limiter=limiter, max_retries=0).complete("x").usage == {}


def test_factory_fallback_parser_and_failures(tmp_path, monkeypatch):
    assert _scalar("true") is True
    assert _scalar("3.5") == 3.5
    assert _scalar("[1, 2]") == [1, 2]
    assert _scalar("{\"a\": 1}") == {"a": 1}
    assert _scalar("'quoted'") == "quoted"
    assert _fallback_yaml("root: plain # comment\n")["root"] == "plain"
    parsed = _fallback_yaml("root:\n  enabled: true\n  ratio: 1.5\n  values: [1, 2]\n")
    assert parsed["root"] == {"enabled": True, "ratio": 1.5, "values": [1, 2]}
    with pytest.raises(ValueError):
        _fallback_yaml("root:\n\tbad: true\n")
    with pytest.raises(ValueError):
        _fallback_yaml("not-a-mapping\n")
    with pytest.raises(ValueError):
        _fallback_yaml("root:\n  a: 1\n  a: 2\n")
    with pytest.raises(ValueError):
        _scalar("[bad")
    with pytest.raises(ValueError):
        _read_config(tmp_path / "missing.yaml")
    root_file = tmp_path / "scalar.yaml"
    root_file.write_text("true\n", encoding="utf-8")
    with pytest.raises(ValueError, match="root"):
        _read_config(root_file)

    original_import = builtins.__import__

    def without_yaml(name, *args, **kwargs):
        if name == "yaml":
            raise ImportError("yaml unavailable")
        return original_import(name, *args, **kwargs)

    fallback_config = tmp_path / "fallback.yaml"
    fallback_config.write_text("llm:\n  timeout_seconds: 5\n", encoding="utf-8")
    monkeypatch.setattr(builtins, "__import__", without_yaml)
    assert _read_config(fallback_config)["llm"]["timeout_seconds"] == 5

    with pytest.raises(ValueError):
        _integer({"x": True}, "x", 1, minimum=0)
    with pytest.raises(ValueError):
        _integer({"x": "bad"}, "x", 1, minimum=0)
    with pytest.raises(ValueError):
        _integer({"x": -1}, "x", 1, minimum=0)

    gemini_file = tmp_path / "gemini.yaml"
    gemini_file.write_text(
        "llm:\n  provider: gemini\n  model: m\n  endpoint: http://localhost:9000/generate\n  cache_path: "
        + str(tmp_path / "g.sqlite")
        + "\n",
        encoding="utf-8",
    )
    gemini = create_llm(gemini_file, {"GEMINI_API_KEY": "key"})
    assert isinstance(gemini, GeminiClient)
    bad_endpoint = tmp_path / "endpoint.yaml"
    bad_endpoint.write_text(
        "llm:\n  provider: openai\n  model: m\n  endpoint: relative\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="URL"):
        create_llm(bad_endpoint, {"OPENAI_API_KEY": "key"})


def test_limiter_and_cache_context(tmp_path, monkeypatch):
    with pytest.raises(ValueError):
        RateLimiter(-1)
    limiter = RateLimiter(0)
    monkeypatch.setattr("campusai.llm.rate_limiter.time.sleep", lambda delay: None)
    limiter.wait()
    limiter.backoff(1, 1000)
    with SQLiteLLMCache(str(tmp_path / "context.sqlite")) as cache:
        cache.put("key", "value", {}, 1)
        assert cache.get("key").text == "value"
