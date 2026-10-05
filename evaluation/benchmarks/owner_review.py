"""Bind the project owner's confirmation of existing inputs without per-row forms."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path, PureWindowsPath

from evaluation.common.release_artifacts import read_json, sha256, write_json


def confirmed_row(source: dict, confirmation: dict) -> dict:
    from evaluation.benchmarks.human_benchmark_intake import REVIEW_CHECKS, digest_record
    owner = confirmation["owner_identity"]
    row = {**source, "original_author_alias": source.get("author"), "author": owner,
            "author_type": "human", "reviewer": owner, "reviewer_role": "project_owner",
            "review_status": "approved", "review_checks": {key: True for key in REVIEW_CHECKS},
            "reviewed_at": confirmation["recorded_at"], "release_eligible": True,
            "review_evidence_kind": "owner_dataset_confirmation",
            "owner_confirmation_sha256": digest_record(confirmation)}
    if source.get("expected_behavior") == "abstain_no_evidence":
        row["expected_behavior"] = "abstain"
        row["review_schema_normalization"] = {"expected_behavior": {"from": "abstain_no_evidence", "to": "abstain"}}
    return row


def confirm_existing(dataset: Path, benchmark_dir: Path, *, owner_statement: str) -> dict:
    """Record a supplied owner statement now; retain the confirmed source bytes."""
    from evaluation.benchmarks.human_benchmark_intake import configured_owner_identity, digest_record
    policy_path = benchmark_dir / "phase7_review_policy.json"
    policy = read_json(policy_path)
    owner = configured_owner_identity(policy_path)
    if not owner or policy.get("owner_dataset_confirmation_allowed") is not True:
        raise ValueError("owner dataset confirmation must be allowed by the project policy")
    if not isinstance(owner_statement, str) or not owner_statement.strip():
        raise ValueError("the actual owner statement is required")
    target = benchmark_dir / "phase7_owner_confirmation.json"
    if target.exists():
        raise ValueError("owner confirmation already exists; use a new dataset cycle")
    content = dataset.read_bytes()
    rows = [json.loads(line) for line in content.decode("utf-8").splitlines() if line.strip()]
    if not rows or len({row["qid"] for row in rows}) != len(rows):
        raise ValueError("owner-confirmed dataset must contain unique records")
    snapshot = benchmark_dir / "owner_confirmed_inputs" / (sha256(dataset) + ".jsonl")
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    if snapshot.exists():
        if snapshot.read_bytes() != content:
            raise ValueError("owner-confirmed snapshot changed")
    else:
        with snapshot.open("xb") as stream:
            stream.write(content)
    confirmation = {"schema_version": 1, "review_mode": "owner_self_review",
                    "evidence_kind": "owner_dataset_confirmation", "status": "owner_confirmed",
                    "owner_identity": owner, "statement": owner_statement,
                    "statement_source": "project_owner_chat_instruction",
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                    "timestamp_meaning": "recorded in this session; no historical review date is asserted",
                    "scope": "existing question, authorship, gold, document scope and expected behavior",
                    "exposure_history_confirmed": False,
                    "review_policy_sha256": sha256(policy_path),
                    "source_snapshot": {"path": snapshot.relative_to(benchmark_dir).as_posix(), "sha256": sha256(snapshot)},
                    "source_record_sha256": {row["qid"]: digest_record(row) for row in rows}}
    write_json(target, confirmation)
    return confirmation


def load_confirmation(benchmark_dir: Path) -> tuple[dict, list[dict]]:
    from evaluation.benchmarks.human_benchmark_intake import configured_owner_identity, digest_record
    policy_path = benchmark_dir / "phase7_review_policy.json"
    policy = read_json(policy_path)
    confirmation = read_json(benchmark_dir / "phase7_owner_confirmation.json")
    owner = configured_owner_identity(policy_path)
    try:
        stamp = datetime.fromisoformat(confirmation["recorded_at"].replace("Z", "+00:00"))
        if stamp.tzinfo is None or stamp > datetime.now(timezone.utc):
            raise ValueError("invalid confirmation recording time")
    except (KeyError, AttributeError, TypeError) as error:
        raise ValueError("timezone-aware owner confirmation time required") from error
    if (not owner or confirmation.get("owner_identity") != owner
            or policy.get("owner_dataset_confirmation_allowed") is not True
            or confirmation.get("review_policy_sha256") != sha256(policy_path)
            or confirmation.get("evidence_kind") != "owner_dataset_confirmation"
            or confirmation.get("review_mode") != "owner_self_review"
            or confirmation.get("status") != "owner_confirmed"
            or confirmation.get("exposure_history_confirmed") is not False
            or not isinstance(confirmation.get("statement"), str) or not confirmation["statement"].strip()):
        raise ValueError("owner confirmation does not bind the current owner policy")
    ref = confirmation["source_snapshot"]
    name = ref["path"]
    if (not isinstance(name, str) or not name or Path(name).is_absolute() or PureWindowsPath(name).drive
            or PureWindowsPath(name).root or ".." in PureWindowsPath(name).parts):
        raise ValueError("unsafe owner-confirmed source reference")
    path = (benchmark_dir / name).resolve()
    if not path.is_relative_to(benchmark_dir.resolve()) or sha256(path) != ref["sha256"]:
        raise ValueError("owner-confirmed source snapshot changed")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    bindings = {row["qid"]: digest_record(row) for row in rows}
    if not rows or len(bindings) != len(rows) or bindings != confirmation.get("source_record_sha256"):
        raise ValueError("owner-confirmed record bindings changed")
    revision = confirmation.get("dev_metadata_revision")
    if revision is not None:
        # Original input bytes and legacy label origins are retained. M1/S1
        # subsequently recompute the correction against the physical index.
        from evaluation.reranker.supplemental_gates import raw_reference
        original_path = raw_reference(benchmark_dir, revision["original_source_snapshot"])
        original = [json.loads(line) for line in original_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if original != revision["original_dev_records"]:
            raise ValueError("dev metadata revision original inputs changed")
        parent_path = benchmark_dir / "parent_owner_confirmation.json"
        if sha256(parent_path) != revision["parent_confirmation_sha256"]:
            raise ValueError("dev metadata revision parent confirmation changed")
        parent = read_json(parent_path)
        allocation = raw_reference(benchmark_dir, revision["original_dev_allocation"])
        prior_dev = [json.loads(line) for line in allocation.read_text(encoding="utf-8").splitlines() if line.strip()]
        expected_dev = [{**confirmed_row(row, parent), "split": "dev"} for row in original]
        if (prior_dev != expected_dev or sorted(row["qid"] for row in prior_dev) != revision["allocated_dev_qids"]
                or parent["source_snapshot"] != revision["original_source_snapshot"]):
            raise ValueError("dev metadata revision original allocation changed")
        source_records = {}
        for split, expected_hash in revision["source_regression_sha256"].items():
            if split not in {"dev", "test", "holdout"}:
                raise ValueError("invalid source regression split")
            regression = benchmark_dir / f"hybrid_retrieval_{split}.jsonl"
            if sha256(regression) != expected_hash:
                raise ValueError("dev metadata revision source regression changed")
            for line in regression.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    record = json.loads(line)
                    if record["qid"] in revision["source_regression_records"]:
                        source_records[record["qid"]] = record
        if source_records != revision["source_regression_records"]:
            raise ValueError("dev metadata revision source records changed")
    return confirmation, rows


def confirmation_audit(confirmation: dict, sources: list[dict]) -> list[dict]:
    from evaluation.benchmarks.human_benchmark_intake import digest_record
    return [{"qid": row["qid"], "review_evidence_kind": "owner_dataset_confirmation",
             "owner_confirmation_sha256": digest_record(confirmation),
             "source_record_sha256": digest_record(row),
             "exported_record_sha256": digest_record(confirmed_row(row, confirmation))} for row in sources]
