from evaluation.grounding import validate_grounding_release


def test_runtime_report_rechecks_embedded_dataset_rows(monkeypatch):
    seen = {}

    def fake_validate(rows):
        seen["rows"] = rows
        return []

    monkeypatch.setattr(validate_grounding_release, "validate_release_records", fake_validate)
    report = {
        "mode": "runtime",
        "benchmark_sha256": "benchmark-hash",
        "metadata": {"commit": "commit-hash"},
        "dataset": {"sha256": "benchmark-hash"},
        "dataset_count": 1,
        "rows": [{"id": "row-1", "review_status": "reviewed"}],
        "metrics": {},
    }

    errors = validate_grounding_release.validate(report)

    assert "dataset_count_rows_mismatch" not in errors
    assert not any(error.startswith("dataset_row_") for error in errors)
    assert seen["rows"] == report["rows"]
