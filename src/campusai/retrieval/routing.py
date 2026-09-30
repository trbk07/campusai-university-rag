"""Deterministic, non-LLM query routing for Phase 6."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any


COURSE_CODE_RE = re.compile(r"(?<![\w])(?:[A-ZĐ]{2,}[A-ZĐ]*[-_.]?\d{1,4}[A-Z]?|DTVT-1)(?![\w])", re.I)
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
    codes = detected_codes(query)
    if codes:
        return "exact_code"
    if filters:
        return "filtered_hybrid_rrf"
    return "hybrid_rrf"
