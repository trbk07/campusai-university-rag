"""Generate answers only from retrieved, page-grounded evidence."""

from __future__ import annotations

from ..request_timings import stage, timed_stage

from dataclasses import dataclass
import json
import math
import re
from typing import Any, Iterable

from ..llm.client import LLMClient, LLMError
from ..retrieval.hybrid import RetrievalResult
from ..retrieval.tokenizer_vi import source_body
from .claims import Claim, align_claims, extract_claims, normalize_text
from .confidence import POLICY_VERSION, score_confidence
from .calibration import IsotonicCalibrator
from .decision import decide
from .abstention import canonicalize_abstention_reason, user_message
from .abstention import AbstentionReason
from .evidence import EvidenceRegistry
from .schemas import SCHEMA_VERSION, validate_response, validate_release_response
from .policies import sanitize_evidence_text
from .policies import has_conflicting_numeric_evidence, is_ambiguous_question, explicit_comparison_request


@dataclass(frozen=True)
class CitationValidation:
    """Machine-checkable result for a citation/provenance lookup."""

    valid: bool
    errors: tuple[str, ...] = ()


def validate_quote(quote: str, content: str) -> bool:
    """Validate quote fidelity without stripping accents or numbers."""
    if not quote:
        return True
    if len(quote) > 1200:
        return False
    normalized = normalize_text(quote)
    if normalized in normalize_text(content):
        return True
    # JSON serializes line breaks inside source table cells as escape sequences.
    # Check decoded cells/one original row, never concatenate separate rows or
    # invent a prose paraphrase. Numeric and accent fidelity still apply.
    start = content.find('{"headers"')
    if start < 0:
        return False
    try:
        table = json.loads(content[start:])
    except (ValueError, TypeError):
        return False
    if not isinstance(table, dict):
        return False
    rows = [table.get('headers'), *(table.get('rows') or [])] if isinstance(table.get('rows'), list) else []
    # A JSON-array quote can contain decoded cell line breaks inside the outer
    # response string. Compare the complete cells to one source row, preserving
    # whitespace, accents, codes and values; never combine cells across rows.
    try:
        quoted_cells = json.loads(quote, strict=False)
    except (ValueError, TypeError):
        quoted_cells = None
    if (isinstance(quoted_cells, list) and quoted_cells
            and all(isinstance(cell, str) for cell in quoted_cells)
            and quoted_cells in rows):
        return True
    for row in rows:
        if isinstance(row, list) and all(isinstance(cell, str) for cell in row):
            if normalized in normalize_text(' '.join(row)):
                return True
            # Providers can display the exact JSON cells as a pipe-separated
            # row while retaining one/two levels of escaped cell whitespace.
            # Accept that presentation only against one original row; do not
            # decode arbitrary escapes or join cells from different rows.
            displayed = re.sub(r'\\{1,2}[nrt]', ' ', quote)
            if normalize_text(displayed) in normalize_text(' | '.join(row)):
                return True
    return False


