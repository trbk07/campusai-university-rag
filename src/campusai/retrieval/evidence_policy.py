"""Observable, versioned evidence sufficiency probabilities for Phase 7.

Gold evidence is a training target only. This module has no benchmark access;
uncertainty and out-of-domain inputs preserve the Phase 6 result.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import re
import unicodedata

from .rerank_policy import route_features

FEATURES = ("top_logit", "score_margin", "score_std", "top_lexical_overlap",
            "top_confidence", "retriever_agreement", "query_length", "constraints",
            "candidate_count", "distinct_documents", "table_fraction", "top_original_rank")
CLASSES = ("no_evidence", "partial_evidence", "sufficient_evidence")
VERSION = "evidence-softmax-v1"


def _tokens(text: str) -> set[str]:
    text = unicodedata.normalize("NFC", text).casefold()
    return set(re.findall(r"\w+", text))


def _get(item, key, default=None):
    return item.get(key, default) if isinstance(item, dict) else getattr(item, key, default)


def evidence_features(query: str, baseline: list, ranked: list, scores: list[float]) -> dict[str, float]:
    """Extract identical features in offline fitting and serving, before top-k."""
    if not ranked or len(ranked) != len(scores) or any(type(s) not in (int, float) or not math.isfinite(s) for s in scores):
        raise ValueError("invalid evidence scoring observations")
    if any(a < b for a, b in zip(scores, scores[1:])):
        raise ValueError("evidence scores must be ranked")
    query_words = _tokens(query)
    top = ranked[0]
    mean = sum(scores) / len(scores)
    # route_features accepts objects; agreement is reproduced for dict replay.
    agreement = sum(set(_get(item, "retriever_ranks", {}) or {}) >= {"bm25", "dense"}
                    for item in baseline[:5]) / max(1, len(baseline[:5]))
    values = (scores[0], scores[0] - scores[1] if len(scores) > 1 else 0.0,
              math.sqrt(sum((score - mean) ** 2 for score in scores) / len(scores)),
              len(query_words & _tokens(_get(top, "content", ""))) / max(1, len(query_words)),
              float(_get(top, "confidence_score", 0.0) or 0.0), agreement,
              float(len(query.split())), route_features(query, []) ["constraints"],
              float(len(ranked)), float(len({_get(item, "doc_id") for item in ranked})),
              sum(bool((_get(item, "metadata", {}) or {}).get("table_id")) or _get(item, "chunk_type") == "table"
                  for item in ranked) / len(ranked), float(_get(top, "rank", 0) or 0))
    result = dict(zip(FEATURES, values))
    validate_features(result)
    return result


def validate_features(features: dict) -> None:
    if set(features) != set(FEATURES) or any(type(v) not in (int, float) or not math.isfinite(v) for v in features.values()):
        raise ValueError("invalid evidence feature schema")


@dataclass(frozen=True)
class EvidenceProbabilityModel:
    version: str
    feature_schema: tuple[str, ...]
    classes: tuple[str, ...]
    means: tuple[float, ...]
    scales: tuple[float, ...]
    weights: tuple[tuple[float, ...], ...]
    biases: tuple[float, ...]
    accept_probability: float = 0.9
    abstain_probability: float = 0.95
    max_standardized_distance: float = 8.0

    def __post_init__(self):
        n = len(FEATURES)
        if (self.version != VERSION or tuple(self.feature_schema) != FEATURES or tuple(self.classes) != CLASSES
                or len(self.means) != n or len(self.scales) != n or len(self.weights) != 3 or len(self.biases) != 3
                or any(len(w) != n for w in self.weights)
                or any(type(v) not in (int, float) or not math.isfinite(v)
                       for v in (*self.means, *self.scales, *self.biases, *(v for w in self.weights for v in w),
                                 self.accept_probability, self.abstain_probability, self.max_standardized_distance))
                or any(s < 1e-6 for s in self.scales)
                or not .5 < self.accept_probability < 1 or not .5 < self.abstain_probability < 1
                or not 1 <= self.max_standardized_distance <= 8):
            raise ValueError("invalid evidence probability model")

    @classmethod
    def from_dict(cls, data: dict):
        if not isinstance(data, dict) or set(data) != set(cls.__dataclass_fields__):
            raise ValueError("invalid evidence probability artifact")
        data = dict(data)
        for field in ("feature_schema", "classes", "means", "scales", "biases"):
            data[field] = tuple(data[field])
        data["weights"] = tuple(tuple(row) for row in data["weights"])
        return cls(**data)

    def to_dict(self):
        # JSON-compatible and deterministic across a save/reload round trip.
        import json
        return json.loads(json.dumps(asdict(self)))

    def probabilities(self, features: dict) -> dict[str, float] | None:
        validate_features(features)
        z = [(features[key] - mean) / scale for key, mean, scale in zip(FEATURES, self.means, self.scales)]
        if any(abs(value) > self.max_standardized_distance for value in z):
            return None
        logits = [bias + sum(w * value for w, value in zip(weights, z))
                  for bias, weights in zip(self.biases, self.weights)]
        maximum = max(logits)
        exp = [math.exp(value - maximum) for value in logits]
        return dict(zip(CLASSES, (value / sum(exp) for value in exp)))

    def action(self, features: dict) -> str:
        probabilities = self.probabilities(features)
        if probabilities is None:
            return "phase6"
        if probabilities["sufficient_evidence"] >= self.accept_probability:
            return "rerank"
        if probabilities["no_evidence"] >= self.abstain_probability:
            return "abstain"
        return "phase6"
