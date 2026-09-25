"""Generate answers only from retrieved, page-grounded evidence."""

from __future__ import annotations

from dataclasses import dataclass
import math
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
    cache_hit: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "citations": [citation.to_dict() for citation in self.citations],
            "confidence": self.confidence,
            "abstained": self.abstained,
            "reason": self.reason,
            "cache_hit": self.cache_hit,
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


def estimate_tokens(text: str) -> int:
    """Conservative, tokenizer-independent token estimate for UTF-8 text."""

    return max(1, math.ceil(len(text) / 4)) if text else 0


def _context_block(result: RetrievalResult) -> tuple[str, str]:
    page_range = result.metadata.get("page_range", [result.page, result.page])
    source_name = result.metadata.get("source_name") or result.doc_id
    section = " > ".join(result.metadata.get("heading_path", [])) or ""
    metadata = (
        f"[EVIDENCE]\nchunk_id={result.chunk_id}\n"
        f"document={source_name}\ndoc_id={result.doc_id}\npage={result.page}\n"
        f"page_range={page_range[0]}-{page_range[1]}\nsection={section}\ncontent:\n"
    )
    return metadata, result.content.strip()


def build_context(
    results: Iterable[RetrievalResult],
    max_chars: int = 12000,
    *,
    max_tokens: int | None = None,
) -> str:
    """Serialize evidence with stable ids and page provenance for the prompt."""

    blocks: list[str] = []
    used_chars = 0
    used_tokens = 0
    for result in results:
        metadata, content = _context_block(result)
        if not content:
            continue
        remaining_chars = max_chars - used_chars
        remaining_tokens = max_tokens - used_tokens if max_tokens is not None else None
        if remaining_chars <= len(metadata) or (remaining_tokens is not None and remaining_tokens <= estimate_tokens(metadata)):
            continue
        available_chars = remaining_chars - len(metadata)
        if remaining_tokens is not None:
            available_chars = min(available_chars, max(0, remaining_tokens * 4 - len(metadata)))
        if available_chars <= 0:
            continue
        truncated = len(content) > available_chars
        excerpt = content[:available_chars].rstrip()
        if truncated:
            marker = "\n[truncated=true]"
            excerpt = excerpt[: max(0, available_chars - len(marker))].rstrip() + marker
        block = metadata + excerpt
        block_tokens = estimate_tokens(block)
        if max_tokens is not None and used_tokens + block_tokens > max_tokens:
            continue
        blocks.append(block)
        used_chars += len(block)
        used_tokens += block_tokens
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

    def __init__(
        self,
        llm: LLMClient | None = None,
        max_context_chars: int = 12000,
        max_context_tokens: int | None = None,
        min_retrieval_score: float | None = None,
    ) -> None:
        self.llm = llm
        self.max_context_chars = max(1000, max_context_chars)
        self.max_context_tokens = max_context_tokens if max_context_tokens is None else max(64, max_context_tokens)
        self.min_retrieval_score = min_retrieval_score

    def prompt(self, question: str, results: list[RetrievalResult], language: str = "vi") -> str:
        context = build_context(results, self.max_context_chars, max_tokens=self.max_context_tokens)
        if language.casefold().startswith("en"):
            instructions = (
                "You are CampusAI, an evidence-grounded university knowledge assistant.\n"
                "Use only the supplied evidence. Do not use outside knowledge, guess, or infer unsupported facts.\n"
                "If evidence is insufficient, set abstained=true and answer briefly that the documents do not establish it.\n"
                "Every material claim must cite one or more supplied chunk_id values.\n"
                "Return valid JSON only with answer, confidence (high|medium|low), abstained, and citations.\n"
                "Keep the answer direct and short (1-3 short paragraphs)."
            )
        else:
            instructions = (
                "Bạn là CampusAI, trợ lý tri thức đại học dựa trên bằng chứng.\n"
                "Chỉ dùng thông tin trong EVIDENCE; không dùng kiến thức bên ngoài, không đoán hoặc suy diễn.\n"
                "Nếu bằng chứng chưa đủ, đặt abstained=true và nói ngắn rằng tài liệu chưa xác lập được câu trả lời.\n"
                "Mọi kết luận quan trọng phải trích dẫn một hoặc nhiều chunk_id có trong EVIDENCE.\n"
                "Chỉ trả về JSON hợp lệ gồm answer, confidence (high|medium|low), abstained và citations.\n"
                "Trả lời trực tiếp, ngắn gọn (1-3 đoạn ngắn)."
            )
        return f"{instructions}\n\nQUESTION:\n{question}\n\nEVIDENCE:\n{context}"

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
        if self.min_retrieval_score is not None and max(result.score for result in results) < self.min_retrieval_score:
            return _abstention("no_relevant_evidence")
        if self.llm is None:
            return _abstention("llm_not_configured")
        if not build_context(results, self.max_context_chars, max_tokens=self.max_context_tokens):
            return _abstention("context_budget_exceeded")

        by_chunk = {result.chunk_id: result for result in results}
        try:
            payload = self.llm.generate_json(
                self.prompt(question, results, language),
                schema=ANSWER_SCHEMA,
            )
        except LLMError:
            return _abstention("llm_error")
        if not isinstance(payload, dict) or not isinstance(payload.get("answer"), str):
            return _abstention("invalid_model_output")
        if not isinstance(payload.get("citations", []), list):
            return _abstention("invalid_model_output")
        if not payload["answer"].strip():
            return _abstention("empty_model_answer")
        if len(payload["answer"].strip()) > 1600 or payload.get("confidence") not in {"high", "medium", "low"}:
            return _abstention("invalid_model_output")

        citations: list[Citation] = []
        seen_chunks: set[str] = set()
        for raw in payload.get("citations", []):
            result = by_chunk.get(str(raw.get("chunk_id", "")))
            if result is None:
                return _abstention("citation_not_in_evidence")
            validation = validate_citation(raw, result)
            if not validation.valid:
                return _abstention("citation_not_in_evidence")
            if result.chunk_id in seen_chunks:
                continue
            seen_chunks.add(result.chunk_id)
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


def format_citation(citation: Citation, language: str = "vi") -> str:
    """Render a human-facing citation without exposing local paths or secrets."""

    source = citation.source_name or citation.doc_id
    if language.casefold().startswith("en"):
        return f"[{source}, page {citation.page}]"
    return f"[{source}, trang {citation.page}]"