def validate_citation(
    citation: "Citation | dict[str, Any]",
    result: RetrievalResult,
    *,
    source_hash: str | None = None,
    require_quote: bool = False,
    require_provenance: bool = False,
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
    expected_range = result.metadata.get("page_range", [result.page, result.page])
    supplied_range = values.get("page_range", expected_range)
    ranges_valid = all(
        isinstance(interval, (list, tuple)) and len(interval) == 2
        and all(type(endpoint) is int for endpoint in interval)
        for interval in (expected_range, supplied_range)
    )
    if (
        not ranges_valid
        or tuple(supplied_range) != tuple(expected_range)
        or not (supplied_range[0] <= page <= supplied_range[1])
    ):
        errors.append("page_range_mismatch")
    expected_table = result.metadata.get("table_id")
    if expected_table is not None and values.get("table_id") != expected_table:
        errors.append("table_id_mismatch")
    if require_provenance:
        if not str(values.get("source_name", "")).strip() and result.metadata.get("source_name"):
            errors.append("source_name_missing")
        if result.metadata.get("source_hash") and values.get("source_hash") != result.metadata.get("source_hash"):
            errors.append("source_hash_missing")
        if not values.get("page_range"):
            errors.append("page_range_missing")
    if require_quote and not str(values.get("quote", "")).strip():
        errors.append("quote_missing")
    cited_hash = values.get("source_hash")
    expected_hash = source_hash or result.metadata.get("source_hash")
    if cited_hash is not None and expected_hash is not None and cited_hash != expected_hash:
        errors.append("source_hash_mismatch")
    if not (require_quote and not str(values.get("quote", "")).strip()) and not validate_quote(str(values.get("quote", "")), result.content):
        errors.append("quote_not_in_evidence")
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
    claims: tuple[Claim, ...] = ()
    evidence_status: str = "found"
    confidence_score: float | None = None
    policy_version: str = POLICY_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "citations": [citation.to_dict() for citation in self.citations],
            "confidence": self.confidence,
            "abstained": self.abstained,
            "reason": self.reason,
            "abstention_reason": canonicalize_abstention_reason(self.reason),
            "cache_hit": self.cache_hit,
            "claims": [
                {"claim_id": claim.claim_id, "text": claim.text, "type": claim.claim_type,
                 "status": claim.status, "citation_ids": list(claim.citation_ids),
                 "support_score": claim.support_score, "numeric_conflict": claim.numeric_conflict}
                for claim in self.claims
            ],
            "evidence_status": self.evidence_status,
            "confidence_score": self.confidence_score,
            "schema_version": SCHEMA_VERSION,
            "confidence_policy_version": self.policy_version,
        }

    def to_public_dict(self) -> dict[str, Any]:
        """Return only the stable UI/API contract; diagnostics stay internal."""
        payload = self.to_dict()
        if self.abstained:
            # A rejected answer must not publish its unverified factual claims.
            # Keep the full alignment/citation diagnostics in to_dict only.
            payload["claims"] = []
            payload["citations"] = []
        payload["citations"] = [
            {key: citation[key] for key in ("chunk_id", "doc_id", "page", "page_range", "quote", "section_path", "source_name", "table_id")}
            for citation in payload.get("citations", [])
        ]
        payload["claims"] = [
            {**{key: claim[key] for key in ("claim_id", "text", "type")},
             "citation_ids": [item for item in claim["citation_ids"]
                              if item in {citation["chunk_id"] for citation in payload.get("citations", [])}]}
            for claim in payload.get("claims", [])
        ]
        public = {key: value for key, value in payload.items()
                  if key in {"answer", "citations", "confidence", "abstained", "claims", "abstention_reason"}}
        if not public.get("abstained"):
            public.pop("abstention_reason", None)
        public["schema_version"] = "grounding-public-v2"
        if not validate_release_response(public)[0]:
            reason = canonicalize_abstention_reason(self.reason if self.abstained else "invalid_citation")
            return {"answer": user_message(reason), "citations": [], "claims": [], "confidence": "low",
                    "abstained": True, "abstention_reason": reason, "schema_version": "grounding-public-v2"}
        return public


ANSWER_SCHEMA = {
    "type": "object",
    "required": ["answer", "confidence", "abstained", "citations"],
    "additionalProperties": False,
    "properties": {
        "answer": {"type": "string", "minLength": 1, "maxLength": 6000},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "abstained": {"type": "boolean"},
        "abstention_reason": {"type": "string", "enum": [reason.value for reason in AbstentionReason]},
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["chunk_id", "page", "quote"],
                "additionalProperties": False,
                "properties": {
                    "chunk_id": {"type": "string", "minLength": 1},
                    "page": {"type": "integer", "minimum": 1},
                    "quote": {"type": "string", "minLength": 1, "maxLength": 1200},
                },
            },
        },
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["claim_id", "text", "citation_ids"],
                "additionalProperties": False,
                "properties": {
                    "claim_id": {"type": "string", "minLength": 1},
                    "text": {"type": "string", "minLength": 1, "maxLength": 1200},
                    "type": {"type": "string"},
                    "citation_ids": {"type": "array", "items": {"type": "string"}},
                    "required_citations": {"type": "integer", "minimum": 1},
                },
            },
        },
    },
}


def estimate_tokens(text: str) -> int:
    """Character-based estimate, not a provider tokenizer's exact count."""

    return max(1, math.ceil(len(text) / 4)) if text else 0


