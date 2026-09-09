"""Metrics-only evaluator for anonymized ingestion ground truth fixtures."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any


def _prf(expected: set[str], actual: set[str]) -> dict[str, float]:
    true_positive = len(expected & actual)
    precision = true_positive / len(actual) if actual else 1.0
    recall = true_positive / len(expected) if expected else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}


def evaluate_case(case: dict[str, Any], parsed: dict[str, Any]) -> dict[str, Any]:
    expected = case.get("expected", {})
    actual = parsed.get("actual", {})
    headers = _prf(set(expected.get("headers", [])), set(actual.get("headers", [])))
    numeric = _prf(set(expected.get("numeric_cells", [])), set(actual.get("numeric_cells", [])))
    dimensions = {"expected": expected.get("dimensions"), "actual": actual.get("dimensions"),
                  "exact": expected.get("dimensions") == actual.get("dimensions")}
    return {"case": case.get("id"), "headers": headers, "numeric_cells": numeric,
            "dimensions": dimensions}


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = [result[metric] for result in results for metric in ("headers", "numeric_cells")]
    return {"cases": len(results), "mean_f1": round(sum(item["f1"] for item in metrics) / len(metrics), 4) if metrics else 0.0,
            "dimension_accuracy": round(sum(item["dimensions"]["exact"] for item in results) / len(results), 4) if results else 0.0}


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    annotations = json.loads(args.annotations.read_text(encoding="utf-8"))
    predictions = json.loads(args.predictions.read_text(encoding="utf-8"))
    by_id = {item["case"]: item for item in predictions.get("predictions", predictions)}
    results = [evaluate_case(case, by_id.get(case["id"], {"actual": {}})) for case in annotations["cases"]]
    report = {"schema_version": 1, "results": results, "summary": aggregate(results)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"]))


if __name__ == "__main__":
    main()
