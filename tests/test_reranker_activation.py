import json
import hashlib

import pytest

from campusai.retrieval.reranker_activation import build_phase7_retriever
from campusai.retrieval.cross_encoder_provider import ModelIdentity, snapshot_sha256


def test_phase7_feature_flag_defaults_to_phase6(tmp_path):
    calibration = tmp_path / "phase6.json"
    calibration.write_text(json.dumps({"mode": "hybrid_rrf", "result": {"threshold": .1}}),
                           encoding="utf-8")
    retriever = build_phase7_retriever(tmp_path / "index", calibration,
                                       tmp_path / "dev.jsonl", environ={})
    assert retriever.phase7_enabled is False
    assert retriever.phase7_activation_reason == "feature_disabled"


def test_phase7_invalid_activation_falls_back_without_loading_model(tmp_path, caplog):
    calibration = tmp_path / "phase6.json"
    calibration.write_text(json.dumps({"mode": "hybrid_rrf", "result": {"threshold": .1}}),
                           encoding="utf-8")
    retriever = build_phase7_retriever(tmp_path / "index", calibration,
                                       tmp_path / "dev.jsonl",
                                       environ={"RERANKER_ENABLED": "true",
                                                "RERANKER_MODEL_DIR": "C:\\private\\model"})
    assert retriever.phase7_enabled is False
    assert retriever.phase7_activation_reason == "activation_rejected"
    assert "C:\\private\\model" not in caplog.text


def test_phase7_production_cannot_activate_without_a_complete_release_manifest(tmp_path):
    calibration = tmp_path / "phase6.json"
    calibration.write_text(json.dumps({"mode": "hybrid_rrf", "result": {"threshold": .1}}), encoding="utf-8")
    retriever = build_phase7_retriever(tmp_path / "index", calibration, tmp_path / "dev.jsonl",
                                     environ={"RERANKER_ENABLED": "true", "RERANKER_DEPLOYMENT": "production"})
    assert retriever.phase7_enabled is False


@pytest.mark.parametrize("device", ["cpu", "cuda:0"])
def test_phase7_valid_opt_in_binds_model_index_and_cache_key(tmp_path, device):
    index = tmp_path / "index"
    index.mkdir()
    (index / "manifest.json").write_text('{"documents":[]}', encoding="utf-8")
    calibration = tmp_path / "phase6.json"
    calibration.write_text(json.dumps({"mode": "hybrid_rrf", "result": {"threshold": .1}}),
                           encoding="utf-8")
    dev = tmp_path / "dev.jsonl"
    dev.write_text("dev-only", encoding="utf-8")
    snapshot = tmp_path / "rev"
    snapshot.mkdir()
    (snapshot / "config.json").write_text("{}", encoding="utf-8")
    identity = ModelIdentity("BAAI/bge-reranker-v2-m3", "rev", snapshot_sha256(snapshot),
                             "rev", device=device)
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    artifact = tmp_path / "reranker_calibration.json"
    artifact.write_text(json.dumps({
        "schema_version": 1, "mode": "hybrid_rerank", "version": "dev-v1",
        "calibration_split": "dev", "holdout_used": False, "status": "pass",
        "model_identity_sha256": identity.fingerprint,
        "index_sha256": digest(index / "manifest.json"),
        "phase6_calibration_sha256": digest(calibration),
        "training_split_sha256": digest(dev), "threshold": 0.0,
        "margin_threshold": 0.0, "easy_confidence_threshold": 1.0,
        "easy_margin_threshold": 1.0, "candidate_cap": 40,
        "rerank_candidate_cap": 10}), encoding="utf-8")
    retriever = build_phase7_retriever(index, calibration, dev, environ={
        "RERANKER_ENABLED": "true", "RERANKER_MODE": "hard_only",
        "RERANKER_MODEL": identity.model_name,
        "RERANKER_MODEL_REVISION": identity.model_revision,
        "RERANKER_MODEL_SHA256": identity.model_sha256,
        "RERANKER_TOKENIZER_REVISION": identity.tokenizer_revision,
        "RERANKER_DEVICE": device,
        "RERANKER_MODEL_DIR": str(snapshot),
        "RERANKER_CALIBRATION": str(artifact),
    })
    try:
        assert retriever.phase7_enabled is True
        assert retriever.phase7_policy.rerank_candidate_cap == 10
        assert retriever.phase7_provider.model_identity.device == device
        assert identity.fingerprint in retriever.phase7_cache_fingerprint
    finally:
        retriever.phase7_provider.close()
    from campusai.retrieval.runtime_provenance import runtime_sha256
    release = tmp_path / "release_manifest.json"
    manifest = {"status": "pass", "score": 10.0, "errors": [],
                "gates": {f"M{i}": {"status": "PASS"} for i in range(13)},
                "runtime_sha256": runtime_sha256(), "model_identity_sha256": identity.fingerprint,
                "index_sha256": digest(index / "manifest.json"), "device": device,
                "candidate_cap": 40, "rerank_cap": 10, "phase6_calibration_sha256": digest(calibration),
                "phase7_calibration_sha256": digest(artifact)}
    release.write_text(json.dumps(manifest), encoding="utf-8")
    env = {"RERANKER_ENABLED": "true", "RERANKER_DEPLOYMENT": "production",
           "RERANKER_RELEASE_MANIFEST": str(release), "RERANKER_MODEL": identity.model_name,
           "RERANKER_MODEL_REVISION": identity.model_revision, "RERANKER_MODEL_SHA256": identity.model_sha256,
           "RERANKER_TOKENIZER_REVISION": identity.tokenizer_revision, "RERANKER_DEVICE": device,
           "RERANKER_MODEL_DIR": str(snapshot), "RERANKER_CALIBRATION": str(artifact)}
    production = build_phase7_retriever(index, calibration, dev, environ=env)
    try:
        assert production.phase7_enabled
    finally:
        production.phase7_provider.close()
    for changed in ({"runtime_sha256": "0"*64}, {"score": None}, {"device": "invalid"},
                    {"gates": {f"M{i}": {"status": "CONDITIONAL" if i == 6 else "PASS"} for i in range(13)}}):
        release.write_text(json.dumps({**manifest, **changed}), encoding="utf-8")
        assert not build_phase7_retriever(index, calibration, dev, environ=env).phase7_enabled
