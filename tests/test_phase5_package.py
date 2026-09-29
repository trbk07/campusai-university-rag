from evaluation.phase5_package import _require_pass, validate_annotation_signoff


def approved_signoff():
    return {
        "status": "approved", "benchmark_sha256": "bench",
        "records_total": 400, "records_reviewed": 400, "records_approved": 400,
        "split_leakage": 0, "missing_gold_evidence": 0, "missing_abstention_reason": 0,
        "creator_ids": ["builder-1"],
        "reviewers": [{"id": "reviewer-2", "independent": True, "records_reviewed": 400,
                       "attestation": "I independently reviewed the frozen benchmark.",
                       "signed_at": "2026-09-30T00:00:00Z"}],
    }


def test_independent_annotation_signoff_passes_complete_attestation():
    assert validate_annotation_signoff(approved_signoff(), "bench") == []


def test_annotation_signoff_rejects_self_review_and_checksum_change():
    value = approved_signoff()
    value["reviewers"][0]["id"] = "builder-1"
    errors = validate_annotation_signoff(value, "different")
    assert "annotation_creator_reviewer_overlap" in errors
    assert "annotation_benchmark_checksum_mismatch" in errors


def test_boolean_evidence_gate_does_not_treat_false_as_numeric_zero_pass():
    errors = _require_pass({"status": "pass", "safe": False}, "security", ("safe",))
    assert errors == ["security_safe_not_pass"]
