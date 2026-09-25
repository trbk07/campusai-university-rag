"""Leakage-safe score calibration utilities for retrieval abstention."""

from __future__ import annotations

from dataclasses import dataclass


class CalibrationError(ValueError):
    pass


@dataclass(frozen=True)
class CalibrationResult:
    threshold: float
    recall: float
    false_positive_rate: float
    abstention_rate: float
    calibration_count: int


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
