"""Fit an abstention threshold on a calibration split only."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from campusai.retrieval.calibration import select_threshold
from campusai.retrieval.hybrid import HybridRetriever
from campusai.retrieval.reranker import Reranker
from evaluation.common.metrics import recall_at_k
from evaluation.retrieval.run_retrieval_benchmark import _indexed_document_ids, load_jsonl


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibration", default="data/benchmark/retrieval_calibration.jsonl")
    parser.add_argument("--index-dir", default="data/index")
    parser.add_argument("--mode", choices=("dense", "hybrid", "hybrid_rerank"), default="dense")
    parser.add_argument("--reranker-model", default=None)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-recall", type=float, default=0.85)
    parser.add_argument("--max-fpr", type=float, default=0.05)
    parser.add_argument("--output", default="evaluation/results/retrieval_calibration.json")
    args = parser.parse_args()
    records = load_jsonl(args.calibration)
    document_ids = _indexed_document_ids(args.index_dir)
    reranker = Reranker(model_name=args.reranker_model) if args.reranker_model else None
    retriever = HybridRetriever(args.index_dir, query_cache_size=0, reranker=reranker)
    if not records or {record.get("split") for record in records} not in ({"dev"}, {"calibration"}):
        raise SystemExit("calibration input must contain only dev/calibration records")
    if not document_ids:
        raise SystemExit("calibration requires a complete index")
    scores, labels, relevant_at_5 = [], [], []
    for record in records:
        results = retriever.search(record["question"], document_ids, top_k=args.top_k, mode=args.mode)
        score = max((float(result.confidence_score or 0.0) for result in results), default=0.0) if args.mode == "hybrid" else (float(results[0].score) if results else 0.0)
        scores.append(score)
        labels.append(bool(record.get("gold_evidence")))
        relevant_at_5.append(recall_at_k(results, record.get("gold_evidence", []), 5))
    result = select_threshold(scores, labels, min_recall=args.min_recall, max_false_positive_rate=args.max_fpr)
    relevant_recall = sum(hit for hit, positive, score in zip(relevant_at_5, labels, scores) if positive and score >= result.threshold) / sum(labels)
    if relevant_recall < args.min_recall:
        raise SystemExit("calibrated answerable Recall@5 is below min-recall")
    benchmark_path = Path(args.calibration)
    index_manifest = Path(args.index_dir) / "manifest.json"
    report = {"calibration_split": str(benchmark_path), "mode": args.mode,
              "score_field": "confidence_score" if args.mode == "hybrid" else "score",
              "benchmark_sha256": hashlib.sha256(benchmark_path.read_bytes()).hexdigest(),
              "index_sha256": hashlib.sha256(index_manifest.read_bytes()).hexdigest() if index_manifest.exists() else None,
              "population": {"total": len(records), "positive": sum(labels), "negative": len(labels) - sum(labels)},
              "constraints": {"min_recall": args.min_recall, "max_false_positive_rate": args.max_fpr},
              "answerable_recall_at_5": relevant_recall, "scores": scores, "labels": labels,
              "result": result.__dict__}
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
