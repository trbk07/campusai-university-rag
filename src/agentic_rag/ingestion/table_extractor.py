"""Helpers for normalizing, validating, and serializing extracted tables."""
from pathlib import Path
import pandas as pd
from .metadata import TableRecord


def normalize_rows(rows: list[list[object | None]]) -> pd.DataFrame | None:
    """Convert pdfplumber rows to a clean DataFrame, including merged-cell blanks."""
    rows = [list(row) for row in rows if row and any(value not in (None, "") for value in row)]
    if not rows:
        return None
    width = max(len(row) for row in rows)
    padded = [row + [None] * (width - len(row)) for row in rows]
    headers = []
    for index, value in enumerate(padded[0]):
        name = " ".join(str(value or "").split()) or f"column_{index}"
        headers.append(name)
    # Make duplicate/blank headers stable instead of silently overwriting columns.
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

