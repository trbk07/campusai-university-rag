"""Provider clients for the foundation layer.

The module intentionally uses the standard library for transport and keeps
provider-specific response parsing behind a small common interface.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import sqlite3
from .retry import retry503
from .overload import OverloadCircuit, ProviderCoolingDown
from contextlib import contextmanager
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from threading import Lock
from typing import Any, Iterator, Protocol


class LLMError(Exception):
    """Base class for provider and response failures."""


class LLMAuthenticationError(LLMError):
    """The provider rejected credentials."""


class LLMRateLimitError(LLMError):
    """The provider rate-limited the request."""


class LLMProviderError(LLMError):
    """A non-retryable provider or network failure."""


class LLMResponseError(LLMError):
    """The provider returned an unusable response."""


@dataclass(frozen=True)
class LLMResponse:
    """Text returned by a provider and its measurements."""

    text: str
    usage: dict
    latency_ms: float
    cached: bool = False
    finish_reason: str | None = None
    model_version: str | None = None


class LLMClient(Protocol):
    """Interface used by the rest of the application."""

    def complete(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """Generate one response."""

    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """Generate text through the provider."""

    def generate_json(
        self,
        prompt: str,
        schema: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate and parse a JSON object."""


def _hash_payload(payload: dict[str, Any]) -> str:
    """Create a stable cache key for a JSON-compatible payload."""

    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _safe_endpoint(endpoint: str) -> str:
    """Return endpoint identity without query-string credentials."""

    parsed = urllib.parse.urlsplit(endpoint)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _credential_free_endpoint(endpoint: str) -> str:
    """Remove credential-like query parameters before sending a request."""

    parsed = urllib.parse.urlsplit(endpoint)
    query = [
        (key, value)
        for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in {"key", "api_key", "apikey", "access_token", "token"}
    ]
    return urllib.parse.urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urllib.parse.urlencode(query),
            parsed.fragment,
        )
    )


def build_cache_key(
    *,
    provider: str,
    endpoint: str,
    request: dict[str, Any],
) -> str:
    """Build the canonical provider-independent cache key.

    The key contains request semantics and a redacted endpoint identity, but
    never contains an API key. Every provider client uses this helper.
    """

    return _hash_payload(
        {
            "provider": provider,
            "endpoint": _safe_endpoint(endpoint),
            "request": request,
        }
    )


_KEY_LOCKS: dict[str, tuple[Lock, int]] = {}
_KEY_LOCKS_GUARD = Lock()


@contextmanager
def _single_flight(key: str) -> Iterator[None]:
    """Serialize a cache miss/provider call/cache write for one key.

    The lock is process-local. SQLite still provides cross-process durability;
    a process-local lock prevents duplicate calls from threads in this process.
    """

    with _KEY_LOCKS_GUARD:
        entry = _KEY_LOCKS.get(key)
        lock = entry[0] if entry else Lock()
        _KEY_LOCKS[key] = (lock, (entry[1] if entry else 0) + 1)
    try:
        with lock:
            yield
    finally:
        with _KEY_LOCKS_GUARD:
            current = _KEY_LOCKS.get(key)
            if current and current[0] is lock:
                if current[1] <= 1:
                    _KEY_LOCKS.pop(key, None)
                else:
                    _KEY_LOCKS[key] = (lock, current[1] - 1)


def _retry_after_seconds(value: str | None) -> float | None:
    """Parse Retry-After's delta-seconds or HTTP-date forms."""

    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        pass
    try:
        date = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
    if date is None:
        return None
    return max(0.0, date.timestamp() - time.time())


def _sleep_backoff(attempt: int, retry_after: float | None = None) -> None:
    """Sleep with bounded exponential backoff when no limiter is configured."""

    if retry_after is None:
        retry_after = min(60.0, 0.5 * (2**max(0, attempt)) + 0.25)
    time.sleep(min(60.0, max(0.0, retry_after)))