def _context_block(result: RetrievalResult) -> tuple[str, str]:
    page_range = result.metadata.get("page_range", [result.page, result.page])
    source_name = result.metadata.get("source_name") or result.doc_id
    section = " > ".join(result.metadata.get("heading_path", [])) or ""
    table_line = f"table_id={result.metadata.get('table_id')}\n" if result.metadata.get("table_id") else ""
    metadata = (
        f"[EVIDENCE]\nchunk_id={result.chunk_id}\n"
        f"document={source_name}\ndoc_id={result.doc_id}\npage={result.page}\n"
        f"page_range={page_range[0]}-{page_range[1]}\n{table_line}section={section}\ncontent:\n"
    )
    # Generated index headers are not source evidence. Keep physical citation
    # coordinates above and preserve the source/table serialization verbatim.
    body = source_body({"content": result.content}, decode_tables=False)
    return metadata, sanitize_evidence_text(body.strip())


def build_context(
    results: Iterable[RetrievalResult],
    max_chars: int = 12000,
    *,
    max_tokens: int | None = None,
) -> str:
    """Serialize evidence within a budget including headers and separators.

    The token budget uses estimate_tokens; it does not bound the entire prompt
    (instructions/question) or claim to match a provider's actual tokenizer.
    """

    blocks: list[str] = []
    used_chars = 0
    char_limit = min(max_chars, max_tokens * 4) if max_tokens is not None else max_chars
    for result in results:
        metadata, content = _context_block(result)
        if not content:
            continue
        separator_chars = 2 if blocks else 0
        available_chars = char_limit - used_chars - separator_chars - len(metadata)
        if available_chars <= 0:
            continue
        if len(content) > available_chars:
            marker = "\n[truncated=true]"
            excerpt = content[:max(0, available_chars - len(marker))].rstrip()
            if not excerpt:
                continue
            excerpt += marker
        else:
            excerpt = content
        block = metadata + excerpt
        blocks.append(block)
        used_chars += separator_chars + len(block)
    return "\n\n".join(blocks)


