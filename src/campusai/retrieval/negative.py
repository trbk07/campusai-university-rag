"""Deterministic retrieval abstention guards for unsupported queries."""

from __future__ import annotations

import re

from .tokenizer_vi import normalized_tokens


INJECTION_RE = re.compile(
    r"(?:ignore|disregard)\s+(?:all\s+)?(?:previous|prior|system)\s+instructions|"
    r"reveal\s+(?:the\s+)?(?:system\s+)?prompt|answer\s+without\s+citation", re.I,
)
STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "in", "to", "is", "what", "please",
    "và", "va", "của", "cua", "trong", "là", "la", "gì", "gi", "hãy", "hay",
    "cho", "biết", "biet", "kiểm", "kiem", "tra", "xác", "xac", "minh", "cứu", "cuu",
}


def negative_query_reason(query: str, *, max_chars: int = 2000) -> str | None:
    value = str(query).strip()
    if not value:
        return "empty_query"
    if len(value) > max_chars:
        return "query_too_long"
    if INJECTION_RE.search(value):
        return "prompt_injection"
    if re.search(r"\b(?:cái\s+đó|cai\s+do|thế\s+nào|the\s+nao)\b", value, re.I):
        return "ambiguous_query"
    meaningful = {token for token in normalized_tokens(value) if token.casefold() not in STOPWORDS and len(token) >= 2}
    if not meaningful or (len(meaningful) == 1 and re.fullmatch(r"xq\d+", next(iter(meaningful)), re.I)):
        return "query_too_short_or_stopwords"
    return None
