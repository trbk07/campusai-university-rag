"""Small observable hard-query router with explicit out-of-domain fallback."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math

FEATURES = ("confidence", "margin", "agreement", "constraints", "query_length",
            "distinct_documents", "concentration")
VERSION = "hard-route-logistic-v1"


def route_observations(query: str, candidates: list) -> dict[str, float]:
    from .rerank_policy import route_features
    values = route_features(query, candidates)
    head = candidates[:2]
    values["confidence"] = float(head[0].confidence_score or 0.0) if head else 0.0
    values["margin"] = max(0.0, float(head[0].fusion_score or 0.0)
                           - float(head[1].fusion_score or 0.0)) if len(head) == 2 else 0.0
    return validate_observations(values)


def validate_observations(values: dict) -> dict[str, float]:
    if not isinstance(values, dict) or any(key not in values or type(values[key]) not in (int, float)
            or not math.isfinite(values[key]) for key in FEATURES):
        raise ValueError("invalid observable routing features")
    return {key: float(values[key]) for key in FEATURES}


@dataclass(frozen=True)
class RouteProbabilityModel:
    version: str
    feature_schema: tuple[str, ...]
    means: tuple[float, ...]
    scales: tuple[float, ...]
    weights: tuple[float, ...]
    bias: float
    threshold: float = .5
    max_standardized_distance: float = 8.0

    def __post_init__(self):
        n = len(FEATURES)
        if (self.version != VERSION or tuple(self.feature_schema) != FEATURES
                or any(len(values) != n for values in (self.means, self.scales, self.weights))
                or any(type(value) not in (int, float) or not math.isfinite(value)
                       for value in (*self.means, *self.scales, *self.weights,
                                     self.bias, self.threshold, self.max_standardized_distance))
                or any(value < 1e-6 for value in self.scales)
                or not 0 < self.threshold <= 1 or not 1 <= self.max_standardized_distance <= 8):
            raise ValueError("invalid route probability model")

    @classmethod
    def from_dict(cls, data: dict):
        if not isinstance(data, dict) or set(data) != set(cls.__dataclass_fields__):
            raise ValueError("invalid route model artifact")
        data = dict(data)
        for name in ("feature_schema", "means", "scales", "weights"):
            data[name] = tuple(data[name])
        return cls(**data)

    def to_dict(self):
        return json.loads(json.dumps(asdict(self)))

    def probability(self, observations: dict) -> float | None:
        values = validate_observations(observations)
        standardized = [(values[key] - mean) / scale for key, mean, scale
                        in zip(FEATURES, self.means, self.scales)]
        if any(abs(value) > self.max_standardized_distance for value in standardized):
            return None
        logit = self.bias + sum(weight * value for weight, value in zip(self.weights, standardized))
        return 1 / (1 + math.exp(-max(-40.0, min(40.0, logit))))

    def selects(self, observations: dict) -> bool:
        probability = self.probability(observations)
        return probability is not None and probability >= self.threshold
