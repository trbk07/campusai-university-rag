"""Freeze and verify a Phase 6 report before any Phase 7 fitting.

The two reruns must come from the same source tree and artifacts. This tool
never rewrites the historical Phase 6 report to make a comparison pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def model_tree_hash(root: Path) -> str:
    if not root.is_dir():
        raise ValueError("dense model snapshot directory is missing")
    files = sorted(path for path in root.rglob("*") if path.is_file())
    if not files:
        raise ValueError("dense model snapshot is empty")
    manifest = [(path.relative_to(root).as_posix(), sha256(path)) for path in files]
    return hashlib.sha256(json.dumps(manifest, separators=(",", ":")).encode()).hexdigest()


def stable_metrics(report: dict) -> dict:
    return {
        "benchmark_sha256": report.get("benchmark_sha256"),
        "index_sha256": report.get("index_sha256"),
        "calibration_sha256": report.get("calibration_sha256"),
        "model": report.get("model"),
        "model_revision": report.get("model_revision"),
        "rrf": report.get("rrf"),
        "test_quality": report.get("primary_test", {}).get("quality"),
        "holdout_quality": report.get("primary_holdout", {}).get("quality"),
        "test_negative": report.get("primary_test", {}).get("negative"),
        "holdout_negative": report.get("primary_holdout", {}).get("negative"),
        "test_auto_ranking": {key: report.get("ablation", {}).get("auto", {}).get(key)
                              for key in ("recall_at_5", "mrr", "ndcg_at_5", "fpr")},
    }


def create_grounding_baseline(args: argparse.Namespace) -> tuple[dict, dict]:
    paths = (args.reference, args.rerun_a, args.rerun_b, args.index_manifest,
             args.corpus_manifest, args.performance, args.model_dir)
    if any(not path.exists() for path in paths):
        raise ValueError("baseline input missing: " + ", ".join(str(path) for path in paths if not path.exists()))
    reference, first, second = (json.loads(path.read_text(encoding="utf-8"))
                                for path in (args.reference, args.rerun_a, args.rerun_b))
    performance = json.loads(args.performance.read_text(encoding="utf-8"))
    index = json.loads(args.index_manifest.read_text(encoding="utf-8"))
    baseline = stable_metrics(reference)
    first_metrics, second_metrics = stable_metrics(first), stable_metrics(second)
    errors = []
    if reference.get("status") != "pass" or first.get("status") != "pass" or second.get("status") != "pass":
        errors.append("phase6_report_not_pass")
    if first_metrics != second_metrics:
        errors.append("reruns_not_deterministic")
    if first_metrics != baseline:
        errors.append("historical_rc3_not_reproduced")
    index_hash = sha256(args.index_manifest)
    if any(report.get("index_sha256") != index_hash for report in (reference, first, second)):
        errors.append("index_hash_mismatch")
    if index.get("model_name") != reference.get("model"):
        errors.append("dense_model_mismatch")
    source_tree = args.source_tree.resolve()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source_tree, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=source_tree, text=True).strip())
    if dirty:
        errors.append("source_tree_dirty")
    manifest = {
        "schema_version": 1, "phase": 7, "base_release": "phase6-rc3",
        "status": "pass" if not errors else "conditional", "errors": errors,
        "commit": commit, "working_tree_clean": not dirty,
        "reference_report_sha256": sha256(args.reference),
        "rerun_report_sha256": [sha256(args.rerun_a), sha256(args.rerun_b)],
        "benchmark_sha256": reference.get("benchmark_sha256"),
        "corpus_sha256": sha256(args.corpus_manifest),
        "index_sha256": index_hash,
        "dense_model": {"name": index.get("model_name"),
                        "revision": args.model_dir.name,
                        "sha256": model_tree_hash(args.model_dir)},
        "calibration_sha256": reference.get("calibration_sha256"),
        "rrf": reference.get("rrf"),
        "performance_report_sha256": sha256(args.performance),
    }
    report = {"schema_version": 1, "phase": 7, "base_release": "phase6-rc3",
              "status": manifest["status"], "errors": errors,
              "historical": baseline, "rerun_a": first_metrics, "rerun_b": second_metrics,
              "performance": {"latency": performance.get("latency"),
                              "memory": performance.get("memory"),
                              "concurrency_20": performance.get("concurrency", {}).get("20")},
              "rejected_baselines": []}
    for path in args.rejected_report:
        if not path.is_file():
            raise ValueError(f"rejected baseline evidence missing: {path}")
        candidate = json.loads(path.read_text(encoding="utf-8"))
        metrics = stable_metrics(candidate)
        report["rejected_baselines"].append({
            "report_sha256": sha256(path), "metrics": metrics,
            "reason": ("different_calibration_or_code" if metrics != baseline
                       else "same_quality_not_rejected")})
    manifest["rejected_report_sha256"] = [item["report_sha256"] for item in report["rejected_baselines"]]
    return report, manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, default=Path("evaluation/results/hybrid_holdout_report.json"))
    parser.add_argument("--rerun-a", type=Path, required=True)
    parser.add_argument("--rerun-b", type=Path, required=True)
    parser.add_argument("--index-manifest", type=Path, default=Path(".tmp/hybrid-index/manifest.json"))
    parser.add_argument("--corpus-manifest", type=Path, default=Path("data/corpus/university/manifest.json"))
    parser.add_argument("--performance", type=Path, default=Path("evaluation/results/hybrid_performance_report.json"))
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--source-tree", type=Path, default=Path("."))
    parser.add_argument("--rejected-report", type=Path, action="append", default=[])
    parser.add_argument("--output-dir", type=Path, default=Path(".tmp/reranker-baseline-evidence"))
    args = parser.parse_args()
    report, manifest = create_grounding_baseline(args)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "retrieval_baseline_comparison.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "retrieval_baseline_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Phase 7 frozen Phase 6 baseline", "", f"Status: {report['status']}.", "",
             f"Commit: `{manifest['commit']}`.", "", "Errors: " + (", ".join(report["errors"]) or "none") + ".", "",
             "Historical RC3 and both reruns are preserved separately; no metric was rewritten.", ""]
    (args.output_dir / "retrieval_baseline_comparison.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": report["status"], "errors": report["errors"],
                      "output_dir": str(args.output_dir)}, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
