"""Provider clients for the foundation layer.

The module intentionally uses the standard library for transport and keeps
provider-specific response parsing behind a small common interface.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
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


def _request_json(request, timeout: int, limiter, max_retries: int) -> dict:
    """Issue a bounded retry request and classify provider failures."""

    transient = {408, 429, 500, 502, 503, 504}
    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.load(response)
                if not isinstance(data, dict):
                    raise LLMResponseError("provider response must be a JSON object")
                return data
        except urllib.error.HTTPError as error:
            if error.code in {401, 403}:
                raise LLMAuthenticationError("provider authentication failed") from error
            failure = (
                LLMRateLimitError("provider rate limit exceeded")
                if error.code == 429
                else LLMProviderError(f"provider returned HTTP {error.code}")
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
    ) -> None:
        if not endpoint or not model:
            raise ValueError("endpoint and model are required")
        if not api_key:
            raise LLMAuthenticationError("provider API key is required")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        self.endpoint = endpoint
        self.api_key = api_key
        self.model = model
        self.provider = "openai-compatible"
        self.cache = cache
        self.limiter = limiter
        self.timeout = timeout
        self.max_retries = max_retries

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
            data = _request_json(request, self.timeout, self.limiter, self.max_retries)
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
        model: str = "gemini-3.8-flash",
        **kwargs: Any,
    ) -> None:
        endpoint = kwargs.pop(
            "endpoint",
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        )
        endpoint = _credential_free_endpoint(endpoint)
        super().__init__(endpoint, api_key, model, **kwargs)
        self.provider = "gemini"

    def complete(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """Send a prompt using Gemini's request and response schema."""

        request_options = dict(kwargs)
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
            if self.limiter is not None:
                self.limiter.wait()
            request = urllib.request.Request(
                self.endpoint,
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key,
                },
            )
            started_at = time.perf_counter()
            data = _request_json(request, self.timeout, self.limiter, self.max_retries)
            try:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError, TypeError) as error:
                raise LLMResponseError("Gemini response has invalid shape") from error
            if not isinstance(text, str):
                raise LLMResponseError("provider response content must be text")
            usage = data.get("usageMetadata", {})
            if not isinstance(usage, dict):
                usage = {}
            latency_ms = (time.perf_counter() - started_at) * 1000
            if self.cache is not None:
                self.cache.put(cache_key, text, usage, latency_ms)
            return LLMResponse(text, usage, latency_ms)

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
            generation_config["responseSchema"] = schema
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
