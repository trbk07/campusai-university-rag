from scripts.validate_t2 import validate
from scripts.create_t2_table_review import CHECK_FIELDS, create_review_queue, validate_review

def test_t2_report_validator_accepts_valid_report():
    report = {"schema_version": 1, "environment": {"python": "3.14"}, "models": {"status": "skipped"}, "parser": [{"path": "a.pdf", "file_size_bytes": 1, "sha256": "a", "status": "success", "pages": 1, "seconds": 0.1}], "summary": {"documents_recorded": 1}}
    assert validate(report) == []

def test_t2_report_validator_rejects_duplicate_and_bad_status():
    report = {"schema_version": 1, "environment": {}, "models": {}, "parser": [{"path": "a", "file_size_bytes": 1, "sha256": "x", "status": "success", "pages": 1, "seconds": 1}, {"path": "b", "file_size_bytes": 1, "sha256": "x", "status": "bad"}], "summary": {"documents_recorded": 2}}
    errors = validate(report)
    assert any("duplicate" in error for error in errors)
    assert any("invalid status" in error for error in errors)


def test_schema_two_requires_evidence_sections():
    report = {
        "schema_version": 2,
        "environment": {},
        "models": {"status": "blocked"},
        "parser": [],
        "summary": {"documents_recorded": 0},
    }
    errors = validate(report)
    assert any("fastembed" in error for error in errors)
    assert any("limits" in error for error in errors)


def test_table_review_queue_has_explicit_manual_checklist():
    review = create_review_queue(
        {
            "parser": [
                {
                    "sha256": "abc",
                    "path": "report.pdf",
                    "table_inventory": [{"table_id": "t1", "pages": [2]}],
                }
            ]
        }
    )
    assert set(review["tables"][0]["review"]) == {*CHECK_FIELDS, "notes"}
    assert validate_review(review) == []
