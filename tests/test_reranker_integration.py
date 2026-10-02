import hashlib
from dataclasses import replace
import pytest

from campusai.retrieval.bm25_index import BM25Index
from campusai.retrieval.calibration import RetrievalPolicy
from campusai.retrieval.dense_index import DenseIndex
from campusai.retrieval.hybrid import HybridRetriever
from campusai.retrieval.rerank_policy import Phase7Policy
from campusai.retrieval.cross_encoder_provider import ModelIdentity, RerankedCandidate, RerankerUnavailable


def _make_retriever(tmp_path, *, enabled=True, wrong_provenance=False, unavailable=False):
    root = tmp_path / "index"
    records = [
        {"chunk_id": "a", "doc_id": "doc", "content": "tuition policy student fees", "page": 1,
         "content_type": "text", "metadata": {"page_range": [1, 1], "language": "en"}},
        {"chunk_id": "b", "doc_id": "doc", "content": "fees policy tuition students", "page": 2,
         "content_type": "text", "metadata": {"page_range": [2, 2], "language": "en"}},
    ]
    target = root / "doc"
    BM25Index(records, "en").save(target / "bm25.json")
    dense = DenseIndex(records)
    dense.build(records)
    dense.save(target / "dense.json")
    manifest = root / "manifest.json"
    manifest.write_text('{"documents":["doc"]}', encoding="utf-8")
    calibration = tmp_path / "phase6.json"
    calibration.write_text("{}", encoding="utf-8")
    identity = ModelIdentity("BAAI/bge-reranker-v2-m3", "rev", "a" * 64, "rev")
    policy = Phase7Policy("v1", identity.fingerprint,
                          hashlib.sha256(manifest.read_bytes()).hexdigest(),
                          hashlib.sha256(calibration.read_bytes()).hexdigest(),
                          "b" * 64, 0.0, 0.0, 1.0, 1.0)

    class Provider:
        model_identity = identity
        calls = 0
        seen = []

        def score(self, _query, candidates):
            self.calls += 1
            self.seen = list(candidates)
            if unavailable:
                raise RerankerUnavailable("queue_full")
            ranked = sorted(candidates, key=lambda item: item.candidate_id, reverse=True)
            return [RerankedCandidate(item.candidate_id,
                                      "other" if wrong_provenance else item.doc_id,
                                      item.chunk_id, item.page, item.original_rank,
                                      item.original_rrf_score, 1.0 - rank * .1, rank + 1, identity)
                    for rank, item in enumerate(ranked)]

    provider = Provider()
    phase6 = RetrievalPolicy("hybrid_rrf", 0.0, source=str(calibration))
    retriever = HybridRetriever(root, policies={"hybrid_rrf": phase6},
                                phase7_provider=provider, phase7_policy=policy,
                                phase7_enabled=enabled)
    return retriever, provider, calibration


def test_phase7_reranks_only_phase6_candidates_and_keeps_provenance(tmp_path):
    retriever, provider, _ = _make_retriever(tmp_path)
    baseline = retriever.search("tuition policy", ["doc"], mode="auto", top_k=2)
    result = retriever.search("tuition policy", ["doc"], mode="phase7", top_k=2)
    assert provider.calls == 1
    assert {item.chunk_id for item in result} == {item.chunk_id for item in baseline}
    assert [item.chunk_id for item in result] == ["b", "a"]
    assert [(item.doc_id, item.page, item.content) for item in result] == [
        ("doc", 2, "fees policy tuition students"),
        ("doc", 1, "tuition policy student fees")]
    assert {item.chunk_id: item.score for item in result} == {
        item.chunk_id: item.score for item in baseline}
    assert result[0].reranker_score == 1.0
    assert "reranker_score" not in result[0].to_dict()
    assert retriever.last_trace.rerank_selected is True


def test_phase7_failure_mismatch_and_disable_fall_back_to_phase6(tmp_path):
    for name, options in (("unavailable", {"unavailable": True}),
                          ("provenance", {"wrong_provenance": True}),
                          ("disabled", {"enabled": False})):
        retriever, provider, calibration = _make_retriever(tmp_path / name, **options)
        baseline = retriever.search("tuition policy", ["doc"], mode="auto", top_k=2)
        result = retriever.search("tuition policy", ["doc"], mode="phase7", top_k=2)
        assert [(item.chunk_id, item.page) for item in result] == [
            (item.chunk_id, item.page) for item in baseline]
        assert retriever.last_trace.rerank_selected is False
        assert provider.calls == (0 if name == "disabled" else 1)
        if name == "unavailable":
            calibration.write_text("changed", encoding="utf-8")
            retriever.search("tuition policy", ["doc"], mode="phase7", top_k=2)
            assert retriever.last_trace.rerank_reason == "calibration_or_index_mismatch"


