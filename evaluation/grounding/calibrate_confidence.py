"""Fit Phase 5 confidence calibration on dev and evaluate held-out splits."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from campusai.rag.calibration import IsotonicCalibrator, calibration_payload_sha256
from campusai.rag.confidence import calibration_metrics


LABEL_SCORES = {"low": 0.25, "medium": 0.60, "high": 0.90}


def _score(row: dict) -> float:
    # Abstention is a verified negative outcome for confidence calibration;
    # mapping a missing runtime score to the cosmetic label ``low`` (0.25)
    # would systematically penalize safe abstentions.
    if row.get("abstained"):
        return 0.0
    value = row.get("confidence_score")
    return float(value if value is not None else LABEL_SCORES.get(row.get("confidence"), 0.0))


def _label(row: dict) -> bool:
    return bool(row.get("answerable", True)) and not bool(row.get("abstained"))


def _validate_calibration_population(rows: list[dict]) -> dict:
    """Reject degenerate or leakage-prone calibration populations."""
    splits = {row.get("split") for row in rows}
    if not {"dev", "test", "holdout"}.issubset(splits):
        raise ValueError("calibration requires dev, test and holdout splits")
    summary = {}
    for split in ("dev", "test", "holdout"):
        subset = [row for row in rows if row.get("split") == split]
        labels = {_label(row) for row in subset}
        if labels != {False, True}:
            raise ValueError(f"calibration {split} split must contain positive and negative labels")
        summary[split] = {"count": len(subset), "positive": sum(labels for labels in (_label(row) for row in subset)),
                          "negative": sum(not _label(row) for row in subset)}
    for field in ("source_group", "template_group", "semantic_topic", "adversarial_pattern"):
        groups = {}
        for row in rows:
            value = str(row.get(field, "")).strip()
            if value:
                groups.setdefault(value, set()).add(row.get("split"))
        if any(len(split_values) > 1 for split_values in groups.values()):
            raise ValueError(f"calibration leakage across {field}")
    return summary


def evaluate_calibrator(rows: list[dict], calibrator: IsotonicCalibrator) -> dict:
    """Evaluate a locked calibrator without refitting on held-out rows."""
    metrics = {}
    for split in ("dev", "test", "holdout"):
        subset = [row for row in rows if row.get("split") == split]
        if not subset:
            metrics[split] = {"count": 0, "brier_score": 1.0, "ece": 1.0}
            continue
        scores = [calibrator.predict(_score(row)) for row in subset]
        metrics[split] = calibration_metrics(scores, [_label(row) for row in subset])
    return metrics


def risk_at_coverage(rows: list[dict], calibrator: IsotonicCalibrator, coverage: float,
                     *, split: str = "holdout") -> float:
    """Return selective error on one untouched split.

    Risk must be measured on the final holdout, not by pooling dev/test rows
    into it. Coverage is measured over publishable (non-abstained) answers;
    abstentions are safety refusals, not low-confidence published answers.
    Stable ID ordering makes tied isotonic scores reproducible.
    """
    if not 0 < coverage <= 1:
        raise ValueError("coverage must be between 0 and 1")
    subset = [row for row in rows if row.get("split") == split]
    if not subset:
        raise ValueError(f"risk split is empty: {split}")
    publishable = [row for row in subset if not row.get("abstained")]
    scored = sorted(
        ((calibrator.predict(_score(row)), _label(row), str(row.get("id", ""))) for row in publishable),
        key=lambda item: (-item[0], item[2]),
    )
    if not scored:
        return 0.0
    selected_count = max(1, math.ceil(len(scored) * coverage))
    selected = scored[:selected_count]
    return round(sum(not label for _score_value, label, _row_id in selected) / len(selected), 6)


def fit_report(report: dict) -> dict:
    rows = report.get("rows", [])
    population = _validate_calibration_population(rows) if {"dev", "test", "holdout"}.issubset({row.get("split") for row in rows}) else None
    dev = [row for row in rows if row.get("split") == "dev"]
    if not dev:
        raise ValueError("calibration requires a non-empty dev split")
    calibrator = IsotonicCalibrator.fit([_score(row) for row in dev], [_label(row) for row in dev])
    metrics = evaluate_calibrator(rows, calibrator)
    artifact = calibrator.to_dict()
    return {"version": calibrator.version, "artifact": artifact,
            "artifact_sha256": calibration_payload_sha256(artifact), "metrics": metrics,
            "fit_split": "dev", "benchmark_sha256": report.get("benchmark_sha256"),
            "population": population}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path, default=Path("evaluation/results/grounding_calibration.json"))
    args = parser.parse_args()
    result = fit_report(json.loads(args.report.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
