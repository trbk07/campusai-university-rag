"""Validate a Task 2 feasibility report and its acceptance evidence."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any


DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_RESULT = {"path", "file_size_bytes", "sha256", "status"}
VALID_STATUSES = {"success", "failed", "skipped"}
VALID_MODEL_STATUSES = {"not_run", "blocked", "failed", "skipped", "success"}
VALID_LIMIT_STATUSES = {"insufficient_evidence", "measured"}
REQUIRED_COVERAGE = (
    "has_vietnamese_text",
    "has_english_text",
    "has_scan_or_image",
    "has_mixed_layout",
    "has_tables",
    "has_holdout",
)
REVIEW_FIELDS = (
    "header_correct",
    "numeric_cells_correct",
    "column_alignment",
    "merged_cells_handled",
    "page_continuity",
)


def _number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and value >= 0
    )


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _review_is_complete(review: Any) -> bool:
    if not isinstance(review, dict) or review.get("status") != "complete":
        return False
    tables = review.get("tables")
    if not isinstance(tables, list) or not tables:
        return False
    for table in tables:
        values = table.get("review") if isinstance(table, dict) else None
        if not isinstance(values, dict):
            return False
        if any(values.get(field) not in (True, False) for field in REVIEW_FIELDS):
            return False
    return True


def _docling_review_is_complete(review: Any) -> bool:
    if not isinstance(review, dict) or review.get("status") != "complete":
        return False
    documents = review.get("documents")
    return isinstance(documents, list) and bool(documents) and all(
        isinstance(document, dict) and document.get("review_status") == "complete"
        for document in documents
    )


def acceptance_errors(
    report: dict[str, Any], review: dict[str, Any] | None = None
) -> list[str]:
    """Return evidence gaps; valid blocked runs are not acceptance evidence."""

    if report.get("schema_version") != 2:
        return ["acceptance requires schema_version 2"]

    errors: list[str] = []
    errors.extend(f"schema: {error}" for error in validate(report))
    summary = report.get("summary")
    if not isinstance(summary, dict) or summary.get("complete") is not True:
        errors.append("summary.complete must be true")

    models = report.get("models")
    if not isinstance(models, dict) or models.get("status") != "success":
        errors.append("models.status must be success")
    else:
        metric_errors: list[str] = []
        _validate_model_metrics(models, metric_errors)
        errors.extend(f"acceptance: {error}" for error in metric_errors)

    fastembed = report.get("fastembed")
    if not isinstance(fastembed, dict) or not fastembed.get("supported_models"):
        errors.append("fastembed supported_models evidence is required")

    limits = report.get("limits")
    if not isinstance(limits, dict) or limits.get("status") != "measured":
        errors.append("limits.status must be measured")
    elif not isinstance(limits.get("limits"), dict):
        errors.append("measured limits require limits.limits")
    else:
        evidence = limits.get("evidence")
        failure_rate = evidence.get("failure_rate") if isinstance(evidence, dict) else None
        if not _number(failure_rate) or failure_rate > 0.05:
            errors.append("limits evidence failure_rate must be <= 0.05")

    coverage = summary.get("coverage") if isinstance(summary, dict) else None
    if not isinstance(coverage, dict):
        errors.append("summary.coverage evidence is required")
    else:
        for field in REQUIRED_COVERAGE:
            if coverage.get(field) is not True:
                errors.append(f"coverage.{field} must be true")

    review = review if review is not None else report.get("table_review")
    external_docling_review = review.get("docling_review") if isinstance(review, dict) else None
    docling_review = report.get("docling_review") or external_docling_review
    if not _docling_review_is_complete(docling_review):
        errors.append("docling_review.status must be complete")

    comparison = report.get("docling_comparison")
    if not isinstance(comparison, dict) or comparison.get("status") != "complete":
        errors.append("docling_comparison.status must be complete")
    elif not isinstance(comparison.get("documents"), list) or not comparison["documents"]:
        errors.append("docling_comparison.documents evidence is required")
    decision = comparison.get("decision") if isinstance(comparison, dict) else None
    if not isinstance(decision, dict) or not decision.get("production_parser"):
        errors.append("docling_comparison.decision is required")

    if not _review_is_complete(review):
        errors.append("table review must be complete for every sampled table")
    return errors


def _validate_model_metrics(models: dict[str, Any], errors: list[str]) -> None:
    status = models.get("status")
    if status not in VALID_MODEL_STATUSES:
        errors.append(f"invalid model status: {status!r}")
    if status != "success":
        return

    for name in ("dense", "reranker"):
        metrics = models.get(name)
        if not isinstance(metrics, dict):
            errors.append(f"models.{name} metrics are required when models succeeds")
            continue
        fields = (
            "cold_seconds",
            "warm_p50_seconds",
            "warm_p95_seconds",
            "peak_rss_mb",
        )
        fields += (
            "throughput_items_per_second",
            "embedding_dimension",
        ) if name == "dense" else ("throughput_pairs_per_second",)
        for field in fields:
            if not _number(metrics.get(field)):
                errors.append(
                    f"models.{name}.{field} must be a non-negative number"
                )
        if name == "dense" and not _positive_int(metrics.get("embedding_dimension")):
            errors.append("models.dense.embedding_dimension must be a positive integer")
        if (
            _number(metrics.get("warm_p50_seconds"))
            and _number(metrics.get("warm_p95_seconds"))
            and metrics["warm_p95_seconds"] < metrics["warm_p50_seconds"]
        ):
            errors.append(f"models.{name} warm_p95_seconds must be >= warm_p50_seconds")


def validate(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    schema_version = report.get("schema_version")
    if schema_version not in {1, 2}:
        errors.append("schema_version must be 1 or 2")
    if not isinstance(report.get("environment"), dict):
        errors.append("environment is required")

    rows = report.get("parser")
    if not isinstance(rows, list):
        return errors + ["parser must be a list"]

    seen: set[Any] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"parser[{index}] must be an object")
            continue
        missing = REQUIRED_RESULT - row.keys()
        if missing:
            errors.append(f"parser[{index}] missing {sorted(missing)}")

        digest = row.get("sha256")
        try:
            if digest in seen:
                errors.append(f"duplicate sha256 at parser[{index}]")
            seen.add(digest)
        except TypeError:
            errors.append(f"parser[{index}] sha256 must be hashable")
        if schema_version == 2 and (
            not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest)
        ):
            errors.append(
                f"parser[{index}] sha256 must be 64 lowercase hex characters"
            )
        file_size = row.get("file_size_bytes")
        if not isinstance(file_size, int) or isinstance(file_size, bool) or file_size < 0:
            errors.append(
                f"parser[{index}] file_size_bytes must be non-negative integer"
            )
        if row.get("status") not in VALID_STATUSES:
            errors.append(f"invalid status at parser[{index}]")
        if row.get("status") == "success":
            elapsed = row.get("cold_parse_seconds", row.get("seconds"))
            if not _positive_int(row.get("pages")) or not _number(elapsed):
                errors.append(f"invalid success metrics at parser[{index}]")

    summary = report.get("summary", {})
    if not isinstance(summary, dict):
        errors.append("summary is required")
    else:
        expected = {
            "documents_recorded": len(rows),
            "successful": sum(
                isinstance(row, dict) and row.get("status") == "success"
                for row in rows
            ),
            "failed": sum(
                isinstance(row, dict) and row.get("status") == "failed"
                for row in rows
            ),
            "skipped": sum(
                isinstance(row, dict) and row.get("status") == "skipped"
                for row in rows
            ),
        }
        fields = expected if schema_version == 2 else {"documents_recorded": len(rows)}
        for field, value in fields.items():
            if summary.get(field) != value:
                errors.append(f"summary {field} mismatch")
        if schema_version == 2 and not isinstance(summary.get("complete"), bool):
            errors.append("summary.complete must be boolean")

    models = report.get("models")
    if not isinstance(models, dict):
        errors.append("models is required")
    else:
        _validate_model_metrics(models, errors)

    if schema_version == 2:
        fastembed = report.get("fastembed")
        if not isinstance(fastembed, dict):
            errors.append("fastembed is required in schema 2")
        elif not isinstance(fastembed.get("supported_models"), list):
            errors.append("fastembed.supported_models must be a list")
        limits = report.get("limits")
        if not isinstance(limits, dict):
            errors.append("limits is required in schema 2")
        else:
            status = limits.get("status")
            if status not in VALID_LIMIT_STATUSES:
                errors.append(f"invalid limits status: {status!r}")
            if status == "measured" and not isinstance(limits.get("limits"), dict):
                errors.append("measured limits require limits.limits")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path", type=Path, nargs="?", default=Path("evaluation/t2_results.json")
    )
    parser.add_argument("--acceptance", action="store_true")
    parser.add_argument("--review", type=Path)
    args = parser.parse_args()

    report = json.loads(args.path.read_text(encoding="utf-8"))
    errors = validate(report)
    if args.acceptance:
        review = (
            json.loads(args.review.read_text(encoding="utf-8"))
            if args.review
            else None
        )
        errors.extend(acceptance_errors(report, review))
    if errors:
        raise SystemExit("\n".join(errors))
    print("acceptance-ready Task 2 report" if args.acceptance else "valid Task 2 report")


if __name__ == "__main__":
    main()
