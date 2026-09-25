"""Generate answers only from retrieved, page-grounded evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from ..llm.client import LLMClient, LLMError
from ..retrieval.hybrid import RetrievalResult


@dataclass(frozen=True)
class CitationValidation:
    """Machine-checkable result for a citation/provenance lookup."""

    valid: bool
    errors: tuple[str, ...] = ()


def validate_citation(
    citation: "Citation | dict[str, Any]",
    result: RetrievalResult,
    *,
    source_hash: str | None = None,
) -> CitationValidation:
    """Validate every citation coordinate against the retrieved evidence.

    This is deliberately independent of an LLM and fails closed when a caller
    supplies an invalid document, chunk, page range, table id, or source hash.
    """

    if isinstance(citation, Citation):
        values = citation.to_dict()
    else:
        values = citation
    errors: list[str] = []
    if str(values.get("chunk_id", "")) != result.chunk_id:
        errors.append("chunk_id_mismatch")
    if str(values.get("doc_id", result.doc_id)) != result.doc_id:
        errors.append("doc_id_mismatch")
    try:
        page = int(values.get("page", -1))
    except (TypeError, ValueError):
        page = -1
    if page != result.page:
        errors.append("page_mismatch")
    expected_range = tuple(result.metadata.get("page_range", [result.page, result.page]))
    supplied_range = tuple(values.get("page_range", expected_range))
    if (
        len(expected_range) != 2
        or len(supplied_range) != 2
        or supplied_range != expected_range
        or not (supplied_range[0] <= page <= supplied_range[1])
    ):
        errors.append("page_range_mismatch")
    expected_table = result.metadata.get("table_id")
    if expected_table is not None and values.get("table_id", expected_table) != expected_table:
        errors.append("table_id_mismatch")
    cited_hash = values.get("source_hash")
    expected_hash = source_hash or result.metadata.get("source_hash")
    if cited_hash is not None and expected_hash is not None and cited_hash != expected_hash:
        errors.append("source_hash_mismatch")
    return CitationValidation(not errors, tuple(errors))


@dataclass(frozen=True)
class Citation:
    """A citation validated against one retrieved chunk."""

    chunk_id: str
    doc_id: str
    page: int
    quote: str = ""
    section_path: str = ""
    source_name: str = ""
    page_range: tuple[int, int] = (0, 0)
    table_id: str = ""
    source_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "page": self.page,
            "page_range": list(self.page_range or (self.page, self.page)),
            "quote": self.quote,
            "section_path": self.section_path,
            "source_name": self.source_name,
            "table_id": self.table_id,
            "source_hash": self.source_hash,
        }


@dataclass(frozen=True)
class GroundedAnswer:
    """Answer contract exposed to a UI/API layer."""

    answer: str
    citations: tuple[Citation, ...] = ()
    confidence: str = "low"
    abstained: bool = False
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "citations": [citation.to_dict() for citation in self.citations],
            "confidence": self.confidence,
            "abstained": self.abstained,
            "reason": self.reason,
        }


ANSWER_SCHEMA = {
    "type": "object",
    "required": ["answer", "confidence", "abstained", "citations"],
    "additionalProperties": False,
    "properties": {
        "answer": {"type": "string", "minLength": 1, "maxLength": 6000},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "abstained": {"type": "boolean"},
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["chunk_id", "page"],
                "additionalProperties": False,
                "properties": {
                    "chunk_id": {"type": "string", "minLength": 1},
                    "page": {"type": "integer", "minimum": 1},
                    "quote": {"type": "string", "maxLength": 1200},
                },
            },
        },
    },
}


def build_context(results: Iterable[RetrievalResult], max_chars: int = 12000) -> str:
    """Serialize evidence with stable ids and page provenance for the prompt."""

    blocks: list[str] = []
    used = 0
    for result in results:
        block = (
            f"[chunk_id={result.chunk_id} doc_id={result.doc_id} page={result.page} "
            f"page_range={result.metadata.get('page_range', [result.page, result.page])}]\n"
            f"{result.content.strip()}"
        )
        if not result.content.strip() or (blocks and used + len(block) > max_chars):
            continue
        if not blocks and len(block) > max_chars:
            block = block[:max_chars]
        blocks.append(block)
        used += len(block)
    return "\n\n".join(blocks)


def _abstention(reason: str, citations: tuple[Citation, ...] = ()) -> GroundedAnswer:
    return GroundedAnswer(
        answer="Mình chưa tìm thấy đủ bằng chứng trong các tài liệu đã chọn để trả lời chắc chắn.",
        citations=citations,
        confidence="low",
        abstained=True,
        reason=reason,
    )


class GroundedAnswerGenerator:
    """Turn retrieval evidence into a validated, citation-safe answer."""

    def __init__(self, llm: LLMClient | None = None, max_context_chars: int = 12000) -> None:
        self.llm = llm
        self.max_context_chars = max(1000, max_context_chars)

    def prompt(self, question: str, results: list[RetrievalResult], language: str = "vi") -> str:
        context = build_context(results, self.max_context_chars)
        return f"""You are CampusAI, a university knowledge assistant.
Answer the user's question using only the evidence below. Do not use outside knowledge.
If the evidence is insufficient, set abstained=true and say so briefly.
Every material claim must be supported by one or more citation chunk_id values from the evidence.
Return JSON only with: answer, confidence (high|medium|low), abstained (boolean), citations.
The user's preferred language is {language}.

QUESTION:
{question}

EVIDENCE:
{context}
"""

    def answer(
        self,
        question: str,
        results: list[RetrievalResult],
        language: str = "vi",
    ) -> GroundedAnswer:
        if not question.strip():
            return _abstention("empty_question")
        if not results:
            return _abstention("no_retrieval_evidence")
        if self.llm is None:
            return _abstention("llm_not_configured")

        by_chunk = {result.chunk_id: result for result in results}
        try:
            payload = self.llm.generate_json(
                self.prompt(question, results, language),
                schema=ANSWER_SCHEMA,
            )
        except LLMError:
            return _abstention("llm_error")

        citations: list[Citation] = []
        for raw in payload.get("citations", []):
            result = by_chunk.get(str(raw.get("chunk_id", "")))
            if result is None:
                return _abstention("citation_not_in_evidence")
            validation = validate_citation(raw, result)
            if not validation.valid:
                return _abstention("citation_not_in_evidence")
            citations.append(
                Citation(
                    result.chunk_id,
                    result.doc_id,
                    result.page,
                    str(raw.get("quote", "")),
                    " > ".join(result.metadata.get("heading_path", [])),
                    str(result.metadata.get("source_name", "")),
                    tuple(result.metadata.get("page_range", [result.page, result.page])),
                    str(result.metadata.get("table_id", "")),
                    str(result.metadata.get("source_hash", "")),
                )
            )
        if not citations or bool(payload.get("abstained")):
            return _abstention("model_abstained", tuple(citations))
        return GroundedAnswer(
            answer=str(payload["answer"]),
            citations=tuple(citations),
            confidence=str(payload["confidence"]),
            abstained=False,
        )
