"""Safety regressions for the independently audited Phase 5 contract."""

from copy import deepcopy
import math

import pytest

from campusai.rag.calibration import IsotonicCalibrator
from campusai.rag.confidence import calibration_metrics, score_confidence
from campusai.rag.grounding import GroundedAnswerGenerator, validate_citation, validate_quote
from campusai.rag.schemas import validate_response, validate_release_response
from campusai.rag.evidence import EvidenceRegistry
from evaluation.grounding.grounding_metrics import evaluate_grounding
from tests.test_grounding_adversarial import valid_payload, result
from tests.test_grounding import LLM


@pytest.mark.parametrize("field,value", [
    ("confidence", []), ("schema_version", {}), ("abstention_reason", []),
    ("confidence_score", "high"), ("confidence_score", float("nan")),
    ("claims", {}),
])
def test_invalid_types_are_validation_errors(field, value):
    payload = valid_payload()
    payload[field] = value
    assert not validate_response(payload)[0]
    assert not validate_release_response(payload)[0]


@pytest.mark.parametrize("mutation", [
    lambda p: p["citations"][0].update(chunk_id=[]),
    lambda p: p["citations"][0].update(page=True, page_range=[True, True]),
    lambda p: p["citations"][0].update(quote="  "),
    lambda p: p["claims"][0].update(citation_ids=[{}]),
    lambda p: p["claims"][0].update(citation_ids=None),
    lambda p: p["claims"][0].update(claim_id=""),
    lambda p: p["claims"].append(deepcopy(p["claims"][0])),
    lambda p: p.update(claims=[], citations=[]),
    lambda p: p.update(abstained=True, abstention_reason="unsupported_claim"),
])
def test_strict_public_schema_rejects_invalid_provenance_and_claims(mutation):
    payload = valid_payload()
    mutation(payload)
    assert not validate_release_response(payload)[0]


@pytest.mark.parametrize("page", [True, 2.0, "2"])
def test_citation_page_is_not_coerced(page):
    assert not validate_citation({"chunk_id": "c1", "page": page}, result()).valid


@pytest.mark.parametrize("quote,content", [
    ("3 tín chỉ", "3 credits"), ("CS201 CS101", "CS201-CS101"),
    ("internship", "thực tập"), ("cs201", "CS201"),
])
def test_quote_fidelity_is_not_semantic_normalization(quote, content):
    assert not validate_quote(quote, content)


def test_quote_fidelity_accepts_only_nfc_and_whitespace_normalization():
    assert validate_quote("tín chỉ", "ti\u0301n\nchỉ")


@pytest.mark.parametrize("field,value", [
    ("abstained", "false"), ("abstained", None),
    ("claims", {"text": "fact"}),
])
def test_malformed_provider_cannot_publish(field, value):
    payload = valid_payload()
    payload[field] = value
    assert GroundedAnswerGenerator(LLM(payload)).answer(
        "How many credits does CS201 require in 2025?", [result()], "en").abstained


@pytest.mark.parametrize("value", [None, {}, [], True, "many", float("nan")])
def test_malformed_claim_requirement_cannot_crash_generator(value):
    payload = valid_payload()
    payload["claims"][0]["required_citations"] = value
    answer = GroundedAnswerGenerator(LLM(payload)).answer(
        "How many credits does CS201 require in 2025?", [result()], "en")
    assert answer.abstained


def test_ece_does_not_count_lower_bins_twice():
    assert calibration_metrics([0.1, 0.9], [False, True])["ece"] == 0.1


@pytest.mark.parametrize("score", [float("nan"), float("inf"), -0.1, 1.1])
def test_calibration_metrics_reject_invalid_probability(score):
    with pytest.raises(ValueError):
        calibration_metrics([score], [True])


def test_isotonic_fit_averages_equal_scores():
    calibrator = IsotonicCalibrator.fit([0.5, 0.5], [False, True])
    assert calibrator.predict(0.5) == 0.5


def test_confidence_cannot_turn_nan_into_high_confidence():
    with pytest.raises(ValueError):
        score_confidence(retrieval_support=math.nan, claim_entailment=1,
                         citation_completeness=1)


def test_matching_gold_id_does_not_establish_claim_truth():
    metrics = evaluate_grounding([{
        "id": "row", "answerable": True, "abstained": False,
        "claims": [{"claim_id": "q1", "text": "CS201 requires 999 credits.",
                    "status": "supported", "citation_ids": ["c1"]}],
        "citations": [{"chunk_id": "c1", "doc_id": "d", "page": 1}],
        "gold_claims": [{"claim_id": "q1", "text": "CS201 requires 3 credits.",
                         "evidence": [{"chunk_id": "c1", "doc_id": "d", "page": 1}]}],
    }])
    assert metrics["grounded_claim_precision"] == 0
    assert metrics["unsupported_claim_leakage"] == 1


