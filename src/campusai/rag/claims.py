"""Deterministic claim extraction and evidence alignment primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
import unicodedata
from typing import Iterable

from .evidence import EvidenceRecord, EvidenceRegistry
from .course_credits import course_credit_support
from .credit_sum import credit_sum_claim_support, credit_difference_claim_support
from ..retrieval.tokenizer_vi import repair_mojibake

CLAIM_STATUSES = {"supported", "partial", "partially_supported", "unsupported", "contradicted", "ambiguous"}


STOPWORDS = {"the", "and", "are", "is", "of", "to", "a", "an", "what", "how", "là", "và", "của", "là", "cần", "phải"}
CODE_RE = re.compile(r"\b[A-Z]{2,}[A-Z0-9]*\d{2,}\b", re.I)
NUMBER_RE = re.compile(r"(?<!\w)\d+(?:[.,]\d+)?\s*(?:%|credits?|tín\s*chỉ|ngày|năm)?", re.I)
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
DATE_RE = re.compile(r"\b(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4})\b")
POSITIVE_POLARITY_RE = re.compile(
    r"\b(?:require(?:s|d)?|must|is\s+required|bắt\s+buộc|bat\s+buoc|phải|cần)\b", re.I
)
NEGATIVE_POLARITY_RE = re.compile(
    r"\b(?:not\s+(?:require(?:d|s)?|mandatory|required)|không\s+(?:bắt\s+buộc|bat\s+buoc|cần)|khong\s+(?:bat\s+buoc|can))\b",
    re.I,
)
MINIMUM_QUALIFIER_RE = re.compile(
    r"\b(?:at\s+least|minimum|min\.?|tối\s+thiểu|ít\s+nhất|it\s+nhat|"
    r"từ\s+\d+(?:[.,]\d+)?\s*%(?:\s+[^\W\d_]+){0,6}\s+trở\s+lên)\b", re.I
)
MAXIMUM_QUALIFIER_RE = re.compile(r"\b(?:at\s+most|maximum|max\.?|không\s+quá|khong\s+qua|no\s+more\s+than)\b", re.I)
EXACT_QUALIFIER_RE = re.compile(r"\b(?:exactly|precisely|chính\s+xác|đúng|dung)\b", re.I)


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFC", repair_mojibake(value)).casefold()
    # Small, auditable academic-domain bilingual aliases. This is not a
    # generative synonym model; numeric/code fidelity remains exact.
    value = re.sub(r"\bcredits?\b", "tín chỉ", value)
    value = re.sub(r"\binternship\b", "thực tập", value)
    value = re.sub(r"\bprerequisite[s]?\b", "tiên quyết", value)
    # Metadata often uses machine-readable separators (for example
    # ``course_catalog``). Treat them like whitespace during grounding.
    value = re.sub(r"[_/\\-]+", " ", value)
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
    normalized = normalize_text(text)
    markers = (
        {f"code:{normalize_text(item)}" for item in CODE_RE.findall(text)}
        | {f"value:{normalize_text(item)}" for item in NUMBER_RE.findall(text)}
        | {f"year:{item}" for item in YEAR_RE.findall(text)}
        | {f"date:{normalize_text(item)}" for item in DATE_RE.findall(text)}
    )
    if NEGATIVE_POLARITY_RE.search(normalized):
        markers.add("polarity:negative")
    elif POSITIVE_POLARITY_RE.search(normalized):
        markers.add("polarity:positive")
    if MINIMUM_QUALIFIER_RE.search(normalized):
        markers.add("qualifier:minimum")
    if MAXIMUM_QUALIFIER_RE.search(normalized):
        markers.add("qualifier:maximum")
    if EXACT_QUALIFIER_RE.search(normalized):
        markers.add("qualifier:exact")
    return markers


def _markers_match(claim_markers: set[str], evidence_markers: set[str]) -> bool:
    """Compare exact markers without inventing polarity from terse evidence."""
    required = set(claim_markers)
    claim_polarity = {item for item in claim_markers if item.startswith("polarity:")}
    evidence_polarity = {item for item in evidence_markers if item.startswith("polarity:")}
    if claim_polarity and not evidence_polarity:
        required -= claim_polarity
    return required <= evidence_markers


def align_claims(claims: Iterable[Claim], registry: EvidenceRegistry, citation_map: dict[str, tuple[str, ...]]) -> list[Claim]:
    aligned: list[Claim] = []
    for claim in claims:
        ids = tuple(citation_map.get(claim.claim_id, claim.citation_ids))
        evidence = [registry.get(item) for item in ids]
        evidence = [item for item in evidence if item is not None]
        missing_requested_evidence = bool(ids) and len(evidence) != len(set(ids))
        if not ids:
            # No provider mapping: search the registry and retain only the
            # evidence that actually supports this claim. Never attach every
            # retrieved citation to every claim by default.
            evidence = list(registry.values())
        if not evidence:
            aligned.append(claim)
            continue
        calculation = credit_difference_claim_support(claim.text, evidence)
        difference = calculation is not None
        if calculation is None:
            calculation = credit_sum_claim_support(claim.text, evidence)
        if calculation is not None:
            correct, used_ids = calculation
            supported = correct and not missing_requested_evidence
            aligned.append(Claim(claim.claim_id, claim.text, claim.claim_type,
                max(2, claim.required_citations) if difference else claim.required_citations,
                used_ids if supported else ids, 'supported' if supported else 'contradicted',
                1.0 if supported else 0.0, tuple(item.chunk_id for item in evidence), not supported))
            continue
        credit_proofs = [(item, course_credit_support(claim.text, item.content)) for item in evidence]
        typed_proofs = [(item, verdict) for item, verdict in credit_proofs if verdict is not None]
        if typed_proofs:
            supporting = [item for item, verdict in typed_proofs if verdict]
            conflict = any(not verdict for _item, verdict in typed_proofs)
            supported = bool(supporting) and not conflict and not missing_requested_evidence
            # A headed credit-column proof has a precise support set. Bare
            # numeric fragments must not become redundant published citations
            # for its unit. Conflicting headed rows cannot be silently pruned.
            aligned.append(Claim(claim.claim_id, claim.text, claim.claim_type, claim.required_citations,
                tuple(item.chunk_id for item in supporting) if supported else ids,
                'supported' if supported else 'contradicted', 1.0 if supported else 0.0,
                tuple(item.chunk_id for item in evidence), not supported))
            continue
        claim_tokens = _tokens(claim.text)
        markers = _exact_markers(claim.text)
        best = 0.0
        best_records = []
        contradicted = False
        numeric_mismatch = False
        for item in evidence:
            credit_verdict = course_credit_support(claim.text, item.content)
            if credit_verdict is not None:
                if credit_verdict:
                    best = 1.0
                    best_records = [item]
                else:
                    numeric_mismatch = True
                    contradicted = True
                # A number elsewhere in this table cannot override the exact
                # credit-column verdict for the asserted course code.
                continue
            # Citation metadata itself is valid support for page/source claims;
            # content-only matching would incorrectly reject answers such as
            # "the requirement is on page 1".
            page_markers = {int(value) for value in re.findall(r"\b(?:page|trang)\s+(\d+)\b", normalize_text(claim.text))}
            if page_markers and page_markers <= {item.page}:
                best = max(best, 1.0)
                best_records = [item]
                continue
            evidence_tokens = _tokens(" ".join((item.content, item.doc_id, item.source_name,
                                                  *item.heading_path, *item.metadata_tokens)))
            overlap = len(claim_tokens & evidence_tokens) / max(1, len(claim_tokens))
            evidence_markers = _exact_markers(item.content)
            metadata_text = normalize_text(" ".join(item.metadata_tokens))
            evidence_markers |= _exact_markers(metadata_text)
            marker_ok = not markers or _markers_match(markers, evidence_markers)
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
        # A proposition can be split across multiple chunks.  Recombine
        # independently useful evidence before classifying the claim so a
        # multi-evidence claim is not incorrectly marked partial merely
        # because no single chunk contains every marker.
        if len(evidence) > 1:
            ranked_support = []
            for item in evidence:
                item_tokens = _tokens(" ".join((item.content, item.doc_id, item.source_name,
                                                  *item.heading_path, *item.metadata_tokens)))
                overlap = len(claim_tokens & item_tokens) / max(1, len(claim_tokens))
                item_markers = _exact_markers(item.content) | _exact_markers(" ".join(item.metadata_tokens))
                if overlap >= 0.2 or (markers & item_markers):
                    ranked_support.append((overlap, item))
            ranked_support.sort(key=lambda value: (-value[0], value[1].chunk_id))
            combined: list[EvidenceRecord] = []
            covered_tokens: set[str] = set()
            covered_markers: set[str] = set()
            for _overlap, item in ranked_support:
                item_tokens = _tokens(item.content)
                item_markers = _exact_markers(item.content) | _exact_markers(" ".join(item.metadata_tokens))
                if (item_tokens - covered_tokens) or (item_markers & markers - covered_markers):
                    combined.append(item)
                    covered_tokens |= item_tokens
                    covered_markers |= item_markers
                if len(covered_tokens & claim_tokens) / max(1, len(claim_tokens)) >= 0.55 and markers <= covered_markers:
                    break
            token_coverage = len(covered_tokens & claim_tokens) / max(1, len(claim_tokens))
            marker_coverage = not markers or _markers_match(markers, covered_markers)
            if combined and token_coverage >= 0.55 and marker_coverage:
                best = max(best, min(1.0, token_coverage))
                best_records = combined
        if missing_requested_evidence:
            best = 0.0
            best_records = []
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
