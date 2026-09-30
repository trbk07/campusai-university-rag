"""Versioned, interpretable retrieval acceptance confidence."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math


FEATURES = (
    "lexical_overlap", "dense_cosine", "agreement", "bm25_reciprocal_rank",
    "dense_reciprocal_rank", "fusion_margin", "query_length", "exact_code", "filter_match",
)


@dataclass(frozen=True)
class RetrievalConfidenceModel:
    version: str
    kind: str
    coefficients: dict[str, float]
    intercept: float = 0.0

    def __post_init__(self) -> None:
        if self.kind not in {"linear", "logistic"}:
            raise ValueError("unsupported confidence model kind")
        if set(self.coefficients) != set(FEATURES):
            raise ValueError("confidence feature schema mismatch")
        if not self.version or not all(math.isfinite(value) for value in (*self.coefficients.values(), self.intercept)):
            raise ValueError("invalid confidence model parameters")

    def predict(self, features: dict[str, float]) -> float:
        if set(features) != set(FEATURES):
            raise ValueError("confidence feature schema mismatch")
        value = self.intercept + sum(self.coefficients[name] * float(features[name]) for name in FEATURES)
        if self.kind == "logistic":
            value = 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, value))))
        return round(max(0.0, min(1.0, value)), 6)

    def to_dict(self) -> dict:
        return {"version": self.version, "kind": self.kind, "feature_schema": list(FEATURES),
                "coefficients": dict(self.coefficients), "intercept": self.intercept}

    @classmethod
    def from_dict(cls, payload: dict) -> "RetrievalConfidenceModel":
        if payload.get("feature_schema") != list(FEATURES):
            raise ValueError("confidence feature schema mismatch")
        return cls(str(payload["version"]), str(payload["kind"]),
                   {name: float(value) for name, value in payload["coefficients"].items()},
                   float(payload.get("intercept", 0.0)))

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


# Historic score is retained only for old calibration artifacts and Phase 3
# diagnostics. New Phase 6 release reports must serialize a fitted logistic
# model and the validator rejects this compatibility version.
LEGACY_CONFIDENCE_MODEL = RetrievalConfidenceModel(
    "legacy-linear-v1", "linear",
    {"lexical_overlap": .55, "dense_cosine": .35, "agreement": .10,
     "bm25_reciprocal_rank": 0.0, "dense_reciprocal_rank": 0.0,
     "fusion_margin": 0.0, "query_length": 0.0, "exact_code": 0.0,
     "filter_match": 0.0},
)
