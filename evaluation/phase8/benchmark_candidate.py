"""Prepare a deterministic, auditable Phase 8 benchmark candidate.

The candidate selects the existing test and holdout rows without copying or
rewriting them. It is intentionally not a release freeze: prior exposure and
independent-review status are recorded so the candidate cannot be mistaken for
fresh, independently approved evidence.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from evaluation.benchmarks.connected_groups import connected_groups


DEFAULT_BENCHMARK = Path("data/benchmark/grounding_reviewed.jsonl")
DEFAULT_CORPUS_MANIFEST = Path("data/corpus/university/manifest.json")
R18_BENCHMARK = Path("data/benchmark/phase7_review_cycles/phase7-release-20261004-r18/human_retrieval.jsonl")
R18_REVIEW = Path("evaluation/results/phase7-source-context-20261004-r18/human_benchmark_manifest.json")
R18_HISTORICAL_RETRIEVAL = Path("evaluation/results/phase7-source-context-20261004-r18/hybrid_holdout_report.json")
P8_R18_RETRIEVAL = Path("evaluation/results/phase8-r18-retrieval-baseline-v1.json")
INCLUDED_SPLITS = {"test", "holdout"}
EXPECTED_CATEGORIES = {
    "answerable", "multi_evidence", "table", "document_does_not_mention",
    "no_evidence", "conflict", "ambiguous", "adversarial",
    "temporal/stale_source", "numeric_contradiction", "partial_support",
    "provider_abstention",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_rows(path: Path = DEFAULT_BENCHMARK) -> tuple[bytes, list[dict]]:
    raw = path.read_bytes()
    rows = [json.loads(line) for line in raw.decode("utf-8-sig").splitlines() if line.strip()]
    return raw, rows


def _r18_alternative() -> dict:
    raw, all_rows = load_rows(R18_BENCHMARK)
    rows = [row for row in all_rows if row.get("split") in INCLUDED_SPLITS]
    connected = connected_groups([{
        "qid": row["qid"], "question": row.get("question", ""),
        "source_group": row.get("source_group", ""),
        "paraphrase_group": row.get("paraphrase_group", ""),
    } for row in rows])
    review_raw = R18_REVIEW.read_bytes()
    review = json.loads(review_raw.decode("utf-8-sig"))
    historical = json.loads(R18_HISTORICAL_RETRIEVAL.read_text(encoding="utf-8-sig"))
    historical_hashes = historical.get("benchmark_sha256", {})
    reviewed_hashes = review.get("split_sha256", {})
    retrieval_baseline = None
    if P8_R18_RETRIEVAL.is_file():
        baseline = json.loads(P8_R18_RETRIEVAL.read_text(encoding="utf-8-sig"))
        retrieval_baseline = {
            "path": P8_R18_RETRIEVAL.as_posix(),
            "sha256": sha256_bytes(P8_R18_RETRIEVAL.read_bytes()),
            "status": baseline.get("status"),
            "gate_eligible": baseline.get("gate_eligible"),
        }
    tags = Counter(tag for row in rows for tag in row.get("tags", []))
    splits = Counter(row["split"] for row in rows)
    return {
        "benchmark_path": R18_BENCHMARK.as_posix(),
        "benchmark_sha256": sha256_bytes(raw),
        "review_manifest_path": R18_REVIEW.as_posix(),
        "review_manifest_sha256": sha256_bytes(review_raw),
        "review_status": review.get("status"),
        "review_mode": review.get("review_mode"),
        "owner_review_complete": review.get("owner_review_complete"),
        "independent_review_complete": review.get("independent_review_complete"),
        "exposure": "previous Phase 7 evaluation; regression use only",
        "rows_in_test_and_holdout": len(rows),
        "splits": dict(sorted(splits.items())),
        "connected_groups": len(set(connected.values())),
        "largest_connected_group": max(Counter(connected.values()).values(), default=0),
        "tag_counts": dict(sorted(tags.items())),
        "temporal_or_comparison_tags_present": bool(tags.keys() & {"temporal", "comparison"}),
        "prior_retrieval_report": {
            "path": R18_HISTORICAL_RETRIEVAL.as_posix(),
            "sha256": sha256_bytes(R18_HISTORICAL_RETRIEVAL.read_bytes()),
            "reported_split_hashes_match_owner_reviewed_splits": all(
                historical_hashes.get(split) == reviewed_hashes.get(split)
                for split in ("test", "holdout")
            ),
        },
        "phase8_retrieval_baseline": retrieval_baseline,
        "candidate_disposition": "reviewed_regression_candidate_with_temporal_comparison_gap",
    }


def build_candidate(path: Path = DEFAULT_BENCHMARK,
                    corpus_manifest_path: Path = DEFAULT_CORPUS_MANIFEST) -> dict:
    raw, all_rows = load_rows(path)
    rows = [row for row in all_rows if row.get("split") in INCLUDED_SPLITS]
    ids = [row.get("id") for row in rows]
    if not 100 <= len(rows) <= 300:
        raise ValueError(f"candidate size must be 100..300; got {len(rows)}")
    if any(not isinstance(item, str) or not item.strip() for item in ids) or len(ids) != len(set(ids)):
        raise ValueError("candidate ids must be unique, non-empty strings")
    categories = Counter(row.get("category") for row in rows)
    missing = EXPECTED_CATEGORIES - categories.keys()
    if missing:
        raise ValueError("candidate missing categories: " + ", ".join(sorted(missing)))

    group_rows = [{
        "qid": row["id"],
        "question": row.get("question", ""),
        "source_group": row.get("source_group", ""),
        "template_group": row.get("template_group", ""),
    } for row in rows]
    groups = connected_groups(group_rows)
    group_sizes = Counter(groups.values())
    exact_groups = connected_groups(group_rows, near_matches=False)
    exact_group_sizes = Counter(exact_groups.values())
    splits = Counter(row["split"] for row in rows)
    reviewer_ids = sorted({str(row.get("annotator_id", "")) for row in rows})
    review_statuses = Counter(str(row.get("review_status", "missing")) for row in rows)
    source_ids = {
        str(evidence.get("doc_id"))
        for row in rows
        for claim in row.get("gold_claims", [])
        for evidence in claim.get("evidence", [])
        if evidence.get("doc_id")
    }
    corpus_manifest = json.loads(corpus_manifest_path.read_text(encoding="utf-8-sig"))
    corpus_docs = corpus_manifest.get("documents", [])
    selected_sources = [doc for doc in corpus_docs if doc.get("sha256") in source_ids]
    unselected_sources = [doc for doc in corpus_docs if doc.get("sha256") not in source_ids]
    blockers = [
        "independent_human_review_not_attested",
        "selected_test_and_holdout_rows_were_previously_evaluated",
        "all_rows_form_one_connected_component",
        "no_eligible_product_answer_baseline_bound_to_this_candidate",
        "latency_and_resource_measurements_not_bound_to_this_candidate",
        "group_aware_confidence_interval_not_estimable_from_one_component",
    ]
    return {
        "schema_version": 1,
        "phase": 8,
        "candidate_version": "phase8-grounding-test-holdout-candidate-v1",
        "status": "not_eligible_existing_data",
        "gate_eligible": False,
        "benchmark": {
            "path": path.as_posix(),
            "source_sha256": sha256_bytes(raw),
            "source_rows": len(all_rows),
            "selection": "split in ['test', 'holdout']",
            "selection_sha256": sha256_bytes("\n".join(sorted(ids)).encode("utf-8")),
            "rows": len(rows),
            "splits": dict(sorted(splits.items())),
            "categories": dict(sorted(categories.items())),
            "ids": sorted(ids),
        },
        "connected_groups": {
            "count": len(group_sizes),
            "largest_group_size": max(group_sizes.values(), default=0),
            "group_size_histogram": dict(sorted(Counter(group_sizes.values()).items())),
            "without_near_match_linking": {
                "count": len(exact_group_sizes),
                "largest_group_size": max(exact_group_sizes.values(), default=0),
                "group_size_histogram": dict(sorted(Counter(exact_group_sizes.values()).items())),
            },
            "method": "transitive shared source_group/template_group/exact normalized question",
            "near_match_threshold": 0.85,
        },
        "corpus_coverage": {
            "manifest_path": corpus_manifest_path.as_posix(),
            "manifest_sha256": sha256_bytes(corpus_manifest_path.read_bytes()),
            "corpus_documents": len(corpus_docs),
            "documents_represented": len(selected_sources),
            "represented_filenames": sorted(doc.get("filename", "") for doc in selected_sources),
            "documents_not_represented": len(unselected_sources),
            "unrepresented_filenames": sorted(doc.get("filename", "") for doc in unselected_sources),
            "exposure_status_of_unrepresented_sources": "not_audited",
        },
        "review": {
            "row_review_statuses": dict(sorted(review_statuses.items())),
            "annotator_ids": reviewer_ids,
            "independent_reviewer_signoff": "missing",
            "note": "Engineering review labels do not prove independent human signoff.",
        },
        "exposure": {
            "prior_phase5_grounding_evaluation": True,
            "fresh_holdout": False,
            "note": "These test/holdout rows were previously evaluated; do not claim fresh validation.",
        },
        "phase8_exit_blockers": blockers,
        "alternative_existing_benchmark": _r18_alternative(),
        "freeze_decision": "new_independently_reviewed_benchmark_required",
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--output", type=Path, default=None,
                        help="Optional path for a review packet; omitted prints JSON to stdout")
    args = parser.parse_args()
    manifest = build_candidate(args.benchmark)
    payload = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
