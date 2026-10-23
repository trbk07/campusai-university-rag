"""Resolve a narrow class of explicit date questions from table footnotes."""
from __future__ import annotations

import re
import unicodedata

from .course_credits import folded


def _requested_range(question: str) -> tuple[int, int] | None:
    text = folded(question)
    if not re.search(r"\b(?:footnote|asterisk note|starred note|chu thich|ghi chu dau sao)\b", text):
        return None
    patterns = (
        r"\b(?:institutions?|organizations?|establishments?|providers?|rows?|items?)\s+(?:numbered|nos?\.?)\s+(\d+)\s+(?:through|to|and)\s+(\d+)\b",
        r"\b(?:co so|don vi|muc|hang)\b.{0,60}\b(?:co\s+)?so thu tu\s+tu\s+(\d+)\s+den\s+(\d+)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            first, last = int(match[1]), int(match[2])
            if 1 <= first <= last <= 100:
                return first, last
    return None


def _fold_with_offsets(value: str) -> tuple[str, list[int]]:
    """Accent-fold source text while retaining offsets into the exact quote."""
    chars, offsets = [], []
    for index, character in enumerate(value):
        decomposed = unicodedata.normalize("NFD", character.casefold().replace("đ", "d"))
        for part in decomposed:
            if not unicodedata.combining(part):
                chars.append(part)
                offsets.append(index)
    return "".join(chars), offsets


def _source_match(content: str, first: int, last: int):
    normalized, offsets = _fold_with_offsets(content)
    date = r"(?P<date>\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})"
    patterns = (
        r"(?P<statement>doi\s+voi.{0,260}?cac\s+co\s+so\s+dao\s+tao\s+co\s+so\s+thu\s+tu\s+tu\s+"
        + str(first) + r"\s+den\s+" + str(last)
        + r"\s+duoc\s+cap\s+tu\s+ngay\s+" + date + r")",
        r"(?P<statement>(?:institutions?|organizations?|establishments?)\s+numbered\s+"
        + str(first) + r"\s+(?:through|to)\s+" + str(last)
        + r".{0,180}?(?:issued|granted|certified)\s+(?:from|on)?\s*" + date + r")",
    )
    for pattern in patterns:
        match = re.search(pattern, normalized, re.I | re.S)
        if match:
            start, end = match.span("statement")
            if start >= len(offsets) or end <= start:
                continue
            statement = content[offsets[start]:offsets[end - 1] + 1]
            return statement, match.group("date")
    return None


def deterministic_footnote_fact(question, results, language, *, calibrator=None):
    """Answer only when retrieved source binds the requested row range to one date."""
    requested = _requested_range(question)
    if requested is None:
        return None

    matches = []
    for result in results:
        if result.content_type != "text":
            continue
        found = _source_match(result.content, *requested)
        if found:
            matches.append((result, *found))

    if not matches:
        from .grounding import _abstention
        return _abstention("unsupported_claim", language=language)

    dates = {value for _result, _statement, value in matches}
    if len(dates) != 1:
        from .grounding import _abstention
        return _abstention("conflicting_evidence", language=language)

    from .claims import Claim
    from .confidence import score_confidence
    from .grounding import Citation, GroundedAnswer, _abstention, validate_citation
    from .source_citations import source_quote

    result, statement, date = matches[0]
    claim_dict = {"text": statement, "citation_ids": [result.chunk_id]}
    quote = source_quote(result, [claim_dict], question=question)
    if not quote or len(quote) > 1200:
        return _abstention("unsupported_claim", language=language)
    citation = Citation(result.chunk_id, result.doc_id, result.page, quote,
        " > ".join(result.metadata.get("heading_path", [])),
        str(result.metadata.get("source_name", "")),
        tuple(result.metadata.get("page_range", [result.page, result.page])),
        str(result.metadata.get("table_id", "")), str(result.metadata.get("source_hash", "")))
    if not validate_citation(citation, result, require_quote=True).valid:
        return _abstention("invalid_citation", language=language)
    answer = (f"The footnote states {date}." if language.casefold().startswith("en")
              else f"Ch\\u00fa th\\u00edch ghi ng\\u00e0y {date}.")
    claim = Claim("footnote-date", statement, "fact", 1, (result.chunk_id,),
                  "supported", 1.0, (result.chunk_id,), False)
    confidence = score_confidence(retrieval_support=max(0.0, min(1.0, float(result.score))),
        claim_entailment=1.0, citation_completeness=1.0, calibrator=calibrator)
    return GroundedAnswer(answer=answer, citations=(citation,), confidence=confidence.label,
        abstained=False, claims=(claim,), evidence_status="found",
        confidence_score=confidence.score, raw_confidence_score=confidence.raw_score,
        policy_version=confidence.policy_version)
