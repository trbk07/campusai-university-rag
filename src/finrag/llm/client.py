"""Provider clients for the foundation layer."""

from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol


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

    def generate_json(self, prompt: str, schema: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        """Generate and parse a JSON object."""


def _hash_payload(payload: dict) -> str:
    """Create a stable cache key for a JSON-compatible payload."""

    serialized = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _request_json(request, timeout: int, limiter, max_retries: int) -> dict:
    """Issue a request with bounded retry handling for transient provider errors."""
    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code not in {408, 429, 500, 502, 503, 504} or attempt >= max_retries:
                raise
            retry_after = error.headers.get("Retry-After")
            try:
                retry_seconds = float(retry_after) if retry_after is not None else None
            except ValueError:
                retry_seconds = None
            if limiter is not None:
                limiter.backoff(attempt, retry_seconds)
            else:
                time.sleep(min(60.0, 0.5 * (2**attempt)))
    raise RuntimeError("unreachable retry state")


class OpenAICompatibleClient:
    """Client for APIs with the OpenAI chat-completions response shape."""

    def __init__(self, endpoint: str, api_key: str, model: str, cache=None, limiter=None, timeout: int = 60, max_retries: int = 3) -> None:
        self.endpoint = endpoint
        self.api_key = api_key
        self.model = model
        self.cache = cache
        self.limiter = limiter
        self.timeout = timeout
        self.max_retries = max(0, max_retries)

    def complete(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """Send a prompt, or return its cached response."""

        payload = {"model": self.model, "messages": [{"role": "user", "content": prompt}], **kwargs}
        cache_key = _hash_payload(payload)

        if self.cache is not None:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return LLMResponse(cached.text, cached.usage, cached.latency_ms, True)

        if self.limiter is not None:
            self.limiter.wait()

        started_at = time.perf_counter()
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
        )
        data = _request_json(request, self.timeout, self.limiter, self.max_retries)

        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        latency_ms = (time.perf_counter() - started_at) * 1000
        if self.cache is not None:
            self.cache.put(cache_key, text, usage, latency_ms)
        return LLMResponse(text, usage, latency_ms)

    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        return self.complete(prompt, **kwargs)

    def generate_json(self, prompt: str, schema: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        """Parse only JSON; model output is never executed as Python."""
        if schema is not None:
            kwargs.setdefault("response_format", {"type": "json_object"})
        text = self.generate(prompt, **kwargs).text.strip()
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.I | re.S)
        if fenced:
            text = fenced.group(1)
        value = json.loads(text)
        if not isinstance(value, dict):
            raise ValueError("LLM JSON response must be an object")
        return value


class GeminiClient(OpenAICompatibleClient):
    """Client for Google's Gemini generateContent REST endpoint."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash", **kwargs: Any) -> None:
        endpoint = kwargs.pop(
            "endpoint",
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
        )
        super().__init__(endpoint, api_key, model, **kwargs)

    def complete(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """Send a prompt using Gemini's request and response schema."""

        cache_key = _hash_payload({"model": self.model, "prompt": prompt, **kwargs})
        if self.cache is not None:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return LLMResponse(cached.text, cached.usage, cached.latency_ms, True)

        if self.limiter is not None:
            self.limiter.wait()

        body = {"contents": [{"parts": [{"text": prompt}]}], **kwargs}
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        started_at = time.perf_counter()
        data = _request_json(request, self.timeout, self.limiter, self.max_retries)

        text = data["candidates"][0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata", {})
        latency_ms = (time.perf_counter() - started_at) * 1000
        if self.cache is not None:
            self.cache.put(cache_key, text, usage, latency_ms)
        return LLMResponse(text, usage, latency_ms)

    def generate_json(self, prompt: str, schema: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
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
        value = json.loads(text)
        if not isinstance(value, dict):
            raise ValueError("LLM JSON response must be an object")
        return value
