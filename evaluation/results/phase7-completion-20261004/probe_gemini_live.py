"""Minimal uncached connectivity probe for the owner-configured Gemini provider."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "evaluation/results/phase7-completion-20261004/gemini-live-connectivity-probe-v4.json"
CONFIG = ROOT / "configs/gemini.yaml"


def main() -> int:
    import yaml
    from campusai.llm.factory import create_llm
    from evaluation.common.release_artifacts import source_identity, write_json

    if OUT.exists():
        raise FileExistsError(OUT)
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    llm_cfg = cfg["llm"]
    provider, model = str(llm_cfg["provider"]), str(llm_cfg["model"])
    key_env = str(llm_cfg.get("api_key_env", "GEMINI_API_KEY"))
    before = source_identity(ROOT)
    client = create_llm(CONFIG)
    original_cache = client.cache
    client.cache = None
    if original_cache is not None:
        original_cache.close()
    endpoint = client.endpoint
    prompt = "Reply with the single word OK."
    observed = datetime.now(timezone.utc).isoformat()
    try:
        generation_config = {
            "temperature": 0, "maxOutputTokens": 128,
            "thinkingConfig": {"thinkingLevel": "low"},
        }
        response = client.generate(prompt, generationConfig=generation_config)
        usage = response.usage or {}
        input_tokens = usage.get("promptTokenCount")
        output_tokens = usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0)
        estimated_list_cost = None
        if type(input_tokens) is int and type(output_tokens) is int:
            estimated_list_cost = (input_tokens * 0.50 + output_tokens * 3.00) / 1_000_000
        result = {
            "schema_version": 1, "status": "PASS", "provider": provider,
            "client_class": type(client).__name__, "model": model, "endpoint": endpoint,
            "credential_env_name": key_env, "credential_present": bool(os.environ.get(key_env)),
            "cache_enabled": False, "cached": response.cached, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "generation_config": generation_config,
            "response_sha256": hashlib.sha256(response.text.encode()).hexdigest(),
            "response_nonempty": bool(response.text.strip()), "usage": usage,
            "usage_status": "reported" if response.usage else "unknown",
            "latency_ms": response.latency_ms, "estimated_list_cost_usd": estimated_list_cost,
            "account_billed_cost_usd": None,
            "cost_status": "list_price_estimate; account billing tier unavailable",
            "price_basis": {"input_usd_per_million_tokens": 0.50,
                            "output_usd_per_million_tokens_including_thoughts": 3.00,
                            "source": "https://ai.google.dev/gemini-api/docs/generate-content/gemini-3",
                            "price_effective_scope": "Gemini 3 Flash Preview list price; account billed amount not queried"},
            "observed_at": observed, "source_identity_before": before,
            "source_identity_after": source_identity(ROOT), "release_eligible": False,
        }
        result["source_stable"] = result["source_identity_before"] == result["source_identity_after"]
        result["checks"] = {
            "live_response_received": result["response_nonempty"],
            "not_cached": not response.cached and client.cache is None,
            "token_usage_available": bool(response.usage),
            "key_value_excluded": client.api_key not in json.dumps(result),
        }
        write_json(OUT, result)
        print(json.dumps({"status": result["status"], "provider": provider, "model": model,
                          "endpoint": endpoint, "usage": response.usage,
                          "latency_ms": response.latency_ms, "cached": response.cached,
                          "report": OUT.as_posix()}, ensure_ascii=True, indent=2))
        return int(not all(result["checks"].values()) or not result["source_stable"])
    except Exception as error:
        code = getattr(error, "code", None)
        report = {
            "schema_version": 1, "status": "FAIL", "provider": provider,
            "client_class": type(client).__name__, "model": model, "endpoint": endpoint,
            "credential_env_name": key_env, "credential_present": bool(os.environ.get(key_env)),
            "cache_enabled": False, "observed_at": observed,
            "error_type": type(error).__name__, "http_status_code": code,
            "error_cause_type": type(error.__cause__).__name__ if error.__cause__ else None,
            "error_cause_key": str(error.__cause__.args[0]) if isinstance(error.__cause__, KeyError) and error.__cause__.args else None,
            "error_message_suppressed": True, "release_eligible": False,
            "source_identity_before": before, "source_identity_after": source_identity(ROOT),
        }
        report["source_stable"] = report["source_identity_before"] == report["source_identity_after"]
        write_json(OUT, report)
        print(json.dumps({"status": report["status"], "provider": provider, "model": model,
                          "endpoint": endpoint, "error_type": report["error_type"],
                          "http_status_code": code, "message_suppressed": True,
                          "report": OUT.as_posix()}, ensure_ascii=True, indent=2))
        return 1
    finally:
        close = getattr(client, "close", None)
        if close:
            close()


if __name__ == "__main__":
    raise SystemExit(main())
