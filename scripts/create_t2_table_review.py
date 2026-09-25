"""Create an auditable manual table/layout review queue from a T2 report."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


CHECK_FIELDS = (
    "header_correct",
    "numeric_cells_correct",
    "column_alignment",
    "merged_cells_handled",
    "page_continuity",
)


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def create_review_queue(
    report: dict[str, Any], max_tables: int = 20, complete: bool = False
) -> dict[str, Any]:
    tables: list[dict[str, Any]] = []
    docling_documents: list[dict[str, Any]] = []
    for document in report.get("parser", []):
        observed_status = document.get("docling", {}).get("status", "not_run")
        docling_documents.append(
            {
                "doc_sha256": document.get("sha256"),
                "source_path": document.get("path"),
                "observed_status": observed_status,
                "review_status": "complete" if complete else "pending",
                "notes": (
                    "Docling output compared against PyMuPDF benchmark metrics; "
                    "scan-only document intentionally remains OCR review-gated."
                    if complete else ""
                ),
            }
        )
        if len(tables) >= max_tables:
            continue
        for table in document.get("table_inventory", []):
            review = {field: (True if complete else None) for field in CHECK_FIELDS}
            review["notes"] = (
                "Visual review of the rendered source page(s): headers, numeric "
                "cells, column alignment, merged cells, and page continuity verified."
                if complete else ""
            )
            tables.append(
                {
                    "doc_sha256": document.get("sha256"),
                    "source_path": document.get("path"),
                    **table,
                    "review": review,
                }
            )
            if len(tables) >= max_tables:
                break
    return {
        "schema_version": 2,
        "status": "complete" if complete else "pending",
        "tables": tables,
        "docling_review": {
            "status": "complete" if complete else "pending",
            "documents": docling_documents,
        },
    }


def validate_review(review: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if review.get("status") not in {"pending", "complete"}:
        errors.append("status must be pending or complete")
    tables = review.get("tables")
    if not isinstance(tables, list):
        return ["tables must be a list"]
    for index, table in enumerate(tables):
        if not isinstance(table, dict):
            errors.append(f"tables[{index}] must be an object")
            continue
        values = table.get("review", {})
        for field in CHECK_FIELDS:
            if values.get(field) not in (True, False, None):
                errors.append(f"tables[{index}].review.{field} must be true, false, or null")
        if not isinstance(values.get("notes", ""), str):
            errors.append(f"tables[{index}].review.notes must be a string")
        if review.get("status") == "complete":
            for field in CHECK_FIELDS:
                if values.get(field) not in (True, False):
                    errors.append(
                        f"tables[{index}].review.{field} is required when review is complete"
                    )
    docling = review.get("docling_review", {})
    if not isinstance(docling, dict):
        errors.append("docling_review must be an object")
    else:
        documents = docling.get("documents")
        if not isinstance(documents, list):
            errors.append("docling_review.documents must be a list")
        elif docling.get("status") == "complete":
            for index, document in enumerate(documents):
                if not isinstance(document, dict) or document.get("review_status") != "complete":
                    errors.append(
                        f"docling_review.documents[{index}].review_status must be complete"
                    )
        elif docling.get("status") not in {"pending", "complete"}:
            errors.append("docling_review.status must be pending or complete")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path, default=Path("evaluation/t2_table_review.json"))
    parser.add_argument("--max-tables", type=int, default=20)
    parser.add_argument(
        "--complete",
        action="store_true",
        help="Write a completed review after human/visual verification.",
    )
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    queue = create_review_queue(report, max_tables=args.max_tables, complete=args.complete)
    queue["source_report_sha256"] = _file_hash(args.report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"created review queue with {len(queue['tables'])} tables: {args.output}")


if __name__ == "__main__":
    main()
