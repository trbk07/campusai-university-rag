import math
from threading import Event

import pytest

from campusai.retrieval.cross_encoder_provider import (
    ModelIdentity, OfflineCrossEncoderReranker, RerankCandidate,
    RerankerUnavailable, snapshot_sha256,
)


def _identity(path):
    return ModelIdentity("BAAI/bge-reranker-v2-m3", path.name, snapshot_sha256(path), path.name)


def _candidate(name, rank):
    return RerankCandidate(name, "doc", name, 2, f"content {name}", rank, 1 / rank)


def test_phase7_provider_is_batched_singleton_and_provenance_preserving(tmp_path):
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    loads = []

    class Model:
        def predict(self, pairs, *, batch_size, show_progress_bar, activation_fn):
            assert batch_size == 8
            assert show_progress_bar is False
            assert activation_fn(.2) == .2
            assert len(pairs) == 3
            return [.2, .9, .9]

    def load():
        loads.append(1)
        return Model()

    provider = OfflineCrossEncoderReranker(_identity(tmp_path), tmp_path, model_loader=load)
    candidates = [_candidate("a", 1), _candidate("b", 2), _candidate("c", 3)]
    try:
        result = provider.score("question", candidates)
        assert [item.chunk_id for item in result] == ["b", "c", "a"]
        assert [(item.doc_id, item.page, item.original_rank) for item in result] == [
            ("doc", 2, 2), ("doc", 2, 3), ("doc", 2, 1)]
        assert [item.final_rank for item in result] == [1, 2, 3]
        assert provider.score("question", candidates) == result
        assert len(loads) == 1
    finally:
        provider.close()


def test_phase7_provider_rejects_model_mismatch_and_opens_circuit(tmp_path):
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    identity = _identity(tmp_path)
    (tmp_path / "config.json").write_text("changed", encoding="utf-8")
    provider = OfflineCrossEncoderReranker(identity, tmp_path, failure_limit=1, model_loader=lambda: None)
    try:
        with pytest.raises(RerankerUnavailable, match="model_checksum_mismatch"):
            provider.score("question", [_candidate("a", 1)])
        with pytest.raises(RerankerUnavailable, match="circuit_open"):
            provider.score("question", [_candidate("a", 1)])
    finally:
        provider.close()


def test_phase7_provider_rejects_invalid_scores_and_candidates(tmp_path):
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")

    class Model:
        def predict(self, *_args, **_kwargs):
            return [math.nan]

    provider = OfflineCrossEncoderReranker(_identity(tmp_path), tmp_path,
                                           candidate_cap=2, model_loader=lambda: Model())
    try:
        with pytest.raises(RerankerUnavailable, match="candidate_cap"):
            provider.score("question", [_candidate("a", 1), _candidate("b", 2), _candidate("c", 3)])
        with pytest.raises(RerankerUnavailable, match="candidate_provenance"):
            provider.score("question", [_candidate("a", 1), _candidate("a", 2)])
        with pytest.raises(RerankerUnavailable, match="invalid_model_scores"):
            provider.score("question", [_candidate("a", 1)])
    finally:
        provider.close()


def test_phase7_provider_timeout_and_bounded_queue(tmp_path):
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    release = Event()

    class SlowModel:
        def predict(self, *_args, **_kwargs):
            release.wait(1)
            return [.1]

    provider = OfflineCrossEncoderReranker(_identity(tmp_path), tmp_path,
                                           timeout_ms=10, queue_limit=0, model_loader=lambda: SlowModel())
    try:
        with pytest.raises(RerankerUnavailable, match="reranker_timeout"):
            provider.score("question", [_candidate("a", 1)])
        with pytest.raises(RerankerUnavailable, match="queue_full"):
            provider.score("question", [_candidate("a", 1)])
    finally:
        release.set()
        provider.close()


def test_phase7_identity_rejects_local_path():
    with pytest.raises(ValueError, match="canonical repository ID"):
        ModelIdentity("C:\\private\\model", "rev", "0" * 64, "rev")


def test_phase7_identity_allows_explicit_cuda_but_rejects_ambiguous_device():
    cpu = ModelIdentity("BAAI/bge-reranker-v2-m3", "rev", "0" * 64, "rev")
    gpu = ModelIdentity("BAAI/bge-reranker-v2-m3", "rev", "0" * 64, "rev",
                        device="cuda:0")
    assert gpu.fingerprint != cpu.fingerprint
    assert gpu.device == "cuda:0"
    with pytest.raises(ValueError, match="invalid reranker model identity"):
        ModelIdentity("BAAI/bge-reranker-v2-m3", "rev", "0" * 64, "rev",
                      device="auto")


def test_phase7_provider_rejects_snapshot_revision_mismatch(tmp_path):
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    identity = ModelIdentity("BAAI/bge-reranker-v2-m3", "other-revision",
                             snapshot_sha256(tmp_path), "other-revision")
    with pytest.raises(ValueError, match="snapshot revision mismatch"):
        OfflineCrossEncoderReranker(identity, tmp_path)


def test_closed_provider_cannot_submit_new_inference(tmp_path):
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    loads = []
    provider = OfflineCrossEncoderReranker(_identity(tmp_path), tmp_path, model_loader=lambda: loads.append(1))
    provider.close()
    with pytest.raises(RerankerUnavailable, match="feature_disabled"):
        provider.score("question", [_candidate("a", 1)])
    assert loads == []
