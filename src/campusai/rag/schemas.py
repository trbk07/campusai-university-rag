"""Strict Phase 5 response contract."""

from __future__ import annotations

from typing import NotRequired, TypedDict

PUBLIC_SCHEMA_VERSION = "phase5-public-v2"
SCHEMA_VERSION = "phase5-internal-v2"
PUBLIC_FIELDS = {"answer", "citations", "confidence", "abstained", "claims", "abstention_reason", "schema_version"}
INTERNAL_FIELDS = {
    "reason", "cache_hit", "evidence_status", "confidence_score",
    "schema_version", "confidence_policy_version", "policy_version",
    "trace_id", "source_versions", "source_manifest_hash", "cache_key",
}


class PublicResponse(TypedDict):
    answer: str
    citations: list[dict]
    confidence: str
    abstained: bool
    claims: NotRequired[list[dict]]
    abstention_reason: NotRequired[str | None]


class InternalGroundingTrace(TypedDict):
    reason: str | None
    evidence_status: str
    confidence_score: float | None
    schema_version: str
    confidence_policy_version: str


def validate_response(payload: object, *, include_internal: bool = False) -> tuple[bool, tuple[str, ...]]:
    if not isinstance(payload, dict):
        return False, ("response_not_object",)
    errors = []
    allowed = PUBLIC_FIELDS | (INTERNAL_FIELDS if include_internal else set())
    errors.extend(f"unknown_{key}" for key in payload if key not in allowed)
    for field in ("answer", "citations", "confidence", "abstained"):
        if field not in payload:
            errors.append(f"missing_{field}")
    if "schema_version" in payload and payload["schema_version"] not in {PUBLIC_SCHEMA_VERSION, SCHEMA_VERSION}:
        errors.append("schema_version_invalid")
    if include_internal and payload.get("schema_version") not in {SCHEMA_VERSION, PUBLIC_SCHEMA_VERSION}:
        errors.append("internal_schema_version_invalid")
    if not isinstance(payload.get("answer"), str) or not payload.get("answer", "").strip():
        errors.append("answer_invalid")
    if not isinstance(payload.get("citations"), list):
        errors.append("citations_invalid")
    if payload.get("confidence") not in {"high", "medium", "low"}:
        errors.append("confidence_invalid")
    if not isinstance(payload.get("abstained"), bool):
        errors.append("abstained_invalid")
    if isinstance(payload.get("citations"), list):
        for index, citation in enumerate(payload["citations"]):
            if not isinstance(citation, dict) or not isinstance(citation.get("chunk_id"), str) or not isinstance(citation.get("page"), int):
                errors.append(f"citation_{index}_invalid")
    if "abstained" in payload:
        if payload["abstained"] and not (payload.get("abstention_reason") or payload.get("reason")):
            errors.append("abstention_reason_missing")
        if not payload["abstained"] and payload.get("abstention_reason"):
            errors.append("unexpected_abstention_reason")
    if isinstance(payload.get("claims"), list):
        citation_ids = {item.get("chunk_id") for item in payload.get("citations", []) if isinstance(item, dict)}
        for index, claim in enumerate(payload["claims"]):
            if not isinstance(claim, dict) or not isinstance(claim.get("text"), str):
                errors.append(f"claim_{index}_invalid")
                continue
            if claim.get("status") not in {None, "supported", "partial", "partially_supported", "unsupported", "contradicted", "ambiguous"}:
                errors.append(f"claim_{index}_status_invalid")
            if not include_internal and any(item not in citation_ids for item in claim.get("citation_ids", [])):
                errors.append(f"claim_{index}_citation_unknown")
    if payload.get("confidence_score") is not None and not 0 <= payload["confidence_score"] <= 1:
        errors.append("confidence_score_invalid")
    return not errors, tuple(errors)
