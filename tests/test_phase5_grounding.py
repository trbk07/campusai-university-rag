from campusai.rag.abstention import AbstentionReason, user_message
from campusai.rag.claims import align_claims, extract_claims
from campusai.rag.confidence import calibration_metrics, score_confidence
from campusai.rag.evidence import EvidenceRegistry
from campusai.rag.grounding import GroundedAnswerGenerator, validate_quote
from campusai.retrieval.hybrid import RetrievalResult


def evidence(content="CS201 requires CS101 and 3 credits."):
    return RetrievalResult("c1", "doc", 2, content, "text", 0.9, "hybrid", {"page_range": [2, 2]})


class LLM:
    def __init__(self, payload): self.payload = payload
    def generate_json(self, *_args, **_kwargs): return self.payload


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


def test_confidence_is_recomputed_and_calibration_is_deterministic():
    confidence = score_confidence(retrieval_support=1, claim_entailment=1, citation_completeness=1)
    assert confidence.label == "high"
    metrics = calibration_metrics([0.9, 0.1], [True, False])
    assert metrics["brier_score"] == 0.01
    assert validate_quote("CS101", "Course CS101")
    assert not validate_quote("CS999", "Course CS101")


def test_abstention_taxonomy_has_stable_user_messages():
    assert AbstentionReason.CONFLICTING_EVIDENCE.value == "conflicting_evidence"
    assert "evidence" in user_message("no_evidence_found", "en").lower()
