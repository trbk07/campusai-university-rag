"""Fit the explainable hard-query route using dev only, never test/holdout."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from campusai.retrieval.calibration import RetrievalPolicy
from campusai.retrieval.hybrid import HybridRetriever
from evaluation.phase6_schema import load_jsonl


def route_metrics(samples: list[dict], confidence_threshold: float,
                  margin_threshold: float) -> dict:
    selected = [item for item in samples if not (
        item["confidence"] >= confidence_threshold and item["margin"] >= margin_threshold)]
    hard = [item for item in samples if item["difficulty"] == "hard"]
    easy = [item for item in samples if item["difficulty"] == "easy"]
    hard_selected = sum(item in selected for item in hard)
    easy_selected = sum(item in selected for item in easy)
    return {"eligible": len(samples), "selected": len(selected),
            "coverage": len(selected) / len(samples) if samples else 0.0,
            "hard_recall": hard_selected / len(hard) if hard else 0.0,
            "easy_unnecessary_rerank_rate": easy_selected / len(easy) if easy else 1.0,
            "selection_precision": sum(item["difficulty"] == "hard" for item in selected)
                                   / len(selected) if selected else 0.0,
            "false_skip_rate": 1 - hard_selected / len(hard) if hard else 1.0,
            "hard_count": len(hard), "easy_count": len(easy)}


def fit_route(samples: list[dict]) -> tuple[float, float, dict, bool]:
    confidence_values = sorted({0.0, 1.0, *(item["confidence"] for item in samples)})
    margin_values = sorted({0.0, *(item["margin"] for item in samples)})
    options = []
    for confidence in confidence_values:
        for margin in margin_values:
            metrics = route_metrics(samples, confidence, margin)
            feasible = (metrics["hard_recall"] >= .95
                        and metrics["easy_unnecessary_rerank_rate"] <= .20)
            options.append((feasible, confidence, margin, metrics))
    passing = [item for item in options if item[0]]
    if passing:
        chosen = min(passing, key=lambda item: (item[3]["coverage"],
                                                -item[3]["selection_precision"], item[1], item[2]))
    else:
        chosen = max(options, key=lambda item: (
            item[3]["hard_recall"] - max(0.0, item[3]["easy_unnecessary_rerank_rate"] - .20),
            -item[3]["coverage"]))
    return chosen[1], chosen[2], chosen[3], bool(passing)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", type=Path, default=Path("data/benchmark/phase6_retrieval_dev.jsonl"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/phase6-index"))
    parser.add_argument("--phase6-calibration", type=Path,
                        default=Path("evaluation/results/phase6_retrieval_calibration.json"))
    parser.add_argument("--output", type=Path, default=Path(".tmp/phase7-route-calibration.json"))
    args = parser.parse_args()
    policy = RetrievalPolicy.from_report(args.phase6_calibration, expected_mode="hybrid_rrf")
    retriever = HybridRetriever(args.index_dir, query_cache_size=0,
                                policies={"hybrid_rrf": policy})
    doc_ids = json.loads((args.index_dir / "manifest.json").read_text(encoding="utf-8"))["documents"]
    rows = load_jsonl(args.dev)
    samples = []
    bypass = {"exact_or_abstained": 0, "single_candidate": 0}
    for row in rows:
        results = retriever.search(row["question"], doc_ids=doc_ids,
                                   filters=row.get("filters"), top_k=40, mode="auto")
        trace = retriever.last_trace
        if trace.route in {"exact_code", "abstain"} or trace.abstained:
            bypass["exact_or_abstained"] += 1
            continue
        if len(results) < 2:
            bypass["single_candidate"] += 1
            continue
        samples.append({"qid": row["qid"], "difficulty": row["difficulty"],
                        "confidence": float(results[0].confidence_score or 0.0),
                        "margin": max(0.0, float(results[0].fusion_score or 0.0)
                                      - float(results[1].fusion_score or 0.0))})
    confidence, margin, metrics, feasible = fit_route(samples)
    report = {"schema_version": 1, "phase": 7, "version": "phase7-hard-route-dev-v1",
              "status": "pass" if feasible else "conditional", "calibration_split": "dev",
              "holdout_used": False,
              "training_split_sha256": hashlib.sha256(args.dev.read_bytes()).hexdigest(),
              "index_sha256": hashlib.sha256((args.index_dir / "manifest.json").read_bytes()).hexdigest(),
              "phase6_calibration_sha256": hashlib.sha256(args.phase6_calibration.read_bytes()).hexdigest(),
              "easy_confidence_threshold": confidence, "easy_margin_threshold": margin,
              "routing_metrics": metrics, "bypass": bypass}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if feasible else 1


if __name__ == "__main__":
    raise SystemExit(main())
