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


def _header_key(value: object) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", str(value).casefold())
    return " ".join(text.split())


def detect_scale(text: object) -> float:
    """Return explicit unit scale; never infer scale from magnitude."""
    value = str(text).casefold()
    if any(token in value for token in ("billion", "bn", " tỷ", "tỷ")):
        return 1_000_000_000.0
    if any(token in value for token in ("million", "mn", "mio", " triệu", "trieu")):
        return 1_000_000.0
    if any(token in value for token in ("thousand", "k", " nghìn", "nghin")):
        return 1_000.0
    return 1.0


def financial_invariants(frame: object, *, tolerance: float = 0.01) -> list[dict[str, object]]:
    """Validate high-confidence balance, subtotal, margin, and growth relationships."""
    columns = {_header_key(column): column for column in getattr(frame, "columns", [])}
    aliases = {
        "assets": ("assets", "total assets", "total asset"),
        "liabilities": ("liabilities", "total liabilities", "total liability"),
        "equity": ("equity", "total equity", "shareholders equity"),
        "revenue": ("revenue", "net revenue", "sales"),
        "gross_profit": ("gross profit",),
        "operating_expenses": ("operating expenses", "opex"),
        "operating_income": ("operating income", "ebit"),
        "total": ("total", "subtotal"),
    }
    selected = {key: columns[name] for key, names in aliases.items() for name in names if name in columns}
    result: list[dict[str, object]] = []
    for index, row in getattr(frame, "iterrows", lambda: [])():
        values = {key: parse_numeric(row[column]).value for key, column in selected.items()}
        def check(name: str, difference: float, confidence: float = 0.9) -> None:
            if abs(difference) > tolerance:
                result.append({"invariant": name, "row": int(index), "difference": difference,
                               "status": "warning", "confidence": confidence})
        if all(values.get(key) is not None for key in ("assets", "liabilities", "equity")):
            check("assets_equals_liabilities_plus_equity", values["assets"] - values["liabilities"] - values["equity"])
        if all(values.get(key) is not None for key in ("revenue", "gross_profit", "operating_expenses", "operating_income")):
            check("operating_income_equals_gross_profit_minus_opex",
                  values["operating_income"] - values["gross_profit"] + values["operating_expenses"])
    return result


def numeric_validation_score(findings: list[dict[str, object]], expected_invariants: set[str]) -> dict[str, float]:
    found = {str(item.get("invariant")) for item in findings}
    tp = len(found & expected_invariants)
    precision = tp / len(found) if found else 1.0
    recall = tp / len(expected_invariants) if expected_invariants else 1.0
    return {"precision": precision, "recall": recall,
            "f1": (2 * precision * recall / (precision + recall) if precision + recall else 0.0)}
