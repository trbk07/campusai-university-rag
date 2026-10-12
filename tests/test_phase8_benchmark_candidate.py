from __future__ import annotations

from pathlib import Path

import pytest

from evaluation.phase8.benchmark_candidate import build_candidate


ROOT = Path(__file__).resolve().parents[1]


def test_candidate_is_bounded_versionable_and_marks_prior_exposure():
    report = build_candidate(ROOT / "data/benchmark/grounding_reviewed.jsonl")

    assert report["status"] == "not_eligible_existing_data"
    assert report["gate_eligible"] is False
    assert report["benchmark"]["rows"] == 280
    assert report["benchmark"]["splits"] == {"holdout": 150, "test": 130}
    assert set(report["benchmark"]["categories"]) == {
        "answerable", "multi_evidence", "table", "document_does_not_mention",
        "no_evidence", "conflict", "ambiguous", "adversarial",
        "temporal/stale_source", "numeric_contradiction", "partial_support",
        "provider_abstention",
    }
    assert report["connected_groups"]["count"] == 1
    assert report["connected_groups"]["without_near_match_linking"]["count"] == 2
    assert report["connected_groups"]["without_near_match_linking"]["largest_group_size"] == 168
    assert report["corpus_coverage"]["documents_represented"] == 3
    assert report["corpus_coverage"]["documents_not_represented"] == 10
    assert report["corpus_coverage"]["exposure_status_of_unrepresented_sources"] == "not_audited"
    assert report["review"]["independent_reviewer_signoff"] == "missing"
    assert report["exposure"]["fresh_holdout"] is False
    assert "all_rows_form_one_connected_component" in report["phase8_exit_blockers"]
    assert "no_eligible_product_answer_baseline_bound_to_this_candidate" in report["phase8_exit_blockers"]
    alternative = report["alternative_existing_benchmark"]
    assert alternative["review_status"] == "pass"
    assert alternative["owner_review_complete"] is True
    assert alternative["independent_review_complete"] is False
    assert alternative["rows_in_test_and_holdout"] == 326
    assert alternative["connected_groups"] == 96
    assert alternative["temporal_or_comparison_tags_present"] is False
    assert alternative["prior_retrieval_report"]["reported_split_hashes_match_owner_reviewed_splits"] is False
    phase8_baseline = alternative["phase8_retrieval_baseline"]
    assert phase8_baseline["status"] == "retrieval_baseline_measured_phase8_incomplete"
    assert phase8_baseline["gate_eligible"] is False
    assert len(report["benchmark"]["source_sha256"]) == 64


def test_candidate_rejects_out_of_range_benchmark(tmp_path):
    path = tmp_path / "small.jsonl"
    path.write_text('{"id":"only","split":"test"}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="candidate size"):
        build_candidate(path)
