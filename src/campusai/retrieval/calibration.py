"""Leakage-safe score calibration utilities for retrieval abstention."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


class CalibrationError(ValueError):
    pass


@dataclass(frozen=True)
class CalibrationResult:
    threshold: float
    recall: float
    false_positive_rate: float
    abstention_rate: float
    calibration_count: int


@dataclass(frozen=True)
class RetrievalPolicy:
    """Leakage-safe retrieval acceptance policy.

    A policy is deliberately explicit about the retrieval mode it belongs to.
    RRF scores and cross-encoder scores are not interchangeable, so one global
    threshold is unsafe.  Keeping the policy as a small serialisable object
    also makes the value auditable in production logs and release artifacts.
    """

    mode: str
    threshold: float
    min_recall: float = 0.85
    max_false_positive_rate: float = 0.05
    source: str = "calibration"

    def __post_init__(self) -> None:
        if self.mode not in {"bm25", "dense", "hybrid", "rerank", "hybrid_rerank"}:
            raise CalibrationError(f"unsupported retrieval mode: {self.mode}")
        if self.threshold < 0:
            raise CalibrationError("threshold must be non-negative")

    def accepts(self, score: float) -> bool:
        return float(score) >= self.threshold

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "threshold": self.threshold,
            "min_recall": self.min_recall,
            "max_false_positive_rate": self.max_false_positive_rate,
            "source": self.source,
        }

    @classmethod
    def from_report(cls, path: str | Path, *, expected_mode: str | None = None) -> "RetrievalPolicy":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        mode = data.get("mode")
        result = data.get("result", {})
        if expected_mode is not None and mode != expected_mode:
            raise CalibrationError(f"calibration mode mismatch: expected {expected_mode}, got {mode}")
        if not isinstance(mode, str) or not isinstance(result.get("threshold"), (int, float)):
            raise CalibrationError("calibration report is missing mode or threshold")
        constraints = data.get("constraints", {})
        return cls(mode, float(result["threshold"]), float(constraints.get("min_recall", 0.85)),
                   float(constraints.get("max_false_positive_rate", 0.05)), str(path))


def select_threshold(
    scores: list[float],
    relevant: list[bool],
    *,
    min_recall: float = 0.85,
    max_false_positive_rate: float = 0.05,
) -> CalibrationResult:
    """Select the highest safe threshold using calibration data only.

    ``scores`` contains one confidence score per calibration query and
    ``relevant`` says whether that query had a valid positive result. Negative
    queries must therefore be represented as ``False``. Test data is never
    consulted by this function.
    """
    if len(scores) != len(relevant) or not scores:
        raise CalibrationError("scores and labels must be non-empty and equal length")
    if not 0 <= min_recall <= 1 or not 0 <= max_false_positive_rate <= 1:
        raise CalibrationError("calibration constraints must be between 0 and 1")
    positives = sum(relevant)
    negatives = len(relevant) - positives
    if not positives or not negatives:
        raise CalibrationError("calibration split needs both positive and negative queries")
    candidates = sorted(set([0.0, *scores]), reverse=True)
    valid: list[CalibrationResult] = []
    for threshold in candidates:
        accepted = [score >= threshold for score in scores]
        true_positive = sum(ok and label for ok, label in zip(accepted, relevant))
        false_positive = sum(ok and not label for ok, label in zip(accepted, relevant))
        recall = true_positive / positives
        fpr = false_positive / negatives
        abstention = sum(not ok for ok in accepted) / len(accepted)
        if recall >= min_recall and fpr <= max_false_positive_rate:
            valid.append(CalibrationResult(round(threshold, 8), recall, fpr, abstention, len(scores)))
    if not valid:
        raise CalibrationError("no threshold satisfies recall/FPR constraints")
    return max(valid, key=lambda result: (result.threshold, result.recall, -result.false_positive_rate))
