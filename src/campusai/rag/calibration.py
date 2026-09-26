"""Small dependency-free isotonic calibrator for Phase 5 confidence scores."""

from __future__ import annotations

from dataclasses import dataclass


CALIBRATION_VERSION = "phase5-isotonic-v1"


@dataclass(frozen=True)
class IsotonicCalibrator:
    thresholds: tuple[float, ...]
    values: tuple[float, ...]
    version: str = CALIBRATION_VERSION

    @classmethod
    def fit(cls, scores: list[float], labels: list[bool]) -> "IsotonicCalibrator":
        if len(scores) != len(labels) or not scores:
            raise ValueError("scores and labels must be non-empty and equal length")
        ordered = sorted((max(0.0, min(1.0, float(score))), int(label)) for score, label in zip(scores, labels))
        blocks: list[list[float | int]] = []
        for score, label in ordered:
            blocks.append([score, score, 1, label])
            while len(blocks) >= 2 and blocks[-2][3] / blocks[-2][2] > blocks[-1][3] / blocks[-1][2]:
                right = blocks.pop()
                left = blocks.pop()
                blocks.append([left[0], right[1], left[2] + right[2], left[3] + right[3]])
        return cls(
            tuple(float(block[1]) for block in blocks),
            tuple(round(float(block[3]) / float(block[2]), 8) for block in blocks),
        )

    def predict(self, score: float) -> float:
        value = max(0.0, min(1.0, float(score)))
        for threshold, calibrated in zip(self.thresholds, self.values):
            if value <= threshold:
                return calibrated
        return self.values[-1]

    def to_dict(self) -> dict:
        return {"version": self.version, "thresholds": list(self.thresholds), "values": list(self.values)}

    @classmethod
    def from_dict(cls, payload: dict) -> "IsotonicCalibrator":
        if payload.get("version") != CALIBRATION_VERSION:
            raise ValueError("unsupported calibration artifact version")
        thresholds = tuple(float(value) for value in payload["thresholds"])
        values = tuple(float(value) for value in payload["values"])
        if not thresholds or len(thresholds) != len(values):
            raise ValueError("invalid calibration artifact")
        return cls(thresholds, values)
