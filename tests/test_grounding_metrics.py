from evaluation.grounding.grounding_metrics import evaluate_grounding
from evaluation.grounding.validate_grounding_release import validate
from campusai.rag.claims import Claim, align_claims
from campusai.rag.schemas import validate_response
from campusai.rag.calibration import IsotonicCalibrator
from campusai.rag.confidence import score_confidence
from campusai.rag.grounding import GroundedAnswer
from campusai.rag.evidence import EvidenceRegistry
from campusai.retrieval.hybrid import RetrievalResult


def test_one_citation_must_cover_every_reviewed_span_of_a_multi_evidence_claim():
    from copy import deepcopy
    from evaluation.grounding.grounding_metrics import _link_counts, is_grounded_answer
    statement = 'Candidates must use both systems.'
    gold = {'text': statement, 'evidence': [
        {'doc_id': 'd', 'page': 4, 'quote': 'Register on both systems.'},
        {'doc_id': 'd', 'page': 4, 'quote': 'Use the university system.'},
        {'doc_id': 'd', 'page': 4, 'quote': 'Use the Ministry system.'}]}
    predicted = {'text': statement, 'status': 'supported', 'citation_ids': ['page-four']}
    row = {'answerable': True, 'claims': [predicted], 'gold_claims': [gold], 'citations': [
        {'chunk_id': 'page-four', 'doc_id': 'd', 'page': 4,
         'quote': 'Register on both systems. Use the university system. Use the Ministry system.'}]}
    assert _link_counts(row, predicted, gold) == (3, 3, 3)
    assert is_grounded_answer(row)
    report = evaluate_grounding([row])
    assert report['claim_citation_precision'] == report['claim_citation_recall'] == 1.0
    partial = deepcopy(row)
    partial['citations'][0]['quote'] = 'Use the university system.'
    assert _link_counts(partial, predicted, gold) == (3, 1, 1)
    assert not is_grounded_answer(partial)
    wrong_page = deepcopy(row)
    wrong_page['citations'][0]['page'] = 5
    assert _link_counts(wrong_page, predicted, gold) == (3, 1, 0)
    duplicate = deepcopy(row)
    duplicate['citations'].append({**row['citations'][0], 'chunk_id': 'redundant'})
    duplicate['claims'][0]['citation_ids'].append('redundant')
    assert _link_counts(duplicate, duplicate['claims'][0], gold) == (3, 4, 3)
    assert evaluate_grounding([duplicate])['claim_citation_precision'] == .75


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


def test_provider_failure_is_missing_evidence_not_a_correct_abstention():
    failed = {"answerable": True, "abstained": True, "native_failure": {"error_code": "provider_timeout"},
              "gold_claims": [{"text": "MATH101 is required.", "answerable": True}]}
    valid_negative = {"answerable": False, "abstained": True, "gold_claims": [],
                      "gold_abstention_reason": "document_does_not_mention"}
    report = evaluate_grounding([failed, valid_negative])
    assert report["records"] == 1
    assert report["excluded_native_failures"] == 1
    assert report["abstention_precision"] == 1.0


def test_supported_claim_drops_irrelevant_mapped_citations():
    records = [
        RetrievalResult("support", "d", 1, "MATH101 is required.", "text", 1.0, "hybrid", {}),
        RetrievalResult("background", "d", 2, "Admissions open in September.", "text", 0.9, "hybrid", {}),
    ]
    claim = Claim("c1", "MATH101 is required.", citation_ids=("support", "background"))
    aligned = align_claims([claim], EvidenceRegistry(records), {"c1": claim.citation_ids})
    assert aligned[0].status == "supported"
    assert aligned[0].citation_ids == ("support",)


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
            "c1", "doc", 1, quote="ok", source_name="Curriculum", page_range=(1, 1), source_hash="secret"),),
        claims=(__import__("campusai.rag.claims", fromlist=["Claim"]).Claim("1", "ok", citation_ids=("c1",)),),
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