def _request_json(request, timeout: int, limiter, max_retries: int, *, retry_only_503=False,
                  retry_min_wait_seconds=30.0, retry_max_wait_seconds=60.0) -> dict:
    """Issue a bounded retry request and classify provider failures."""

    transient = {408, 429, 500, 502, 503, 504}
    transport = urllib.request.urlopen
    if retry_only_503:
        original = transport
        transport = lambda req, _limit=max_retries, **kw: retry503(
            req, original, max_retries=_limit, min_wait_seconds=retry_min_wait_seconds,
            max_wait_seconds=retry_max_wait_seconds, **kw)
        max_retries = 0  # The narrow transport owns retries; never nest loops.
    for attempt in range(max_retries + 1):
        try:
            with transport(request, timeout=timeout) as response:
                data = json.load(response)
                if not isinstance(data, dict):
                    raise LLMResponseError("provider response must be a JSON object")
                return data
        except urllib.error.HTTPError as error:
            if error.code in {401, 403}:
                raise LLMAuthenticationError("provider authentication failed") from error
            detail = ""
            try:
                raw_detail = error.read().decode("utf-8", errors="replace")
                if raw_detail:
                    try:
                        parsed_detail = json.loads(raw_detail)
                        detail = str(parsed_detail.get("error", {}).get("message", ""))
                    except (json.JSONDecodeError, AttributeError):
                        detail = raw_detail[:300]
            except (OSError, UnicodeError, ValueError):
                detail = ""
            suffix = f": {detail[:300]}" if detail else ""
            failure = (
                LLMRateLimitError(f"provider rate limit exceeded{suffix}")
                if error.code == 429
                else LLMProviderError(f"provider returned HTTP {error.code}{suffix}")
            )
            if error.code not in transient or attempt >= max_retries:
                raise failure from error
            retry_seconds = _retry_after_seconds(error.headers.get("Retry-After"))
            if limiter is not None:
                limiter.backoff(attempt, retry_seconds)
            else:
                _sleep_backoff(attempt, retry_seconds)
        except (TimeoutError, urllib.error.URLError) as error:
            if attempt >= max_retries:
                raise LLMProviderError("provider request failed") from error
            if limiter is not None:
                limiter.backoff(attempt)
            else:
                _sleep_backoff(attempt)
        except json.JSONDecodeError as error:
            raise LLMResponseError("provider returned malformed JSON") from error
    raise LLMProviderError("provider request failed after retries")


