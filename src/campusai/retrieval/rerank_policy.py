"""Fail-closed activation and score policy for optional Phase 7 reranking."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path

from .cross_encoder_provider import ModelIdentity
from .routing import RoutingTrace


class Phase7PolicyError(ValueError):
    pass


def score_action(top_score: float, margin: float, threshold: float,
                 margin_threshold: float, low_score_action: str = "phase6") -> str:
    """A low evidence score and an ambiguous ranking are distinct decisions.

    Provider faults never reach this function. Only an explicitly calibrated
    policy may abstain on a valid low score; a low rank margin keeps Phase 6.
    """
    if (low_score_action not in ("phase6", "abstain")
            or any(type(value) not in (int, float) or not math.isfinite(value)
                   for value in (top_score, margin, threshold, margin_threshold))
            or margin < 0 or margin_threshold < 0):
        raise Phase7PolicyError("invalid Phase 7 score decision")
    if top_score < threshold:
        return low_score_action
    return "rerank" if margin >= margin_threshold else "phase6"


@dataclass(frozen=True)
class Phase7Policy:
    version: str
    model_identity_sha256: str
    index_sha256: str
    phase6_calibration_sha256: str
    training_split_sha256: str
    threshold: float
    margin_threshold: float
    easy_confidence_threshold: float
    easy_margin_threshold: float
    candidate_cap: int = 40
    artifact_sha256: str = ""
    rerank_candidate_cap: int = 40
    minimum_agreement: float = 0.0
    constraint_threshold: int = 0
    low_score_action: str = "phase6"
    evidence_model: object | None = None
    route_model: object | None = None

    def __post_init__(self) -> None:
        if self.evidence_model is not None:
            from .evidence_policy import EvidenceProbabilityModel
            model = self.evidence_model
            if isinstance(model, dict):
                model = EvidenceProbabilityModel.from_dict(model)
                object.__setattr__(self, "evidence_model", model)
            if not isinstance(model, EvidenceProbabilityModel):
                raise Phase7PolicyError("invalid evidence probability policy")
        if self.route_model is not None:
            from .route_probability import RouteProbabilityModel
            route = self.route_model
            if isinstance(route, dict):
                route = RouteProbabilityModel.from_dict(route)
                object.__setattr__(self, "route_model", route)
            if not isinstance(route, RouteProbabilityModel):
                raise Phase7PolicyError("invalid routing probability policy")
        values = (self.threshold, self.margin_threshold,
                  self.easy_confidence_threshold, self.easy_margin_threshold)
        if (not self.version or any(not math.isfinite(value) for value in values)
                or self.margin_threshold < 0 or not 0 <= self.easy_confidence_threshold <= 1
                or self.easy_margin_threshold < 0 or self.candidate_cap != 40
                or not 1 <= self.rerank_candidate_cap <= self.candidate_cap
                or not 0 <= self.minimum_agreement <= 1 or self.constraint_threshold < 0
                or self.low_score_action not in ("phase6", "abstain")):
            raise Phase7PolicyError("invalid Phase 7 policy values")
        for value in (self.model_identity_sha256, self.index_sha256,
                      self.phase6_calibration_sha256, self.training_split_sha256):
            if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
                raise Phase7PolicyError("missing or invalid Phase 7 policy checksum")

    @property
    def fingerprint(self) -> str:
        return self.artifact_sha256 or hashlib.sha256(json.dumps(
            {key: value for key, value in asdict(self).items() if key != "artifact_sha256"},
            sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    @classmethod
    def from_report(cls, path: str | Path, *, model_identity: ModelIdentity,
                    index_manifest: str | Path, phase6_calibration: str | Path,
                    dev_benchmark: str | Path) -> "Phase7Policy":
        source = Path(path)
        data = json.loads(source.read_text(encoding="utf-8"))
        if (data.get("schema_version") != 1 or data.get("mode") != "hybrid_rerank"
                or data.get("calibration_split") != "dev" or data.get("holdout_used") is not False
                or data.get("status") != "pass"):
            raise Phase7PolicyError("Phase 7 calibration is not a passing dev-only artifact")
        expected = {
            "model_identity_sha256": model_identity.fingerprint,
            "index_sha256": hashlib.sha256(Path(index_manifest).read_bytes()).hexdigest(),
            "phase6_calibration_sha256": hashlib.sha256(Path(phase6_calibration).read_bytes()).hexdigest(),
            "training_split_sha256": hashlib.sha256(Path(dev_benchmark).read_bytes()).hexdigest(),
        }
        if any(data.get(key) != value for key, value in expected.items()):
            raise Phase7PolicyError("Phase 7 calibration provenance mismatch")
        return cls(str(data["version"]), *[expected[key] for key in expected],
                   float(data["threshold"]), float(data["margin_threshold"]),
                   float(data["easy_confidence_threshold"]), float(data["easy_margin_threshold"]),
                   int(data.get("candidate_cap", 40)),
                   hashlib.sha256(source.read_bytes()).hexdigest(),
                   int(data.get("rerank_candidate_cap", 40)),
                   float(data.get("minimum_agreement", 0.0)),
                   int(data.get("constraint_threshold", 0)),
                   data.get("low_score_action", "phase6"), data.get("evidence_model"), data.get("route_model"))

    def score_action(self, top_score: float, margin: float, *, features: dict | None = None) -> str:
        if self.evidence_model is not None:
            if features is None:
                raise Phase7PolicyError("probability policy requires observable features")
            return self.evidence_model.action(features)
        return score_action(top_score, margin, self.threshold, self.margin_threshold,
                            self.low_score_action)

    def route(self, query: str, candidates: list, trace: RoutingTrace) -> tuple[bool, str]:
        if trace.route in {"exact_code", "abstain"} or trace.abstained or not candidates:
            return False, "exact_or_abstained"
        if len(candidates) < 2:
            return False, "single_candidate"
        if self.route_model is not None:
            from .route_probability import route_observations
            return ((True, "hard_probability") if self.route_model.selects(route_observations(query, candidates))
                    else (False, "easy_or_uncertain_probability"))
        features = route_features(query, candidates) if self.minimum_agreement or self.constraint_threshold else {}
        if self.minimum_agreement and features["agreement"] < self.minimum_agreement:
            return True, "hard_retrieval_disagreement"
        if self.constraint_threshold and features["constraints"] >= self.constraint_threshold:
            return True, "hard_multiple_constraints"
        top_confidence = float(candidates[0].confidence_score or 0.0)
        top_margin = max(0.0, float(candidates[0].fusion_score or 0.0)
                         - float(candidates[1].fusion_score or 0.0))
        if top_confidence >= self.easy_confidence_threshold and top_margin >= self.easy_margin_threshold:
            return False, "easy_confident"
        return True, "hard_low_confidence_or_margin"


def route_features(query: str, candidates: list) -> dict[str, float]:
    """Label-free features shared by calibration and serving.

    No language/difficulty/template identifier is used as a routing feature.
    Rank agreement and distinct document coverage describe retrieval itself.
    """
    import re
    head = candidates[:5]
    agreement = sum(set((getattr(item, "retriever_ranks", None) or {})) >= {"bm25", "dense"}
                    for item in head) / max(1, len(head))
    words = query.split()
    # Numbers, comparisons and independent clauses describe query structure,
    # without corpus names, gold labels or difficulty/template identifiers.
    # A year alone is common in easy factual questions; compound requirements
    # and multiple numerical conditions distinguish more demanding requests.
    constraints = len(re.findall(r"\b\d+(?:[.,]\d+)?\b|[\"“][^\"”]+[\"”]|[<>]=?|"
                                 r"\b(?:nếu|if|unless|và|and|hoặc|or|cả|both|mọi|every|nhiều|multiple|cùng|same)\b",
                                 query, flags=re.I))
    total = sum(max(0.0, float(item.fusion_score or 0.0)) for item in head)
    return {"query_length": float(len(words)), "constraints": float(constraints),
            "agreement": agreement, "distinct_documents": float(len({getattr(item, "doc_id", "") for item in head})),
            "concentration": float(head[0].fusion_score or 0.0) / total if head and total else 0.0}
