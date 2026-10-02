"""Probe a real staging/production deployment without recording payload data."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import urllib.error
import urllib.request


def request(url: str, path: str, payload: dict | None = None) -> tuple[bool, dict]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {} if data is None else {"content-type": "application/json"}
    try:
        req = urllib.request.Request(url.rstrip("/") + path, data=data, headers=headers,
                                     method="GET" if data is None else "POST")
        with urllib.request.urlopen(req, timeout=15) as response:
            value = json.loads(response.read().decode("utf-8"))
            return 200 <= response.status < 300, value
    except (OSError, ValueError, urllib.error.HTTPError):
        return False, {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--environment", choices=("staging", "production"), required=True)
    parser.add_argument("--output", type=Path, default=Path(".release/grounding/deployment_smoke_report.json"))
    parser.add_argument("--recovery-report", type=Path, required=True)
    args = parser.parse_args()
    health, _ = request(args.url, "/health")
    live, live_value = request(args.url, "/live")
    ready, ready_value = request(args.url, "/ready")
    metrics, _ = request(args.url, "/metrics")
    query, query_value = request(args.url, "/api/query", {"question": "health-check evidence query"})
    answer = query_value.get("answer", {}) if isinstance(query_value, dict) else {}
    citation_contract = bool(answer.get("abstained") or answer.get("citations"))
    try:
        recovery = json.loads(args.recovery_report.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        recovery = {}
    recovery_ok = recovery.get("status") == "pass" and recovery.get("environment") == args.environment
    passed = health and live and live_value.get("status") == "alive" and ready and ready_value.get("status") == "ready" and metrics and query and citation_contract and recovery_ok
    report = {
        "status": "pass" if passed else "fail",
        "timestamp": datetime.now(timezone.utc).isoformat(), "environment": args.environment,
        "deployment_smoke": health and query,
        "readiness": ready and ready_value.get("status") == "ready",
        "liveness": live and live_value.get("status") == "alive", "metrics": metrics,
        "citation_contract": citation_contract, "recovery": recovery_ok,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
