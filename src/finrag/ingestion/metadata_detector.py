"""Document metadata detection based on document content."""

from __future__ import annotations

import re
import unicodedata


def _repair_mojibake(value: str) -> str:
    """Best-effort repair for common UTF-8-as-Latin-1 display errors."""
    if not any(marker in value for marker in ("Ã", "Â", "â", "Ä", "á")):
        return value
    try:
        repaired = value.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value
    return repaired if repaired.count("�") <= value.count("�") else value


def _fold(value: str) -> str:
    value = _repair_mojibake(value)
    normalized = unicodedata.normalize("NFKD", value.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return normalized.replace("đ", "d")


def detect_metadata(text: str) -> dict:
    """Infer metadata and expose evidence for each inferred field."""
    low = _fold(text)
    years = sorted({int(x) for x in re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", text)})

    vi_words = re.findall(r"\b(?:doanh|thu|tai|chinh|bao|cao|hop|nhat|rieng|le|dong|trieu|ty)\b", low)
    en_words = re.findall(r"\b(?:revenue|income|financial|report|consolidated|separate|million|billion)\b", low)
    language = "vi" if len(vi_words) > len(en_words) else "en"
    language_confidence = min(0.99, 0.55 + 0.08 * abs(len(vi_words) - len(en_words)))

    units: list[str] = []
    unit_evidence: list[str] = []
    if re.search(r"\b(trieu|million)\b", low):
        units.append("million")
        unit_evidence.append("million/triệu")
    if re.search(r"\b(ty|billion)\b", low):
        units.append("billion")
        unit_evidence.append("billion/tỷ")

    currency = None
    currency_evidence: list[str] = []
    if re.search(r"(?:₫|vnd|dong)", low):
        currency, currency_evidence = "VND", ["VND/đồng"]
    elif re.search(r"(?:\$|usd|us dollars?)", low):
        currency, currency_evidence = "USD", ["USD/$"]

    consolidation = None
    consolidation_evidence: list[str] = []
    if re.search(r"\b(hop nhat|consolidated)\b", low):
        consolidation, consolidation_evidence = "consolidated", ["hợp nhất/consolidated"]
    elif re.search(r"\b(rieng le|separate)\b", low):
        consolidation, consolidation_evidence = "separate", ["riêng lẻ/separate"]

    return {
        "language": language,
        "language_confidence": language_confidence,
        "fiscal_years": years,
        "units": sorted(set(units)),
        "units_evidence": unit_evidence,
        "currency": currency,
        "currency_evidence": currency_evidence,
        "consolidation": consolidation,
        "consolidation_evidence": consolidation_evidence,
    }
