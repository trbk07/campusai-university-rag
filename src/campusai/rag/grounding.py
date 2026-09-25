"""Generate answers only from retrieved, page-grounded evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from ..llm.client import LLMClient, LLMError
from ..retrieval.hybrid import RetrievalResult


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "page": self.page,
            "page_range": list(self.page_range or (self.page, self.page)),
            "quote": self.quote,
            "section_path": self.section_path,
            "source_name": self.source_name,
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
            if result is None or int(raw.get("page", -1)) != result.page:
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