def _validate_schema(value: Any, schema: dict[str, Any], path: str = "$") -> None:
    """Validate the deliberately supported T1 JSON Schema subset."""

    expected = schema.get("type")
    valid = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }
    if expected in valid and not valid[expected]:
        raise LLMResponseError(f"JSON schema type mismatch at {path}")
    if "enum" in schema and value not in schema["enum"]:
        raise LLMResponseError(f"JSON schema enum mismatch at {path}")
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise LLMResponseError(f"JSON schema minLength mismatch at {path}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise LLMResponseError(f"JSON schema maxLength mismatch at {path}")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            raise LLMResponseError(f"JSON schema pattern mismatch at {path}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise LLMResponseError(f"JSON schema minimum mismatch at {path}")
        if "maximum" in schema and value > schema["maximum"]:
            raise LLMResponseError(f"JSON schema maximum mismatch at {path}")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                raise LLMResponseError(f"JSON schema missing required field: {path}.{key}")
        properties = schema.get("properties", {})
        for key, child in properties.items():
            if key in value:
                _validate_schema(value[key], child, f"{path}.{key}")
        if schema.get("additionalProperties") is False:
            unknown = set(value) - set(properties)
            if unknown:
                raise LLMResponseError(
                    f"JSON schema unexpected field: {path}.{sorted(unknown)[0]}"
                )
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            _validate_schema(item, schema["items"], f"{path}[{index}]")


_GEMINI_SCHEMA_KEYS = {
    "type", "format", "title", "description", "nullable", "enum",
    "items", "properties", "required", "propertyOrdering",
    "minItems", "maxItems", "minProperties", "maxProperties",
}


def _gemini_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Project application JSON Schema to Gemini's supported dialect."""

    def project(value: Any) -> Any:
        if isinstance(value, dict):
            result = {}
            for key, child in value.items():
                if key == "properties" and isinstance(child, dict):
                    result[key] = {name: project(node) for name, node in child.items()}
                elif key in _GEMINI_SCHEMA_KEYS:
                    projected = project(child)
                    if key == "type" and isinstance(projected, str):
                        projected = projected.upper()
                    result[key] = projected
            return result
        if isinstance(value, list):
            return [project(item) for item in value]
        return value

    projected = project(schema)
    if not isinstance(projected, dict):
        raise TypeError("Gemini response schema must be an object")
    return projected


class OpenAICompatibleClient:
    """Client for APIs with the OpenAI chat-completions response shape."""

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        model: str,
        cache=None,
        limiter=None,
        timeout: int = 60,
        max_retries: int = 3,
        retry_only_503: bool = False,
        retry_min_wait_seconds: float = 30.0,
        retry_max_wait_seconds: float = 60.0,
    ) -> None:
        if not endpoint or not model:
            raise ValueError("endpoint and model are required")
        if not api_key:
            raise LLMAuthenticationError("provider API key is required")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        if type(retry_only_503) is not bool or (retry_only_503 and max_retries not in (0, 1)):
            raise ValueError("retry_only_503 requires a boolean and at most one retry")
        if (not isinstance(retry_min_wait_seconds, (int, float)) or isinstance(retry_min_wait_seconds, bool)
                or not isinstance(retry_max_wait_seconds, (int, float)) or isinstance(retry_max_wait_seconds, bool)
                or not math.isfinite(retry_min_wait_seconds) or not math.isfinite(retry_max_wait_seconds)
                or retry_min_wait_seconds < 0 or retry_max_wait_seconds < retry_min_wait_seconds):
            raise ValueError("503 retry wait bounds must be ordered non-negative numbers")
        self.endpoint = endpoint
        self.api_key = api_key
        self.model = model
        self.provider = "openai-compatible"
        self.cache = cache
        self.limiter = limiter
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_only_503 = retry_only_503
        self.retry_min_wait_seconds = float(retry_min_wait_seconds)
        self.retry_max_wait_seconds = float(retry_max_wait_seconds)

    def close(self) -> None:
        """Release the client's cache when its application shuts down."""
        cache, self.cache = self.cache, None
        if cache is not None:
            cache.close()

    def _cached(self, cache_key: str):
        if self.cache is None:
            return None
        cached = self.cache.get(cache_key)
        if cached is not None:
            return LLMResponse(cached.text, cached.usage, cached.latency_ms, True)
        return None

    def complete(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """Send a prompt, or return its cached response.

        A second cache check inside the per-key lock is what makes concurrent
        identical cache misses single-flight.
        """

        request_options = dict(kwargs)
        system_prompt = request_options.pop("system_prompt", None)
        messages = []
        if system_prompt is not None:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": self.model, "messages": messages, **request_options}
        cache_key = build_cache_key(
            provider=self.provider,
            endpoint=self.endpoint,
            request=payload,
        )
        legacy_cache_key = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()

        cached = self._cached(cache_key)
        if cached is None and self.cache is not None:
            cached = self._cached(legacy_cache_key)
        if cached is not None:
            return cached

        with _single_flight(cache_key):
            cached = self._cached(cache_key)
            if cached is None and self.cache is not None:
                cached = self._cached(legacy_cache_key)
            if cached is not None:
                return cached

            if self.limiter is not None:
                self.limiter.wait()
            started_at = time.perf_counter()
            request = urllib.request.Request(
                self.endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
            data = _request_json(request, self.timeout, self.limiter, self.max_retries,
                                 retry_only_503=self.retry_only_503,
                                 retry_min_wait_seconds=self.retry_min_wait_seconds,
                                 retry_max_wait_seconds=self.retry_max_wait_seconds)
            try:
                text = data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as error:
                raise LLMResponseError(
                    "OpenAI-compatible response has invalid shape"
                ) from error
            if not isinstance(text, str):
                raise LLMResponseError("provider response content must be text")
            usage = data.get("usage", {})
            if not isinstance(usage, dict):
                usage = {}
            latency_ms = (time.perf_counter() - started_at) * 1000
            if self.cache is not None:
                self.cache.put(cache_key, text, usage, latency_ms)
            return LLMResponse(text, usage, latency_ms)

    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        return self.complete(prompt, **kwargs)

    def generate_json(
        self,
        prompt: str,
        schema: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Parse only JSON; model output is never executed as Python."""

        if schema is not None:
            kwargs.setdefault("response_format", {"type": "json_object"})
        text = self.generate(prompt, **kwargs).text.strip()
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.I | re.S)
        if fenced:
            text = fenced.group(1)
        try:
            value = json.loads(text)
        except json.JSONDecodeError as error:
            raise LLMResponseError("LLM returned malformed JSON") from error
        if not isinstance(value, dict):
            raise LLMResponseError("LLM JSON response must be an object")
        if schema is not None:
            _validate_schema(value, schema)
        return value


class GeminiClient(OpenAICompatibleClient):
    """Client for Google's Gemini generateContent REST endpoint."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3-flash-preview",
        generation_config: dict[str, Any] | None = None,
        overload_circuit_path: str | None = None,
        **kwargs: Any,
    ) -> None:
        if generation_config is not None and not isinstance(generation_config, dict):
            raise ValueError("generation_config must be a JSON object")
        # Isolate caller-owned nested settings; include them in the actual
        # request/cache identity, rather than relying on provider defaults.
        self.generation_config = json.loads(json.dumps(generation_config or {}, allow_nan=False))
        endpoint = kwargs.pop(
            "endpoint",
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        )
        endpoint = _credential_free_endpoint(endpoint)
        super().__init__(endpoint, api_key, model, **kwargs)
        self.provider = "gemini"
        if overload_circuit_path and self.max_retries:
            raise ValueError("overload circuit requires max_retries=0; recovery uses the next real request")
        self.overload_circuit = (OverloadCircuit(overload_circuit_path, _safe_endpoint(endpoint))
                                 if overload_circuit_path else None)

    def _send(self, request):
        circuit = self.overload_circuit
        generation = None
        try:
            if circuit:
                generation = circuit.acquire(self.timeout)
            if self.limiter is not None:
                self.limiter.wait()
            if circuit:
                circuit.check(generation)
            result = _request_json(request, self.timeout, self.limiter, self.max_retries,
                                   retry_only_503=self.retry_only_503,
                                   retry_min_wait_seconds=self.retry_min_wait_seconds,
                                   retry_max_wait_seconds=self.retry_max_wait_seconds)
        except ProviderCoolingDown as error:
            failure = LLMProviderError("provider is cooling down; please try again later")
            failure.retry_after_seconds = error.retry_after_seconds
            raise failure from None
        except sqlite3.Error:
            raise LLMProviderError("provider health state unavailable; request stopped") from None
        except LLMError as error:
            cause = error.__cause__
            if circuit and generation is not None:
                overloaded = isinstance(cause, urllib.error.HTTPError) and cause.code == 503
                hint = _retry_after_seconds(cause.headers.get("Retry-After")) if overloaded and cause.headers else None
                if hint is not None and not math.isfinite(hint):
                    hint = None
                try:
                    circuit.failed(generation, overloaded=overloaded, retry_after=hint)
                except sqlite3.Error:
                    raise LLMProviderError("provider health state unavailable; request stopped") from None
            raise
        else:
            if circuit:
                try:
                    circuit.succeeded(generation)
                except sqlite3.Error:
                    # The successful provider output remains usable; an old
                    # probe lease expires rather than triggering another call.
                    pass
            return result

    def complete(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """Send a prompt using Gemini's request and response schema."""

        request_options = dict(kwargs)
        if self.generation_config:
            overrides = request_options.pop("generationConfig", {})
            request_options["generationConfig"] = {**self.generation_config, **overrides}
        system_prompt = request_options.pop("system_prompt", None)
        body: dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            **request_options,
        }
        if system_prompt is not None:
            body["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        cache_key = build_cache_key(
            provider=self.provider,
            endpoint=self.endpoint,
            request=body,
        )
        cached = self._cached(cache_key)
        if cached is not None:
            return cached

        with _single_flight(cache_key):
            cached = self._cached(cache_key)
            if cached is not None:
                return cached
            request = urllib.request.Request(
                self.endpoint,
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key,
                },
            )
            started_at = time.perf_counter()
            data = self._send(request)
            try:
                candidate = data["candidates"][0]
                parts = candidate["content"]["parts"]
            except (KeyError, IndexError, TypeError) as error:
                raise LLMResponseError("Gemini response has invalid shape") from error
            if not isinstance(parts, list):
                raise LLMResponseError("provider response content must be text")
            # Native responses can place thought parts before the final answer.
            # Neither application parsing nor audit capture should expose them.
            text = "".join(part["text"] for part in parts if isinstance(part, dict)
                           and part.get("thought") is not True and isinstance(part.get("text"), str))
            if not text:
                raise LLMResponseError("Gemini response has no final text")
            usage = data.get("usageMetadata", {})
            if not isinstance(usage, dict):
                usage = {}
            latency_ms = (time.perf_counter() - started_at) * 1000
            if self.cache is not None:
                self.cache.put(cache_key, text, usage, latency_ms)
            reason = candidate.get("finishReason")
            model_version = data.get("modelVersion")
            return LLMResponse(text, usage, latency_ms,
                finish_reason=reason if isinstance(reason, str) else None,
                model_version=model_version if isinstance(model_version, str) else None)

    def generate_json(
        self,
        prompt: str,
        schema: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate JSON using Gemini's native generation configuration."""

        generation_config = dict(kwargs.pop("generationConfig", {}))
        generation_config["responseMimeType"] = "application/json"
        if schema is not None:
            generation_config["responseSchema"] = _gemini_schema(schema)
        response = self.generate(prompt, generationConfig=generation_config, **kwargs)
        text = response.text.strip()
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.I | re.S)
        if fenced:
            text = fenced.group(1)
        try:
            value = json.loads(text)
        except json.JSONDecodeError as error:
            raise LLMResponseError("LLM returned malformed JSON") from error
        if not isinstance(value, dict):
            raise LLMResponseError("LLM JSON response must be an object")
        if schema is not None:
            _validate_schema(value, schema)
        return value
