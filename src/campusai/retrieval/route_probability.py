"""Small observable hard-query router with explicit out-of-domain fallback."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
import re
import unicodedata

FEATURES = ("operation_required", "long_request")
VERSION = "hard-route-logistic-v3"


def route_observations(query: str, candidates: list) -> dict[str, float]:
    """Observable operations shared by calibration and serving.

    A history topic supplies a subject, rather than another requested operation.
    Pool size, corpus names, gold, labels, language and template identities never
    enter these features. Candidate/abstention bypass is handled by Phase7Policy.
    """
    from .routing import detected_course_codes
    if not isinstance(query, str):
        raise ValueError("routing query must be text")
    raw = query.split("\nContext topic (untrusted user input): ", 1)[0]
    text = "".join(c for c in unicodedata.normalize("NFD", raw.casefold())
                   if not unicodedata.combining(c)).replace("đ", "d")
    operations = (
        r"\b(?:if|unless|whether|dieu kien|neu|ma|although|despite|van|con|duoc khong|co duoc|permitted|allowed|eligible|eligibility)\b|\b(?:co|duoc|can|does|is|do)\b.*\b(?:khong|ko|k|not|no|waive|mien)\b",
        r"\b(?:waive\w*|exempt\w*|except\w*|mien|bo qua|chua|pending|later|bo sung|nop sau|submit later|thi ho|duoi|rot|failed?|bay|an 0|bi loai|f|c\+)\b",
        r"\b(?:prerequisites?|tien quyet|hoc truoc|can qua|hoc gi truoc|truoc hay sau|before|after)\b",
        r"\b(?:threshold|cap|maximum|minimum|limit|ceiling|floor|nguong|tran|toi da|toi thieu|muc nao|cach tinh|cong don)\b",
        r"\b(?:compare|comparison|difference|versus|vs|so sanh|khac nhau|khac biet|doi chieu|khac)\b",
    )
    # "How much" asks for a quantity; it does not request multiple operations.
    cardinality_text = re.sub(r"\bbao nhieu\b", "", text)
    # An abbreviation joined by a slash is a name, rather than two requested
    # outputs. Detect this spelling before case folding; explicit course-code
    # pairs remain multiple lookups below.
    joined_names = re.findall(r"\b[A-Z][A-Z0-9-]+/[A-Z][A-Z0-9-]+\b", raw)
    for name in joined_names:
        cardinality_text = cardinality_text.replace(name.casefold(), name.casefold().replace("/", " "))
    # "Find X and report its credits" describes one lookup. Keep the
    # conjunction when the first clause already requests a field, so
    # "find its semester and report its credits" still requests two outputs.
    fields = r"\b(?:credits?|semester|term|tin chi|hoc ky|hoc ki)\b"
    def lookup_sequence(match):
        return match.group(0) if re.search(fields, match.group("subject")) else match.group(0).rsplit("and", 1)[0]
    cardinality_text = re.sub(
        r"\b(?:find|locate|search|look up)\b(?P<subject>.*?)\band\s+(?=(?:report|state|give|provide|return|tell)\b)",
        lookup_sequence, cardinality_text)
    multiple = re.search(r"\b(?:and|both|all|two|multiple|va|voi|hai|ca|nhieu|vua|roi|xong|cung|moi)\b|[+/;]", cardinality_text)
    multiple_fields = bool(re.search(r"\b(?:credits?|tin chi)\b", cardinality_text)
                           and re.search(r"\b(?:semester|term|hoc ky|hoc ki)\b", cardinality_text))
    # A single identifier's basic fields can be read in one lookup. Operations
    # such as comparison, conditions or prerequisites still require ranking.
    code_count = len(detected_course_codes(raw))
    required = any(re.search(pattern, text) for pattern in operations) or code_count > 1 or (
        bool(multiple or multiple_fields) and code_count != 1)
    return {"operation_required": float(required), "long_request": float(len(raw.split()) >= 40)}


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
