"""Create a blank review attestation or validate a completed one.

The template is deliberately pending.  Only an independent human reviewer can
turn it into an approved sign-off; the release validator checks identity
separation, coverage and the frozen benchmark checksum.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.phase5_package import validate_annotation_signoff


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    template = sub.add_parser("template")
    template.add_argument("benchmark", type=Path)
    template.add_argument("output", type=Path)
    template.add_argument("--creator-id", action="append", required=True)
    check = sub.add_parser("validate")
    check.add_argument("benchmark", type=Path)
    check.add_argument("signoff", type=Path)
    args = parser.parse_args()
    if args.command == "template":
        payload = {
            "schema_version": 1,
            "status": "pending",
            "benchmark_sha256": checksum(args.benchmark),
            "records_total": 400,
            "records_reviewed": 0,
            "records_approved": 0,
            "records_adjudicated": 0,
            "split_leakage": 0,
            "missing_gold_evidence": 0,
            "missing_abstention_reason": 0,
            "creator_ids": args.creator_id,
            "reviewers": [],
            "adjudicator": None,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "created_pending_template", "path": str(args.output)}, indent=2))
        return 0
    payload = json.loads(args.signoff.read_text(encoding="utf-8"))
    errors = validate_annotation_signoff(payload, checksum(args.benchmark))
    print(json.dumps({"status": "pass" if not errors else "fail", "errors": errors},
                     ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
