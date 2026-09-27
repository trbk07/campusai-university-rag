from campusai.rag.abstention import AbstentionReason, user_message
from campusai.rag.claims import align_claims, extract_claims
from campusai.rag.confidence import calibration_metrics, score_confidence
from campusai.rag.evidence import EvidenceRegistry
from campusai.rag.grounding import GroundedAnswerGenerator, validate_citation, validate_quote
from campusai.rag.service import choose_query_mode
from campusai.retrieval.hybrid import RetrievalResult


def evidence(content="CS201 requires CS101 and 3 credits."):
    return RetrievalResult("c1", "doc", 2, content, "text", 0.9, "hybrid", {"page_range": [2, 2]})


class LLM:
    def __init__(self, payload): self.payload = payload
    def generate_json(self, *_args, **_kwargs): return self.payload


def legacy_evidence(chunk_id="c1", page=3):
    return RetrievalResult(
        chunk_id,
        "doc-1",
        page,
        "Điều kiện tiên quyết: MATH101.",
        "text",
        1.0,
        "hybrid",
        {"document_type": "curriculum"},
    )


class LegacyLLM:
    def __init__(self, payload):
        self.payload = payload

    def generate_json(self, prompt, schema=None, **kwargs):
        assert "chunk_id=c1" in prompt
        assert schema["required"]
        return self.payload


def test_grounded_answer_accepts_only_retrieved_citations():
    answer = GroundedAnswerGenerator(LegacyLLM({
        "answer": "Cần hoàn thành MATH101.",
        "confidence": "high",
        "abstained": False,
        "citations": [{"chunk_id": "c1", "page": 3, "quote": "MATH101"}],
    })).answer("Môn tiên quyết là gì?", [legacy_evidence()])
    assert answer.abstained is False
    assert answer.citations[0].page == 3


def test_grounded_answer_abstains_on_fabricated_citation():
    answer = GroundedAnswerGenerator(LegacyLLM({
        "answer": "Không chắc.",
        "confidence": "low",
        "abstained": False,
        "citations": [{"chunk_id": "missing", "page": 99}],
    })).answer("Câu hỏi", [legacy_evidence()])
    assert answer.abstained is True
    assert answer.reason == "citation_not_in_evidence"


def test_no_evidence_abstains_without_calling_llm():
    answer = GroundedAnswerGenerator(LegacyLLM({})).answer("Câu hỏi", [])
    assert answer.abstained is True
    assert answer.reason == "no_retrieval_evidence"


def test_citation_validator_rejects_wrong_page_range_and_source_hash():
    evidence_item = legacy_evidence()
    evidence_item.metadata.update({"page_range": [3, 4], "source_hash": "sha-good"})
    validation = validate_citation({
        "chunk_id": "c1",
        "doc_id": "doc-1",
        "page": 3,
        "page_range": [9, 9],
        "source_hash": "sha-bad",
    }, evidence_item)
    assert validation.valid is False
    assert "page_range_mismatch" in validation.errors
    assert "source_hash_mismatch" in validation.errors


def test_hard_questions_only_use_reranker_when_available():
    assert choose_query_mode("So sánh hai chương trình", reranker_available=False) == "hybrid"
    assert choose_query_mode("So sánh hai chương trình", reranker_available=True) == "hybrid_rerank"


def test_claim_alignment_rejects_unsupported_numeric_leakage():
    registry = EvidenceRegistry([evidence()])
    claims = extract_claims("CS201 requires CS101 and 4 credits.")
    aligned = align_claims(claims, registry, {claims[0].claim_id: ("c1",)})
    assert any(claim.status == "unsupported" for claim in aligned)


def test_grounding_abstains_when_provider_adds_unsupported_claim():
    answer = GroundedAnswerGenerator(LLM({
        "answer": "CS201 requires CS101 and 4 credits.", "confidence": "high", "abstained": False,
        "citations": [{"chunk_id": "c1", "page": 2, "quote": "CS201 requires CS101 and 3 credits."}],
    })).answer("What is required?", [evidence()])
    assert answer.abstained is True
    assert answer.reason == "unsupported_claim"
    assert answer.evidence_status == "unsupported_claim"


def test_grounding_does_not_publish_partially_supported_claim():
    answer = GroundedAnswerGenerator(LLM({
        "answer": "CS201 requires CS101 and 4 credits.", "confidence": "high", "abstained": False,
        "citations": [{"chunk_id": "c1", "page": 2}],
    })).answer("What is required?", [evidence("CS201 requires CS101.")])
    assert answer.abstained is True
    assert answer.reason == "unsupported_claim"


def test_structured_claim_without_direct_citation_is_rejected():
    answer = GroundedAnswerGenerator(LLM({
        "answer": "CS201 requires CS101.", "confidence": "high", "abstained": False,
        "citations": [{"chunk_id": "c1", "page": 2}],
        "claims": [{"claim_id": "c1", "text": "CS201 requires CS101.", "citation_ids": []}],
    })).answer("What is required?", [evidence("CS201 requires CS101.")])
    assert answer.abstained is True
    assert answer.reason == "unsupported_claim"


def test_confidence_is_recomputed_and_calibration_is_deterministic():
    confidence = score_confidence(retrieval_support=1, claim_entailment=1, citation_completeness=1)
    assert confidence.label == "high"
    metrics = calibration_metrics([0.9, 0.1], [True, False])
    assert metrics["brier_score"] == 0.01
    assert validate_quote("CS101", "Course CS101")
    assert not validate_quote("CS999", "Course CS101")


def test_abstention_taxonomy_has_stable_user_messages():
    assert AbstentionReason.CONFLICTING_EVIDENCE.value == "conflicting_evidence"
    assert AbstentionReason.PROVIDER_ABSTENTION.value == "provider_abstention"
    assert "evidence" in user_message("no_evidence_found", "en").lower()
