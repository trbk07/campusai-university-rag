"""Fit Phase 5 confidence calibration on dev and evaluate held-out splits."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from campusai.rag.calibration import IsotonicCalibrator
from campusai.rag.confidence import calibration_metrics


LABEL_SCORES = {"low": 0.25, "medium": 0.60, "high": 0.90}


def _score(row: dict) -> float:
    value = row.get("confidence_score")
    return float(value if value is not None else LABEL_SCORES.get(row.get("confidence"), 0.0))


def _label(row: dict) -> bool:
    return bool(row.get("answerable", True)) and not bool(row.get("abstained"))


def fit_report(report: dict) -> dict:
    rows = report.get("rows", [])
    dev = [row for row in rows if row.get("split") == "dev"]
    if not dev:
        raise ValueError("calibration requires a non-empty dev split")
    calibrator = IsotonicCalibrator.fit([_score(row) for row in dev], [_label(row) for row in dev])
    metrics = {}
    for split in ("dev", "test", "holdout"):
        subset = [row for row in rows if row.get("split") == split]
        if not subset:
            metrics[split] = {"count": 0, "brier_score": 1.0, "ece": 1.0}
            continue
        scores = [calibrator.predict(_score(row)) for row in subset]
        metrics[split] = calibration_metrics(scores, [_label(row) for row in subset])
    return {"version": calibrator.version, "artifact": calibrator.to_dict(), "metrics": metrics}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path, default=Path("evaluation/results/phase5_calibration.json"))
    args = parser.parse_args()
    result = fit_report(json.loads(args.report.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
