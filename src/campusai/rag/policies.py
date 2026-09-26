"""Deterministic evidence-status and adversarial-content policies."""

from __future__ import annotations

import re
from collections import defaultdict

from ..retrieval.hybrid import RetrievalResult
from .claims import normalize_text

INJECTION_RE = re.compile(
    r"(?:ignore|disregard)\s+(?:all\s+)?(?:previous|prior|system)\s+instructions|"
    r"you\s+are\s+now\s+an?\s+(?:assistant|system)|reveal\s+(?:the\s+)?prompt", re.I
)


def sanitize_evidence_text(content: str) -> str:
    """Treat instruction-like PDF text as data, never as executable prompt text."""
    return "\n".join(
        "[redacted_untrusted_instruction]" if INJECTION_RE.search(line) else line
        for line in str(content).splitlines()
    )


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[\wÀ-ỹ]{2,}", normalize_text(value)))


def is_ambiguous_question(question: str, results: list[RetrievalResult]) -> bool:
    """Abstain only for genuinely broad questions spanning multiple topics."""
    normalized = normalize_text(question)
    tokens = _tokens(normalized)
    scoped = bool(re.search(
        r"\b(?:20\d{2}|[a-z]{2,}\d{2,}|program|course|graduation|prerequisite|"
        r"tuition|admission|credits?|internship)\b", normalized, re.I
    ))
    if scoped or len(tokens) > 5 or len({result.doc_id for result in results}) < 2:
        return False
    matching_docs = {
        result.doc_id for result in results if tokens & _tokens(result.content)
    }
    return len(matching_docs) > 1 or not matching_docs


def has_conflicting_numeric_evidence(results: list[RetrievalResult], question: str | None = None) -> bool:
    """Detect disagreement only among evidence relevant to the question."""
    if question is not None:
        normalized_question = normalize_text(question)
        numeric_intent = bool(re.search(
            r"\d|how many|how much|which year|page|version|credits?|tín\s*chỉ|bao nhiêu|trang|năm",
            normalized_question, re.I
        ))
        if not numeric_intent:
            return False
        query_tokens = {token for token in _tokens(question) if len(token) >= 4}
        related = [result for result in results if query_tokens & _tokens(result.content)]
        if len({result.doc_id for result in related}) < 2:
            return False
        results = related
    values: dict[str, set[str]] = defaultdict(set)
    for result in results:
        content = normalize_text(result.content)
        numbers = set(re.findall(r"\d+(?:[.,]\d+)?\s*(?:credits?|tín\s*chỉ|%)?", content))
        # Remove volatile words and retain a compact semantic signature so
        # unrelated numeric facts do not create a false conflict.
        topic_tokens = {
            token for token in _tokens(content)
            if token not in {"requires", "require", "credits", "credit"}
            and not token.isdigit()
        }
        topic = " ".join(sorted(topic_tokens)[:10])
        for value in numbers:
            values[topic].add(value)
    return any(len(items) > 1 for items in values.values())
