"""Preserve human question bytes and produce deterministic, honest intake reports.

No author/reviewer identity, approval, document scope or evidence is invented.
Question overlap is reported separately from authorship and exposure.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from evaluation.benchmarks.connected_groups import connected_groups, normalized_question
from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence, validate_rows, PLACEHOLDER_IDENTITIES
from evaluation.common.release_artifacts import read_json, sha256, write_json

TAG_ALIASES = {"multi-hop": "multi_hop", "exact-code": "exact_code", "course-code": "course_code"}


def load_rows(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("candidate rows must be objects")
    return rows


def prepare(path: Path, index_dir: Path, benchmark_dir: Path) -> tuple[list[dict], dict, dict]:
    raw = load_rows(path)
    rows, corrections, mapping = [], [], []
    for source in raw:
        candidate_id = source.get("candidate_id")
        if not isinstance(candidate_id, str) or not candidate_id:
            raise ValueError("stable candidate_id required; row numbers are not identities")
        row = {**source, "schema_version": 2, "qid": "human-" + candidate_id,
               "question_source": "direct_author", "evidence_source": "frozen_pdf",
               "tags": sorted({TAG_ALIASES.get(tag, tag) for tag in source.get("tags", [])}),
               "raw_tags": source.get("tags", []), "raw_review_status": source.get("review_status"),
               "selected_text": source.get("selected_text", source.get("document_context", {}).get("selected_text")),
               "release_eligible": False}
        # Preserve an existing explicit approval only when its full packet audit
        # is supplied later. A generic label cannot identify an independent human.
        if (source.get("review_status") != "approved"
                or str(source.get("reviewer", "")).strip().casefold() in PLACEHOLDER_IDENTITIES):
            row.update(review_status="pending", reviewer="")
        mapping.append({"candidate_id": candidate_id, "source_record_id": source.get("source_record_id"), "qid": row["qid"]})
        for field in ("tags", "evidence_source", "review_status", "reviewer", "release_eligible"):
            if row.get(field) != source.get(field):
                corrections.append({"qid": row["qid"], "field": field, "before": source.get(field),
                                    "after": row.get(field), "reason": "schema_normalization_or_pending_packet_audit"})
        rows.append(row)
    families = connected_groups(rows)
    known = {}
    for other in sorted(benchmark_dir.glob("*.jsonl")):
        if other.resolve() == path.resolve() or other.name.startswith("human_"):
            continue
        other_hash = sha256(other)
        for source in load_rows(other):
            text = normalized_question(source.get("question", source.get("query", "")))
            if text:
                known.setdefault(text, []).append({"dataset": other.as_posix(), "dataset_sha256": other_hash,
                                                   "qid": source.get("qid", source.get("id")), "split": source.get("split")})
    overlaps = [{"qid": row["qid"], "connected_group": families[row["qid"]],
                 "matches": known[normalized_question(row["question"])],
                 "exposure_status": "requires_study_history_audit", "authorship_inferred": False}
                for row in rows if normalized_question(row["question"]) in known]
    validation = validate_rows(rows, frozen_evidence(index_dir))
    missing = {}
    for error in validation["errors"]:
        if error.startswith("row_"):
            number, reason = error.split(":", 1)
            missing.setdefault(rows[int(number[4:]) - 1]["qid"], []).append(reason)
    compact_validation = {**validation, "errors": [error for error in validation["errors"] if not error.startswith("row_")],
                          "row_error_counts": dict(sorted(Counter(reason for values in missing.values() for reason in values).items()))}
    counts = Counter(tag for row in rows for tag in row["tags"])
    summary = {"schema_version": 2, "status": "pending_release_review", "dataset_sha256": sha256(path),
               "total": len(raw), "answerable": sum(row.get("answerable") is True for row in raw),
               "negative": sum(row.get("answerable") is False for row in raw),
               "ambiguous": sum(row.get("ambiguous") is True or "ambiguous" in row["tags"] for row in rows),
               "hard_or_multi_hop": sum(row.get("difficulty") == "hard" or "multi_hop" in row["tags"] for row in rows),
               "exact_code": counts["exact_code"], "contextual_followup": counts["contextual_followup"],
               "multi_hop": counts["multi_hop"], "table_evidence": counts["table"],
               "difficulty": dict(sorted(Counter(row.get("difficulty") for row in rows).items())),
               "tags": dict(sorted(counts.items())), "groups": len(set(families.values())),
               "document_counts": dict(sorted(Counter(doc for row in rows for doc in row.get("doc_ids", [])).items())),
               "duplicate_question_count": len(rows) - len({normalized_question(row["question"]) for row in rows}),
               "release_eligible": validation["status"] == "pass", "validation": compact_validation,
               "raw_authorship": dict(sorted(Counter(row.get("author", "") for row in raw).items())),
               "authorship_basis": "project_owner_confirmation_recorded_in_plan_2026_10_02",
               "review_status": "pending_identity_and_packet_audit", "overlap_records": len(overlaps),
               "required_next_step": "Bind actual independent reviews, explicit scopes/context and exposure history before freezing."}
    sidecar = {"schema_version": 2, "dataset_sha256": sha256(path),
               "index_sha256": sha256(index_dir / "manifest.json"), "qid_mapping": mapping,
               "corrections": corrections, "connected_groups": families, "overlaps": overlaps,
               "missing_fields_by_qid": missing,
               "heldout_eligible": False, "heldout_blocker": "review_and_exposure_audit_pending"}
    return rows, summary, sidecar


def verify_summary(dataset: Path, summary: dict) -> None:
    if summary.get("dataset_sha256") != sha256(dataset) or summary.get("total") != len(load_rows(dataset)):
        raise ValueError("candidate summary does not bind current raw bytes/count")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("data/benchmark/human_candidate_pool.jsonl"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/hybrid-index"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/benchmark"))
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)
    rows, summary, sidecar = prepare(args.dataset, args.index_dir, args.dataset.parent)
    summary_path = args.output_dir / "human_candidate_pool.summary.json"
    staging_path = args.output_dir / "human_candidate_staging.jsonl"
    if args.verify:
        actual = read_json(summary_path)
        verify_summary(args.dataset, actual)
        if actual != summary or load_rows(staging_path) != rows or read_json(args.output_dir / "human_candidate_lineage.json") != sidecar:
            raise ValueError("candidate artifacts are not the deterministic regeneration")
    else:
        # Never overwrite the author's raw input even with a custom output-dir.
        destinations = (staging_path, summary_path, args.output_dir / "human_candidate_lineage.json")
        if any(destination.resolve() == args.dataset.resolve() for destination in destinations):
            raise ValueError("candidate artifact destination aliases raw input")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        staging_path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n" for row in rows), encoding="utf-8")
        write_json(summary_path, summary)
        write_json(args.output_dir / "human_candidate_lineage.json", sidecar)
    print(json.dumps({"records": summary["total"], "groups": summary["groups"],
                      "release_eligible": summary["release_eligible"], "overlaps": summary["overlap_records"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
