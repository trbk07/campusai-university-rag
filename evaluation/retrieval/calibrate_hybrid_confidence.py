"""Fit the Phase 6 hybrid confidence threshold on dev only."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from campusai.retrieval.hybrid import HybridRetriever
from campusai.retrieval.confidence import FEATURES, RetrievalConfidenceModel
from sklearn.linear_model import LogisticRegression
import sklearn
from evaluation.common.metrics import recall_at_k
from evaluation.common.metrics import _is_relevant
from evaluation.benchmarks.retrieval_schema import load_jsonl


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=Path("data/benchmark/hybrid_retrieval_dev.jsonl"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/hybrid-index"))
    parser.add_argument("--output", type=Path, default=Path("evaluation/results/hybrid_retrieval_calibration.json"))
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
        evaluated.append((row, results, retriever.last_trace))
    answerable = [(row, values, trace) for row, values, trace in evaluated if row.get("answerable")]
    negative = [(row, values, trace) for row, values, trace in evaluated if not row.get("answerable")]
    feature_rows = []
    feature_labels = []
    for row, values, _trace in evaluated:
        for item in values:
            feature_rows.append([item.confidence_features[name] for name in FEATURES])
            feature_labels.append(int(_is_relevant(item, row.get("gold_evidence", []))))
    if len(set(feature_labels)) != 2:
        raise SystemExit("dev calibration requires relevant and irrelevant candidate examples")
    fitted = LogisticRegression(class_weight="balanced", solver="liblinear", C=1.0,
                                random_state=0, max_iter=1000).fit(feature_rows, feature_labels)
    confidence_model = RetrievalConfidenceModel(
        version="phase6-logistic-v1", kind="logistic",
        coefficients={name: float(value) for name, value in zip(FEATURES, fitted.coef_[0])},
        intercept=float(fitted.intercept_[0]),
    )
    def confidence(values, trace):
        if trace.exact_match and trace.route == "exact_code":
            return 1.0
        return max((confidence_model.predict(item.confidence_features) for item in values), default=0.0)
    scored = [(row, values, confidence(values, trace)) for row, values, trace in evaluated]
    answerable = [(row, values, score) for row, values, score in scored if row.get("answerable")]
    negative = [(row, values, score) for row, values, score in scored if not row.get("answerable")]
    baseline = sum(recall_at_k(values, row["gold_evidence"], 5) for row, values, _score in answerable) / len(answerable)
    candidates = sorted({0.0, 1.0, *(score for _row, _values, score in scored)})
    trials = []
    for threshold in candidates:
        def accepted(values, score):
            return values if values and score >= threshold else []
        positive_recall = sum(recall_at_k(accepted(values, score), row["gold_evidence"], 5)
                              for row, values, score in answerable) / len(answerable)
        fpr = sum(bool(accepted(values, score)) for _row, values, score in negative) / len(negative)
        trials.append({"threshold": threshold, "answerable_recall_at_5": positive_recall,
                       "false_positive_rate": fpr,
                       "recall_drop": baseline - positive_recall})
    valid = [trial for trial in trials if trial["false_positive_rate"] <= args.max_fpr
             and trial["recall_drop"] <= args.max_recall_drop]
    selected = min(valid, key=lambda item: (item["threshold"], -item["answerable_recall_at_5"])) if valid else None
    manifest_path = args.index_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = {
        "schema_version": 2, "phase": 6, "mode": "hybrid_rrf",
        "confidence_model": confidence_model.to_dict(),
        "confidence_model_sha256": confidence_model.fingerprint,
        "feature_schema": list(FEATURES), "training_split_sha256": _sha(args.benchmark),
        "training_candidates": len(feature_rows), "training_positive_candidates": sum(feature_labels),
        "sklearn_version": sklearn.__version__,
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
