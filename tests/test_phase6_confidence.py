import json

import pytest

from campusai.retrieval.calibration import RetrievalPolicy
from campusai.retrieval.confidence import FEATURES, RetrievalConfidenceModel


def test_confidence_model_round_trip_and_feature_schema():
    model = RetrievalConfidenceModel(
        "phase6-logistic-v1", "logistic", {name: 0.1 for name in FEATURES}, -0.3)
    restored = RetrievalConfidenceModel.from_dict(model.to_dict())
    assert restored.fingerprint == model.fingerprint
    assert restored.predict({name: 0.5 for name in FEATURES}) == model.predict({name: 0.5 for name in FEATURES})
    with pytest.raises(ValueError, match="feature schema"):
        restored.predict({"lexical_overlap": 0.5})


def test_calibrated_policy_loads_versioned_model(tmp_path):
    model = RetrievalConfidenceModel("phase6-logistic-v1", "logistic",
                                     {name: 0.0 for name in FEATURES}, 0.0)
    path = tmp_path / "calibration.json"
    path.write_text(json.dumps({"mode": "hybrid_rrf", "result": {"threshold": 0.5},
                                "confidence_model": model.to_dict(),
                                "confidence_model_sha256": model.fingerprint}), encoding="utf-8")
    policy = RetrievalPolicy.from_report(path, expected_mode="hybrid_rrf")
    assert policy.confidence_model.version == "phase6-logistic-v1"
    with pytest.raises(ValueError, match="feature schema"):
        RetrievalConfidenceModel.from_dict({**model.to_dict(), "feature_schema": ["wrong"]})
