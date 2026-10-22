"""Create a blank review attestation or validate a completed one.

The template is deliberately pending. Independent human review or the explicit
Phase 5 AI/owner policy can qualify; neither template creates actual approval.
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

with redirect_stdout(sys.stderr):
    from evaluation.release.grounding_package import validate_annotation_signoff
    from evaluation.benchmarks.benchmark_schema import validate_release_records
    from evaluation.grounding.repair_benchmark import load_rows
    from evaluation.grounding.review_evidence import AI_REVIEW_POLICY, validate_independent_review


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    template = sub.add_parser("template")
    template.add_argument("benchmark", type=Path)
    template.add_argument("output", type=Path)
    template.add_argument("--creator-id", action="append", required=True)
    template.add_argument("--review-type", choices=("independent_human", "independent_ai_owner"),
                          default="independent_human")
    check = sub.add_parser("validate")
    check.add_argument("benchmark", type=Path)
    check.add_argument("signoff", type=Path)
    check.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    check.add_argument("--acceptance-scope", choices=("public_release", "phase5_acceptance"), default="public_release")
    args = parser.parse_args()
    try:
        return execute(args)
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        print(json.dumps({"status": "fail", "errors": ["signoff_or_benchmark_invalid"]}))
        return 1


def execute(args) -> int:
    rows = load_rows(args.benchmark)
    benchmark_sha256 = checksum(args.benchmark)
    if args.command == "template":
        payload = {
            "schema_version": 2,
            "status": "pending",
            "review_type": args.review_type,
            "benchmark_sha256": benchmark_sha256,
            "records_total": len(rows),
            "records_reviewed": 0,
            "records_approved": 0,
            "records_adjudicated": 0,
            "split_leakage": None,
            "missing_gold_evidence": None,
            "missing_abstention_reason": None,
            "creator_ids": args.creator_id,
            "reviewers": [],
            "row_decisions": [],
            "exposure_review": None,
            "adjudicator": None,
        }
        if args.review_type == "independent_ai_owner":
            payload.update(review_policy=AI_REVIEW_POLICY, review_artifacts=[],
                           owner_authorization=None, owner_approval=None)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"status": "created_pending_template", "path": str(args.output)}, indent=2))
        return 0
    payload = json.loads(args.signoff.read_text(encoding="utf-8"))
    errors = validate_annotation_signoff(payload, benchmark_sha256)
    scope = getattr(args, "acceptance_scope", "public_release")
    errors.extend(validate_independent_review(payload, rows, benchmark_sha256=benchmark_sha256, root=args.root,
                                            acceptance_scope=scope))
    errors.extend(f"benchmark_{error}" for error in validate_release_records(rows, acceptance_scope=scope))
    errors = sorted(set(errors))
    print(json.dumps({"status": "pass" if not errors else "fail", "errors": errors},
                     ensure_ascii=True, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
