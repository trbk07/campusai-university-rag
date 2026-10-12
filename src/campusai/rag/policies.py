"""Deterministic evidence-status and adversarial-content policies."""

from __future__ import annotations

import re
from collections import defaultdict

from ..retrieval.hybrid import RetrievalResult
from ..retrieval.source_context_inputs import source_body
from .claims import normalize_text
from .course_credits import folded, headed_credit_rows

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


def explicit_comparison_request(question: str) -> bool:
    intent = folded(str(question).split("Topic:", 1)[0])
    return bool(re.search(r"\b(?:compare|comparison|difference|versus|vs|so sanh|chenh lech|tru)\b", intent)
        and not re.search(r"\b(?:do not|don't|not|khong)\s+(?:compare|so sanh)\b", intent))


def _numeric_assertion_signature(text: str, number: re.Pattern) -> str:
    # A cited legal instrument's number identifies a different subject, like a
    # course code. Replacing it with <number> conflates unrelated decisions.
    # Dates/amounts remain variable, so conflicting facts for the SAME instrument
    # still trigger abstention, including contradictions within one document.
    identities = [match.span('identifier') for match in re.finditer(
        r'\b(?:(?:quyet dinh|nghi dinh|thong tu)\s+so|'
        r'(?:decision|decree|circular)\s+no\.?)\s+'
        r'(?P<identifier>\d+(?:[/-][a-z0-9]+)*)\b', text)]
    return number.sub(lambda match: match[0] if any(
        start <= match.start() and match.end() <= end for start, end in identities)
        else '<number>', text)


def has_conflicting_numeric_evidence(results: list[RetrievalResult], question: str | None = None) -> bool:
    """Compare the same numeric assertion, never numbers within one assertion.

    Explicit source comparisons may describe different source values. Individual
    claims still pass the normal source/citation validators; disagreement inside
    one document remains a conflict even for a comparison request.
    """
    explicit_comparison = False
    requested_codes = set()
    query_tokens = set()
    credit_intent = question is None
    if question is not None:
        # Candidate/evaluation prompts may append a quoted topic after the
        # actual user intent. Numbers in that quote are evidence context, not
        # a request for numeric comparison and must not trigger conflict
        # abstention by themselves.
        intent_question = str(question).split("Topic:", 1)[0]
        normalized_question = normalize_text(intent_question)
        # A bare page reference describes the retrieval scope; it is not a
        # request to compare numeric facts. Keep page numbers themselves so
        # queries such as ``What is on page 3?`` remain numeric intent.
        normalized_question = re.sub(r"\b(?:page|trang)\b", "", normalized_question)
        numeric_intent = bool(re.search(
            r"\d|how many|how much|which year|page|version|credits?|tín\s*chỉ|bao nhiêu|trang|năm",
            normalized_question, re.I
        ))
        if not numeric_intent:
            return False
        query_tokens = {token for token in _tokens(intent_question) if len(token) >= 4}
        related = [result for result in results if query_tokens & _tokens(result.content)]
        if not related:
            return False
        results = related
        intent = folded(intent_question)
        explicit_comparison = explicit_comparison_request(intent_question)
        credit_intent = bool(re.search(r"\b(?:credits?|tin chi)\b", intent))
        requested_codes = {code.upper() for code in re.findall(r"\b[a-z]{2,5}\d{3,5}[a-z]?\b", intent)}
    values = defaultdict(lambda: defaultdict(set))
    number = re.compile(r"(?<!\w)[+-]?\d+(?:[.,]\d+)?(?!\w)")
    for result in results:
        table_rows = headed_credit_rows(result.content) if credit_intent else None
        if table_rows is not None:
            for code, value, _row in table_rows:
                if value is not None and (not requested_codes or code in requested_codes):
                    values[("course_credits", code)][result.doc_id].add((value,))
            continue
        # Complete assertions retain all numeric positions. Course identifiers
        # are words, not standalone numeric values. Identical multi-number
        # sentences therefore agree, and unrelated sentences do not merge.
        body = source_body({"content": result.content}, decode_tables=False)
        for sentence in re.split(r"\n+|[.!?](?:\s+|$)", body):
            text = re.sub(r"\bcredits?\b", "tin chi", folded(sentence))
            numbers = tuple(v.replace(",", ".") for v in number.findall(text))
            # A flattened table value or numbered course title has no numeric
            # assertion by itself. Generated source headers are never facts.
            if requested_codes and credit_intent and not any(
                re.search(r'\b' + re.escape(code.casefold()) + r'\b', text) for code in requested_codes):
                continue
            relation = re.search(r'\b(?:has|have|requires?|required|needs?|must|is|are|carries|worth|co|can|phai|la|yeu cau)\b', text)
            if numbers and relation and (not query_tokens or query_tokens & _tokens(sentence)):
                signature = _numeric_assertion_signature(text, number)
                values[("assertion", signature)][result.doc_id].add(numbers)
    for documents in values.values():
        if any(len(items) > 1 for items in documents.values()):
            return True
        if not explicit_comparison and len(set().union(*documents.values())) > 1:
            return True
    return False
