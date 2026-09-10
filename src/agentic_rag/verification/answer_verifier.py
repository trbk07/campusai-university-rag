"""Evidence-grounded answer checks without requiring an LLM."""
from .citation_checker import check_citations
from evaluation.metrics.answer_metrics import normalize_answer

def verify_answer(answer: str, *, evidence: dict[str, str], citations: list[str], expected: str | None = None) -> dict:
    citation = check_citations(citations, evidence.keys())
    normalized = normalize_answer(answer)
    evidence_text = normalize_answer(" ".join(evidence.get(key, "") for key in citations if key in evidence))
    grounded = bool(normalized) and all(token in evidence_text.split() for token in normalized.split()) if normalized else False
    result = {"grounded": grounded, "citation": citation, "answer_present": bool(normalized)}
    if expected is not None: result["answer_match"] = normalize_answer(answer) == normalize_answer(expected)
    result["reliable"] = grounded and bool(citation["valid"])
    return result

