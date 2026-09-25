"""Conservative extraction of simple text-rendered PDF tables."""

from __future__ import annotations

import re
from pathlib import Path

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
    # Document navigation often uses the same visual spacing as a table
    # (for example, "PRINCIPLE 03" or "STEP 01").  It is a layout marker,
    # not a structured row, and accepting it creates false tables.
    if cells[0].casefold() in {"principle", "step"} and len(cells) == 2:
        return False
    numeric_cells = sum(bool(_NUMBER.fullmatch(cell.replace(" ", ""))) for cell in cells)
    return "|" in line or numeric_cells >= 1


def _extract_pdfplumber(pdf_path: str | Path, doc_id: str) -> list[Table]:
    import pdfplumber

    tables: list[Table] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            for table_number, raw_table in enumerate(page.extract_tables() or [], start=1):
                rows = [["" if cell is None else str(cell).strip() for cell in row] for row in raw_table]
                rows = [row for row in rows if any(row)]
                if len(rows) < 2:
                    continue
                width = max(map(len, rows))
                rows = [row + [""] * (width - len(row)) for row in rows]
                tables.append(Table(
                    table_id=f"{doc_id}_p{page_number}_t{table_number}",
                    doc_id=doc_id,
                    pages=[page_number],
                    headers=rows[0],
                    rows=rows[1:],
                    schema={"columns": width, "row_count": len(rows) - 1,
                            "parser": "pdfplumber", "pages": [page_number],
                            "warnings": [], "raw_preserved": True},
                ))
    return tables


def extract_tables(
    pages: list[dict], doc_id: str, pdf_path: str | Path | None = None
) -> list[Table]:
    """Extract candidate tables and merge adjacent repeated-header pages.

    The extractor preserves raw cell text. Ambiguous rows are retained with a
    warning in the schema instead of being silently rewritten.
    """
    if pdf_path is not None:
        parsed = _extract_pdfplumber(pdf_path, doc_id)
        if parsed:
            # Keep the heuristic parser as a page-level fallback. pdfplumber
            # can miss a tab-aligned or merged-cell table on one page while
            # finding another table elsewhere in the document.
            parsed_pages = {page for table in parsed for page in table.pages}
            fallback = _extract_heuristic_tables(pages, doc_id)
            parsed.extend(table for table in fallback if table.pages[0] not in parsed_pages)
            return parsed
    return _extract_heuristic_tables(pages, doc_id)


def _extract_heuristic_tables(pages: list[dict], doc_id: str) -> list[Table]:
    """Extract tables from already-flattened page text as a fallback."""
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
