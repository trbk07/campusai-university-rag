from evaluation.phase8.build_temporal_review_draft import (
    REWARDS_SHA256,
    SOURCE_SHA256,
    TRAINING_SHA256,
    build,
    render_review_packet,
    _write_generated_outputs,
)

from pathlib import Path

import pytest


def test_combined_candidate_has_source_bound_categories_and_no_group_leakage():
    temporal_rows, fact_rows, combined_rows, report = build()
    benchmark = report["benchmark"]
    supplemental = benchmark["supplemental_draft"]
    facts = benchmark["factual_supplemental_draft"]

    assert len(temporal_rows) == 20
    assert len(fact_rows) == 10
    assert len(combined_rows) == 300
    assert all(row["split"] == "holdout" for row in temporal_rows)
    assert all(row["source_document_sha256"] == SOURCE_SHA256 for row in temporal_rows)
    assert all(row["source_review_status"] == "draft_pending_owner_review" for row in temporal_rows)
    assert all(row["gold_answer"] and row["gold_claims"] for row in temporal_rows)
    assert all(row["gold_answer"] == row["expected_claims"][0]["adjusted_course_code"]
               for row in temporal_rows if "adjusted_course_code" in row["expected_claims"][0])
    assert all("mã trước và mã sau" not in row["question"].lower()
               for row in temporal_rows)
    semester_rows = [row for row in combined_rows if "-semester-" in row["qid"]]
    assert semester_rows
    for row in semester_rows:
        claim = row["gold_claims"][0]["text"]
        assert f"semester {row['expected_claims'][0]['semester']}" in claim
        assert "credits" not in claim
    assert all(row["gold_claims"][0]["evidence"][0]["quote"] for row in temporal_rows)
    assert sum("temporal" in row["tags"] for row in temporal_rows) == 20
    assert sum("comparison" in row["tags"] for row in temporal_rows) == 19
    assert supplemental["owner_review"] == "pending"
    exposure = supplemental["exposure_audit"]
    assert exposure["status"] == "historical_content_overlap_detected_regression_only"
    assert exposure["files_scanned"] > 0
    assert exposure["records_scanned"] > 0
    assert exposure["provider_egress_logs_audited"] is False
    assert exposure["correction_facts_with_any_prior_code_overlap"] == 13
    assert exposure["correction_fact_count"] == 20

    assert all(row["source_review_status"] == "draft_pending_owner_review" for row in fact_rows)
    assert {row["source_document_sha256"] for row in fact_rows} == {REWARDS_SHA256, TRAINING_SHA256}
    assert all(row["tags"] == ["fact", "single_hop"] for row in fact_rows)
    assert {row["split"] for row in fact_rows} == {"test", "holdout"}
    assert all(row["gold_claims"][0]["evidence"][0]["quote"] for row in fact_rows)
    assert facts["owner_review"] == "pending"
    assert facts["provider_egress_logs_audited"] is False
    assert facts["fresh_validation"] is False

    assert benchmark["combined_split_counts_if_adopted"] == {"holdout": 160, "test": 140}
    assert benchmark["combined_selected_ids_sha256"] == (
        "2e36cfdb7f605b8f57a99d20ea33a619b95e977dcff69e4d35d5f0a2deac2796"
    )
    assert len(benchmark["excluded_historical_qids"]) == 10
    assert report["connected_groups_if_combined"]["count"] == 117
    assert report["connected_groups_if_combined"]["largest_group_size"] == 22
    assert report["connected_groups_if_combined"]["cross_split_group_count"] == 0
    assert report["connected_groups_if_combined"]["cross_split_groups"] == []

    coverage = benchmark["query_type_coverage_if_combined"]
    assert coverage["single_hop_fact"]["count"] == 10
    assert coverage["table_or_calculation"]["count"] == 135
    assert coverage["prerequisite_or_multi_hop"]["count"] == 33
    assert coverage["temporal_or_comparison"]["count"] == 20
    assert coverage["unanswerable_or_adversarial"]["count"] == 155
    assert benchmark["missing_required_query_categories"] == []
    assert "required_query_type_coverage_incomplete" not in report["phase8_exit_blockers"]
    assert report["status"] == "draft_pending_owner_review_and_provider_exposure_audit"
    assert report["gate_eligible"] is False


def test_owner_review_packet_binds_drafts_and_discloses_regression_only():
    temporal_rows, fact_rows, _combined, report = build()
    packet = render_review_packet(
        temporal_rows, fact_rows, report,
        temporal_sha256="a" * 64,
        factual_sha256="b" * 64,
    )

    assert "OWNER REVIEW REQUIRED" in packet
    assert "a" * 64 in packet and "b" * 64 in packet
    assert SOURCE_SHA256 in packet
    assert "Historical exact-code overlap in temporal draft: 13/20" in packet
    assert "Do not call this fresh validation." in packet
    assert packet.count("Decision: [ ] Accept  [ ] Reject") == 30
    assert report["benchmark"]["combined_selected_ids_sha256"] in packet
    assert "Connected groups / largest / cross-split: `117` / `22` / `0`" in packet
    assert "Missing required query types: `none`" in packet
    assert "All 30 rows reviewed" in packet
    assert "Overall decision: [ ] Accept for regression benchmark" in packet


def test_regeneration_refuses_to_overwrite_owner_review_edits(tmp_path):
    edited_packet = tmp_path / "owner-review.md"
    generated_candidate = tmp_path / "candidate.jsonl"
    edited_packet.write_bytes(b"reviewer note and signature")
    generated_candidate.write_bytes(b"old candidate")

    with pytest.raises(FileExistsError, match="refusing to overwrite changed Phase 8 artifacts"):
        _write_generated_outputs([
            (generated_candidate, b"new candidate"),
            (edited_packet, b"unreviewed template"),
        ])

    assert generated_candidate.read_bytes() == b"old candidate"
    assert edited_packet.read_bytes() == b"reviewer note and signature"
