"""Regression fixtures only; these tests create no official review evidence."""
from copy import deepcopy
import json

from campusai.llm.client import GeminiClient, LLMProviderError
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.service import CampusAIQueryService
from evaluation.grounding.collect_native_predictions import collect, inference_request, prepare_egress
from evaluation.grounding.repair_benchmark import grouped_split, load_rows
from evaluation.grounding.review_evidence import validate_independent_review
from evaluation.grounding.validate_grounding_release import validate
from tests.test_basic_rag import FakeRetriever, evidence, valid_payload


def test_release_rejects_gold_copied_into_legacy_question_topic_suffix():
    from evaluation.benchmarks.benchmark_schema import disclosed_gold_claims, validate_release_records
    row = {"id": "copied-answer", "split": "dev", "question":
           "What does page 1 state? TOPIC : document_name The admission code is ABC.",
           "language": "en", "category": "answerable", "answerable": True,
           "expected_status": "found", "gold_claims": [{"claim_id": "c1", "text": "The admission code is ABC.",
                "evidence": [{"doc_id": "source", "page": 1, "quote": "The admission code is ABC."}]}],
           "gold_abstention_reason": None}
    assert disclosed_gold_claims(row) == ["c1"]
    assert "row_0_gold_disclosed_in_question" in validate_release_records([row])


def test_normal_fact_check_or_topic_scope_does_not_count_as_disclosed_gold():
    from evaluation.benchmarks.benchmark_schema import disclosed_gold_claims
    claim = {"claim_id": "c1", "text": "CS101 is a prerequisite of CS201."}
    assert not disclosed_gold_claims({"question": "Is CS101 a prerequisite of CS201?", "gold_claims": [claim]})
    assert not disclosed_gold_claims({"question": "Which course comes first? Topic: prerequisites", "gold_claims": [claim]})


def test_original_gold_disclosure_is_measured_without_mutating_benchmark():
    from pathlib import Path
    from evaluation.benchmarks.benchmark_schema import disclosed_gold_claims
    rows = load_rows(Path("data/benchmark/grounding_reviewed.jsonl"))
    before = deepcopy(rows)
    assert sum(bool(disclosed_gold_claims(row)) for row in rows) == 213
    assert rows == before


def test_grouped_split_is_deterministic_preserves_gold_and_discloses_infeasibility():
    from pathlib import Path
    rows = load_rows(Path("data/benchmark/grounding_reviewed.jsonl"))
    original = deepcopy(rows)
    candidate, report = grouped_split(rows)
    reversed_candidate, reversed_report = grouped_split(list(reversed(rows)))
    assert candidate == reversed_candidate and report == reversed_report
    assert rows == original
    assert {row["id"]: row["gold_claims"] for row in candidate} == {row["id"]: row["gold_claims"] for row in original}
    assert report["cross_split_family_leakage"] == 0
    assert len(report["connected_components"]) == 1
    assert not report["minimums_feasible"] and not report["fresh_holdout_restored"]
    assert len(candidate) == 400
    assert all(row["review_status"] == "review_required" and not row["official_evaluation_eligible"] for row in candidate)


def test_runtime_boundary_never_uses_gold_labels_expected_sources_or_split():
    row = {"question": "Which course?", "language": "en", "selected_doc_ids": ["declared"],
           "gold_answer": "POISON_GOLD_900", "gold_claims": [{"text": "POISON_GOLD_901"}],
           "expected_evidence": ["POISON_EVIDENCE"], "source_group": "GOLD_DOCUMENT", "split": "holdout",
           "answerable": True, "category": "adversarial", "expected_output": "POISON_EXPECTED"}
    assert inference_request(row) == {"question": "Which course?", "language": "en", "doc_ids": ["declared"]}


def test_collector_captures_provider_text_without_gold_injection_and_enforces_cap(tmp_path):
    from campusai.llm import client as client_module
    previous_transport = client_module._request_json
    llm = GeminiClient(api_key="unit-test-placeholder", max_retries=0, cache=None)
    service = CampusAIQueryService(FakeRetriever([evidence()]), GroundedAnswerGenerator(llm))
    prompts = []
    provider_payload = valid_payload()
    provider_payload["citations"] = [{"chunk_id": "c1", "page": 3, "quote": "MATH101 is required."}]
    def transport(request, *_args, **_kwargs):
        prompts.append(request.data.decode())
        return {"candidates": [{"content": {"parts": [{"text": json.dumps(provider_payload)}]}}],
                "modelVersion": "unit-test-only"}
    rows = [{"id": str(i), "question": f"Which prerequisite course? {i}", "language": "en",
             "gold_answer": "POISON_GOLD", "expected_evidence": "POISON_SOURCE",
             "category": "POISON_CATEGORY"} for i in range(2)]
    try:
        report = collect(service, rows, llm, max_provider_calls=1, output=tmp_path / "run", transport=transport)
        assert report["provider_posts"] == 1
        assert report["real_model_outputs_successful"] == 1
        assert report["official_predictions"] == 0
        assert report["stop_reason"] == "provider_call_cap"
        assert all("POISON" not in prompt for prompt in prompts)
        raw = load_rows(tmp_path / "run/raw-model.jsonl")
        assert raw[0]["model_version"] == "unit-test-only"
        assert raw[0]["raw_model_text"] == json.dumps(provider_payload)
        assert client_module._request_json is previous_transport
    finally:
        service.close()


