"""Stable abstention taxonomy and user-safe messages."""

from __future__ import annotations

from enum import Enum


class AbstentionReason(str, Enum):
    NO_EVIDENCE_FOUND = "no_evidence_found"
    DOCUMENT_DOES_NOT_MENTION = "document_does_not_mention"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    AMBIGUOUS_QUESTION = "ambiguous_question"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    CONTRADICTED_CLAIM = "contradicted_claim"
    INVALID_CITATION = "invalid_citation"
    RETRIEVAL_BELOW_THRESHOLD = "retrieval_below_threshold"
    CONTEXT_BUDGET_EXCEEDED = "context_budget_exceeded"
    PROVIDER_ERROR = "provider_error"
    PROVIDER_ABSTENTION = "provider_abstention"
    # Legacy/internal values retained for cache/API compatibility. They are
    # never emitted as public abstention reasons.
    PROVIDER_ABSTAINED = "provider_abstained"
    SYSTEM_ERROR = "system_error"


CANONICAL_ABSTENTION_REASONS = frozenset({
    "no_evidence_found", "document_does_not_mention", "unsupported_claim",
    "contradicted_claim", "ambiguous_question", "conflicting_evidence",
    "provider_abstention", "invalid_citation",
})


MESSAGES = {
    "no_evidence_found": "Chưa tìm thấy đoạn nguồn phù hợp. Bạn có thể chọn đúng PDF, chỉ rõ mục/trang cần tra cứu hoặc bổ sung tài liệu liên quan.",
    "document_does_not_mention": "Các tài liệu đã kiểm tra không đề cập đến thông tin này. Bạn có thể bổ sung một nguồn khác có nội dung cần tra cứu.",
    "conflicting_evidence": "Các tài liệu hiện có đưa ra thông tin khác nhau; cần xác định phiên bản hoặc năm áp dụng.",
    "ambiguous_question": "Bạn đang hỏi về đối tượng hoặc phần nào trong tài liệu? Hãy cho biết tên đầy đủ, mục/trang hoặc phiên bản cần tra cứu để mình xác định đúng phạm vi.",
    "unsupported_claim": "Mình chưa xác minh đầy đủ câu trả lời từ các đoạn nguồn hiện có. Bạn có thể chỉ rõ mục/trang cần tra cứu hoặc bổ sung tài liệu liên quan.",
    "contradicted_claim": "Bằng chứng hiện có mâu thuẫn với nội dung câu trả lời.",
    "invalid_citation": "Không thể xác minh nguồn trích dẫn trong bằng chứng hiện có.",
    "retrieval_below_threshold": "Kết quả tìm kiếm chưa đạt ngưỡng bằng chứng cần thiết.",
    "context_budget_exceeded": "Bằng chứng tồn tại nhưng vượt quá giới hạn xử lý an toàn.",
    "provider_error": "Dịch vụ trả lời đang gặp lỗi; vui lòng thử lại sau.",
    "provider_abstained": "Mô hình không đưa ra câu trả lời có thể xác minh; cần thêm bằng chứng.",
    "provider_abstention": "Mô hình không đưa ra câu trả lời có thể xác minh; cần thêm bằng chứng.",
    "system_error": "Hệ thống chưa thể hoàn tất yêu cầu này.",
}

LEGACY_REASON_MAP = {
    "no_retrieval_evidence": "no_evidence_found",
    "no_relevant_evidence": "retrieval_below_threshold",
    "citation_not_in_evidence": "invalid_citation",
    "llm_error": "provider_error",
    "llm_not_configured": "system_error",
    "invalid_model_output": "system_error",
    "empty_model_answer": "system_error",
    "model_abstained": "provider_abstained",
}


def taxonomy_reason(reason: str | None) -> str | None:
    return LEGACY_REASON_MAP.get(reason or "", reason)


def canonicalize_abstention_reason(
    reason: str | None,
    *,
    evidence_found: bool | None = None,
    claim_status: str | None = None,
    citation_valid: bool | None = None,
    conflict: bool = False,
    ambiguous: bool = False,
) -> str | None:
    """Map internal/provider state to the one public reason taxonomy."""
    raw = str(reason or "").strip()
    if not raw:
        return None
    if citation_valid is False or raw in {"citation_not_in_evidence", "invalid_citation"}:
        return "invalid_citation"
    if claim_status == "contradicted" or raw == "contradicted_claim":
        return "contradicted_claim"
    if conflict or raw == "conflicting_evidence":
        return "conflicting_evidence"
    if ambiguous or raw in {"empty_question", "ambiguous_question"}:
        return "ambiguous_question"
    mapped = LEGACY_REASON_MAP.get(raw, raw)
    if mapped in {"provider_abstained", "provider_error", "system_error", "invalid_model_output",
                  "empty_model_answer", "llm_error", "llm_not_configured", "model_abstained"}:
        return "provider_abstention"
    if mapped == "retrieval_below_threshold":
        # A retrieved top-k below threshold cannot establish document absence.
        return "no_evidence_found"
    if mapped in CANONICAL_ABSTENTION_REASONS:
        return mapped
    if evidence_found is False:
        return "no_evidence_found"
    return "unsupported_claim"


def user_message(reason: str, language: str = "vi") -> str:
    if language.casefold().startswith("en"):
        return {
            "no_evidence_found": "No relevant source passage was found. Please select the matching PDF, specify a section/page, or add a relevant document.",
            "document_does_not_mention": "The checked documents do not mention this information. You can add another source that covers it.",
            "conflicting_evidence": "The available documents contain conflicting information.",
            "provider_error": "The answer service is temporarily unavailable. Please try again later.",
            "unsupported_claim": "I could not verify the complete answer from the available passages. Please specify a section/page or add a relevant document.",
            "contradicted_claim": "The available evidence contradicts the proposed answer.",
            "invalid_citation": "The cited source could not be verified against the available evidence.",
            "ambiguous_question": "Which subject or part of the document do you mean? Please give its full name, section/page, or relevant version so I can identify the correct scope.",
            "provider_abstention": "The model did not provide an answer that could be verified.",
        }.get(reason, "There is not enough verified evidence to answer safely.")
    return MESSAGES.get(reason, MESSAGES["system_error"])
