"""Validate and fingerprint the complete Phase 6 RC3 release evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "configs/phase6_retrieval_release.json",
    "data/corpus/university/manifest.json",
    "data/benchmark/phase6_retrieval_dev.jsonl",
    "data/benchmark/phase6_retrieval_test.jsonl",
    "data/benchmark/phase6_retrieval_holdout.jsonl",
    "evaluation/results/phase6_dataset_report.json",
    "evaluation/results/phase6_retrieval_calibration.json",
    "evaluation/results/phase6_bm25_report.json",
    "evaluation/results/phase6_dense_report.json",
    "evaluation/results/phase6_hybrid_report.json",
    "evaluation/results/phase6_ablation_report.json",
    "evaluation/results/phase6_holdout_report.json",
    "evaluation/results/phase6_performance_report.json",
    "evaluation/results/phase6_security_report.json",
    "evaluation/results/phase6_grounding_regression.json",
    "evaluation/results/phase6_rc1_remediation.json",
    "evaluation/results/phase6_rc2_remediation.json",
    "docs/phase6_retrieval_release.md",
    "docs/phase6_operations.md",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def validate() -> tuple[list[str], dict]:
    errors = [f"missing:{name}" for name in REQUIRED if not (ROOT / name).is_file()]
    if errors:
        return errors, {}
    config = _json(REQUIRED[0])
    corpus = _json(REQUIRED[1])
    dataset = _json("evaluation/results/phase6_dataset_report.json")
    calibration = _json("evaluation/results/phase6_retrieval_calibration.json")
    release = _json("evaluation/results/phase6_holdout_report.json")
    performance = _json("evaluation/results/phase6_performance_report.json")
    security = _json("evaluation/results/phase6_security_report.json")
    grounding = _json("evaluation/results/phase6_grounding_regression.json")
    if config.get("release_candidate") != "phase6-rc3" or not config.get("thresholds_frozen"):
        errors.append("release_config_not_locked_rc3")
    if dataset.get("status") != "pass" or dataset.get("records", 0) < 400 or dataset.get("documents", 0) < 8:
        errors.append("dataset_gate")
    if dataset.get("split_leakage") or dataset.get("duplicate_queries") or dataset.get("missing_gold_evidence"):
        errors.append("dataset_integrity")
    if calibration.get("status") != "pass" or calibration.get("calibration_split") != "dev" or calibration.get("holdout_used"):
        errors.append("calibration_gate")
    expected_rrf = config.get("rrf", {})
    if calibration.get("rrf") != expected_rrf:
        errors.append("rrf_config_mismatch")
    if release.get("status") != "pass" or release.get("errors"):
        errors.append("locked_holdout_gate")
    test, holdout = release.get("primary_test", {}), release.get("primary_holdout", {})
    for label, report in (("test", test), ("holdout", holdout)):
        if report.get("quality", {}).get("answerable_recall", {}).get("5", 0) < .90:
            errors.append(f"{label}_recall_at_5")
        if report.get("negative", {}).get("false_positive_rate", 1) > .05:
            errors.append(f"{label}_negative_fpr")
        if report.get("schema_invalid_rate") or report.get("provenance_loss_rate") or report.get("filter_leakage"):
            errors.append(f"{label}_contract")
    if release.get("exact_code_recall_at_5", 0) < .99 or release.get("routing_accuracy", 0) < .98:
        errors.append("exact_or_routing_gate")
    ablation = release.get("ablation", {})
    primary = ablation.get("auto", {})
    singles = [ablation.get("bm25", {}), ablation.get("dense", {})]
    if primary.get("recall_at_5", 0) <= max(item.get("recall_at_5", 0) for item in singles):
        errors.append("hybrid_recall_not_best")
    if primary.get("mrr", 0) <= max(item.get("mrr", 0) for item in singles):
        errors.append("hybrid_mrr_not_best")
    paired = release.get("statistical_validation", {}).get("paired_comparison", {})
    for name in ("hybrid_vs_bm25", "hybrid_vs_dense"):
        for metric in ("recall_at_5", "mrr"):
            if paired.get(name, {}).get(metric, {}).get("ci95", [-1])[0] <= 0:
                errors.append(f"bootstrap_not_positive:{name}:{metric}")
    if performance.get("status") != "pass" or performance.get("error_rate") or performance.get("timeout_rate"):
        errors.append("performance_gate")
    if performance.get("latency", {}).get("warm_p95_ms", 10**9) > 500:
        errors.append("warm_p95")
    if performance.get("concurrency", {}).get("20", {}).get("p99_ms", 10**9) > 1000:
        errors.append("concurrent_p99")
    if security.get("status") != "pass" or security.get("adversarial_false_positive_rate", 1) > .01:
        errors.append("security_gate")
    metrics = grounding.get("metrics", {})
    for key, expected in {
        "unsupported_claim_leakage": 0.0,
        "contradicted_claim_leakage": 0.0,
        "schema_invalid_rate": 0.0,
        "citation_coordinate_validity": 1.0,
        "citation_precision": 1.0,
        "citation_recall": 1.0,
    }.items():
        if metrics.get(key) != expected:
            errors.append(f"grounding:{key}")
    actual_checksums = {
        split: _sha(ROOT / f"data/benchmark/phase6_retrieval_{split}.jsonl")
        for split in ("dev", "test", "holdout")
    }
    if dataset.get("checksums") != actual_checksums:
        errors.append("benchmark_checksum_mismatch")
    if calibration.get("benchmark_sha256") != actual_checksums["dev"]:
        errors.append("calibration_benchmark_mismatch")
    if release.get("benchmark_sha256") != {key: actual_checksums[key] for key in ("test", "holdout")}:
        errors.append("release_benchmark_mismatch")
    if len(corpus.get("documents", [])) != dataset.get("documents"):
        errors.append("corpus_document_count_mismatch")
    summary = {
        "release_candidate": config.get("release_candidate"),
        "dataset": {"documents": dataset.get("documents"), "records": dataset.get("records")},
        "test_recall_at_5": test.get("quality", {}).get("answerable_recall", {}).get("5"),
        "holdout_recall_at_5": holdout.get("quality", {}).get("answerable_recall", {}).get("5"),
        "negative_fpr": max(test.get("negative", {}).get("false_positive_rate", 1),
                            holdout.get("negative", {}).get("false_positive_rate", 1)),
        "warm_p95_ms": performance.get("latency", {}).get("warm_p95_ms"),
        "concurrency_20_p99_ms": performance.get("concurrency", {}).get("20", {}).get("p99_ms"),
    }
    return errors, summary


def write_manifest(output: Path, index_dir: Path) -> dict:
    errors, summary = validate()
    if errors:
        raise SystemExit("cannot fingerprint failing release: " + ", ".join(errors))
    manifest_path = index_dir / "manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"index manifest not found: {manifest_path}")
    dirty_before_write = bool(_git("status", "--porcelain"))
    manifest = {
        "schema_version": 1, "phase": 6, "release_candidate": "phase6-rc3",
        "commit": _git("rev-parse", "HEAD"), "working_tree": dirty_before_write,
        "corpus_sha256": _sha(ROOT / "data/corpus/university/manifest.json"),
        "benchmark_dev_sha256": _sha(ROOT / "data/benchmark/phase6_retrieval_dev.jsonl"),
        "benchmark_test_sha256": _sha(ROOT / "data/benchmark/phase6_retrieval_test.jsonl"),
        "benchmark_holdout_sha256": _sha(ROOT / "data/benchmark/phase6_retrieval_holdout.jsonl"),
        "index_sha256": _sha(manifest_path),
        "model": "BAAI/bge-m3", "model_revision": "1",
        "config_sha256": _sha(ROOT / "configs/phase6_retrieval_release.json"),
        "python": platform.python_version(), "platform": platform.platform(),
        "artifacts": {name: _sha(ROOT / name) for name in REQUIRED},
        "summary": summary, "status": "pass",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-manifest", action="store_true")
    parser.add_argument("--manifest", type=Path, default=Path("evaluation/results/phase6_release_manifest.json"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/phase6-index"))
    parser.add_argument("--require-clean", action="store_true")
    args = parser.parse_args()
    errors, summary = validate()
    if args.require_clean and _git("status", "--porcelain"):
        errors.append("working_tree_dirty")
    if args.write_manifest and not errors:
        manifest = write_manifest(ROOT / args.manifest, ROOT / args.index_dir)
        summary["manifest"] = str(args.manifest)
        summary["source_commit"] = manifest["commit"]
    result = {"schema_version": 1, "phase": 6, "status": "pass" if not errors else "fail",
              "score": 10.0 if not errors else 0.0, "errors": errors, **summary}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
