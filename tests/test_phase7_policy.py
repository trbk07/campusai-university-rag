import hashlib
import json

import pytest

from campusai.retrieval.phase7_policy import Phase7Policy, Phase7PolicyError
from campusai.retrieval.phase7_reranker import ModelIdentity
from campusai.retrieval.routing import RoutingTrace


def _hash(value):
    return hashlib.sha256(value).hexdigest()


def test_phase7_policy_is_bound_to_dev_model_index_and_phase6_calibration(tmp_path):
    identity = ModelIdentity("BAAI/bge-reranker-v2-m3", "rev", "a" * 64, "rev")
    paths = [tmp_path / name for name in ("index.json", "phase6.json", "dev.jsonl")]
    for path, value in zip(paths, (b"index", b"calibration", b"dev")):
        path.write_bytes(value)
    data = {"schema_version": 1, "mode": "hybrid_rerank", "version": "phase7-dev-v1",
            "status": "pass", "calibration_split": "dev", "holdout_used": False,
            "model_identity_sha256": identity.fingerprint, "index_sha256": _hash(b"index"),
            "phase6_calibration_sha256": _hash(b"calibration"),
            "training_split_sha256": _hash(b"dev"), "threshold": .1,
            "margin_threshold": .01, "easy_confidence_threshold": .8,
            "easy_margin_threshold": .05, "candidate_cap": 40}
    report = tmp_path / "report.json"
    report.write_text(json.dumps(data), encoding="utf-8")
    policy = Phase7Policy.from_report(report, model_identity=identity,
                                      index_manifest=paths[0], phase6_calibration=paths[1],
                                      dev_benchmark=paths[2])
    assert policy.artifact_sha256 == _hash(report.read_bytes())
    paths[2].write_bytes(b"changed")
    with pytest.raises(Phase7PolicyError, match="provenance mismatch"):
        Phase7Policy.from_report(report, model_identity=identity,
                                 index_manifest=paths[0], phase6_calibration=paths[1],
                                 dev_benchmark=paths[2])


def test_phase7_route_is_deterministic_and_bypasses_exact_and_abstained():
    policy = Phase7Policy("v1", *(["a" * 64] * 4), .1, .01, .8, .05)

    class Candidate:
        def __init__(self, confidence, fusion):
            self.confidence_score = confidence
            self.fusion_score = fusion

    hard = [Candidate(.6, .3), Candidate(.5, .29)]
    assert policy.route("question", hard, RoutingTrace(route="hybrid_rrf")) == (
        True, "hard_low_confidence_or_margin")
    assert policy.route("question", hard, RoutingTrace(route="exact_code"))[0] is False
    assert policy.route("question", hard, RoutingTrace(route="abstain", abstained=True))[0] is False
    easy = [Candidate(.9, .5), Candidate(.5, .3)]
    assert policy.route("question", easy, RoutingTrace(route="hybrid_rrf")) == (False, "easy_confident")