def test_phase7_abstention_never_calls_reranker(tmp_path):
    retriever, provider, _ = _make_retriever(tmp_path)
    assert retriever.search("", ["doc"], mode="phase7") == []
    assert retriever.search("ZZ999 prerequisite", ["doc"], mode="phase7") == []
    assert provider.calls == 0


def test_calibrated_low_evidence_abstention_keeps_legacy_policy_and_margin_fallback(tmp_path):
    retriever, provider, _ = _make_retriever(tmp_path)
    baseline = retriever.search("tuition policy", ["doc"], mode="auto", top_k=2)
    retriever.phase7_policy = replace(retriever.phase7_policy, threshold=2.0)
    assert retriever.search("tuition policy", ["doc"], mode="phase7", top_k=2) == baseline
    assert not retriever.last_trace.abstained
    retriever.phase7_policy = replace(retriever.phase7_policy, low_score_action="abstain")
    assert retriever.search("tuition policy", ["doc"], mode="phase7", top_k=2) == []
    assert provider.calls == 2
    assert retriever.last_trace.rerank_selected and retriever.last_trace.abstained
    assert retriever.last_trace.abstention_reason == "reranker_no_evidence"
    assert retriever.phase7_enabled
    retriever.phase7_policy = replace(retriever.phase7_policy, threshold=0.0, margin_threshold=1.0)
    assert retriever.search("tuition policy", ["doc"], mode="phase7", top_k=2) == baseline
    assert not retriever.last_trace.abstained and not retriever.last_trace.rerank_selected


@pytest.mark.parametrize('reason', ['queue_full', 'reranker_timeout', 'circuit_open'])
def test_evidence_abstention_never_converts_provider_faults_to_missing_evidence(tmp_path, reason):
    retriever, provider, _ = _make_retriever(tmp_path)
    baseline = retriever.search("tuition policy", ["doc"], mode="auto", top_k=2)
    retriever.phase7_policy = replace(retriever.phase7_policy, threshold=2.0, low_score_action="abstain")
    def fail(_query, _candidates):
        raise RerankerUnavailable(reason)
    provider.score = fail
    assert retriever.search("tuition policy", ["doc"], mode="phase7", top_k=2) == baseline
    assert not retriever.last_trace.abstained and not retriever.last_trace.rerank_selected
    assert retriever.last_trace.rerank_reason == reason


def test_low_scores_with_invalid_provenance_still_use_phase6(tmp_path):
    retriever, _, _ = _make_retriever(tmp_path, wrong_provenance=True)
    baseline = retriever.search("tuition policy", ["doc"], mode="auto", top_k=2)
    retriever.phase7_policy = replace(retriever.phase7_policy, threshold=2.0, low_score_action="abstain")
    assert retriever.search("tuition policy", ["doc"], mode="phase7", top_k=2) == baseline
    assert retriever.last_trace.rerank_reason == "reranker_provenance_invalid"
    assert not retriever.phase7_enabled


def test_service_abstention_skips_llm_and_policy_change_invalidates_answer_cache(tmp_path):
    from campusai.rag.service import CampusAIQueryService
    from campusai.rag.grounding import GroundedAnswerGenerator
    from campusai.rag.cache import RAGAnswerCache
    from tests.test_basic_rag import FakeLLM, valid_payload
    retriever, provider, _ = _make_retriever(tmp_path)
    retriever.phase7_policy = replace(retriever.phase7_policy, threshold=2.0, low_score_action='abstain')
    llm = FakeLLM(valid_payload())
    with RAGAnswerCache() as cache:
        service = CampusAIQueryService(retriever, GroundedAnswerGenerator(llm), cache=cache)
        answer = service.ask('tuition policy', ['doc'], mode='phase7')
        assert answer.abstained and not answer.citations and llm.calls == 0
        assert service.last_retrieval == []
        cached = service.ask('tuition policy', ['doc'], mode='phase7')
        assert cached.answer == answer.answer and cached.abstained and cached.cache_hit
        assert service.last_cache_hit and provider.calls == 1
        retriever.phase7_policy = replace(retriever.phase7_policy, low_score_action='phase6')
        service.ask('tuition policy', ['doc'], mode='phase7')
        assert not service.last_cache_hit and provider.calls == 2 and llm.calls == 1