def test_native_failure_is_retained_and_does_not_trigger_another_question(tmp_path):
    from campusai.llm import client as client_module
    previous_transport = client_module._request_json
    llm = GeminiClient(api_key="unit-test-placeholder", max_retries=0, cache=None)
    service = CampusAIQueryService(FakeRetriever([evidence()]), GroundedAnswerGenerator(llm))
    def transport(*_args, **_kwargs):
        raise LLMProviderError("unit-test failure")
    try:
        report = collect(service, [{"id": str(i), "question": "Which prerequisite course?", "language": "en"}
                                   for i in range(3)], llm, max_provider_calls=3,
                         output=tmp_path / "run", transport=transport)
        assert report["provider_posts"] == 1 and report["pipeline_predictions"] == 1
        assert report["real_model_outputs_successful"] == 0
        assert report["stop_reason"] == "provider_failure"
        assert load_rows(tmp_path / "run/raw-model.jsonl")[0]["success"] is False
        assert client_module._request_json is previous_transport
    finally:
        service.close()


def test_legacy_reviewed_flags_and_ai_annotations_do_not_supply_human_signoff():
    rows = [{"id": "fixture-row", "review_status": "reviewed", "annotator_id": "engineering-review-1"}]
    assert validate_independent_review(None, rows) == ["independent_annotation_signoff_missing"]
    assert "independent_human_approval_missing" in validate_independent_review(
        {"status": "approved", "review_type": "ai_review", "row_decisions": []}, rows)
    assert "independent_annotation_signoff_missing" in validate({"rows": rows, "metrics": {}})


def test_egress_preparation_never_calls_provider_or_creates_predictions(tmp_path):
    llm = GeminiClient(api_key="unit-test-placeholder", max_retries=0, cache=None)
    service = CampusAIQueryService(FakeRetriever([evidence()]), GroundedAnswerGenerator(llm))
    def no_inference(*_args, **_kwargs):
        raise AssertionError("preflight must never generate model text")
    llm.generate = no_inference
    try:
        packet = prepare_egress(service, [{"id": "fixture-only", "question": "Which prerequisite course?", "language": "en"}],
                                llm, tmp_path / "egress", 1)
        assert len(packet["cases"]) == 1 and packet["provider_posts"] == 0
        assert packet["model_predictions"] == 0
        assert not (tmp_path / "egress/predictions.jsonl").exists()
    finally:
        service.close()


def test_egress_payload_drift_stops_before_transport(tmp_path):
    llm = GeminiClient(api_key="unit-test-placeholder", max_retries=0, cache=None)
    service = CampusAIQueryService(FakeRetriever([evidence()]), GroundedAnswerGenerator(llm))
    def never_transport(*_args, **_kwargs):
        raise AssertionError("payload drift must never send")
    try:
        report = collect(service, [{"id": "fixture-only", "question": "Which prerequisite course?", "language": "en"}],
            llm, max_provider_calls=1, output=tmp_path / "run", transport=never_transport,
            egress_prompts={"fixture-only": "wrong-prompt-hash"})
        assert report["provider_posts"] == 0 and report["real_model_outputs_successful"] == 0
        assert report["stop_reason"] == "provider_failure"
    finally:
        service.close()


def test_scoring_refuses_gold_fixture_capture_before_reading_predictions(tmp_path):
    import pytest
    from evaluation.grounding.score_native_predictions import score
    (tmp_path / "run.json").write_text('{"generation_kind":"gold_fixture","gold_seeded":true}', encoding="utf-8")
    with pytest.raises(ValueError, match="never gold fixtures"):
        score(tmp_path / "unused-benchmark", tmp_path, tmp_path)


def test_review_evidence_rejects_legacy_blanket_approval_without_row_decisions():
    from tests.test_grounding_package import approved_signoff
    errors = validate_independent_review(approved_signoff(), [{"id": "fixture-only"}])
    assert "independent_human_approval_missing" in errors
    assert "independent_row_decisions_missing" in errors


def test_package_annotation_scale_uses_actual_population_above_minimum():
    from tests.test_grounding_package import approved_signoff
    from evaluation.release.grounding_package import validate_annotation_signoff
    value = approved_signoff()
    for field in ("records_total", "records_reviewed", "records_approved"):
        value[field] = 680
    value["reviewers"][0]["records_reviewed"] = 680
    assert validate_annotation_signoff(value, "bench") == []


