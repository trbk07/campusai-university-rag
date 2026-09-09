"""Helpers for normalizing, validating, and serializing extracted tables."""
from pathlib import Path
import pandas as pd
from .metadata import TableRecord
from .numeric import financial_invariants, numeric_diagnostics


def _clean_rows(rows: list[list[object | None]]) -> list[list[str | None]]:
    return [[None if value is None else " ".join(str(value).split()) for value in row]
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
    # Invariants are evaluated only after normalization, never used to rewrite raw cells.
    frame = normalize_rows(cleaned)
    result["financial_invariants"] = financial_invariants(frame) if frame is not None else []
    return result


def normalize_rows(rows: list[list[object | None]]) -> pd.DataFrame | None:
    """Normalize ragged, merged, repeated-header, and nested-table-like rows safely."""
    rows = _clean_rows(rows)
    if not rows:
        return None
    width = max(len(row) for row in rows)
    padded = [row + [None] * (width - len(row)) for row in rows]
    headers = [" ".join(str(value or "").split()) or f"column_{index}"
               for index, value in enumerate(padded[0])]
    seen: dict[str, int] = {}
    unique_headers = []
    for header in headers:
        count = seen.get(header, 0)
        unique_headers.append(header if count == 0 else f"{header}_{count}")
        seen[header] = count + 1
    frame = pd.DataFrame(padded[1:], columns=unique_headers)
    frame = frame.dropna(axis=0, how="all").dropna(axis=1, how="all").reset_index(drop=True)
    return frame if not frame.empty else None


def save_table(record: TableRecord, output_dir: str | Path) -> Path:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{record.table_id}.csv"
    record.dataframe.to_csv(path, index=False)
    return path


def table_schema(frame: pd.DataFrame) -> dict[str, str]:
    return {str(column): str(dtype) for column, dtype in frame.dtypes.items()}

