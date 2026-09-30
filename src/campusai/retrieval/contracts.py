"""Versioned public contracts for Phase 6 retrieval."""

from __future__ import annotations

from typing import Any


RETRIEVAL_SCHEMA_VERSION = "retrieval-public-v1"
INDEX_SCHEMA_VERSION = "hybrid-index-v2"
RETRIEVAL_MODES = {
    "auto", "exact_code", "exact_course", "bm25", "dense",
    "hybrid", "hybrid_rrf", "rerank", "hybrid_rerank",
}
FILTER_FIELDS = {
    "institution", "program", "course_code", "academic_year",
    "semester", "document_type", "language",
}


class RetrievalContractError(ValueError):
    """Raised when a query/filter cannot satisfy the public contract."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def validate_filters(filters: dict[str, Any] | None) -> dict[str, Any]:
    if filters is None:
        return {}
    if not isinstance(filters, dict):
        raise RetrievalContractError("filters_not_object", "filters must be an object")
    normalized: dict[str, Any] = {}
    for key, value in filters.items():
        if key not in FILTER_FIELDS:
            raise RetrievalContractError("unsupported_filter", f"unsupported retrieval filter: {key}")
        if value is None or isinstance(value, (list, dict, tuple, set)):
            raise RetrievalContractError("invalid_filter_value", f"invalid value for filter: {key}")
        if key == "academic_year":
            text = str(value).strip()
            if not text.isdigit() or len(text) != 4:
                raise RetrievalContractError("invalid_academic_year", "academic_year must be a four-digit year")
            normalized[key] = text
        else:
            text = str(value).strip()
            if not text:
                raise RetrievalContractError("empty_filter_value", f"empty value for filter: {key}")
            normalized[key] = text
    return normalized


def validate_result(result: object) -> tuple[bool, tuple[str, ...]]:
    errors: list[str] = []
    for field in ("chunk_id", "doc_id", "content", "content_type", "retriever"):
        if not isinstance(getattr(result, field, None), str) or not getattr(result, field, "").strip():
            errors.append(f"{field}_invalid")
    if not isinstance(getattr(result, "page", None), int) or getattr(result, "page", 0) < 1:
        errors.append("page_invalid")
    page_range = getattr(result, "page_range", None)
    if not isinstance(page_range, tuple) or len(page_range) != 2 or not page_range[0] <= getattr(result, "page", 0) <= page_range[1]:
        errors.append("page_range_invalid")
    if not isinstance(getattr(result, "score", None), (int, float)):
        errors.append("score_invalid")
    if not isinstance(getattr(result, "rank", None), int) or getattr(result, "rank", 0) < 1:
        errors.append("rank_invalid")
    if not isinstance(getattr(result, "metadata", None), dict):
        errors.append("metadata_invalid")
    return not errors, tuple(errors)
