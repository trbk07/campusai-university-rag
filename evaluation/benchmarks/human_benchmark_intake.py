"""Human-authored question intake and role-declared review packets.

This CLI never creates questions or approvals. It validates, binds and exports
the packets explicitly supplied by authors and reviewers.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence, validate_rows, PLACEHOLDER_IDENTITIES
from evaluation.benchmarks.human_record_contract import REVIEWER_ROLES
from evaluation.common.release_artifacts import read_json, sha256, write_json

REVIEW_CHECKS = ("natural", "answerability", "evidence_sufficient", "corpus_temporal_scope",
                 "difficulty", "no_paraphrase_leakage", "expected_behavior")


def configured_owner_identity(policy_path: Path, explicit: str | None = None) -> str | None:
    if explicit is not None:
        return explicit
    try:
        policy = read_json(policy_path)
    except (OSError, ValueError, TypeError):
        return None
    identity = policy.get("owner_identity")
    if policy.get("owner_self_review_allowed") is True and isinstance(identity, str) and identity.strip():
        return identity
    return None


def digest_record(record: dict) -> str:
    return hashlib.sha256(json.dumps(record, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def packet_path(root: Path, folder: str, qid: str) -> Path:
    if not isinstance(qid, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", qid):
        raise ValueError("qid must be a safe, unique record identifier")
    return root / folder / (qid + ".json")


def submit_question(root: Path, record: dict, index_dir: Path) -> dict:
    if record.get("author_type") != "human" or not isinstance(record.get("author"), str) or not record["author"].strip():
        raise ValueError("explicit human author provenance required")
    if record.get("review_status") == "approved" or record.get("reviewer"):
        raise ValueError("author packet must not include a reviewer approval")
    record = {**record, "review_status": "pending", "reviewer": "", "review_checks": {key: False for key in REVIEW_CHECKS}}
    record.pop("reviewer_role", None)
    path = packet_path(root, "questions", record.get("qid"))
    # Check schema and frozen evidence without inventing a reviewer. Coverage
    # and review gates apply to the completed export, not to a single intake.
    report = validate_rows([record], frozen_evidence(index_dir))
    row_errors = [e for e in report["errors"] if e.startswith("row_")
                  and not e.endswith(("independent_human_review_required", "owner_review_identity_mismatch",
                                      "human_authorship_and_approval_required", "incomplete_review_checks"))]
    if row_errors:
        raise ValueError("invalid author packet: " + ", ".join(row_errors))
    packet = {"schema_version": 1, "record": record, "record_sha256": digest_record(record),
              "index_sha256": sha256(index_dir / "manifest.json"),
              "submitted_at": datetime.now(timezone.utc).isoformat()}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(packet, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    return packet


def submit_review(root: Path, review: dict, index_dir: Path, *, owner_identity: str | None = None) -> dict:
    question = read_json(packet_path(root, "questions", review.get("qid")))
    validate_review(question, review, index_dir, owner_identity=owner_identity)
    path = packet_path(root, "reviews", review["qid"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(review, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    return review


def validate_review(question: dict, review: dict, index_dir: Path, *, owner_identity: str | None = None) -> None:
    # An unchanged manifest cannot authorize approval after physical evidence
    # files changed. Submission and export already load this verified snapshot;
    # a separately submitted reviewer packet needs the same check.
    frozen_evidence(index_dir)
    record = question["record"]
    if review.get("qid") != record["qid"]:
        raise ValueError("review question ID mismatch")
    reviewer = review.get("reviewer")
    role = review.get("reviewer_role")
    if role not in REVIEWER_ROLES or not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError("reviewer identity and role must be explicit")
    if reviewer.strip().casefold() in PLACEHOLDER_IDENTITIES:
        raise ValueError("placeholder reviewer identity is not allowed")
    if role == "independent_reviewer":
        author = record.get("author")
        if (not isinstance(author, str) or not author.strip()
                or reviewer.strip().casefold() == author.strip().casefold()):
            raise ValueError("independent reviewer must differ from a valid author identity")
    if role == "project_owner" and (not isinstance(owner_identity, str) or not owner_identity.strip()
                                     or reviewer.strip().casefold() != owner_identity.strip().casefold()):
        raise ValueError("project owner self-review requires the configured owner identity")
    if (digest_record(record) != question["record_sha256"] or review.get("record_sha256") != question["record_sha256"]
            or question["index_sha256"] != sha256(index_dir / "manifest.json")
            or review.get("index_sha256") != question["index_sha256"]):
        raise ValueError("review packet does not bind the current question and frozen index")
    status = review.get("review_status")
    if status not in {"approved", "rejected"}:
        raise ValueError("review_status must be explicitly approved or rejected")
    checks = review.get("review_checks")
    if not isinstance(checks, dict) or any(type(checks.get(key)) is not bool for key in REVIEW_CHECKS):
        raise ValueError("every review check requires an explicit boolean decision")
    if status == "approved" and not all(checks[key] for key in REVIEW_CHECKS):
        raise ValueError("approval requires every per-record review check")
    reviewed_at = review.get("reviewed_at")
    try:
        stamp = datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
        submitted = datetime.fromisoformat(question["submitted_at"])
        if stamp.tzinfo is None or stamp < submitted or stamp > datetime.now(timezone.utc):
            raise ValueError("invalid review time")
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError("review timestamp must have a timezone and follow submission") from error


def export_reviewed(root: Path, output: Path, index_dir: Path, *, owner_identity: str | None = None) -> dict:
    records, audit = [], []
    index_hash = sha256(index_dir / "manifest.json")
    for path in sorted((root / "questions").glob("*.json")):
        question = read_json(path)
        record = question["record"]
        review_path = packet_path(root, "reviews", record["qid"])
        if not review_path.exists():
            raise ValueError(f"review packet missing: {record['qid']}")
        review = read_json(review_path)
        validate_review(question, review, index_dir, owner_identity=owner_identity)
        if (question["record_sha256"] != digest_record(record) or review["record_sha256"] != question["record_sha256"]
                or review["index_sha256"] != index_hash or question["index_sha256"] != index_hash):
            raise ValueError("question/evidence changed after review")
        if review["review_status"] != "approved":
            continue
        final = {**record, **{key: review[key] for key in ("reviewer", "reviewer_role", "review_status", "review_checks")},
                 "reviewed_at": review["reviewed_at"]}
        records.append(final)
        audit.append({"qid": record["qid"], "question_packet": question, "review_packet": review,
                      "exported_record_sha256": digest_record(final)})
    if not records:
        raise ValueError("no approved questions to export")
    # A second validation also catches tampered reviewer/check fields. A partial
    # export is useful for collection but cannot bypass M1's coverage gates.
    report = validate_rows(records, frozen_evidence(index_dir), owner_identity=owner_identity)
    row_errors = [e for e in report["errors"] if e.startswith("row_")]
    if row_errors:
        raise ValueError("reviewed export rejected: " + ", ".join(row_errors))
    audit_path = output.with_name(output.stem + "_review_audit.jsonl")
    if output.exists() or audit_path.exists():
        raise ValueError("export destination exists; use a new dataset path")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        stream.write("".join(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n" for row in records))
    with audit_path.open("x", encoding="utf-8") as stream:
        stream.write("".join(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n" for row in audit))
    return {"records": len(records), "dataset_sha256": sha256(output), "review_audit_sha256": sha256(audit_path),
            "coverage_status": report["status"], "remaining": report["errors"]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("submit", "inspect", "review", "export", "evidence"))
    parser.add_argument("--intake-dir", type=Path, default=Path("data/benchmark/human_intake"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/hybrid-index"))
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--qid")
    parser.add_argument("--doc-id")
    parser.add_argument("--chunk-id")
    parser.add_argument("--owner-identity", help="required to submit/export project_owner self-review packets")
    parser.add_argument("--review-policy", type=Path, default=Path("data/benchmark/phase7_review_policy.json"),
                        help="owner identity policy used when --owner-identity is omitted")
    parser.add_argument("--output", type=Path, default=Path("data/benchmark/human_retrieval.jsonl"))
    args = parser.parse_args(argv)
    owner_identity = configured_owner_identity(args.review_policy, args.owner_identity)
    try:
        if args.action in {"submit", "review"}:
            if not args.packet:
                parser.error("--packet is required (author/reviewer submitted JSON)")
            if args.action == "submit":
                result = submit_question(args.intake_dir, read_json(args.packet), args.index_dir)
            else:
                result = submit_review(args.intake_dir, read_json(args.packet), args.index_dir,
                                       owner_identity=owner_identity)
        elif args.action == "export":
            result = export_reviewed(args.intake_dir, args.output, args.index_dir,
                                     owner_identity=owner_identity)
        elif args.action == "inspect":
            result = read_json(packet_path(args.intake_dir, "questions", args.qid))
        else:
            evidence = frozen_evidence(args.index_dir)
            if args.doc_id and args.chunk_id:
                result = evidence[(args.doc_id, args.chunk_id)]
            else:
                result = {"index_sha256": sha256(args.index_dir / "manifest.json"),
                          "evidence": [{"doc_id": doc, "chunk_id": chunk, "page": item["page"]}
                                       for (doc, chunk), item in evidence.items() if not args.doc_id or doc == args.doc_id]}
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
