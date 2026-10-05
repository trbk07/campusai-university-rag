"""Deterministic, non-LLM query routing for Phase 6."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any


COURSE_CODE_RE = re.compile(r"(?<![\w])(?:[A-ZĐ]{2,}[A-ZĐ]*[-_.]?\d{1,5}[A-Z]?|DTVT-1)(?![\w])", re.I)
PROGRAM_CODE_RE = re.compile(r"(?<![\w])(?:CNTT|KHMT|ĐTVT|DTVT|CTĐT\d{2}|CTDT\d{2})(?![\w])", re.I)


def detected_codes(query: str) -> tuple[str, ...]:
    matches = [match for pattern in (COURSE_CODE_RE, PROGRAM_CODE_RE) for match in pattern.finditer(query)]
    values: list[str] = []
    seen: set[str] = set()
    for match in sorted(matches, key=lambda item: (item.start(), item.end())):
        value = match.group(0).upper()
        if value not in seen:
            seen.add(value)
            values.append(value)
    return tuple(values)


def detected_course_codes(query: str) -> tuple[str, ...]:
    """Separate academic identifiers from program/semester shorthand."""
    return tuple(code for code in detected_codes(query) if re.search(r"\d{2,}", code)
                 and not re.fullmatch(r"(?:CTĐT|CTDT|HK|SEM)\d+|QH[-_.]?(?:19|20|21)\d{2}", code, re.I))


@dataclass(frozen=True)
class RoutingTrace:
    route: str
    detected_codes: tuple[str, ...] = ()
    exact_match: bool = False
    filters_applied: bool = False
    bm25_used: bool = False
    dense_used: bool = False
    abstained: bool = False
    abstention_reason: str | None = None
    fallback: str | None = None
    rerank_selected: bool = False
    rerank_route_selected: bool = False
    rerank_inference_started: bool = False
    rerank_applied: bool = False
    rerank_fallback: bool = False
    rerank_abstained: bool = False
    retrieval_cache_hit: bool = False
    answer_cache_hit: bool = False
    rerank_score_cache_hit: bool = False
    reranker_model_identity: str | None = None
    reranker_policy_identity: str | None = None
    rerank_reason: str | None = None
    candidate_count: int = 0
    final_count: int = 0
    latency_ms: dict[str, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["detected_codes"] = list(self.detected_codes)
        return value


def choose_route(query: str, *, filters: dict | None = None) -> str:
    if not isinstance(query, str) or not query.strip():
        return "abstain"
    codes = detected_course_codes(query)
    if codes:
        return "exact_code"
    if filters:
        return "filtered_hybrid_rrf"
    return "hybrid_rrf"
