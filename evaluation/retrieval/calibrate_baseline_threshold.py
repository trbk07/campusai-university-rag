"""Fit the Phase 3 hybrid abstention threshold on dev records only."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from campusai.retrieval.hybrid import HybridRetriever
from evaluation.common.metrics import recall_at_k
from evaluation.retrieval.evaluate_baseline_release import load_splits


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-dir", type=Path, default=Path("data/benchmark"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/baseline-clean/baseline-index"))
    parser.add_argument("--output", type=Path, default=Path("evaluation/results/baseline_calibration.json"))
    parser.add_argument("--allow-draft", action="store_true", help="Diagnostic only; not release calibration")
    args = parser.parse_args()
    rows_by_split, errors = load_splits(args.benchmark_dir, require_review=not args.allow_draft)
    if errors:
        raise SystemExit(f"invalid Phase 3 benchmark: {errors}")
    dev = rows_by_split["dev"]
    doc_ids = json.loads((args.index_dir / "manifest.json").read_text(encoding="utf-8"))["documents"]
    retriever = HybridRetriever(args.index_dir, query_cache_size=0)
    observations = []
    for row in dev:
        results = retriever.search(row["question"], doc_ids, filters=row.get("filters"), top_k=5, mode="hybrid_rrf")
        observations.append({"positive": row["answerable"],
                             "confidence": max((float(result.confidence_score or 0.0) for result in results), default=0.0),
                             "relevant": recall_at_k(results, row["gold_evidence"], 5)})
    positives = [row for row in observations if row["positive"]]
    negatives = [row for row in observations if not row["positive"]]
    if not positives or not negatives:
        raise SystemExit("dev split needs positive and negative queries")
    trials = []
    for threshold in sorted({0.0, 1.0, *(row["confidence"] for row in observations)}):
        recall = sum(row["relevant"] for row in positives if row["confidence"] >= threshold) / len(positives)
        fpr = sum(row["confidence"] >= threshold for row in negatives) / len(negatives)
        trials.append({"threshold": threshold, "answerable_recall_at_5": recall, "false_positive_rate": fpr})
    feasible = [row for row in trials if row["answerable_recall_at_5"] >= .95 and row["false_positive_rate"] <= .01]
    selected = max(feasible, key=lambda row: row["threshold"]) if feasible else None
    safe = [row for row in trials if row["false_positive_rate"] <= .01]
    high_recall = [row for row in trials if row["answerable_recall_at_5"] >= .95]
    manifest = json.loads((args.index_dir / "manifest.json").read_text(encoding="utf-8"))
    report = {"schema_version": 1, "phase": 3, "mode": "hybrid_rrf", "score_field": "confidence_score",
              "annotation_status": "draft_unreviewed" if args.allow_draft else "independently_reviewed",
              "calibration_split": "dev", "holdout_used": False,
              "benchmark_sha256": sha(args.benchmark_dir / "baseline_retrieval_dev.jsonl"),
              "index_sha256": sha(args.index_dir / "manifest.json"),
              "model": manifest["model_name"], "model_revision": manifest["model_revision"],
              "population": {"total": len(dev), "positive": len(positives), "negative": len(negatives)},
              "constraints": {"min_answerable_recall_at_5": .95, "max_false_positive_rate": .01},
              "baseline_answerable_recall_at_5": trials[0]["answerable_recall_at_5"],
              "best_recall_with_fpr_at_most_1pct": max((row["answerable_recall_at_5"] for row in safe), default=None),
              "best_fpr_with_recall_at_least_95pct": min((row["false_positive_rate"] for row in high_recall), default=None),
              "result": selected, "status": "diagnostic" if args.allow_draft and selected else "pass" if selected else "fail"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if selected else 1


if __name__ == "__main__":
    raise SystemExit(main())
