"""Report concrete M1/S1 input gaps without changing review or exposure decisions."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

from evaluation.benchmarks.freeze_human_benchmark import (
    assign_grouped_splits, exposure_registry_errors, frozen_evidence, grouped_split_report, validate_rows,
)
from evaluation.benchmarks.human_benchmark_intake import (
    configured_owner_identity, packet_path, validate_review,
)
from evaluation.common.release_artifacts import read_json, sha256, source_identity, write_json
from evaluation.reranker.reranker_release_gates import ARTIFACTS
from evaluation.reranker.supplemental_gates import SUPPLEMENTAL
from scripts.benchmarks.prepare_human_candidates import load_rows


def inspect_inputs(benchmark_dir: Path, intake_dir: Path, index_dir: Path) -> dict:
    """Return actionable gaps; legacy approved labels never stand in for valid packets."""
    if (benchmark_dir / "phase7_generation_authorization.json").is_file():
        from evaluation.benchmarks.owner_generation import load_generation
        from evaluation.benchmarks.owner_review import load_confirmation
        from evaluation.reranker.supplemental_gates import review_audit_errors
        authorization, generated = load_generation(benchmark_dir, index_dir)
        rows = load_rows(benchmark_dir / "human_retrieval.jsonl")
        audit = load_rows(benchmark_dir / "human_retrieval_review_audit.jsonl")
        confirmation, sources = (load_confirmation(benchmark_dir)
            if any(item.get('review_evidence_kind') == 'owner_dataset_confirmation' for item in audit)
            else (None, None))
        registry = read_json(benchmark_dir / "phase7_exposure_registry.json")
        owner = configured_owner_identity(benchmark_dir / "phase7_review_policy.json")
        validation = validate_rows(rows, frozen_evidence(index_dir), owner_identity=owner,
                                   generated_records=generated)
        issues = review_audit_errors(rows, audit,
                                    index_dir, owner_identity=owner, owner_confirmation=confirmation,
                                    confirmed_sources=sources, generation_authorization=authorization,
                                    generated_records=generated)
        issues += exposure_registry_errors(rows, registry, source_pool=benchmark_dir / "human_candidate_pool.jsonl",
                    source_lineage=benchmark_dir / "human_candidate_lineage.json", index_manifest=index_dir / "manifest.json")
        issues += validation["errors"]
        return {"schema_version": 2, "phase": 7, "status": "blocked" if issues else "ready_for_freeze",
                "release_eligible": False, "benchmark_profile": validation["benchmark_profile"],
                "recorded_at": datetime.now(timezone.utc).isoformat(), "issues": sorted(set(issues)),
                "blockers": sorted(set(issues)),
                "split_coverage_gaps": [e for e in validation["errors"] if "split_coverage" in e or "route_coverage" in e],
                "counts": {"records": len(rows), "approved_review": len(rows) if not issues else 0,
                           "review_pending_or_invalid": len(rows) if issues else 0,
                           "known_exposed": sum(str(r["status"]).startswith("known_exposed") for r in registry["records"]),
                           "unexposed_audited": sum(r["status"] == "unexposed_audited" for r in registry["records"])},
                "validation": validation, "safe_split_proposal": grouped_split_report(rows)}
    staging = benchmark_dir / "human_candidate_staging.jsonl"
    pool = benchmark_dir / "human_candidate_pool.jsonl"
    lineage_path = benchmark_dir / "human_candidate_lineage.json"
    registry_path = benchmark_dir / "phase7_exposure_registry.json"
    policy_path = benchmark_dir / "phase7_review_policy.json"
    rows, raw_rows = load_rows(staging), load_rows(pool)
    lineage, registry = read_json(lineage_path), read_json(registry_path)
    policy = read_json(policy_path)
    owner = configured_owner_identity(policy_path)
    confirmation, confirmed, published = None, {}, {}
    if (benchmark_dir / "phase7_owner_confirmation.json").is_file():
        from evaluation.benchmarks.owner_review import load_confirmation, confirmed_row
        confirmation, sources = load_confirmation(benchmark_dir)
        confirmed = {row["qid"]: confirmed_row(row, confirmation) for row in sources}
        if set(confirmed) != {row["qid"] for row in rows}:
            raise ValueError("owner confirmation must cover every source candidate")
        rows = [confirmed[row["qid"]] for row in rows]
        canonical = benchmark_dir / "human_retrieval.jsonl"
        if canonical.is_file():
            published_rows = load_rows(canonical)
            published = {row["qid"]: row for row in published_rows}
            if len(published) != len(published_rows):
                raise ValueError("duplicate published owner-confirmed qid")
    evidence = frozen_evidence(index_dir)
    raw = {"human-" + row["candidate_id"]: row for row in raw_rows}
    exposure_rows = registry.get("records", [])
    if not isinstance(exposure_rows, list) or any(not isinstance(row, dict) for row in exposure_rows):
        raise ValueError("invalid exposure registry records")
    histories = {row.get("qid"): row for row in exposure_rows}
    qids = {row.get("qid") for row in rows}
    if (len(qids) != len(rows) or len(raw) != len(raw_rows) or len(histories) != len(exposure_rows)
            or qids != set(raw) or qids != set(histories) or qids != set(lineage.get("connected_groups", {}))):
        raise ValueError("staging, source, lineage and exposure must cover every qid exactly once")
    if (lineage.get("dataset_sha256") != sha256(pool)
            or lineage.get("index_sha256") != sha256(index_dir / "manifest.json")
            or registry.get("dataset_sha256") != sha256(pool)
            or registry.get("lineage_sha256") != sha256(lineage_path)
            or registry.get("index_sha256") != sha256(index_dir / "manifest.json")):
        raise ValueError("review input bindings changed")
    entries, reviewed_rows = [], []
    counts = Counter(records=len(rows), negative=sum(row["answerable"] is False for row in rows))
    for row in rows:
        qid = row["qid"]
        if row["question"] != raw[qid]["question"]:
            raise ValueError("staging question differs from source: " + qid)
        history = histories[qid]
        if history.get("connected_group") != lineage["connected_groups"][qid]:
            raise ValueError("exposure group differs from lineage: " + qid)
        issues = []
        question, review = None, None
        for folder in (() if confirmation is not None else ("questions", "reviews")):
            path = packet_path(intake_dir, folder, qid)
            try:
                packet = read_json(path)
                if folder == "questions":
                    question = packet
                else:
                    review = packet
            except (OSError, ValueError, TypeError):
                issues.append("missing_or_invalid_" + folder + "_packet")
        approved = confirmation is not None
        if approved:
            actual = published.get(qid)
            expected = {**row, "split": actual.get("split")} if actual else None
            if actual != expected:
                approved = False
                issues.append("owner_confirmation_export_missing_or_changed")
            else:
                reviewed_rows.append(row)
        if question is not None and review is not None:
            try:
                if question["record"]["question"] != raw[qid]["question"]:
                    raise ValueError("question packet differs from the original question")
                if question["record"]["qid"] != qid:
                    raise ValueError("question packet qid mismatch")
                validate_review(question, review, index_dir, owner_identity=owner)
                approved = review["review_status"] == "approved"
                if approved:
                    reviewed_rows.append({**question["record"],
                                          **{key: review[key] for key in
                                             ("reviewer", "reviewer_role", "review_status", "review_checks")},
                                          "reviewed_at": review["reviewed_at"]})
                if not approved:
                    issues.append("record_rejected_by_reviewer")
            except (ValueError, KeyError, TypeError, AttributeError) as error:
                issues.append("review_packet_rejected:" + str(error))
        counts["valid_approved_review" if approved else "review_pending_or_invalid"] += 1
        if not row["answerable"] and not approved:
            counts["negative_scope_pending"] += 1
            issues.append("negative_scope_requires_valid_per_record_review")
        status = history.get("status")
        if status == "unknown_pending_history_audit":
            counts["unknown_history"] += 1
            issues.append("exposure_history_unresolved")
        elif isinstance(status, str) and status.startswith("known_exposed"):
            counts["known_exposed"] += 1
        elif status != "unexposed_audited":
            issues.append("invalid_exposure_status")
        entries.append({"qid": qid, "answerable": row["answerable"], "review_approved": approved,
                        "connected_group": history["connected_group"], "exposure_status": status,
                        "heldout_eligible": history.get("heldout_eligible"), "issues": issues})
    proposal = assign_grouped_splits(rows, histories)
    split_report = grouped_split_report(proposal)
    split_gaps = []
    for split in ("dev", "test", "holdout"):
        members = [row for row in proposal if row["split"] == split]
        for answerable in (True, False):
            if not any(row["answerable"] is answerable for row in members):
                split_gaps.append(f"{split}:missing_{'positive' if answerable else 'negative'}")
        for difficulty in ("easy", "hard"):
            if not any(row["answerable"] is True and row["difficulty"] == difficulty for row in members):
                split_gaps.append(f"{split}:missing_answerable_{difficulty}")
    blockers = []
    if counts["review_pending_or_invalid"]:
        blockers.append("per_record_review_incomplete")
    if registry.get("status") != "pass":
        blockers.append("exposure_history_audit_incomplete")
    if any(entry["issues"] for entry in entries):
        blockers.append("record_input_gaps")
    if split_gaps:
        blockers.append("independent_split_coverage_missing")
    exposure_errors = exposure_registry_errors(proposal, registry, source_pool=pool,
                                               source_lineage=lineage_path,
                                               index_manifest=index_dir / "manifest.json")
    if exposure_errors:
        blockers.append("exposure_registry_validation_failed")
    canonical_errors = []
    if len(reviewed_rows) == len(rows):
        regression = [row for path in benchmark_dir.glob("hybrid_retrieval_*.jsonl") for row in load_rows(path)]
        assigned = assign_grouped_splits(reviewed_rows, histories)
        canonical_errors = validate_rows(assigned, evidence, regression, owner_identity=owner)["errors"]
        canonical_errors += exposure_registry_errors(assigned, registry, source_pool=pool,
                                                     source_lineage=lineage_path,
                                                     index_manifest=index_dir / "manifest.json")
        if canonical_errors:
            blockers.append("reviewed_canonical_validation_failed")
    return {"schema_version": 1, "phase": 7, "artifact_type": "review_input_diagnostic",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "blocked" if blockers else "ready_for_freeze_validation",
            "release_eligible": False, "owner_self_review_allowed": policy.get("owner_self_review_allowed") is True,
            "review_basis": "owner_dataset_confirmation" if confirmation is not None else "per_record_packets",
            "inputs": {"staging_sha256": sha256(staging), "dataset_sha256": sha256(pool),
                       "lineage_sha256": sha256(lineage_path), "exposure_registry_sha256": sha256(registry_path),
                       "review_policy_sha256": sha256(policy_path), "index_sha256": sha256(index_dir / "manifest.json")},
            "counts": dict(counts), "blockers": blockers, "safe_split_proposal": split_report,
            "split_coverage_gaps": split_gaps, "exposure_validation_errors": exposure_errors,
            "canonical_validation_errors": sorted(set(canonical_errors)), "records": entries}


def main(argv=None) -> int:
    from evaluation.reranker.active_cycle import active_cycle
    cycle = active_cycle()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-dir", type=Path, default=cycle["benchmark_dir"])
    parser.add_argument("--intake-dir", type=Path, default=Path("data/benchmark/human_intake"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/hybrid-index"))
    parser.add_argument("--output", type=Path, default=Path(".tmp/phase7-review-inputs.json"))
    args = parser.parse_args(argv)
    output = args.output.resolve()
    inputs = {path.resolve() for root in (args.benchmark_dir, args.intake_dir, args.index_dir)
              for path in root.rglob("*") if path.is_file()}
    gate_names = set(ARTIFACTS.values()) | {filename for _, _, filename in SUPPLEMENTAL.values()}
    if output in inputs or output.name in gate_names:
        parser.error("diagnostic output must not overwrite source, intake, index or gate evidence")
    try:
        report = inspect_inputs(args.benchmark_dir, args.intake_dir, args.index_dir)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}))
        return 1
    report.update(source_identity(Path(__file__).resolve().parents[2]))
    report["command"] = "python -m scripts.phase7_release_pipeline preflight"
    write_json(args.output, report)
    print(json.dumps({key: report[key] for key in
                      ("status", "counts", "blockers", "safe_split_proposal", "split_coverage_gaps")}, ensure_ascii=False))
    return 0 if not report["blockers"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
