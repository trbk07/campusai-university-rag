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


def create_review_queue(report: dict[str, Any], max_tables: int = 20) -> dict[str, Any]:
    tables: list[dict[str, Any]] = []
    for document in report.get("parser", []):
        for table in document.get("table_inventory", []):
            review = {field: None for field in CHECK_FIELDS}
            review["notes"] = ""
            tables.append(
                {
                    "doc_sha256": document.get("sha256"),
                    "source_path": document.get("path"),
                    **table,
                    "review": review,
                }
            )
            if len(tables) >= max_tables:
                return {"schema_version": 1, "status": "pending", "tables": tables}
    return {"schema_version": 1, "status": "pending", "tables": tables}


def validate_review(review: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    tables = review.get("tables")
    if not isinstance(tables, list):
        return ["tables must be a list"]
    for index, table in enumerate(tables):
        values = table.get("review", {})
        for field in CHECK_FIELDS:
            if values.get(field) not in (True, False, None):
                errors.append(f"tables[{index}].review.{field} must be true, false, or null")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path, default=Path("evaluation/t2_table_review.json"))
    parser.add_argument("--max-tables", type=int, default=20)
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    queue = create_review_queue(report, max_tables=args.max_tables)
    queue["source_report_sha256"] = _file_hash(args.report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"created review queue with {len(queue['tables'])} tables: {args.output}")


if __name__ == "__main__":
    main()
