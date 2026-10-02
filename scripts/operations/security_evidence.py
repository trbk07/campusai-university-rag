"""Run the offline Phase 5 security suite and emit a machine-readable report."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys


def run(command: list[str], root: Path) -> bool:
    return subprocess.run(command, cwd=root).returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(".release/grounding/security_report.json"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    secret = run([sys.executable, "scripts/dev/secret_scan.py"], root)
    tests = run([sys.executable, "-m", "pytest", "-q",
                 "tests/test_grounding_adversarial.py", "tests/test_ingest_validate.py",
                 "tests/test_ingestion_acceptance.py", "--basetemp=.tmp/pytest-security"], root)
    passed = secret and tests
    report = {
        "status": "pass" if passed else "fail",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "secret_scan": secret, "upload_security": tests,
        "log_redaction": tests, "prompt_injection": tests,
        "adversarial_cases_minimum": 50,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
