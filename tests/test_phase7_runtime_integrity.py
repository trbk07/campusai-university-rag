"""Runtime regressions; synthetic fixtures are never release evidence."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
from threading import Event

import pytest

from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.service import CampusAIQueryService
from campusai.retrieval.cross_encoder_provider import (
    OfflineCrossEncoderReranker, RerankerUnavailable,
)
from campusai.retrieval.routing import RoutingTrace
from campusai.retrieval.rerank_policy import Phase7Policy, Phase7PolicyError
from tests.test_basic_rag import FakeLLM, FakeRetriever, evidence, valid_payload
from tests.test_cross_encoder_provider import _candidate, _identity
from tests.test_reranker_integration import _make_retriever


def test_score_cache_does_not_claim_model_inference(tmp_path):
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    calls = []

    class Model:
        def predict(self, pairs, **_kwargs):
            calls.append(pairs)
            return [1.] * len(pairs)

    provider = OfflineCrossEncoderReranker(_identity(tmp_path), tmp_path,
        model_loader=Model, score_cache_size=1)
    try:
        provider.score("question", [_candidate("a", 1)])
        assert provider.last_call["inference_started"]
        assert not provider.last_call["score_cache_hit"]
        provider.score("question", [_candidate("a", 1)])
        assert provider.last_call["score_cache_hit"]
        assert not provider.last_call["inference_started"]
        assert provider.last_call["inference_observed_ms"] == 0.
        assert len(calls) == provider.metrics_snapshot()["inference_calls"] == 1
    finally:
        provider.close()


@pytest.mark.parametrize("batch_window_ms", [0, 2])
def test_pre_prediction_failure_never_claims_inference(tmp_path, batch_window_ms):
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    identity = replace(_identity(tmp_path), batch_window_ms=batch_window_ms)
    loads = []
    provider = OfflineCrossEncoderReranker(identity, tmp_path,
        model_loader=lambda: loads.append(1))
    (tmp_path / "config.json").write_text("changed", encoding="utf-8")
    try:
        with pytest.raises(RerankerUnavailable, match="checksum"):
            provider.score("question", [_candidate("a", 1)])
        assert not provider.last_call["inference_started"]
        assert provider.last_call["inference_observed_ms"] == 0.
        assert not loads and provider.metrics_snapshot()["inference_calls"] == 0
    finally:
        provider.close()


@pytest.mark.parametrize("batch_window_ms", [0, 2])
def test_close_during_loader_stops_prediction_and_drops_pending_inputs(tmp_path, batch_window_ms):
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    identity = replace(_identity(tmp_path), batch_window_ms=batch_window_ms)
    entered, release, predicted = Event(), Event(), Event()

    class Model:
        def predict(self, pairs, **_kwargs):
            predicted.set()
            return [1.] * len(pairs)

    def loader():
        entered.set()
        assert release.wait(3)
        return Model()

    provider = OfflineCrossEncoderReranker(identity, tmp_path, model_loader=loader)
    try:
        with ThreadPoolExecutor(max_workers=1) as workers:
            first = workers.submit(provider.score, "question", [_candidate("a", 1)])
            assert entered.wait(2)
            provider.close()
            assert not provider._batch_queue
            release.set()
            with pytest.raises(RerankerUnavailable, match="disabled"):
                first.result(timeout=3)
        provider.drain()
        assert not predicted.is_set()
        assert provider.metrics_snapshot()["inference_calls"] == 0
        assert provider._model is None
    finally:
        release.set()
        provider.close()


def test_answer_cache_hit_has_current_request_trace_and_zero_worker_execution():
    retriever = FakeRetriever([evidence()])
    retriever.last_trace = RoutingTrace(route="auto", rerank_route_selected=True,
        rerank_inference_started=True, rerank_applied=True, rerank_selected=True)
    service = CampusAIQueryService(retriever, GroundedAnswerGenerator(FakeLLM(valid_payload())))
    try:
        service.ask("Which course?", corpus_version="fixed")
        answer = service.ask("Which course?", corpus_version="fixed")
        assert answer.cache_hit and service.last_cache_hit
        trace = retriever.last_trace
        assert trace.answer_cache_hit and not trace.retrieval_cache_hit
        assert not (trace.rerank_route_selected or trace.rerank_inference_started
                    or trace.rerank_applied or trace.rerank_selected)
        assert trace.candidate_count == trace.final_count == 0
        assert not service.last_retrieval
        assert all(value == 0 for value in trace.latency_ms.values())
    finally:
        service.close()


def test_transient_phase7_fallback_is_retried_after_provider_recovers(tmp_path):
    retriever, provider, _ = _make_retriever(tmp_path)
    normal_score = provider.score
    failed = []

    def once_unavailable(query, candidates):
        if not failed:
            failed.append(1)
            raise RerankerUnavailable("queue_full")
        return normal_score(query, candidates)

    provider.score = once_unavailable
    llm = FakeLLM({"answer": "tuition policy student fees", "confidence": "high", "abstained": False,
        "citations": [{"chunk_id": "a", "doc_id": "doc", "page": 1, "page_range": [1, 1],
                       "quote": "tuition policy student fees"}]})
    service = CampusAIQueryService(retriever, GroundedAnswerGenerator(llm))
    try:
        first = service.ask("tuition policy", ["doc"], language="en", mode="phase7")
        assert first.citations and not first.abstained
        assert retriever.last_trace.rerank_reason == "queue_full"
        assert not retriever.last_trace.rerank_inference_started
        second = service.ask("tuition policy", ["doc"], language="en", mode="phase7")
        assert second.citations and not service.last_cache_hit
        assert provider.calls == 1 and retriever.last_trace.rerank_applied
        third = service.ask("tuition policy", ["doc"], language="en", mode="phase7")
        assert third.cache_hit and retriever.last_trace.answer_cache_hit
        assert not retriever.last_trace.rerank_inference_started
    finally:
        service.close()


def test_physical_index_change_invalidates_answer_cache_with_unchanged_manifest(tmp_path):
    retriever, _, _ = _make_retriever(tmp_path)
    service = CampusAIQueryService(retriever, GroundedAnswerGenerator())
    try:
        old = service.corpus_version(["doc"])
        bm25 = retriever.index_root / "doc" / "bm25.json"
        manifest = (retriever.index_root / "manifest.json").read_bytes()
        data = json.loads(bm25.read_text(encoding="utf-8"))
        data["items"][0]["content"] = "Replaced tuition policy and changed source content."
        bm25.write_text(json.dumps(data), encoding="utf-8")
        assert service.corpus_version(["doc"]) != old
        assert (retriever.index_root / "manifest.json").read_bytes() == manifest
        same = service.corpus_version(["doc"])
        assert service.corpus_version(["doc"]) == same
    finally:
        service.close()


def test_bm25_only_documents_are_in_corpus_cache_identity(tmp_path):
    retriever, _, _ = _make_retriever(tmp_path)
    (retriever.index_root / "doc" / "dense.json").unlink()
    service = CampusAIQueryService(retriever, GroundedAnswerGenerator())
    try:
        assert service.corpus_version() == service.corpus_version(["doc"])
        assert service.corpus_version() != service.corpus_version([])
    finally:
        service.close()


def test_retrieval_cache_reports_current_request_work_without_old_latency(tmp_path):
    retriever, _, _ = _make_retriever(tmp_path)
    before = retriever.search("tuition policy", ["doc"], mode="auto")
    assert retriever.last_trace.bm25_used and not retriever.last_trace.retrieval_cache_hit
    original = retriever.last_trace
    after = retriever.search("tuition policy", ["doc"], mode="auto")
    assert after == before
    trace = retriever.last_trace
    assert trace.retrieval_cache_hit and not trace.bm25_used and not trace.dense_used
    assert trace.route == original.route and trace.candidate_count == original.candidate_count
    assert trace.latency_ms["bm25"] == trace.latency_ms["dense"] == trace.latency_ms["fusion"] == 0.


@pytest.mark.parametrize("values", [
    {"threshold": True}, {"threshold": "0.1"}, {"margin_threshold": False},
    {"easy_confidence_threshold": True}, {"candidate_cap": 40.0},
    {"rerank_candidate_cap": 10.5}, {"rerank_candidate_cap": True},
    {"minimum_agreement": False}, {"constraint_threshold": 1.5},
    {"constraint_threshold": True}, {"version": True},
])
def test_runtime_policy_rejects_boolean_and_lossy_calibration_values(values):
    policy = Phase7Policy("dev-v1", *(["a" * 64] * 4), .1, .01, .8, .05)
    with pytest.raises(Phase7PolicyError):
        replace(policy, **values)


@pytest.mark.parametrize("field,value", [("rerank_candidate_cap", 10.5),
    ("threshold", True), ("constraint_threshold", 1.5), ("minimum_agreement", "0.1")])
def test_policy_report_never_coerces_invalid_values_into_an_active_policy(tmp_path, field, value):
    import hashlib

    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    identity = _identity(tmp_path)
    paths = [tmp_path / name for name in ("index.json", "phase6.json", "dev.jsonl")]
    for path in paths:
        path.write_text("frozen", encoding="utf-8")
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    data = {"schema_version": 1, "mode": "hybrid_rerank", "version": "dev-v1",
        "status": "pass", "calibration_split": "dev", "holdout_used": False,
        "model_identity_sha256": identity.fingerprint, "index_sha256": digest(paths[0]),
        "phase6_calibration_sha256": digest(paths[1]), "training_split_sha256": digest(paths[2]),
        "threshold": .1, "margin_threshold": .01, "easy_confidence_threshold": .8,
        "easy_margin_threshold": .05, "rerank_candidate_cap": 10, field: value}
    report = tmp_path / "policy.json"
    report.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(Phase7PolicyError):
        Phase7Policy.from_report(report, model_identity=identity, index_manifest=paths[0],
            phase6_calibration=paths[1], dev_benchmark=paths[2])


def test_model_batch_window_rejects_boolean_configuration(tmp_path):
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="batching identity"):
        replace(_identity(tmp_path), batch_window_ms=True)