def test_independent_review_binds_benchmark_rows_and_holdout_exposure():
    from evaluation.grounding.review_evidence import annotation_sha256
    from evaluation.grounding.repair_benchmark import stable_hash
    # Fictional unit fixture; never written as an approval artifact.
    rows = [{"id": "unit-only", "question": "Unit?", "split": "holdout", "gold_claims": []}]
    value = {"status": "approved", "review_type": "independent_human", "benchmark_sha256": "unit-benchmark",
        "records_total": 1, "records_reviewed": 1, "records_approved": 1,
        "creator_ids": ["unit-creator"], "reviewers": [{"id": "unit-reviewer", "reviewer_type": "human",
            "independent": True, "attestation": "Fictional fixture only", "signed_at": "2026-10-16"}],
        "exposure_review": {"status": "approved", "holdout_fresh": True,
            "holdout_ids_sha256": stable_hash(["unit-only"]), "reviewer_id": "unit-reviewer",
            "signed_at": "2026-10-16", "evidence_reference": "fictional-unit-fixture"},
        "row_decisions": [{"id": "unit-only", "status": "approved", "reviewer_id": "unit-reviewer",
            "signed_at": "2026-10-16", "annotation_sha256": annotation_sha256(rows[0])}]}
    assert validate_independent_review(value, rows, benchmark_sha256="unit-benchmark") == []
    assert "independent_review_benchmark_checksum_mismatch" in validate_independent_review(
        value, rows, benchmark_sha256="different-benchmark")
    stale = deepcopy(value)
    stale["exposure_review"]["holdout_fresh"] = False
    assert "independent_holdout_exposure_review_missing_or_stale" in validate_independent_review(stale, rows)
    changed = deepcopy(rows)
    changed[0]["question"] = "Changed?"
    assert "independent_row_decision_unapproved_or_stale" in validate_independent_review(value, changed)


def test_release_rejects_paraphrase_and_evidence_source_leakage_despite_authored_labels():
    from evaluation.benchmarks.benchmark_schema import validate_release_records
    from tests.test_benchmark_schema import row
    records = []
    for split, question in (("dev", "What does page 1 state?"), ("test", "Which source page contains this statement?")):
        record = row(split, split=split)
        record.update(question=question, source_group=split, template_group=split,
                      semantic_topic=split, adversarial_pattern=split)
        record["gold_claims"][0]["evidence"][0]["doc_id"] = "shared-actual-source"
        records.append(record)
    errors = validate_release_records(records)
    assert "derived_source_family_cross_split_leakage_shared-actual-source" in errors
    assert "derived_intent-paraphrase_family_cross_split_leakage_page-statement-source-lookup" in errors


def test_regrouped_exposed_holdout_is_not_eligible_for_release():
    from evaluation.benchmarks.benchmark_schema import validate_release_records
    from tests.test_benchmark_schema import row
    record = row("unit-only", split="holdout")
    record.update(fresh_holdout=False, exposure_status="previously_exposed", official_evaluation_eligible=False)
    errors = validate_release_records([record])
    assert "row_0_holdout_previously_exposed" in errors
    assert "row_0_official_evaluation_ineligible" in errors


def test_uploaded_document_wrapper_cannot_hide_the_same_query_template():
    from evaluation.benchmarks.families import question_template
    assert question_template("Use only the uploaded dev.pdf. What is the quota?") == question_template(
        "Use only the uploaded holdout.pdf. What is the quota?") == "what is the quota?"
    assert question_template("Chỉ dùng tài liệu đã tải lên test.pdf. Quy định này có hiệu lực khi nào?") == question_template(
        "Chỉ dùng tài liệu đã tải lên holdout.pdf. Quy định này có hiệu lực khi nào?")


def test_topic_suffix_casing_and_spacing_cannot_hide_duplicate_templates():
    from evaluation.benchmarks.families import question_template
    for suffix in ("Topic: source-a", "topic: source-b", "TOPIC: source-c", "Topic : source-d"):
        assert question_template("What does page 3 state? " + suffix) == "what does page <n> state?"


def test_negative_selected_scope_is_an_observable_source_family():
    from evaluation.benchmarks.benchmark_schema import validate_release_records
    from tests.test_benchmark_schema import row
    records = []
    for split in ("dev", "holdout"):
        item = row(f"unit-{split}", split=split)
        item.update(question=f"Distinct {split} request", answerable=False, gold_claims=[],
                    gold_abstention_reason="document_does_not_mention", expected_status="document_does_not_mention",
                    source_group=f"authored-{split}", selected_doc_ids=["actual-selected-document"])
        records.append(item)
    assert "derived_source_family_cross_split_leakage_actual-selected-document" in validate_release_records(records)