def _abstention(reason: str, citations: tuple[Citation, ...] = (), *, language: str = "vi") -> GroundedAnswer:
    return GroundedAnswer(
        answer=(user_message("provider_error", language) if reason == "llm_error" else
                "Mình chưa tìm thấy đủ bằng chứng trong các tài liệu đã chọn để trả lời chắc chắn."),
        # Abstained public responses never expose orphan citations.  Evidence
        # remains available in the internal trace when needed for diagnosis.
        citations=(),
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
        calibrator: IsotonicCalibrator | None = None,
    ) -> None:
        self.llm = llm
        self.max_context_chars = max(1000, max_context_chars)
        self.max_context_tokens = max_context_tokens if max_context_tokens is None else max(64, max_context_tokens)
        self.min_retrieval_score = min_retrieval_score
        self.calibrator = calibrator

    def prompt(self, question: str, results: list[RetrievalResult], language: str = "vi", *, temporal_context: dict | None = None,
               multi_hop_context: dict | None = None) -> str:
        context = build_context(results, self.max_context_chars, max_tokens=self.max_context_tokens)
        if language.casefold().startswith("en"):
            instructions = (
                "You are CampusAI, an evidence-grounded university knowledge assistant.\n"
                "Use only the supplied evidence. Do not use outside knowledge, guess, or infer unsupported facts.\n"
                "If evidence is insufficient, set abstained=true and answer briefly that the documents do not establish it.\n"
                "Every material claim must cite one or more supplied chunk_id values.\n"
                "Split distinct facts into short atomic claims. For course credits use 'Course CODE has N credits.' with the value from that course's own credit column, not hours or prerequisite rows.\n"
                "For tables, quote exact cells from one source row; preserve codes, numbers and accents. Give citation.page from the evidence page field.\n"
                "Return valid JSON only with answer, claims, confidence (high|medium|low), abstained, and citations. Each claim must list citation_ids.\n"
                "Keep the answer direct and short (1-3 short paragraphs)."
            )
        else:
            instructions = (
                "Bạn là CampusAI, trợ lý tri thức đại học dựa trên bằng chứng.\n"
                "Chỉ dùng thông tin trong EVIDENCE; không dùng kiến thức bên ngoài, không đoán hoặc suy diễn.\n"
                "Nếu bằng chứng chưa đủ, đặt abstained=true và nói ngắn rằng tài liệu chưa xác lập được câu trả lời.\n"
                "Mọi kết luận quan trọng phải trích dẫn một hoặc nhiều chunk_id có trong EVIDENCE.\n"
                "Tách các sự kiện thành claim ngắn, riêng biệt. Với tín chỉ, dùng 'Môn CODE có N tín chỉ.' và lấy N từ cột tín chỉ của đúng hàng môn đó, không lấy số giờ hay hàng tiên quyết.\n"
                "Với bảng, quote phải chép đúng các ô trong một hàng nguồn; giữ nguyên mã, số và dấu. citation.page lấy từ trường page của bằng chứng.\n"
                "Chỉ trả về JSON hợp lệ gồm answer, claims, confidence (high|medium|low), abstained và citations. Mỗi claim phải có citation_ids.\n"
                "Trả lời trực tiếp, ngắn gọn (1-3 đoạn ngắn)."
            )
        from .course_credits import folded
        if explicit_comparison_request(question) and re.search(r'\b(?:credits?|tin chi)\b', folded(question)):
            instructions += (
                "\nLabel each source's credit value separately. For subtraction, emit one atomic claim exactly as "
                "'Credit difference for CODE_B minus CODE_A is B - A = D credits.' with numeric operands and result. "
                "Cite both source chunks in operand order (B, A); for the same code in two sources, repeat that code. "
                "Use only each cited course row's credit column; if either row is absent, abstain."
                if language.casefold().startswith('en') else
                "\nGhi rõ giá trị tín chỉ của từng nguồn. Với phép trừ, dùng một claim đúng mẫu "
                "'Chênh lệch tín chỉ của CODE_B trừ CODE_A là B - A = D tín chỉ.' thay B, A, D bằng số. "
                "Trích dẫn đủ hai chunk theo thứ tự toán hạng (B, A); cùng mã ở hai nguồn thì lặp lại mã. "
                "Chỉ lấy cột tín chỉ đúng hàng môn của mỗi nguồn; thiếu một hàng thì abstain."
            )
        if temporal_context is not None:
            instructions += (
                "\nTEMPORAL SOURCE SCOPE (system-resolved eligibility, not a new fact source):\n"
                + json.dumps(temporal_context, ensure_ascii=False, sort_keys=True)
                + "\nIdentify the requested version(s) in the answer and cite the supporting source quotes. "
                  "Answer only within the selected sources; never claim global current validity or infer "
                  "an effective date from a version label, issue date, upload date, or publication date. "
                  "For comparisons, state each version's fact separately and cite each source."
            )
        if multi_hop_context is not None and not multi_hop_context.get('preserve_existing_prompt'):
            # Full row/cell proofs remain in the internal trace. The prompt
            # references those exact evidence rows without duplicating tables.
            required = dict(kind=multi_hop_context['kind'], roles=multi_hop_context['roles'],
                premises=[{k:p[k] for k in ('doc_id','chunk_id','page','code','credits')}
                          for p in multi_hop_context['premises']])
            if multi_hop_context['edge']:
                edge = multi_hop_context['edge']
                required['edge'] = dict(kind=edge['kind'], bridge_code=edge['bridge_code'],
                    parent_chunk_id=edge['parent']['chunk_id'], target_code=edge['parent']['code'],
                    lookup_name=edge['lookup_name'])
            instructions += ('\nREQUIRED SOURCE ROLES (resolved from the retrieved source rows):\n'
                + json.dumps(required,ensure_ascii=False,sort_keys=True)
                + '\nAnswer every requested role. Label each source separately and cite its own row. '
                  'For every requested credit use one atomic claim: Course CODE has N credits. '
                  'A prerequisite edge must have an atomic claim: Course BRIDGE is a prerequisite of course TARGET. '
                  'For a name-to-code lookup, state the source course name and its code in a separate cited claim. '
                  'Same codes in different sources do not establish equivalence or credit transfer. '
                  'If any required fact or edge is missing, abstain.')
        return f"{instructions}\n\nQUESTION:\n{question}\n\nEVIDENCE:\n{context}"

    @timed_stage("grounding")
    def answer(
        self,
        question: str,
        results: list[RetrievalResult],
        language: str = "vi",
        *, temporal_context: dict | None = None, multi_hop_context: dict | None = None,
    ) -> GroundedAnswer:
        if not question.strip():
            return _abstention("empty_question")
        if not results:
            return _abstention("no_retrieval_evidence")
        if is_ambiguous_question(question, results):
            return _abstention("ambiguous_question")
        conflict = (any(has_conflicting_numeric_evidence([r for r in results if r.doc_id == doc], question)
                        for doc in {r.doc_id for r in results}) if multi_hop_context is not None
                    else has_conflicting_numeric_evidence(results, question))
        if conflict:
            return _abstention("conflicting_evidence")
        if self.min_retrieval_score is not None and max(result.score for result in results) < self.min_retrieval_score:
            return _abstention("no_relevant_evidence")
        if multi_hop_context is not None:
            from .multi_hop_evidence import deterministic_calculation
            context = build_context(results, self.max_context_chars, max_tokens=self.max_context_tokens)
            # A required source row truncated from the model's context is not
            # still available as hidden evidence to validate its answer.
            visible = True
            if multi_hop_context.get('preserve_existing_prompt'):
                for p in multi_hop_context['premises']:
                    marker='chunk_id='+p['chunk_id']+'\n'
                    block=context.split(marker,1)[1].split('[EVIDENCE]',1)[0] if marker in context else ''
                    if (json.dumps(p['cells'],ensure_ascii=False) not in block
                            or json.dumps(p['headers'],ensure_ascii=False) not in block):
                        visible=False
            elif '[truncated=true]' in context or any('chunk_id='+r.chunk_id+'\n' not in context for r in results):
                visible=False
            if not visible:
                return _abstention('context_budget_exceeded')
            calculated = deterministic_calculation(multi_hop_context, results, language)
            if calculated is not None:
                return calculated
        from .credit_sum import deterministic_credit_sum
        calculated = deterministic_credit_sum(question, results, language)
        if calculated is not None:
            return calculated
        if self.llm is None:
            return _abstention("llm_not_configured")
        if not build_context(results, self.max_context_chars, max_tokens=self.max_context_tokens):
            return _abstention("context_budget_exceeded")

        by_chunk = {result.chunk_id: result for result in results}
        try:
            kwargs = {}
            if temporal_context is not None: kwargs['temporal_context'] = temporal_context
            if multi_hop_context is not None: kwargs['multi_hop_context'] = multi_hop_context
            prompt = self.prompt(question, results, language, **kwargs)
            with stage("llm"):
                payload = self.llm.generate_json(prompt, schema=ANSWER_SCHEMA)
        except LLMError:
            return _abstention("llm_error", language=language)
        if not isinstance(payload, dict) or not isinstance(payload.get("answer"), str):
            return _abstention("invalid_model_output")
        if not isinstance(payload.get("citations", []), list):
            return _abstention("invalid_model_output")
        if not payload["answer"].strip():
            return _abstention("empty_model_answer")
        if (len(payload["answer"].strip()) > 1600 or not isinstance(payload.get("confidence"), str)
                or payload["confidence"] not in {"high", "medium", "low"}):
            return _abstention("invalid_model_output")
        raw_claims = payload.get("claims")
        if isinstance(raw_claims, list):
            # Structured claims are the authoritative claim/citation contract:
            # a claim without an explicit direct citation is unsafe to publish.
            for raw_claim in raw_claims:
                if not isinstance(raw_claim, dict) or not str(raw_claim.get("text", "")).strip():
                    return _abstention("invalid_model_output")
                citation_ids = raw_claim.get("citation_ids", raw_claim.get("citation_chunk_ids", []))
                if not isinstance(citation_ids, list) or not citation_ids or any(not str(item).strip() for item in citation_ids):
                    return _abstention("unsupported_claim")

        citations: list[Citation] = []
        seen_chunks: set[str] = set()
        for raw in payload.get("citations", []):
            if not isinstance(raw, dict):
                return _abstention("invalid_model_output")
            result = by_chunk.get(str(raw.get("chunk_id", "")))
            if result is None:
                return _abstention("citation_not_in_evidence")
            # ANSWER_SCHEMA deliberately exposes chunk/page/quote only. Derive
            # table identity from that exact request-scoped chunk, as we already
            # do for the published citation. Explicit contradictory IDs still
            # fail the strict validator; no provider page or quote is replaced.
            validated_raw = dict(raw)
            if "table_id" not in validated_raw and result.metadata.get("table_id") is not None:
                validated_raw["table_id"] = result.metadata["table_id"]
            validation = validate_citation(validated_raw, result)
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
            provider_reason = payload.get("abstention_reason")
            allowed = {reason.value for reason in AbstentionReason}
            if not isinstance(provider_reason, str) or provider_reason not in allowed:
                provider_reason = "provider_abstained"
            # Provider labels are accepted only after deterministic policy
            # checks above have had the opportunity to classify conflict and
            # ambiguity. Unknown or unsupported labels remain generic.
            return _abstention(provider_reason, tuple(citations))
        answer = _grounding_finalize(str(payload["answer"]), tuple(citations), payload, results, language,
                                     calibrator=self.calibrator)
        if multi_hop_context is not None:
            from .multi_hop_evidence import composition_complete
            if not composition_complete(answer, multi_hop_context, results):
                return _abstention('unsupported_claim')
        return answer


