"""Fit an abstention threshold on a calibration split only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from campusai.retrieval.calibration import select_threshold
from campusai.retrieval.hybrid import HybridRetriever
from campusai.retrieval.reranker import Reranker
from evaluation.metrics import _is_relevant
from evaluation.run_retrieval_benchmark import _indexed_document_ids, load_jsonl


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibration", default="data/benchmark/retrieval_calibration.jsonl")
    parser.add_argument("--index-dir", default="data/index")
    parser.add_argument("--mode", choices=("dense", "hybrid", "hybrid_rerank"), default="dense")
    parser.add_argument("--reranker-model", default=None)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-recall", type=float, default=0.85)
    parser.add_argument("--max-fpr", type=float, default=0.05)
    parser.add_argument("--output", default="evaluation/results/phase3_calibration.json")
    args = parser.parse_args()
    records = load_jsonl(args.calibration)
    document_ids = _indexed_document_ids(args.index_dir)
    reranker = Reranker(model_name=args.reranker_model) if args.reranker_model else None
    retriever = HybridRetriever(args.index_dir, query_cache_size=0, reranker=reranker)
    scores, labels = [], []
    for record in records:
        results = retriever.search(record["question"], document_ids, top_k=args.top_k, mode=args.mode)
        scores.append(float(results[0].score) if results else 0.0)
        labels.append(any(_is_relevant(result, record.get("gold_evidence", [])) for result in results))
    result = select_threshold(scores, labels, min_recall=args.min_recall, max_false_positive_rate=args.max_fpr)
    report = {"calibration_split": str(args.calibration), "mode": args.mode, "constraints": {"min_recall": args.min_recall, "max_false_positive_rate": args.max_fpr}, "scores": scores, "labels": labels, "result": result.__dict__}
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
