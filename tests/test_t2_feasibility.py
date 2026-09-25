import importlib.util

from scripts.benchmark_t2 import (
    _benchmark_encoder,
    benchmark_models,
    corpus_coverage,
    derive_limits,
)
from scripts.create_t2_table_review import (
    CHECK_FIELDS,
    create_review_queue,
    validate_review,
)
from scripts.validate_t2 import acceptance_errors


def test_schema_two_blocked_report_is_not_acceptance_ready():
    report = {
        "schema_version": 2,
        "environment": {},
        "fastembed": {"supported_models": ["model"]},
        "models": {"status": "blocked"},
        "limits": {"status": "insufficient_evidence"},
        "parser": [],
        "summary": {"complete": True},
    }
    errors = acceptance_errors(report)
    assert "models.status must be success" in errors
    assert "limits.status must be measured" in errors


def test_encoder_metrics_use_validator_field_names():
    class FakeEncoder:
        def encode(self, texts, **_kwargs):
            return [[0.0, 1.0, 2.0] for _ in texts]

    metrics = _benchmark_encoder(FakeEncoder(), ["a", "b"], batch_size=2, repeats=2)
    assert metrics["embedding_dimension"] == 3
    assert "dimension" not in metrics
    assert metrics["warm_p95_seconds"] >= metrics["warm_p50_seconds"]


def test_cuda_without_hardware_is_blocked_without_loading_models():
    result = benchmark_models(["course prerequisite"], device="cuda", batch_size=1, repeats=1)
    assert result["status"] == "blocked"
    if importlib.util.find_spec("torch") is None:
        assert result["reason"] == "torch_not_installed"
    else:
        assert result["reason"] in {"cuda_unavailable", "cuda_probe_failed"}


def test_corpus_coverage_exposes_all_acceptance_dimensions():
    coverage = corpus_coverage(
        [
            {"content_type": "text", "language": "vi", "tables": 1, "holdout": True},
            {"content_type": "text", "language": "en", "tables": 0},
            {"content_type": "scan_or_image"},
        ]
    )
    assert coverage == {
        "documents": 3,
        "text_documents": 2,
        "scan_or_image_documents": 1,
        "languages": ["en", "vi"],
        "has_vietnamese_text": True,
        "has_english_text": True,
        "has_scan_or_image": True,
        "has_mixed_layout": False,
        "mixed_layout_documents": 0,
        "has_tables": True,
        "table_documents": 1,
        "has_holdout": True,
    }


def test_limits_are_not_promoted_when_failure_rate_exceeds_gate():
    report = {
        "models": {"status": "blocked"},
        "parser": [
            {"status": "success", "pages": 10, "cold_seconds_per_page": 1, "cold_peak_rss_delta_mb": 1},
            {"status": "success", "pages": 20, "cold_seconds_per_page": 2, "cold_peak_rss_delta_mb": 2},
            {"status": "failed", "pages": 0},
        ],
    }
    limits = derive_limits(report, memory_budget_mb=100, concurrency=1, timeout_seconds=120)
    assert limits["status"] == "insufficient_evidence"
    assert "failure_rate" in limits["evidence"]["reason"]

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


def test_table_limit_does_not_drop_docling_review_coverage():
    review = create_review_queue(
        {
            "parser": [
                {
                    "sha256": "a",
                    "path": "a.pdf",
                    "table_inventory": [{"table_id": "t1", "pages": [1]}],
                },
                {
                    "sha256": "b",
                    "path": "b.pdf",
                    "table_inventory": [{"table_id": "t2", "pages": [1]}],
                },
            ]
        },
        max_tables=1,
    )
    assert len(review["tables"]) == 1
    assert len(review["docling_review"]["documents"]) == 2


def test_acceptance_requires_and_accepts_complete_review_evidence():
    digest = "a" * 64
    review = {
        "status": "complete",
        "tables": [{"review": {field: True for field in CHECK_FIELDS} | {"notes": "ok"}}],
    }
    report = {
        "schema_version": 2,
        "environment": {},
        "fastembed": {"supported_models": ["model"]},
        "models": {
            "status": "success",
            "dense": {
                "cold_seconds": 1,
                "warm_p50_seconds": 1,
                "warm_p95_seconds": 1,
                "peak_rss_mb": 1,
                "throughput_items_per_second": 1,
                "embedding_dimension": 3,
            },
            "reranker": {
                "cold_seconds": 1,
                "warm_p50_seconds": 1,
                "warm_p95_seconds": 1,
                "peak_rss_mb": 1,
                "throughput_pairs_per_second": 1,
            },
        },
        "limits": {
            "status": "measured",
            "evidence": {"failure_rate": 0.0},
            "limits": {"hard_max_pages": 1},
        },
        "parser": [
            {
                "path": "a.pdf",
                "file_size_bytes": 1,
                "sha256": digest,
                "status": "success",
                "pages": 1,
                "cold_parse_seconds": 1,
            }
        ],
        "summary": {
            "documents_recorded": 1,
            "successful": 1,
            "failed": 0,
            "skipped": 0,
            "complete": True,
            "coverage": {
                "has_vietnamese_text": True,
                "has_english_text": True,
                "has_scan_or_image": True,
                "has_mixed_layout": True,
                "has_tables": True,
                "has_holdout": True,
            },
        },
        "docling_review": {
            "status": "complete",
            "documents": [{"review_status": "complete"}],
        },
        "docling_comparison": {
            "status": "complete",
            "documents": [{"document": "a.pdf"}],
            "decision": {"production_parser": "pymupdf"},
        },
    }
    assert acceptance_errors(report, review) == []
