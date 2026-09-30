"""Fit the Phase 6 hybrid confidence threshold on dev only."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from campusai.retrieval.hybrid import HybridRetriever
from evaluation.metrics import recall_at_k
from evaluation.phase6_schema import load_jsonl


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=Path("data/benchmark/phase6_retrieval_dev.jsonl"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/phase6-index"))
    parser.add_argument("--output", type=Path, default=Path("evaluation/results/phase6_retrieval_calibration.json"))
    parser.add_argument("--max-fpr", type=float, default=0.05)
    parser.add_argument("--max-recall-drop", type=float, default=0.02)
    args = parser.parse_args()
    rows = load_jsonl(args.benchmark)
    if not rows or {row.get("split") for row in rows} != {"dev"}:
        raise SystemExit("calibration input must contain the dev split only")
    doc_ids = sorted(path.name for path in args.index_dir.iterdir()
                     if path.is_dir() and (path / "bm25.json").is_file())
    retriever = HybridRetriever(args.index_dir, query_cache_size=0)
    evaluated = []
    for row in rows:
        results = retriever.search(
            row["question"], doc_ids, filters=row.get("filters"), top_k=10, mode="auto"
        )
        evaluated.append((row, results))
    answerable = [(row, values) for row, values in evaluated if row.get("answerable")]
    negative = [(row, values) for row, values in evaluated if not row.get("answerable")]
    baseline = sum(recall_at_k(values, row["gold_evidence"], 5) for row, values in answerable) / len(answerable)
    candidates = sorted({0.0, 1.0, *[float(item.confidence_score or 0.0) for _row, values in evaluated for item in values]})
    trials = []
    for threshold in candidates:
        def accepted(values):
            return values if values and max((item.confidence_score or 0) for item in values) >= threshold else []
        positive_recall = sum(recall_at_k(accepted(values), row["gold_evidence"], 5)
                              for row, values in answerable) / len(answerable)
        fpr = sum(bool(accepted(values)) for _row, values in negative) / len(negative)
        trials.append({"threshold": threshold, "answerable_recall_at_5": positive_recall,
                       "false_positive_rate": fpr,
                       "recall_drop": baseline - positive_recall})
    valid = [trial for trial in trials if trial["false_positive_rate"] <= args.max_fpr
             and trial["recall_drop"] <= args.max_recall_drop]
    selected = min(valid, key=lambda item: (item["threshold"], -item["answerable_recall_at_5"])) if valid else None
    manifest_path = args.index_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = {
        "schema_version": 1, "phase": 6, "mode": "hybrid_rrf",
        "calibration_split": "dev", "holdout_used": False,
        "benchmark_sha256": _sha(args.benchmark), "index_sha256": _sha(manifest_path),
        "model": manifest.get("model_name"), "model_revision": manifest.get("model_revision"),
        "rrf": {"k": retriever.rrf_k, "bm25_weight": retriever.rrf_weights[0],
                "dense_weight": retriever.rrf_weights[1], "candidate_limit": retriever.candidate_limit},
        "constraints": {"max_false_positive_rate": args.max_fpr,
                        "max_answerable_recall_drop": args.max_recall_drop},
        "baseline_answerable_recall_at_5": round(baseline, 6),
        "result": None if selected is None else {key: round(value, 6) for key, value in selected.items()},
        "status": "pass" if selected else "fail", "population": {"total": len(rows),
        "answerable": len(answerable), "negative": len(negative)},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if selected else 1


if __name__ == "__main__":
    raise SystemExit(main())