def test_matched_gold_claim_count_is_scoped_to_each_question():
    rows = [{
        "id": str(index), "answerable": True, "abstained": False,
        "claims": [{"claim_id": "q1", "text": "3 credits", "status": "supported",
                    "citation_ids": ["c1"]}],
        "citations": [{"chunk_id": "c1", "doc_id": "d", "page": 1}],
        "gold_claims": [{"claim_id": "q1", "text": "3 credits",
                         "evidence": [{"chunk_id": "c1", "doc_id": "d", "page": 1}]}],
    } for index in range(2)]
    assert evaluate_grounding(rows)["matched_gold_claim_count"] == 2


def test_conflicting_chunk_identity_never_silently_overwrites_evidence():
    first, second = result(), result("CS201 requires 99 credits.")
    with pytest.raises(ValueError, match="chunk identity"):
        EvidenceRegistry([first, second])
    answer = GroundedAnswerGenerator(LLM(valid_payload())).answer("CS201 credits?", [first, second])
    assert answer.abstained and answer.reason == "invalid_citation"


@pytest.mark.parametrize("value", [None, True, "22", [2], [2, 0], [True, 2], {}, [3, 2]])
def test_malformed_evidence_range_fails_closed(value):
    item = result()
    item.metadata["page_range"] = value
    answer = GroundedAnswerGenerator(LLM(valid_payload())).answer("CS201 credits?", [item])
    assert answer.abstained and answer.reason == "invalid_citation"


def test_missing_gold_claims_remain_in_citation_recall_denominator():
    row = {"answerable": True, "abstained": True, "claims": [], "citations": [],
           "gold_claims": [{"text": "3 credits", "evidence": [{"doc_id": "d", "page": 1}]}]}
    metrics = evaluate_grounding([row])
    assert metrics["citation_recall"] == 0
    assert metrics["citation_completeness"] == 0
    assert metrics["denominators"]["gold_citation_links"] == 1


def test_provider_cannot_assert_document_absence_from_top_k():
    from campusai.rag.abstention import canonicalize_abstention_reason
    assert canonicalize_abstention_reason("retrieval_below_threshold", evidence_found=True) == "no_evidence_found"
    payload = {"answer": "Absent", "citations": [], "confidence": "low", "abstained": True,
               "abstention_reason": "document_does_not_mention"}
    generator = GroundedAnswerGenerator(LLM(payload))
    answer = generator.answer("Does the document mention scholarships?", [result()], "en")
    assert answer.reason == "unsupported_claim"
    assert "not enough evidence" in answer.answer
    verified = generator.answer("Does the document mention scholarships?", [result()], "en",
                                verified_document_absence=True)
    assert verified.reason == "document_does_not_mention"


@pytest.mark.parametrize("payload", [None, [], {"metrics": []}, {"metrics": {"citation_precision": float("nan")}}])
def test_release_report_validator_fails_closed_for_bad_types(payload):
    from evaluation.grounding.validate_grounding_release import validate
    assert validate(payload)


def test_calibration_is_not_applied_twice_to_runtime_scores():
    from evaluation.grounding.calibrate_confidence import evaluate_calibrator
    calibrator = IsotonicCalibrator((0.5, 1.0), (0.2, 0.6))
    confidence = score_confidence(retrieval_support=1, claim_entailment=1,
                                 citation_completeness=1, calibrator=calibrator)
    assert confidence.raw_score == 1
    assert confidence.score == 0.6
    metrics = evaluate_calibrator([{"split": "holdout", "abstained": False, "answerable": True,
        "confidence_score": confidence.score, "raw_confidence_score": confidence.raw_score}], calibrator)
    assert metrics["holdout"]["brier_score"] == 0.16


def test_split_specific_group_names_cannot_hide_same_question_template():
    from evaluation.benchmarks.benchmark_schema import validate_release_records
    from tests.test_benchmark_schema import row
    records = []
    for split, page in (("dev", 1), ("test", 2), ("holdout", 3)):
        record = row(split, split=split)
        record.update(question=f"What does page {page} state? Topic: {split} source",
                      source_group=split, template_group=f"{split}-template",
                      semantic_topic=split, adversarial_pattern=split)
        records.append(record)
    assert any(error.startswith("derived_template_cross_split_leakage")
               for error in validate_release_records(records))
