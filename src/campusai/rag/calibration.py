"""Small dependency-free isotonic calibrator for Phase 5 confidence scores."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path


CALIBRATION_VERSION = "grounding-isotonic-v1"


def calibration_payload_sha256(payload: dict) -> str:
    """Return the stable digest used to pin a calibration artifact."""
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_calibration_artifact(path: str | Path, *, expected_sha256: str | None = None) -> tuple["IsotonicCalibrator", str]:
    """Load and verify a persisted Phase 5 calibrator fail-closed."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    artifact = payload.get("artifact", payload)
    actual = calibration_payload_sha256(artifact)
    declared = payload.get("artifact_sha256")
    if declared and declared != actual:
        raise ValueError("calibration artifact checksum mismatch")
    if expected_sha256 and expected_sha256 != actual:
        raise ValueError("calibration artifact checksum mismatch")
    return IsotonicCalibrator.from_dict(artifact), actual


@dataclass(frozen=True)
class IsotonicCalibrator:
    thresholds: tuple[float, ...]
    values: tuple[float, ...]
    version: str = CALIBRATION_VERSION

    @classmethod
    def fit(cls, scores: list[float], labels: list[bool]) -> "IsotonicCalibrator":
        if len(scores) != len(labels) or not scores:
            raise ValueError("scores and labels must be non-empty and equal length")
        cleaned = []
        for score, label in zip(scores, labels):
            value = float(score)
            if not math.isfinite(value):
                raise ValueError("calibration scores must be finite")
            cleaned.append((max(0.0, min(1.0, value)), int(bool(label))))
        ordered = sorted(cleaned)
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
        value = float(score)
        if not math.isfinite(value):
            raise ValueError("calibration score must be finite")
        value = max(0.0, min(1.0, value))
        for threshold, calibrated in zip(self.thresholds, self.values):
            if value <= threshold:
                return calibrated
        return self.values[-1]

    def to_dict(self) -> dict:
        return {"version": self.version, "thresholds": list(self.thresholds), "values": list(self.values)}

    @classmethod
    def from_dict(cls, payload: dict) -> "IsotonicCalibrator":
        if not isinstance(payload, dict) or payload.get("version") != CALIBRATION_VERSION:
            raise ValueError("unsupported calibration artifact version")
        try:
            thresholds = tuple(float(value) for value in payload["thresholds"])
            values = tuple(float(value) for value in payload["values"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("invalid calibration artifact") from None
        if not thresholds or len(thresholds) != len(values):
            raise ValueError("invalid calibration artifact")
        if (any(not math.isfinite(value) or not 0 <= value <= 1 for value in thresholds)
                or any(not math.isfinite(value) or not 0 <= value <= 1 for value in values)
                or tuple(sorted(thresholds)) != thresholds
                or tuple(sorted(values)) != values):
            raise ValueError("invalid calibration artifact")
        return cls(thresholds, values)
