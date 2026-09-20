"""Configuration-driven construction of the LLM foundation."""

from __future__ import annotations

import ast
import json
import os
import re
import urllib.parse
from pathlib import Path
from typing import Any

from .cache import SQLiteLLMCache
from .client import GeminiClient, LLMClient, OpenAICompatibleClient
from .rate_limiter import RateLimiter


def _scalar(value: str) -> Any:
    """Parse common YAML scalar forms for the no-dependency fallback parser."""

    value = value.strip()
    if not value:
        return None
    if value.lower() in {"null", "~"}:
        return None
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value[0:1] in {"'", '"'}:
        try:
            return ast.literal_eval(value)
        except (SyntaxError, ValueError) as error:
            raise ValueError(f"invalid quoted YAML value: {value}") from error
    if value[0:1] in {"[", "{"}:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            try:
                return ast.literal_eval(value)
            except (SyntaxError, ValueError) as error:
                raise ValueError(f"invalid YAML collection: {value}") from error
    if re.fullmatch(r"[-+]?\d+", value):
        return int(value)
    if re.fullmatch(r"[-+]?(?:\d+\.\d*|\d*\.\d+)(?:[eE][-+]?\d+)?", value):
        return float(value)
    return value


def _remove_inline_comment(value: str) -> str:
    """Remove a YAML comment outside a quoted scalar."""

    quote: str | None = None
    escaped = False
    for index, character in enumerate(value):
        if escaped:
            escaped = False
        elif character == "\\" and quote == '"':
            escaped = True
        elif character in {"'", '"'}:
            quote = None if quote == character else character if quote is None else quote
        elif character == "#" and quote is None and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
    return value.rstrip()


def _fallback_yaml(text: str) -> dict[str, Any]:
    """Parse the small nested mapping subset used by project configuration."""

    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for line_number, raw in enumerate(text.splitlines(), start=1):
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise ValueError(f"tabs are not supported in YAML indentation (line {line_number})")
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        content = raw[indent:]
        if ":" not in content:
            raise ValueError(f"expected key: value (line {line_number})")
        key, raw_value = content.split(":", 1)
        key = key.strip().strip("'\"")
        if not key:
            raise ValueError(f"empty YAML key (line {line_number})")
        value_text = _remove_inline_comment(raw_value).strip()
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if key in parent:
            raise ValueError(f"duplicate YAML key {key!r} (line {line_number})")
        if value_text:
            parent[key] = _scalar(value_text)
        else:
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
    return root


def _read_config(path: str | Path) -> dict[str, Any]:
    """Read YAML with PyYAML when installed and a strict fallback otherwise."""

    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except OSError as error:
        raise ValueError(f"cannot read LLM config {path!s}: {error}") from error
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        result = _fallback_yaml(text)
    else:
        try:
            result = yaml.safe_load(text)
        except yaml.YAMLError as error:
            raise ValueError(f"invalid YAML config: {error}") from error
    if not isinstance(result, dict):
        raise ValueError("LLM config root must be a mapping")
    return result


def _integer(config: dict[str, Any], name: str, default: int, *, minimum: int) -> int:
    value = config.get(name, default)
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be an integer") from error
    if parsed < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return parsed


def _endpoint(value: str, name: str = "endpoint") -> str:
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{name} must be an absolute HTTP(S) URL")
    return value


def create_llm(
    config_path: str | Path = "configs/default.yaml",
    environ: dict[str, str] | None = None,
) -> LLMClient:
    """Build a configured client; credentials are read only from the environment."""

    env = os.environ if environ is None else environ
    document = _read_config(config_path)
    config = document.get("llm")
    if not isinstance(config, dict):
        raise ValueError("config must contain an llm mapping")

    provider = str(config.get("provider", "gemini")).strip().lower()
    if provider not in {"gemini", "openai", "openai-compatible", "groq"}:
        raise ValueError(f"unsupported LLM provider: {provider}")
    model = str(config.get("model", "")).strip()
    if not model:
        raise ValueError("llm.model is required")

    default_key_name = {
        "gemini": "GEMINI_API_KEY",
        "groq": "GROQ_API_KEY",
        "openai": "OPENAI_API_KEY",
        "openai-compatible": "OPENAI_API_KEY",
    }[provider]
    key_name = str(config.get("api_key_env", default_key_name)).strip()
    if not key_name or not re.fullmatch(r"[A-Z][A-Z0-9_]*", key_name):
        raise ValueError("llm.api_key_env must be an environment variable name")
    api_key = env.get(key_name)
    if not api_key:
        raise ValueError(f"missing required environment variable: {key_name}")

    timeout = _integer(config, "timeout_seconds", 60, minimum=1)
    requests_per_minute = _integer(config, "requests_per_minute", 60, minimum=0)
    max_retries = _integer(config, "max_retries", 3, minimum=0)
    cache_path = str(config.get("cache_path", "data/cache/llm_cache.sqlite")).strip()
    if not cache_path:
        raise ValueError("llm.cache_path cannot be empty")

    cache = SQLiteLLMCache(cache_path)
    limiter = RateLimiter(requests_per_minute)
    common = {
        "cache": cache,
        "limiter": limiter,
        "timeout": timeout,
        "max_retries": max_retries,
    }
    if provider == "gemini":
        gemini_options = dict(common)
        if config.get("endpoint"):
            gemini_options["endpoint"] = _endpoint(str(config["endpoint"]), "endpoint")
        return GeminiClient(api_key, model=model, **gemini_options)

    endpoint = str(
        config.get("endpoint")
        or env.get("LLM_ENDPOINT")
        or "https://api.groq.com/openai/v1/chat/completions"
    ).strip()
    return OpenAICompatibleClient(
        _endpoint(endpoint), api_key, model, **common
    )


build_llm_client = create_llm

__all__ = ["create_llm", "build_llm_client"]
