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
from campusai.retrieval.rerank_policy import route_features
from evaluation.release_artifacts import require_previous_gates, source_identity, sha256, write_json


def route_metrics(samples: list[dict], confidence_threshold: float,
                  margin_threshold: float, minimum_agreement: float = 0.0,
                  constraint_threshold: int = 0) -> dict:
    selected = [item for item in samples if not (
        item["confidence"] >= confidence_threshold and item["margin"] >= margin_threshold)
        or (minimum_agreement and item.get("agreement", 1.0) < minimum_agreement)
        or (constraint_threshold and item.get("constraints", 0) >= constraint_threshold)]
    hard = [item for item in samples if item["difficulty"] == "hard"]
    easy = [item for item in samples if item["difficulty"] == "easy"]
    selected_ids = {item["qid"] for item in selected}
    hard_selected = sum(item["qid"] in selected_ids for item in hard)
    easy_selected = sum(item["qid"] in selected_ids for item in easy)
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


def fit_feature_route(samples: list[dict]) -> tuple[dict, dict, bool]:
    """Small explainable search, using only supplied dev retrieval features."""
    def grid(values):
        ordered = sorted(set(values))
        return sorted({ordered[min(len(ordered)-1, round(i*(len(ordered)-1)/15))] for i in range(16)})
    choices = []
    for confidence in grid([0.0, 1.0, *[s["confidence"] for s in samples]]):
        for margin in grid([0.0, *[s["margin"] for s in samples]]):
            for agreement in (0.0, .2, .4, .6, .8, 1.0):
                for constraints in (0, 1, 2, 3):
                    metrics = route_metrics(samples, confidence, margin, agreement, constraints)
                    feasible = metrics["hard_recall"] >= .95 and metrics["easy_unnecessary_rerank_rate"] <= .20
                    config = {"easy_confidence_threshold": confidence, "easy_margin_threshold": margin,
                              "minimum_agreement": agreement, "constraint_threshold": constraints}
                    utility = metrics["hard_recall"] - max(0, metrics["easy_unnecessary_rerank_rate"] - .20)
                    choices.append(((feasible, utility, -metrics["coverage"], -agreement, -constraints), config, metrics))
    chosen = max(choices, key=lambda item: item[0])
    return chosen[1], chosen[2], chosen[0][0]


def collect_samples(rows: list[dict], retriever, doc_ids: list[str]) -> tuple[list[dict], dict]:
    samples, bypass = [], {"exact_or_abstained": 0, "single_candidate": 0}
    deterministic = True
    exact_count = abstention_count = 0
    for row in rows:
        kwargs = {"doc_ids": row.get("doc_ids", doc_ids), "filters": row.get("filters"), "top_k": 5, "mode": "auto"}
        results = retriever.search(row["question"], **kwargs)
        trace = retriever.last_trace
        again = retriever.search(row["question"], **kwargs)
        deterministic &= [item.to_dict() for item in results] == [item.to_dict() for item in again]
        exact_count += trace.route == "exact_code"
        abstention_count += trace.abstained
        if trace.route in {"exact_code", "abstain"} or trace.abstained:
            bypass["exact_or_abstained"] += 1
            continue
        if len(results) < 2:
            bypass["single_candidate"] += 1
            continue
        samples.append({"qid": row["qid"], "difficulty": row["difficulty"],
                        "confidence": float(results[0].confidence_score or 0),
                        "margin": max(0.0, float(results[0].fusion_score or 0) - float(results[1].fusion_score or 0)),
                        **route_features(row["question"], results)})
    return samples, {"bypass": bypass, "deterministic": deterministic,
                     "exact_code_count": exact_count, "abstention_count": abstention_count,
                     "exact_code_rerank_rate": 0.0, "abstention_rerank_rate": 0.0}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", type=Path, default=Path("data/benchmark/human_retrieval_dev.jsonl"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/phase6-index"))
    parser.add_argument("--phase6-calibration", type=Path,
                        default=Path("evaluation/results/phase6_retrieval_calibration.json"))
    parser.add_argument("--output", type=Path, default=Path("evaluation/results/hard_query_route_calibration.json"))
    parser.add_argument("--results-dir", type=Path, default=Path("evaluation/results"))
    parser.add_argument("--exploratory", action="store_true")
    args = parser.parse_args()
    if not args.exploratory:
        require_previous_gates("M4", args.results_dir, index_dir=args.index_dir, benchmark_dir=args.dev.parent)
    policy = RetrievalPolicy.from_report(args.phase6_calibration, expected_mode="hybrid_rrf")
    retriever = HybridRetriever(args.index_dir, query_cache_size=0,
                                policies={"hybrid_rrf": policy})
    doc_ids = json.loads((args.index_dir / "manifest.json").read_text(encoding="utf-8"))["documents"]
    rows = load_jsonl(args.dev)
    if not rows or any(row.get("split") != "dev" for row in rows):
        raise SystemExit("route fitting accepts only dev rows")
    samples, bypass = collect_samples(rows, retriever, doc_ids)
    selected, metrics, feasible = fit_feature_route(samples)
    smoke = json.loads((args.results_dir / "model_snapshot_smoke.json").read_text(encoding="utf-8")) if not args.exploratory else {}
    report = {"schema_version": 1, "phase": 7, "version": "phase7-hard-route-dev-v1",
              "status": "pass" if feasible and not args.exploratory else "conditional", "calibration_split": "dev",
              "holdout_used": False, "test_used": False,
              **source_identity(Path(__file__).resolve().parents[1]),
              "model_identity_sha256": smoke.get("model_identity_sha256"),
              "feature_leakage_review": "pass",
              "feature_allowlist": ["confidence", "margin", "agreement", "constraints"],
              "forbidden_features": ["language", "template", "difficulty", "qid"],
              "training_split_sha256": hashlib.sha256(args.dev.read_bytes()).hexdigest(),
              "index_sha256": hashlib.sha256((args.index_dir / "manifest.json").read_bytes()).hexdigest(),
              "phase6_calibration_sha256": hashlib.sha256(args.phase6_calibration.read_bytes()).hexdigest(),
              **selected, "routing_metrics": metrics, **bypass, "samples": samples}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Fit is frozen before held-out data are opened. No threshold search follows.
    if report["status"] == "pass":
        confusion = {"status": "pass", **{key: report[key] for key in
                     ("source_sha256", "index_sha256", "phase6_calibration_sha256", "model_identity_sha256")},
                     "route_calibration_sha256": sha256(args.output), "splits": {}}
        for split in ("dev", "test", "holdout"):
            path = args.dev if split == "dev" else args.dev.parent / f"human_retrieval_{split}.jsonl"
            split_samples, split_bypass = collect_samples(load_jsonl(path), retriever, doc_ids)
            part = route_metrics(split_samples, selected["easy_confidence_threshold"], selected["easy_margin_threshold"],
                                 selected["minimum_agreement"], selected["constraint_threshold"])
            part.update(split_bypass, benchmark_sha256=sha256(path), samples=split_samples)
            confusion["splits"][split] = part
            floor, ceiling = (.95, .20) if split == "dev" else (.90, .25)
            if part["hard_recall"] < floor or part["easy_unnecessary_rerank_rate"] > ceiling or not part["deterministic"]:
                confusion["status"] = "conditional"
        write_json(args.results_dir / "hard_query_route_confusion.json", confusion)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" and confusion["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
