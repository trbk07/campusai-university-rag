"""Conservative extraction of simple text-rendered PDF tables."""

from __future__ import annotations

import re

from ..schemas import Table

_COLUMN_SEPARATOR = re.compile(r"\s{2,}|\|")
_NUMBER = re.compile(r"[-+]?\(?\d[\d.,]*\)?%?")


def _split_row(line: str) -> list[str]:
    cleaned = line.strip().strip("|").strip()
    return [cell.strip() for cell in _COLUMN_SEPARATOR.split(cleaned) if cell.strip()]


def _is_candidate(line: str) -> bool:
    cells = _split_row(line)
    if len(cells) < 2:
        return False
    numeric_cells = sum(bool(_NUMBER.fullmatch(cell.replace(" ", ""))) for cell in cells)
    return "|" in line or numeric_cells >= 1


def extract_tables(pages: list[dict], doc_id: str) -> list[Table]:
    """Extract candidate tables and merge adjacent repeated-header pages.

    The extractor preserves raw cell text. Ambiguous rows are retained with a
    warning in the schema instead of being silently rewritten.
    """
    tables: list[Table] = []
    for page in pages:
        page_number = int(page["page"])
        lines = [line.strip() for line in str(page.get("text", "")).splitlines() if line.strip()]
        candidates = [line for line in lines if _is_candidate(line)]
        if len(candidates) < 2:
            continue

        rows = [_split_row(line) for line in candidates]
        width = max(len(row) for row in rows)
        warnings: list[str] = []
        if any(len(row) != width for row in rows):
            warnings.append("inconsistent_column_count")
        rows = [row + [""] * (width - len(row)) for row in rows]
        headers, body = rows[0], rows[1:]

        previous = tables[-1] if tables else None
        if previous and previous.headers == headers and previous.pages[-1] == page_number - 1:
            previous.rows.extend(body)
            previous.pages.append(page_number)
            previous.schema["pages"] = previous.pages
            previous.schema["row_count"] = len(previous.rows)
            previous.schema["warnings"] = sorted(set(previous.schema.get("warnings", []) + warnings))
            continue

        table_id = f"{doc_id}_p{page_number}_t1"
        tables.append(
            Table(
                table_id=table_id,
                doc_id=doc_id,
                pages=[page_number],
                headers=headers,
                rows=body,
                schema={
                    "columns": width,
                    "row_count": len(body),
                    "parser": "heuristic",
                    "pages": [page_number],
                    "warnings": warnings,
                    "raw_preserved": True,
                },
            )
        )
    return tables
