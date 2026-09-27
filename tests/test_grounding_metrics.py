from evaluation.grounding_metrics import evaluate_grounding
from evaluation.validate_release import validate
from campusai.rag.schemas import validate_response
from campusai.rag.calibration import IsotonicCalibrator
from campusai.rag.confidence import score_confidence
from campusai.rag.grounding import GroundedAnswer
from campusai.rag.evidence import EvidenceRegistry
from campusai.retrieval.hybrid import RetrievalResult


def test_metrics_do_not_trust_self_reported_supported_status():
    report = evaluate_grounding([{
        "answerable": True,
        "abstained": False,
        "claims": [{"text": "4 credits", "status": "supported", "citation_ids": ["wrong"]}],
        "citations": [{"chunk_id": "wrong", "doc_id": "d", "page": 1}],
        "gold_claims": [{"text": "4 credits", "answerable": True,
                         "evidence": [{"chunk_id": "gold", "doc_id": "d", "page": 2}]}],
    }])
    assert report["grounded_claim_precision"] == 0.0
    assert report["citation_precision"] == 0.0


def test_public_schema_requires_reason_for_abstention():
    valid, errors = validate_response({
        "answer": "KhÃ´ng Ä‘á»§ báº±ng chá»©ng.", "citations": [], "confidence": "low",
        "abstained": True, "abstention_reason": "unsupported_claim",
    })
    assert valid, errors
    invalid, errors = validate_response({
        "answer": "KhÃ´ng Ä‘á»§ báº±ng chá»©ng.", "citations": [], "confidence": "low", "abstained": True,
    })
    assert not invalid
    assert "abstention_reason_missing" in errors


def test_release_validator_requires_full_benchmark_and_strict_metrics():
    errors = validate({"dataset_count": 30, "metrics": {"citation_precision": 1.0}})
    assert "dataset_too_small_for_release" in errors
    assert "grounded_claim_precision" in errors


def test_isotonic_calibration_is_monotonic_and_versioned():
    calibrator = IsotonicCalibrator.fit([0.1, 0.2, 0.9, 0.8], [False, True, True, False])
    assert calibrator.predict(0.1) <= calibrator.predict(0.9)
    restored = IsotonicCalibrator.from_dict(calibrator.to_dict())
    confidence = score_confidence(retrieval_support=0.8, claim_entailment=0.8,
                                  citation_completeness=1.0, calibrator=restored)
    assert confidence.method == "isotonic_v1"


def test_public_grounding_response_excludes_internal_trace():
    payload = GroundedAnswer(answer="ok", confidence="low").to_public_dict()
    assert "confidence_score" not in payload
    assert "evidence_status" not in payload
    assert "reason" not in payload


def test_public_schema_rejects_internal_version_and_hides_source_hash():
    answer = GroundedAnswer(
        answer="ok", confidence="high",
        citations=(__import__("campusai.rag.grounding", fromlist=["Citation"]).Citation(
            "c1", "doc", 1, source_hash="secret"),),
    )
    public = answer.to_public_dict()
    assert "source_hash" not in public["citations"][0]
    valid, errors = validate_response({**public, "schema_version": "grounding-internal-v2"})
    assert not valid
    assert "schema_version_invalid" in errors


def test_evidence_registry_reports_provenance_and_version_conflicts():
    records = [
        RetrievalResult("a", "doc", 1, "one", "text", 1.0, "hybrid", {"version": "1", "source_hash": "a"}),
        RetrievalResult("b", "doc", 2, "two", "text", 1.0, "hybrid", {"version": "2"}),
    ]
    registry = EvidenceRegistry(records)
    assert registry.version_conflicts() == (("doc", ("1", "2")),)
    assert registry.missing_provenance() == ()
