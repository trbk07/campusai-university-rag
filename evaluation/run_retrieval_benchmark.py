"""Reproducible Phase 3 retrieval quality and latency benchmark."""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from campusai.retrieval.hybrid import HybridRetriever
from campusai.retrieval.reranker import Reranker
from evaluation.metrics import evaluate_retrieval


def load_jsonl(path: str | Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def load_calibration_threshold(path: str | Path) -> tuple[float, dict]:
    """Load a locked threshold produced from a calibration split."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    result = data.get("result", {})
    threshold = result.get("threshold")
    if not isinstance(threshold, (int, float)) or threshold < 0:
        raise ValueError("calibration report has no valid non-negative threshold")
    mode = data.get("mode")
    if mode not in {"bm25", "dense", "hybrid", "rerank", "hybrid_rerank"}:
        raise ValueError("calibration report has no valid retrieval mode")
    return float(threshold), {"path": str(path), "mode": mode, "calibration_split": data.get("calibration_split"), "result": result}


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((percentile / 100) * len(ordered) + 0.5) - 1))
    return round(ordered[index], 3)


def _indexed_document_ids(index_dir: str | Path) -> list[str]:
    """Return every complete document index in the selected corpus.

    Gold evidence is used only for scoring. It must never determine the search
    scope, otherwise the benchmark leaks the answer's document into retrieval.
    """
    root = Path(index_dir)
    if not root.exists():
        return []
    return sorted(
        path.name
        for path in root.iterdir()
        if path.is_dir() and (path / "bm25.json").is_file() and (path / "dense.json").is_file()
    )


def _corpus_metadata(index_dir: str | Path, document_ids: list[str]) -> dict:
    """Read reproducibility metadata from every dense index manifest."""
    metadata = []
    for doc_id in document_ids:
        path = Path(index_dir) / doc_id / "dense.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        manifest = data.get("manifest", {})
        metadata.append({
            "document_id": doc_id,
            "model_name": manifest.get("model_name"),
            "model_revision": manifest.get("model_revision"),
            "provider": manifest.get("provider"),
            "embedding_dimension": manifest.get("embedding_dimension"),
            "item_count": manifest.get("item_count", len(data.get("items", []))),
            "corpus_hash": manifest.get("corpus_hash"),
        })
    models = sorted({item["model_name"] for item in metadata})
    revisions = sorted({item["model_revision"] for item in metadata})
    providers = sorted({item["provider"] for item in metadata})
    dimensions = sorted({item["embedding_dimension"] for item in metadata})
    return {
        "document_count": len(metadata),
        "chunk_count": sum(int(item["item_count"] or 0) for item in metadata),
        "models": models,
        "model_revisions": revisions,
        "providers": providers,
        "embedding_dimensions": dimensions,
        "documents": metadata,
    }


def _negative_metrics(records: list[dict], result_counts: dict[str, int], top_k: int) -> dict:
    negative = [record for record in records if record.get("category") == "negative" or record.get("query_type") == "negative"]
    if not negative:
        return {"n": 0, "abstention_rate": None, "false_positive_rate": None, "mean_results": None, "top_k": top_k}
    counts = [result_counts.get(record.get("qid"), 0) for record in negative]
    return {
        "n": len(negative),
        "abstention_rate": round(sum(count == 0 for count in counts) / len(counts), 6),
        "false_positive_rate": round(sum(count > 0 for count in counts) / len(counts), 6),
        "mean_results": round(statistics.mean(counts), 6),
        "top_k": top_k,
    }


def benchmark_mode(records: list[dict], index_dir: str | Path, mode: str, top_k: int, score_threshold: float | None = None, reranker_model: str | None = None) -> dict:
    reranker = Reranker(model_name=reranker_model) if reranker_model and mode in {"rerank", "hybrid_rerank"} else None
    retriever = HybridRetriever(index_dir, query_cache_size=0, reranker=reranker)
    latencies: list[float] = []
    result_counts: dict[str, int] = {}
    document_ids = _indexed_document_ids(index_dir)
    if not document_ids:
        raise ValueError(f"no complete document indexes found under {index_dir}")
    corpus_metadata = _corpus_metadata(index_dir, document_ids)
    load_started = time.perf_counter()
    for doc_id in document_ids:
        retriever.load_document(doc_id)
    load_ms = (time.perf_counter() - load_started) * 1000

    def retrieve(record):
        started = time.perf_counter()
        # Do not derive candidates from gold_evidence: that would leak the
        # answer's document and invalidate Recall@k as a retrieval metric.
        result = retriever.search(record["question"], document_ids, top_k=top_k, mode=mode, score_threshold=score_threshold)
        result_counts[record.get("qid")] = len(result)
        latencies.append((time.perf_counter() - started) * 1000)
        return result

    quality = evaluate_retrieval(records, retrieve, k_values=(1, 3, 5))
    by_qid = {row["qid"]: row for row in quality["per_query"]}

    def grouped(field: str) -> dict[str, dict]:
        groups: dict[str, list[dict]] = {}
        for record in records:
            groups.setdefault(str(record.get(field, "unknown")), []).append(by_qid[record["qid"]])
        return {
            key: {
                "n": len(rows),
                "recall_at_5": round(sum(row["recall"]["5"] for row in rows) / len(rows), 6),
                "mrr": round(sum(row["mrr"] for row in rows) / len(rows), 6),
            }
            for key, rows in groups.items()
        }

    warm_latencies = latencies[1:] if len(latencies) > 1 else latencies
    return {
        "quality": quality,
        "score_threshold": score_threshold,
        "negative_queries": _negative_metrics(records, result_counts, top_k),
        "corpus": corpus_metadata,
        "breakdown": {field: grouped(field) for field in ("category", "difficulty", "language", "query_type")},
        "latency_ms": {"cold_query": round(latencies[0], 3) if latencies else None,
                        "p50": _percentile(warm_latencies, 50), "p95": _percentile(warm_latencies, 95),
                        "p99": _percentile(warm_latencies, 99), "count": len(latencies)},
        "warm_query_ms": round(statistics.mean(warm_latencies), 3) if warm_latencies else None,
        "load_ms": round(load_ms, 3), "loaded_documents": len(retriever._indexes),
        "index_size_bytes": sum(path.stat().st_size for path in Path(index_dir).rglob("*") if path.is_file()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", default="data/benchmark/retrieval_test.jsonl")
    parser.add_argument("--index-dir", "--index-root", dest="index_dir", default="data/index")
    parser.add_argument("--output", default="evaluation/results/phase3_hash.json")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--score-threshold", type=float, default=None)
    parser.add_argument("--reranker-model", default=None)
    parser.add_argument("--mode", choices=("all", "bm25", "dense", "hybrid", "rerank", "hybrid_rerank"), default="all")
    parser.add_argument("--calibration-report", default=None, help="Use the locked threshold from a calibration report")
    args = parser.parse_args()
    threshold_source = None
    if args.calibration_report:
        calibrated_threshold, threshold_source = load_calibration_threshold(args.calibration_report)
        if args.score_threshold is not None and args.score_threshold != calibrated_threshold:
            raise SystemExit("--score-threshold conflicts with --calibration-report threshold")
        args.score_threshold = calibrated_threshold
        calibrated_mode = threshold_source["mode"]
        if args.mode not in {"all", calibrated_mode}:
            raise SystemExit("--mode conflicts with --calibration-report mode")
        args.mode = calibrated_mode
    records = load_jsonl(args.benchmark)
    modes = (args.mode,) if args.mode != "all" else ("bm25", "dense", "hybrid", "hybrid_rerank")
    report = {
        "schema_version": 1, "phase": "phase3", "benchmark": str(Path(args.benchmark)),
        "benchmark_count": len(records), "environment": {"python": sys.version, "platform": platform.platform()},
        "index_dir": str(Path(args.index_dir)), "top_k": args.top_k,
        "score_threshold": args.score_threshold,
        "reranker_model": args.reranker_model,
        "threshold_source": threshold_source,
        "modes": {mode: benchmark_mode(records, args.index_dir, mode, args.top_k, args.score_threshold, args.reranker_model) for mode in modes if not (mode in {"rerank", "hybrid_rerank"} and not args.reranker_model)},
    }
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
