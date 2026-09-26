"""Recomputed confidence scoring and calibration metrics."""

from __future__ import annotations

from dataclasses import dataclass
import math

from .calibration import IsotonicCalibrator


POLICY_VERSION = "phase5-v1"


@dataclass(frozen=True)
class Confidence:
    label: str
    score: float
    method: str = "calibrated_v1"
    policy_version: str = POLICY_VERSION


def score_confidence(*, retrieval_support: float, claim_entailment: float, citation_completeness: float,
                     evidence_agreement: float = 1.0, answer_consistency: float = 1.0,
                     contradiction_penalty: float = 0.0, ambiguity_penalty: float = 0.0,
                     calibrator: IsotonicCalibrator | None = None) -> Confidence:
    score = (0.30 * retrieval_support + 0.35 * claim_entailment + 0.15 * citation_completeness
             + 0.10 * evidence_agreement + 0.10 * answer_consistency
             - contradiction_penalty - ambiguity_penalty)
    score = max(0.0, min(1.0, score))
    if calibrator is not None:
        score = calibrator.predict(score)
    label = "high" if score >= 0.85 else "medium" if score >= 0.65 else "low"
    return Confidence(label, round(score, 6), "isotonic_v1" if calibrator else "heuristic_v1",
                      calibrator.version if calibrator else POLICY_VERSION)


def calibration_metrics(scores: list[float], labels: list[bool], bins: int = 10) -> dict[str, float]:
    if len(scores) != len(labels) or not scores:
        raise ValueError("scores and labels must be non-empty and equal length")
    brier = sum((float(score) - int(label)) ** 2 for score, label in zip(scores, labels)) / len(scores)
    ece = 0.0
    for index in range(bins):
        lower, upper = index / bins, (index + 1) / bins
        selected = [(score, label) for score, label in zip(scores, labels) if lower <= score < upper or (index == bins - 1 and score <= upper)]
        if selected:
            ece += len(selected) / len(scores) * abs(sum(score for score, _ in selected) / len(selected) - sum(label for _, label in selected) / len(selected))
    return {"brier_score": round(brier, 6), "ece": round(ece, 6), "count": len(scores)}
