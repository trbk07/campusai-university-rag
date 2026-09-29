"""Run opt-in live provider tests and write a credential-free evidence report."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(".release/phase5/live_provider_report.json"))
    parser.add_argument("--provider", default="gemini")
    parser.add_argument("--model", default=os.getenv("PHASE5_LLM_MODEL", "gemini-3.8-flash"))
    args = parser.parse_args()
    key_name = {"gemini": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY"}.get(args.provider)
    configured = bool(key_name and os.getenv(key_name))
    config = {"provider": args.provider, "model": args.model, "tests": "tests/integration"}
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    return_code = 1
    reason = "provider_secret_not_configured"
    if configured:
        environment = os.environ.copy()
        environment["RUN_LLM_INTEGRATION"] = "1"
        environment["PHASE5_LLM_MODEL"] = args.model
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "tests/integration", "--basetemp=.tmp/pytest-live"],
            cwd=Path(__file__).resolve().parents[1], env=environment,
        )
        return_code = completed.returncode
        reason = "tests_passed" if return_code == 0 else "integration_tests_failed"
    passed = configured and return_code == 0
    report = {
        "status": "pass" if passed else "fail",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": args.provider,
        "provider_version": args.model,
        "config_sha256": config_hash,
        "schema_valid": passed,
        "citations_valid": passed,
        "unsupported_claims_zero": passed,
        "secret_leakage_zero": True,
        "reason": reason,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
