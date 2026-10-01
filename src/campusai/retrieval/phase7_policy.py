"""Fail-closed activation and score policy for optional Phase 7 reranking."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path

from .phase7_reranker import ModelIdentity
from .routing import RoutingTrace


class Phase7PolicyError(ValueError):
    pass


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

    def __post_init__(self) -> None:
        values = (self.threshold, self.margin_threshold,
                  self.easy_confidence_threshold, self.easy_margin_threshold)
        if (not self.version or any(not math.isfinite(value) for value in values)
                or self.margin_threshold < 0 or not 0 <= self.easy_confidence_threshold <= 1
                or self.easy_margin_threshold < 0 or self.candidate_cap != 40
                or not 1 <= self.rerank_candidate_cap <= self.candidate_cap):
            raise Phase7PolicyError("invalid Phase 7 policy values")
        for value in (self.model_identity_sha256, self.index_sha256,
                      self.phase6_calibration_sha256, self.training_split_sha256):
            if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
                raise Phase7PolicyError("missing or invalid Phase 7 policy checksum")

    @property
    def fingerprint(self) -> str:
        return self.artifact_sha256 or hashlib.sha256(json.dumps(
            {key: value for key, value in self.__dict__.items() if key != "artifact_sha256"},
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
                   int(data.get("rerank_candidate_cap", 40)))

    def route(self, query: str, candidates: list, trace: RoutingTrace) -> tuple[bool, str]:
        if trace.route in {"exact_code", "abstain"} or trace.abstained or not candidates:
            return False, "exact_or_abstained"
        if len(candidates) < 2:
            return False, "single_candidate"
        top_confidence = float(candidates[0].confidence_score or 0.0)
        top_margin = max(0.0, float(candidates[0].fusion_score or 0.0)
                         - float(candidates[1].fusion_score or 0.0))
        if top_confidence >= self.easy_confidence_threshold and top_margin >= self.easy_margin_threshold:
            return False, "easy_confident"
        return True, "hard_low_confidence_or_margin"
