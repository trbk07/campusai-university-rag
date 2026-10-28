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
from .quota_hints import google_quota_hints, scoped_quota_hint
from .quota import QuotaExceeded, QuotaStateError, estimate_gemini_tokens
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
    input_measurement: dict | None = None


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
        number = float(value)
        return max(0.0, number) if math.isfinite(number) else None
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
                  retry_min_wait_seconds=30.0, retry_max_wait_seconds=60.0,
                  response_reader=None) -> dict:
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
                data = response_reader(response) if response_reader else json.load(response)
                if not isinstance(data, dict):
                    raise LLMResponseError("provider response must be a JSON object")
                return data
        except urllib.error.HTTPError as error:
            if error.code in {401, 403}:
                raise LLMAuthenticationError("provider authentication failed") from error
            detail = ""
            parsed_detail = {}
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
            if error.code == 429:
                failure.quota_hints = google_quota_hints(parsed_detail)
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
        except (json.JSONDecodeError, RecursionError) as error:
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
        quota_governor=None,
        json_mode: str = 'native',
        allow_pdf_scope: bool = False,
        project_router=None,
        **kwargs: Any,
    ) -> None:
        if generation_config is not None and not isinstance(generation_config, dict):
            raise ValueError("generation_config must be a JSON object")
        # Isolate caller-owned nested settings; include them in the actual
        # request/cache identity, rather than relying on provider defaults.
        self.generation_config = json.loads(json.dumps(generation_config or {}, allow_nan=False))
        if json_mode not in {'native', 'prompt'}:
            raise ValueError('json_mode must be native or prompt')
        self.json_mode = json_mode
        endpoint = kwargs.pop(
            "endpoint",
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        )
        endpoint = _credential_free_endpoint(endpoint)
        super().__init__(endpoint, api_key, model, **kwargs)
        self.provider = "gemini"
        if overload_circuit_path and self.max_retries:
            raise ValueError("overload circuit requires max_retries=0; recovery uses the next real request")
        if quota_governor is not None and self.max_retries:
            raise ValueError('quota admission requires max_retries=0; each attempt needs a reservation')
        self.quota_governor = quota_governor
        self._count_tokens_governor = None
        self._count_tokens_governor_identity = None
        if (type(allow_pdf_scope) is not bool or (allow_pdf_scope and
                (self.max_retries != 0 or quota_governor is None))):
            raise ValueError('PDF scope requires explicit opt-in, durable quota and max_retries=0')
        self.allow_pdf_scope = allow_pdf_scope
        if project_router is not None:
            from .project_router import GeminiProjectRouter
            if (not isinstance(project_router, GeminiProjectRouter) or project_router.model != model
                    or self.max_retries != 0 or quota_governor is None or not overload_circuit_path):
                raise ValueError('project routing requires durable quota,shared overload protection and no retries')
        self.project_router = project_router
        self.overload_circuit = (OverloadCircuit(overload_circuit_path, _safe_endpoint(endpoint))
                                 if overload_circuit_path else None)

    @property
    def count_tokens_quota_governor(self):
        """Durable project-scoped tokenization quota, separate from inference.

        Google documents countTokens as outside model RPM/TPM/RPD. HTTP
        collection budgets still count both endpoints. Derive from the active
        governor so an operator's explicit project selection remains correct.
        """
        base = self.quota_governor
        if base is None:
            return None
        identity = (str(base.path.resolve()), base.scope, base.identity)
        if identity != self._count_tokens_governor_identity:
            from .quota import QuotaGovernor, QuotaPolicy
            scope = base.scope + ':countTokens'
            if len(scope) > 200:
                scope = 'countTokens:' + hashlib.sha256(base.scope.encode()).hexdigest()
            self._count_tokens_governor = QuotaGovernor(base.path, scope,
                QuotaPolicy(3000, max_in_flight=base.policy.max_in_flight),
                max_wait_seconds=base.max_wait_seconds)
            self._count_tokens_governor_identity = identity
        return self._count_tokens_governor

    def _send(self, request, *, token_budget=None, stream=None):
        circuit = self.overload_circuit
        governor = self.quota_governor
        generation = None
        reservation = None
        project = None
        attempted = False
        result = None
        # urllib has distinct header/read waits. Keep an active stream's lease
        # through both socket waits, including cancellation at an I/O checkpoint.
        lease_timeout = self.timeout * (2 if stream is not None else 1)
        try:
            if urllib.parse.urlsplit(request.full_url).path.endswith(':countTokens'):
                governor = self.count_tokens_quota_governor
            if governor is not None:
                try:
                    if token_budget is None:
                        input_tokens, output_tokens = estimate_gemini_tokens(json.loads(request.data))
                    else:
                        if (not self.allow_pdf_scope or not isinstance(token_budget, tuple)
                                or len(token_budget) != 2
                                or any(type(n) is not int or not 0 <= n <= 1_000_000_000 for n in token_budget)):
                            raise ValueError('invalid PDF token budget')
                        input_tokens, output_tokens = token_budget
                except (ValueError, TypeError, AttributeError):
                    raise LLMProviderError('request cannot be admitted under the text token budget') from None
            if circuit:
                generation = circuit.acquire(lease_timeout)
            if self.project_router is not None:
                try:
                    project = self.project_router.route(request, lease_timeout)
                except ValueError:
                    raise LLMProviderError('request is outside independent project routing scope') from None
                request = project.request
            def check_admission():
                if circuit:
                    circuit.check(generation)
                if project:
                    project.circuit.check(project.generation)
            if governor is not None:
                reservation = governor.reserve(input_tokens, output_tokens,
                    lease_seconds=lease_timeout + 5,
                    check=check_admission if circuit or project else None)
            elif self.limiter is not None:
                self.limiter.wait()
            check_admission()
            reader = None
            if stream is not None:
                from .streaming import read_gemini_stream
                stream.begin(self.model)
                reader = lambda response: read_gemini_stream(response, stream, self.timeout)
            attempted = True
            result = _request_json(request, self.timeout, self.limiter, 0 if stream is not None else self.max_retries,
                                   retry_only_503=self.retry_only_503,
                                   retry_min_wait_seconds=self.retry_min_wait_seconds,
                                   retry_max_wait_seconds=self.retry_max_wait_seconds,
                                   **({'response_reader': reader} if reader is not None else {}))
        except ProviderCoolingDown as error:
            failure_type = LLMRateLimitError if error.provider_error_code == 'provider_rate_limited' else LLMProviderError
            failure = failure_type("provider is cooling down; please try again later")
            failure.provider_error_code = error.provider_error_code
            failure.retry_after_seconds = error.retry_after_seconds
            raise failure from None
        except QuotaExceeded as error:
            failure = LLMRateLimitError('local provider budget exhausted; request stopped before transport')
            failure.retry_after_seconds = error.retry_after_seconds
            raise failure from None
        except (sqlite3.Error, QuotaStateError):
            raise LLMProviderError("provider admission state unavailable; request stopped") from None
        except LLMError as error:
            cause = error.__cause__
            structured_hint, observations = (scoped_quota_hint(error.quota_hints, self.model)
                if hasattr(error, 'quota_hints') else (None, []))
            if structured_hint is not None:
                error.retry_after_seconds = structured_hint
            if circuit and generation is not None and attempted:
                overloaded = isinstance(cause, urllib.error.HTTPError) and cause.code == 503
                rate_limited = isinstance(cause, urllib.error.HTTPError) and cause.code == 429
                hint = _retry_after_seconds(cause.headers.get("Retry-After")) if (overloaded or rate_limited) and cause.headers else None
                if hint is not None and not math.isfinite(hint):
                    hint = None
                if rate_limited and structured_hint is not None:
                    hint = max(hint or 0, structured_hint)
                try:
                    if project and rate_limited:
                        project.circuit.failed(project.generation, overloaded=False, rate_limited=True, retry_after=hint)
                    elif project:
                        project.circuit.failed(project.generation, overloaded=False)
                    circuit.failed(generation, overloaded=overloaded,
                        rate_limited=rate_limited and project is None, retry_after=hint)
                    if overloaded or rate_limited:
                        error.retry_after_seconds = (project.circuit.remaining_seconds()
                            if project and rate_limited else circuit.remaining_seconds())
                except sqlite3.Error:
                    raise LLMProviderError("provider health state unavailable; request stopped") from None
            if observations and governor is not None and project is None:
                try:
                    governor.observe(observations)
                except sqlite3.Error:
                    # The circuit already protects the exhausted window. A
                    # broken quota store will fail closed on next admission.
                    pass
            raise
        else:
            if project:
                try:
                    project.circuit.succeeded(project.generation)
                except sqlite3.Error:
                    pass
            if circuit:
                try:
                    circuit.succeeded(generation)
                except sqlite3.Error:
                    # The successful provider output remains usable; an old
                    # probe lease expires rather than triggering another call.
                    pass
            return result
        finally:
            if project and (not attempted or stream is not None and stream.cancelled()):
                try:
                    project.circuit.abandon(project.generation)
                except sqlite3.Error:
                    pass
            if reservation is not None:
                try:
                    governor.finish(reservation, result.get('usageMetadata') if result else None)
                except sqlite3.Error:
                    # Counters remain charged; the crash-safe lease expires.
                    pass
            if circuit and generation is not None and (not attempted or stream is not None and stream.cancelled()):
                try:
                    circuit.abandon(generation)
                except sqlite3.Error:
                    pass

    def prepare_request(self, prompt: str, **kwargs: Any) -> dict:
        """Build the exact request locally, including only verified PDF parts."""
        request_options = dict(kwargs)
        documents = request_options.pop('pdf_documents', None)
        if documents is not None:
            from .pdf_scope import pdf_parts
            if not self.allow_pdf_scope or 'contents' in request_options:
                raise LLMProviderError('PDF scope is not enabled or has conflicting content')
            expected = f'https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent'
            if self.endpoint != expected or not re.fullmatch(r'gemini-[a-zA-Z0-9._-]+', self.model):
                raise LLMProviderError('PDF scope requires the configured official Gemini endpoint')
            try:
                parts = pdf_parts(documents)
            except (ValueError, TypeError, RuntimeError) as error:
                raise LLMProviderError('PDF source identity or bounded scope invalid') from error
        else:
            parts = []
        if self.generation_config:
            overrides = request_options.pop("generationConfig", {})
            request_options["generationConfig"] = {**self.generation_config, **overrides}
        system_prompt = request_options.pop("system_prompt", None)
        body: dict[str, Any] = {
            "contents": [{**({'role': 'user'} if parts else {}), "parts": parts + [{"text": prompt}]}],
            **request_options,
        }
        if system_prompt is not None:
            body["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        if documents is None and any('inlineData' in part or 'fileData' in part
                for content in body.get('contents', []) for part in content.get('parts', [])):
            raise LLMProviderError('multimodal input requires a verified PDF scope')
        return body

    def prepare_json_request(self, prompt: str, schema=None, **kwargs) -> dict:
        prompt, options = self._json_options(prompt, schema, kwargs)
        return self.prepare_request(prompt, **options)

    def complete(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """Send a prompt using Gemini's request and response schema."""
        from .streaming import current_stream, stream_endpoint
        stream = current_stream()
        streaming_url = stream_endpoint(self.endpoint) if stream is not None else None
        if streaming_url is None:
            stream = None
        body = self.prepare_request(prompt, **kwargs)
        pdf_mode = kwargs.get('pdf_documents') is not None
        cache_key = build_cache_key(
            provider=self.provider,
            endpoint=self.endpoint,
            request=body,
        )
        cached = None if pdf_mode else self._cached(cache_key)
        if cached is not None:
            return cached

        with _single_flight(cache_key):
            cached = None if pdf_mode else self._cached(cache_key)
            if cached is not None:
                return cached
            request = urllib.request.Request(
                streaming_url or self.endpoint,
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key,
                },
            )
            started_at = time.perf_counter()
            measurement = None
            budget = None
            if kwargs.get('pdf_documents') is not None:
                from .pdf_scope import body_hash, measured_budget
                count_endpoint = self.endpoint.removesuffix(':generateContent') + ':countTokens'
                count_body = {'generateContentRequest': {'model': 'models/'+self.model, **body}}
                count_request = urllib.request.Request(count_endpoint,
                    data=json.dumps(count_body).encode('utf-8'),
                    headers={'Content-Type': 'application/json', 'x-goog-api-key': self.api_key})
                # Tokenization is not generation. Its separate durable ledger
                # must not consume model inference RPM/TPM/RPD. The collector
                # still charges every HTTP POST to the approved egress cap.
                counts = self._send(count_request, token_budget=(0, 0))
                try:
                    budget = measured_budget(body, counts.get('totalTokens'))
                except (ValueError, TypeError, AttributeError) as error:
                    raise LLMProviderError('PDF token measurement unavailable; generation stopped') from error
                measurement = {'endpoint': count_endpoint, 'request_body_sha256': body_hash(count_body),
                    'generation_body_sha256': body_hash(body), 'response': counts,
                    'reserved_input_tokens': budget[0], 'reserved_output_tokens': budget[1]}
            send_options = {}
            if budget is not None:
                send_options['token_budget'] = budget
            if stream is not None:
                send_options['stream'] = stream
            data = self._send(request, **send_options)
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
            if self.cache is not None and not pdf_mode and stream is None:
                self.cache.put(cache_key, text, usage, latency_ms)
            reason = candidate.get("finishReason")
            model_version = data.get("modelVersion")
            return LLMResponse(text, usage, latency_ms,
                finish_reason=reason if isinstance(reason, str) else None,
                model_version=model_version if isinstance(model_version, str) else None,
                input_measurement=measurement)

    def _json_options(self, prompt, schema, kwargs):
        kwargs = dict(kwargs)
        generation_config = dict(kwargs.pop('generationConfig', {}))
        if self.json_mode == 'native':
            generation_config['responseMimeType'] = 'application/json'
            if schema is not None:
                generation_config['responseSchema'] = _gemini_schema(schema)
        elif schema is not None:
            prompt += '\nOUTPUT_JSON_SCHEMA:\n' + json.dumps(schema, ensure_ascii=False, separators=(',', ':'))
        return prompt, {**kwargs, 'generationConfig': generation_config}

    def generate_json(
        self,
        prompt: str,
        schema: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate JSON using Gemini's native generation configuration."""

        prompt, options = self._json_options(prompt, schema, kwargs)
        response = self.generate(prompt, **options)
        text = response.text.strip()
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.I | re.S)
        if fenced:
            text = fenced.group(1)
        try:
            value = json.loads(text)
        except (json.JSONDecodeError, RecursionError) as error:
            raise LLMResponseError("LLM returned malformed JSON") from error
        if not isinstance(value, dict):
            raise LLMResponseError("LLM JSON response must be an object")
        if schema is not None:
            _validate_schema(value, schema)
        return value
