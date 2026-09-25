"""Detect deterministic, auditable metadata for university documents."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime


def _repair_mojibake(value: str) -> str:
    """Repair common UTF-8-as-Latin-1 display errors before matching."""
    if not any(marker in value for marker in ("Ãƒ", "Ã‚", "Ã¢", "Ã„", "Ã¡")):
        return value
    try:
        repaired = value.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value
    return repaired if repaired.count("ï¿½") <= value.count("ï¿½") else value


def _fold(value: str) -> str:
    value = _repair_mojibake(value)
    normalized = unicodedata.normalize("NFKD", value.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return normalized.replace("đ", "d").replace("Ä‘", "d")


def _first_match(patterns: list[str], text: str) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = " ".join(match.group(1).split()).strip(" -:;,.\t")
            if value:
                return value
    return None


def _iso_date(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(
        r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b|\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b",
        value,
    )
    if not match:
        month_names = {
            "january": 1, "jan": 1, "february": 2, "feb": 2,
            "march": 3, "mar": 3, "april": 4, "apr": 4,
            "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
            "august": 8, "aug": 8, "september": 9, "sep": 9,
            "october": 10, "oct": 10, "november": 11, "nov": 11,
            "december": 12, "dec": 12,
        }
        named = re.search(r"\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b", value)
        vietnamese = re.search(r"\bngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})\b", value, re.IGNORECASE)
        if vietnamese:
            try:
                return datetime.strptime(
                    f"{vietnamese.group(1)}/{vietnamese.group(2)}/{vietnamese.group(3)}", "%d/%m/%Y"
                ).date().isoformat()
            except ValueError:
                return None
        if not named or named.group(2).casefold() not in month_names:
            return None
        try:
            return datetime(
                int(named.group(3)), month_names[named.group(2).casefold()], int(named.group(1))
            ).date().isoformat()
        except ValueError:
            return None
    try:
        if match.group(1):
            return datetime.strptime(
                f"{match.group(1)}/{match.group(2)}/{match.group(3)}", "%d/%m/%Y"
            ).date().isoformat()
        return datetime.strptime(
            f"{match.group(4)}-{match.group(5)}-{match.group(6)}", "%Y-%m-%d"
        ).date().isoformat()
    except ValueError:
        return None


def _extract_entities(text: str, years: list[int]) -> dict[str, object]:
    """Extract labelled entities; absent evidence is deliberately ``None``."""
    institution = _first_match(
        [
            r"(?:institution|university|school|trường(?:\s+đại\s+học)?|đơn vị)\s*[:\-]\s*([^\n]+)",
            r"((?:trường\s+đại\s+học|đại học)\s+[^\n,;]+)",
            r"((?:[A-ZĐ][\wÀ-ỹ]+\s+){1,6}(?:University|College))",
        ],
        text,
    )
    program = _first_match(
        [
            r"(?:program|programme|chương trình(?: đào tạo)?)\s*[:\-]\s*([^\n,;]+)",
            r"(?:ngành|major)\s*[:\-]\s*([^\n,;]+)",
        ],
        text,
    )
    course = _first_match(
        [r"(?:course code|course|mã học phần|học phần)\s*[:\-]\s*([A-ZĐ][A-Z0-9._-]{2,})"],
        text,
    )
    if course is None:
        codes = re.findall(r"\b[A-Z]{2,}[A-Z0-9-]*\d{2,4}\b", text)
        course = codes[0] if codes else None
    version = _first_match(
        [r"(?:version|revision|phiên bản|lần ban hành)\s*[:#\-]?\s*([^\n,;]+)"], text
    )
    effective_raw = _first_match(
        [r"(?:effective date|effective from|ngày hiệu lực|có hiệu lực từ|ban hành ngày)\s*[:\-]?\s*([^\n,;]+)"],
        text,
    )
    effective_date = _iso_date(effective_raw)
    if effective_date is None:
        nearby = re.search(
            r"(?:effective|hiệu lực).{0,50}?(\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        effective_date = _iso_date(nearby.group(1) if nearby else None)
    issue_raw = _first_match(
        [r"(?:issue date|issued|ngày ban hành|ban hành ngày)\s*[:\-]?\s*([^\n,;]+)"],
        text,
    )
    issue_date = _iso_date(issue_raw)
    faculty = _first_match(
        [r"(?:faculty|school|khoa|viện)\s*[:\-]\s*([^\n,;]+)"], text
    )
    course_code = course if course and re.fullmatch(r"[A-ZĐ][A-Z0-9._-]{2,}", course) else None
    return {
        "institution": institution,
        "faculty": faculty,
        "program": program,
        "course": course,
        "course_code": course_code,
        "version": version,
        "effective_date": effective_date,
        "issue_date": issue_date,
        "academic_year": years[0] if len(years) == 1 else None,
    }


def detect_metadata(text: str) -> dict:
    """Infer academic metadata without asking an LLM to guess properties."""
    low = _fold(text)
    years = sorted({int(x) for x in re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", text)})
    vi_words = re.findall(
        r"\b(?:quy|che|dinh|chuong|trinh|hoc|phan|sinh|vien|ky|tin|chi|phi|dieu|kien|dang|ky|mon|nganh|dao|tao)\b",
        low,
    )
    en_words = re.findall(
        r"\b(?:regulation|policy|curriculum|course|student|semester|prerequisite|credit|tuition|academic|enrollment|syllabus|handbook)\b",
        low,
    )
    language = "vi" if len(vi_words) > len(en_words) else "en"
    language_confidence = min(0.99, 0.55 + 0.08 * abs(len(vi_words) - len(en_words)))
    academic_patterns = {
        "regulation": r"\b(quy che|quy dinh|regulation|policy)\b",
        "curriculum": r"\b(chuong trinh dao tao|curriculum|study plan)\b",
        "syllabus": r"\b(de cuong|syllabus|course outline)\b",
        "handbook": r"\b(cam nang|handbook|student guide)\b",
        "course_catalog": r"\b(danh muc hoc phan|course catalog|course catalogue)\b",
        "academic_notice": r"\b(thong bao|announcement|academic notice)\b",
    }
    scores: dict[str, int] = {}
    evidence: list[str] = []
    for candidate, pattern in academic_patterns.items():
        count = len(re.findall(pattern, low))
        if count:
            scores[candidate] = count
            evidence.append(candidate)
    document_type = (
        max(scores, key=lambda item: (scores[item], -list(academic_patterns).index(item)))
        if scores
        else "unknown"
    )
    semesters = sorted(
        {
            value
            for value in (
                re.findall(r"\b(?:hk|hoc ky|semester|term)\s*([123])\b", low)
                + re.findall(r"\b(fall|spring|summer|autumn)\b", low)
            )
        }
    )
    semesters.extend(
        str(index)
        for index, roman in enumerate(("i", "ii", "iii"), start=1)
        if re.search(rf"\b(?:hoc ky|semester)\s+{roman}\b", low)
    )
    semesters = sorted(set(semesters))
    academic_years = sorted(
        set(
            years
            + [
                int(start)
                for start in re.findall(r"\b((?:19|20)\d{2})\s*[-/]\s*(?:19|20)?\d{2}\b", text)
            ]
        )
    )
    units: list[str] = []
    unit_evidence: list[str] = []
    if re.search(r"\b(tin chi|credit|credits)\b", low):
        units.append("credit")
        unit_evidence.append("credit/tin chi")
    if re.search(r"\b(trieu|million)\b", low):
        units.append("million")
        unit_evidence.append("million/trieu")
    if re.search(r"\b(ty|billion)\b", low):
        units.append("billion")
        unit_evidence.append("billion/ty")
    currency = None
    currency_evidence: list[str] = []
    if re.search(r"(?:₫|đ|vnd|dong)", low):
        currency, currency_evidence = "VND", ["VND/dong"]
    elif re.search(r"(?:\$|usd|us dollars?)", low):
        currency, currency_evidence = "USD", ["USD/$"]
    is_academic = document_type != "unknown" or bool(semesters) or bool(
        re.search(r"\b(quy che|quy dinh|chuong trinh|hoc phan|sinh vien|hoc ky|regulation|curriculum|course|student|semester|prerequisite|tuition)\b", low)
    )
    entities = _extract_entities(text, academic_years)
    academic_metadata = {
        "institution": entities["institution"],
        "faculty": entities["faculty"],
        "program": entities["program"],
        "course": entities["course"],
        "course_code": entities["course_code"],
        "academic_year": entities["academic_year"],
        "academic_years": academic_years,
        "version": entities["version"],
        "effective_date": entities["effective_date"],
        "issue_date": entities["issue_date"],
    }
    document_type_confidence = min(0.99, 0.55 + 0.12 * max(scores.values(), default=0)) if document_type != "unknown" else 0.0
    field_values = {
        "institution": entities["institution"],
        "faculty": entities["faculty"],
        "program": entities["program"],
        "course": entities["course"],
        "course_code": entities["course_code"],
        "version": entities["version"],
        "effective_date": entities["effective_date"],
        "issue_date": entities["issue_date"],
        "language": language,
    }
    metadata_evidence = {
        field: {
            "value": value,
            "confidence": 0.9 if value is not None else 0.0,
            "evidence": None,
        }
        for field, value in field_values.items()
    }
    # Preserve a short, auditable source snippet without storing the entire PDF.
    for field, value in field_values.items():
        if value is None:
            continue
        match = re.search(re.escape(str(value)), text, re.IGNORECASE)
        if match:
            start = max(0, match.start() - 80)
            metadata_evidence[field]["evidence"] = text[start : match.end() + 80].strip()
    return {
        "domain": "academic" if is_academic else "general",
        "language": language,
        "language_confidence": language_confidence,
        "document_type": document_type,
        "document_type_evidence": evidence,
        "document_type_confidence": document_type_confidence,
        "academic_years": academic_years,
        "years": years,
        "semesters": semesters,
        "units": sorted(set(units)),
        "units_evidence": unit_evidence,
        "currency": currency,
        "currency_evidence": currency_evidence,
        "institution": entities["institution"],
        "faculty": entities["faculty"],
        "program": entities["program"],
        "course": entities["course"],
        "course_code": entities["course_code"],
        "version": entities["version"],
        "effective_date": entities["effective_date"],
        "issue_date": entities["issue_date"],
        "metadata_evidence": metadata_evidence,
        **{f"{field}_confidence": item["confidence"] for field, item in metadata_evidence.items()},
        **{f"{field}_evidence": item["evidence"] for field, item in metadata_evidence.items()},
        "academic_metadata": academic_metadata,
    }
