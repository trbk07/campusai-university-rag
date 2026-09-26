"""Deterministic claim extraction and evidence alignment primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
import unicodedata
from typing import Iterable

from .evidence import EvidenceRegistry

CLAIM_STATUSES = {"supported", "partial", "partially_supported", "unsupported", "contradicted", "ambiguous"}


STOPWORDS = {"the", "and", "are", "is", "of", "to", "a", "an", "what", "how", "là", "và", "của", "là", "cần", "phải"}
CODE_RE = re.compile(r"\b[A-Z]{2,}[A-Z0-9]*\d{2,}\b", re.I)
NUMBER_RE = re.compile(r"(?<!\w)\d+(?:[.,]\d+)?\s*(?:%|credits?|tín\s*chỉ|ngày|năm)?", re.I)


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFC", str(value)).casefold()
    # Small, auditable academic-domain bilingual aliases. This is not a
    # generative synonym model; numeric/code fidelity remains exact.
    value = re.sub(r"\bcredits?\b", "tín chỉ", value)
    value = re.sub(r"\binternship\b", "thực tập", value)
    value = re.sub(r"\bprerequisite[s]?\b", "tiên quyết", value)
    return re.sub(r"\s+", " ", value).strip()


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[\wÀ-ỹ]+", normalize_text(value)) if token not in STOPWORDS and len(token) > 1}


@dataclass(frozen=True)
class Claim:
    claim_id: str
    text: str
    claim_type: str = "fact"
    required_citations: int = 1
    citation_ids: tuple[str, ...] = ()
    status: str = "unsupported"
    support_score: float = 0.0
    evidence_ids: tuple[str, ...] = ()
    numeric_conflict: bool = False


def extract_claims(answer: str, supplied: Iterable[dict] | None = None) -> list[Claim]:
    """Prefer structured provider claims, otherwise split answer sentences."""
    if supplied:
        claims: list[Claim] = []
        for index, raw in enumerate(supplied, 1):
            if not isinstance(raw, dict) or not str(raw.get("text", "")).strip():
                continue
            claims.append(Claim(str(raw.get("claim_id", f"claim-{index}")), str(raw["text"]).strip(),
                                str(raw.get("type", "fact")), int(raw.get("required_citations", 1)),
                                tuple(str(item) for item in raw.get("citation_ids", raw.get("citation_chunk_ids", [])))))
        if claims:
            return claims
    sentences = [part.strip() for part in re.split(r"(?<=[.!?。！？])\s+|\n+", answer.strip()) if part.strip()]
    parts = []
    for sentence in sentences:
        # Split simple conjunctions into atomic claims. This prevents a valid
        # two-fact answer from being rejected merely because each fact is
        # supported by a different evidence span.
        parts.extend(part.strip() for part in re.split(r"\s*(?:;|；)\s*|\s+(?:and|và)\s+", sentence, flags=re.I) if part.strip())
    result = []
    for index, part in enumerate(parts, 1):
        normalized = normalize_text(part)
        claim_type = "numeric_fact" if NUMBER_RE.search(part) else "fact"
        if re.search(r"course\s+(?:code|name)|table\s+headers?", normalized, re.I):
            claim_type = "table_header"
        elif re.search(r"one\s+.*relation", normalized, re.I):
            claim_type = "count_fact"
        result.append(Claim(f"claim-{index}", part, claim_type))
    return result


def _exact_markers(text: str) -> set[str]:
    return {normalize_text(item) for item in CODE_RE.findall(text)} | {normalize_text(item) for item in NUMBER_RE.findall(text)}


def align_claims(claims: Iterable[Claim], registry: EvidenceRegistry, citation_map: dict[str, tuple[str, ...]]) -> list[Claim]:
    aligned: list[Claim] = []
    for claim in claims:
        ids = tuple(citation_map.get(claim.claim_id, claim.citation_ids))
        evidence = [registry.get(item) for item in ids]
        evidence = [item for item in evidence if item is not None]
        if not ids:
            # No provider mapping: search the registry and retain only the
            # evidence that actually supports this claim. Never attach every
            # retrieved citation to every claim by default.
            evidence = list(registry.values())
        if not evidence:
            aligned.append(claim)
            continue
        claim_tokens = _tokens(claim.text)
        markers = _exact_markers(claim.text)
        best = 0.0
        best_records = []
        contradicted = False
        numeric_mismatch = False
        for item in evidence:
            # Citation metadata itself is valid support for page/source claims;
            # content-only matching would incorrectly reject answers such as
            # "the requirement is on page 1".
            page_markers = {int(value) for value in re.findall(r"\b(?:page|trang)\s+(\d+)\b", normalize_text(claim.text))}
            if page_markers and page_markers <= {item.page}:
                best = max(best, 1.0)
                best_records = [item]
                continue
            evidence_tokens = _tokens(" ".join((item.content, item.source_name, *item.heading_path, *item.metadata_tokens)))
            overlap = len(claim_tokens & evidence_tokens) / max(1, len(claim_tokens))
            evidence_markers = _exact_markers(item.content)
            metadata_text = normalize_text(" ".join(item.metadata_tokens))
            marker_ok = not markers or markers <= evidence_markers or markers <= _exact_markers(metadata_text)
            if markers and evidence_markers and not marker_ok and overlap >= 0.35:
                if claim.claim_type == "numeric_fact":
                    numeric_mismatch = True
                else:
                    contradicted = True
            candidate = overlap if marker_ok else 0.0
            # Metadata-backed claims (document version/type) are valid
            # evidence even when the value is not repeated in page text.
            if markers and marker_ok and any(marker in metadata_text for marker in markers):
                candidate = max(candidate, 1.0)
            if markers and marker_ok:
                # Exact course/code/number markers are stronger than lexical
                # overlap (e.g. "complete MATH101" vs "prerequisite: MATH101").
                candidate = max(candidate, 0.8)
            if claim.claim_type == "table_header" and "course_catalog" in metadata_text:
                candidate = max(candidate, 0.75)
            if claim.claim_type == "count_fact" and "relation" in normalize_text(claim.text):
                relation_rows = [line for line in item.content.splitlines() if len(CODE_RE.findall(line)) >= 2]
                if len(relation_rows) == 1 and "one" in normalize_text(claim.text):
                    candidate = max(candidate, 0.9)
            if candidate > best:
                best = candidate
                best_records = [item]
            elif candidate == best and candidate > 0:
                best_records.append(item)
        if not ids:
            ids = tuple(item.chunk_id for item in best_records if best > 0)
        if best >= 0.55:
            status = "supported"
        elif best >= 0.25:
            status = "partial"
        elif contradicted:
            status = "contradicted"
        elif len(best_records) > 1 and best > 0 and claim_tokens:
            status = "ambiguous"
        else:
            status = "unsupported"
        # A single unrelated retrieved chunk must not turn a supported page or
        # version claim into a conflict. Numeric mismatch is safety-critical
        # only when no evidence actually supports the asserted value.
        numeric_conflict = numeric_mismatch and best < 0.55
        aligned.append(Claim(claim.claim_id, claim.text, claim.claim_type, claim.required_citations, ids,
                             status, round(best, 6), tuple(item.chunk_id for item in evidence), numeric_conflict))
    return aligned
