"""CLI for BM25, dense, hybrid, and hybrid+rerank retrieval evaluation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.metrics import evaluate_retrieval
from campusai.retrieval.hybrid import HybridRetriever
from campusai.retrieval.reranker import Reranker


def load_jsonl(path: str | Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", default="data/benchmark/dev.jsonl")
    parser.add_argument("--index-root", default="data/index")
    parser.add_argument("--output", default="evaluation/results/retrieval-dev.json")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    records = load_jsonl(args.benchmark)
    output = {}
    for mode, reranker in (("bm25", None), ("dense", None), ("hybrid", None), ("hybrid_rerank", Reranker())):
        retriever = HybridRetriever(args.index_root, reranker=reranker)
        output[mode] = evaluate_retrieval(
            records,
            lambda record, m=mode, r=retriever: r.search(record["question"], [e["doc_id"] for e in record.get("gold_evidence", [])], top_k=args.top_k, mode=m),
        )
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