@timed_stage("citation_validation")
def _grounding_finalize(answer: str, citations: tuple[Citation, ...], payload: dict[str, Any],
                     results: list[RetrievalResult], language: str,
                     calibrator: IsotonicCalibrator | None = None) -> GroundedAnswer:
    """Recompute claim support/confidence; provider labels are never trusted."""
    registry = EvidenceRegistry(results)
    citation_ids = tuple(citation.chunk_id for citation in citations)
    raw_claims = payload.get("claims") if isinstance(payload.get("claims"), list) else None
    claims = extract_claims(answer, raw_claims)
    # Keep claim-to-citation links precise. Claims without an explicit mapping
    # are resolved against the registry by ``align_claims``.
    citation_map = {claim.claim_id: claim.citation_ids for claim in claims}
    claims = align_claims(claims, registry, citation_map)
    # Phase 5 is fail-closed: a partially supported answer can hide an
    # unsupported number, code, date, or polarity change.
    decision = decide(claims, allow_partial=False)
    if decision.status != "answered":
        mapped_ids = {item for claim in claims for item in claim.citation_ids}
        safe_citations = tuple(citation for citation in citations if citation.chunk_id in mapped_ids)
        return GroundedAnswer(
            answer="Chưa đủ bằng chứng để xác nhận đầy đủ câu trả lời.", citations=safe_citations,
            confidence="low", abstained=True, reason=decision.reason or "unsupported_claim", claims=tuple(claims),
            evidence_status=decision.reason or "unsupported_claim", confidence_score=0.0,
        )
    used_citation_ids = {citation_id for claim in claims for citation_id in claim.citation_ids}
    if used_citation_ids:
        citations = tuple(citation for citation in citations if citation.chunk_id in used_citation_ids)
    if not citations:
        return GroundedAnswer(
            answer="Chưa đủ bằng chứng để xác nhận đầy đủ câu trả lời.",
            confidence="low", abstained=True, reason="unsupported_claim", claims=tuple(claims),
            evidence_status="unsupported_claim", confidence_score=0.0,
        )
    claim_support = sum(claim.support_score for claim in claims) / max(1, len(claims))
    completeness = sum(claim.status == "supported" and bool(claim.citation_ids) for claim in claims) / max(1, len(claims))
    retrieval_support = max(0.0, min(1.0, max(float(result.score) for result in results)))
    confidence = score_confidence(retrieval_support=retrieval_support, claim_entailment=claim_support,
                                  citation_completeness=completeness, calibrator=calibrator)
    evidence_status = "partial" if any(claim.status == "partial" for claim in claims) else "found"
    return GroundedAnswer(answer=answer, citations=citations, confidence=confidence.label,
                          abstained=False, claims=tuple(claims), evidence_status=evidence_status,
                          confidence_score=confidence.score)


def format_citation(citation: Citation, language: str = "vi") -> str:
    """Render a human-facing citation without exposing local paths or secrets."""

    source = citation.source_name or citation.doc_id
    if language.casefold().startswith("en"):
        return f"[{source}, page {citation.page}]"
    return f"[{source}, trang {citation.page}]"
