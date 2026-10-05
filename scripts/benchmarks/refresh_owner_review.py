"""Refresh M1/S1 input reports from a bound owner confirmation; never freeze data."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence, validate_rows, exposure_registry_errors, grouped_split_report
from evaluation.benchmarks.owner_review import load_confirmation
from evaluation.common.release_artifacts import read_json, sha256, write_json
from evaluation.reranker.build_supplemental_report import archive_lineage_observations, assemble
from evaluation.reranker.reranker_release_gates import default_args
from evaluation.reranker.supplemental_gates import review_audit_errors
from scripts.benchmarks.prepare_human_candidates import load_rows


def refresh(benchmark: Path, results: Path, index: Path) -> dict:
    confirmation, sources = load_confirmation(benchmark)
    dataset = benchmark / "human_retrieval.jsonl"
    rows = load_rows(dataset)
    audit_path = benchmark / "human_retrieval_review_audit.jsonl"
    audit = load_rows(audit_path)
    errors = review_audit_errors(rows, audit, index, owner_identity=confirmation["owner_identity"],
                                owner_confirmation=confirmation, confirmed_sources=sources)
    if errors:
        raise ValueError("owner-confirmed export changed: " + ", ".join(errors))
    regression = [row for path in benchmark.glob("hybrid_retrieval_*.jsonl") for row in load_rows(path)]
    review = validate_rows(rows, frozen_evidence(index), regression, owner_identity=confirmation["owner_identity"])
    review.update(dataset_sha256=sha256(dataset), index_sha256=sha256(index / "manifest.json"),
                  review_policy_sha256=sha256(benchmark / "phase7_review_policy.json"),
                  owner_confirmation_sha256=sha256(benchmark / "phase7_owner_confirmation.json"),
                  review_audit_sha256=sha256(audit_path), grouped_split=grouped_split_report(rows))
    exposure_errors = exposure_registry_errors(rows, read_json(benchmark / "phase7_exposure_registry.json"),
                                              source_pool=benchmark / "human_candidate_pool.jsonl",
                                              source_lineage=benchmark / "human_candidate_lineage.json",
                                              index_manifest=index / "manifest.json")
    for split in ("dev", "test", "holdout"):
        if load_rows(benchmark / f"human_retrieval_{split}.jsonl") != [row for row in rows if row["split"] == split]:
            raise ValueError("owner-confirmed split content changed: " + split)
    manifest_path = results / "human_benchmark_manifest.json"
    if manifest_path.is_file() and read_json(manifest_path).get("frozen") is True:
        raise ValueError("retain the existing frozen manifest in its historical archive before refreshing inputs")
    write_json(results / "human_benchmark_review.json", review)
    manifest = {**review, "frozen": False, "status": "conditional", "release_eligible": False,
                "errors": sorted(set(review["errors"] + exposure_errors + ["benchmark_not_frozen"])),
                "split_sha256": {split: sha256(benchmark / f"human_retrieval_{split}.jsonl")
                                  for split in ("dev", "test", "holdout")},
                "review_sha256": sha256(results / "human_benchmark_review.json")}
    write_json(manifest_path, manifest)
    cfg = vars(default_args(results))
    cfg.update(benchmark_dir=benchmark, index_dir=index)
    observations = archive_lineage_observations(audit_path, results, benchmark)
    lineage = assemble("S1", cfg, {"baseline": read_json(results / "retrieval_baseline_manifest.json")}, observations)
    write_json(results / "reranker_lineage.json", lineage)
    return {"review_status": review["status"], "review_mode": review["review_mode"],
            "review_complete": review["review_complete"], "benchmark_frozen": False,
            "lineage_status": lineage["status"], "lineage_errors": dict(Counter(e.split(":", 1)[0] for e in lineage["errors"]))}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-dir", type=Path, default=Path("data/benchmark"))
    parser.add_argument("--results-dir", type=Path, default=Path("evaluation/results"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/hybrid-index"))
    args = parser.parse_args(argv)
    try:
        result = refresh(args.benchmark_dir, args.results_dir, args.index_dir)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}))
        return 1
    print(json.dumps(result))
    return 0 if result["review_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
