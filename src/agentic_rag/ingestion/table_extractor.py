"""Helpers for normalizing, validating, and serializing extracted tables."""
from pathlib import Path
import pandas as pd
from .metadata import TableRecord
from .numeric import financial_invariants, numeric_diagnostics
from .text_normalization import normalize_extracted_text, mojibake_score


def _looks_like_mojibake(value: object) -> bool:
    return mojibake_score(str(value or "")) > 0


def _clean_rows(rows: list[list[object | None]]) -> list[list[str | None]]:
    return [[None if value is None else normalize_extracted_text(str(value))[0] for value in row]
            for row in rows if row and any(value not in (None, "") for value in row)]


def table_diagnostics(rows: list[list[object | None]]) -> dict[str, object]:
    """Describe ambiguous headers without mutating extracted cell values."""
    cleaned = _clean_rows(rows)
    if not cleaned:
        return {"raw_rows": 0, "header_rows": 0, "merged_cell_suspected": False, "duplicate_headers": []}
    width = max(map(len, cleaned))
    padded = [row + [None] * (width - len(row)) for row in cleaned]
    first = [str(value or "") for value in padded[0]]
    duplicate_headers = sorted({value for value in first if value and first.count(value) > 1})
    nonempty = [sum(value is not None for value in row) for row in padded[: min(3, len(padded))]]
    header_rows = 2 if len(nonempty) > 1 and nonempty[0] < max(nonempty[1:]) else 1
    result = {"raw_rows": len(cleaned), "raw_columns": width, "header_rows": header_rows,
              "merged_cell_suspected": bool(duplicate_headers or any(value is None for value in padded[0])),
              "duplicate_headers": duplicate_headers}
    result.update(numeric_diagnostics(padded))
    headers, _ = _flatten_headers(padded)
    result["single_column"] = width == 1
    result["generated_columns"] = [header for header in headers if header.startswith("column_")]
    result["mojibake_detected"] = any(_looks_like_mojibake(value) for row in padded for value in row)
    # Invariants are evaluated only after normalization, never used to rewrite raw cells.
    frame = normalize_rows(cleaned)
    result["financial_invariants"] = financial_invariants(frame) if frame is not None else []
    reasons: list[str] = []
    if result["single_column"]:
        reasons.append("single_column")
    if result["merged_cell_suspected"]:
        reasons.append("merged_or_ambiguous_header")
    if result["generated_columns"]:
        reasons.append("generated_columns")
    if result["duplicate_headers"]:
        reasons.append("duplicate_headers")
    if result.get("numeric_unparsed", 0):
        reasons.append("numeric_unparsed")
    if result["financial_invariants"]:
        reasons.append("invariant_failure")
    if result["mojibake_detected"]:
        reasons.append("mojibake")
    result["review_reasons"] = reasons
    result["quality_score"] = table_quality_score(result)
    result["review_required"] = result["quality_score"] < 0.75
    result["status"] = "review_required" if result["review_required"] else ("warning" if result["financial_invariants"] else "ok")
    return result


def _header_text(value: object | None) -> str:
    return " ".join(str(value or "").split())


def _flatten_headers(padded: list[list[object | None]]) -> tuple[list[str], int]:
    """Build stable headers from one or two header rows without inventing cell values.

    Financial PDFs commonly render a grouped header once and leave the following
    cells blank.  We carry labels only into the column name (never into data
    cells), preserving the raw table in diagnostics for review.
    """
    if not padded:
        return [], 0
    width = len(padded[0])
    header_rows = 2 if len(padded) > 1 and sum(v not in (None, "") for v in padded[0]) < sum(v not in (None, "") for v in padded[1]) else 1
    labels: list[str] = []
    for column in range(width):
        parts = []
        for row in range(header_rows):
            value = _header_text(padded[row][column])
            if value and (not parts or value.casefold() != parts[-1].casefold()):
                parts.append(value)
        labels.append(" | ".join(parts) or f"column_{column}")
    return labels, header_rows


def normalize_rows(rows: list[list[object | None]]) -> pd.DataFrame | None:
    """Normalize ragged, merged, repeated-header, and nested-table-like rows safely."""
    rows = _clean_rows(rows)
    if not rows:
        return None
    width = max(len(row) for row in rows)
    padded = [row + [None] * (width - len(row)) for row in rows]
    headers, header_rows = _flatten_headers(padded)
    seen: dict[str, int] = {}
    unique_headers = []
    for header in headers:
        count = seen.get(header, 0)
        unique_headers.append(header if count == 0 else f"{header}_{count}")
        seen[header] = count + 1
    frame = pd.DataFrame(padded[header_rows:], columns=unique_headers)
    frame = frame.dropna(axis=0, how="all").dropna(axis=1, how="all").reset_index(drop=True)
    return frame if not frame.empty else None


def table_quality_score(diagnostics: dict[str, object]) -> float:
    """Return a conservative 0..1 review score for routing difficult tables."""
    candidates = int(diagnostics.get("numeric_candidates", 0) or 0)
    unparsed = int(diagnostics.get("numeric_unparsed", 0) or 0)
    score = 1.0
    if diagnostics.get("merged_cell_suspected"):
        score -= 0.25
    if diagnostics.get("single_column") or diagnostics.get("mojibake_detected"):
        score -= 0.35
    if diagnostics.get("generated_columns"):
        score -= 0.2
    if diagnostics.get("duplicate_headers"):
        score -= 0.15
    if candidates:
        score -= 0.35 * (unparsed / candidates)
    if diagnostics.get("financial_invariants"):
        score -= 0.15
    return round(max(0.0, min(1.0, score)), 4)


def save_table(record: TableRecord, output_dir: str | Path) -> Path:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{record.table_id}.csv"
    record.dataframe.to_csv(path, index=False, encoding="utf-8")
    return path


def table_schema(frame: pd.DataFrame) -> dict[str, str]:
    return {str(column): str(dtype) for column, dtype in frame.dtypes.items()}

