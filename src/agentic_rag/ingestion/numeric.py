"""Locale-aware, lossless numeric parsing for financial table cells."""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class NumericValue:
    raw: str
    value: float | None
    is_percent: bool = False
    scale: float = 1.0
    status: str = "parsed"


_MISSING = {"", "-", "—", "–", "n/a", "na", "nm", "null", "none"}


def parse_numeric(value: object) -> NumericValue:
    raw = "" if value is None else str(value).strip()
    if raw.casefold() in _MISSING:
        return NumericValue(raw, None, status="missing")
    text = raw.replace("\u00a0", " ").strip()
    percent = text.endswith("%")
    if percent:
        text = text[:-1].strip()
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1].strip()
    text = re.sub(r"[^0-9,.'+\-]", "", text)
    if not re.search(r"\d", text):
        return NumericValue(raw, None, is_percent=percent, status="unparsed")
    if "," in text and "." in text:
        text = text.replace(",", "") if text.rfind(".") > text.rfind(",") else text.replace(".", "").replace(",", ".")
    elif "," in text:
        parts = text.split(",")
        text = "".join(parts) if len(parts[-1]) == 3 and len(parts) > 1 else ".".join(parts)
    elif text.count(".") > 1:
        text = text.replace(".", "")
    try:
        number = float(text)
    except ValueError:
        return NumericValue(raw, None, is_percent=percent, status="unparsed")
    if negative:
        number = -abs(number)
    return NumericValue(raw, number, is_percent=percent)


def numeric_diagnostics(rows: list[list[object | None]]) -> dict[str, object]:
    parsed = [parse_numeric(value) for row in rows for value in row]
    candidates = [item for item in parsed if item.status != "missing"]
    return {"numeric_candidates": len(candidates),
            "numeric_parsed": sum(item.value is not None for item in candidates),
            "numeric_unparsed": sum(item.value is None for item in candidates)}


def financial_invariants(frame: object, *, tolerance: float = 0.01) -> list[dict[str, object]]:
    """Check only explicit, high-confidence financial column relationships."""
    columns = {str(column).casefold().strip(): column for column in getattr(frame, "columns", [])}
    result: list[dict[str, object]] = []
    aliases = {"assets": ("assets", "total assets"),
               "liabilities": ("liabilities", "total liabilities"),
               "equity": ("equity", "total equity")}
    selected = {}
    for key, names in aliases.items():
        for name in names:
            if name in columns:
                selected[key] = columns[name]
                break
    if len(selected) == 3:
        for index, row in frame.iterrows():
            values = {key: parse_numeric(row[column]).value for key, column in selected.items()}
            if all(value is not None for value in values.values()):
                difference = values["assets"] - values["liabilities"] - values["equity"]
                if abs(difference) > tolerance:
                    result.append({"invariant": "assets_equals_liabilities_plus_equity",
                                   "row": int(index), "difference": difference,
                                   "status": "warning", "confidence": 0.9})
    return result
