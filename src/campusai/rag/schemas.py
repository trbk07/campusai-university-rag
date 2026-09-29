"""Strict Phase 5 response contract."""

from __future__ import annotations

from typing import NotRequired, TypedDict

from .abstention import CANONICAL_ABSTENTION_REASONS

PUBLIC_SCHEMA_VERSION = "grounding-public-v2"
SCHEMA_VERSION = "grounding-internal-v2"
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
    allowed_schema_versions = {SCHEMA_VERSION, PUBLIC_SCHEMA_VERSION} if include_internal else {PUBLIC_SCHEMA_VERSION}
    if "schema_version" in payload and payload["schema_version"] not in allowed_schema_versions:
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
            if (not isinstance(citation, dict)
                    or not isinstance(citation.get("chunk_id"), str)
                    or not isinstance(citation.get("page"), int)
                    or citation.get("page", 0) < 1):
                errors.append(f"citation_{index}_invalid")
    if "abstained" in payload:
        if payload["abstained"] and not payload.get("abstention_reason") and not (include_internal and payload.get("reason")):
            errors.append("abstention_reason_missing")
        if not payload["abstained"] and payload.get("abstention_reason"):
            errors.append("unexpected_abstention_reason")
        if payload["abstained"] and payload.get("abstention_reason") not in CANONICAL_ABSTENTION_REASONS:
            errors.append("abstention_reason_invalid")
    if isinstance(payload.get("claims"), list):
        citation_ids = {item.get("chunk_id") for item in payload.get("citations", []) if isinstance(item, dict)}
        for index, claim in enumerate(payload["claims"]):
            if not isinstance(claim, dict) or not isinstance(claim.get("text"), str) or not claim.get("text", "").strip():
                errors.append(f"claim_{index}_invalid")
                continue
            if not isinstance(claim.get("citation_ids", []), list):
                errors.append(f"claim_{index}_citations_invalid")
            elif any(not isinstance(item, str) for item in claim.get("citation_ids", [])):
                errors.append(f"claim_{index}_citation_id_invalid")
            elif claim.get("status") == "supported" and not claim.get("citation_ids"):
                errors.append(f"claim_{index}_citation_missing")
            if claim.get("status") not in {None, "supported", "partial", "partially_supported", "unsupported", "contradicted", "ambiguous"}:
                errors.append(f"claim_{index}_status_invalid")
            if not include_internal and any(item not in citation_ids for item in claim.get("citation_ids", [])):
                errors.append(f"claim_{index}_citation_unknown")
    if payload.get("confidence_score") is not None and not 0 <= payload["confidence_score"] <= 1:
        errors.append("confidence_score_invalid")
    return not errors, tuple(errors)


def validate_release_response(payload: object) -> tuple[bool, tuple[str, ...]]:
    """Validate the fail-closed public contract used by release evaluation.

    ``validate_response`` remains permissive enough for backwards-compatible
    adapters.  Runtime/release paths use this stricter validator so a fixture
    cannot pass by omitting quote or claim-to-citation provenance.
    """
    valid, base_errors = validate_response(payload)
    if not isinstance(payload, dict):
        return False, base_errors
    errors = list(base_errors)
    if payload.get("schema_version") != PUBLIC_SCHEMA_VERSION:
        errors.append("schema_version_required")
    citations = payload.get("citations")
    if not isinstance(citations, list):
        return False, tuple(dict.fromkeys(errors))
    citation_ids = set()
    allowed_citation_fields = {"chunk_id", "doc_id", "page", "page_range", "quote", "section_path", "source_name", "table_id"}
    for index, citation in enumerate(citations):
        if not isinstance(citation, dict):
            continue
        unknown = set(citation) - allowed_citation_fields
        errors.extend(f"citation_{index}_unknown_{field}" for field in sorted(unknown))
        chunk_id = citation.get("chunk_id")
        if chunk_id in citation_ids:
            errors.append(f"citation_{index}_duplicate")
        citation_ids.add(chunk_id)
        for field in ("doc_id", "page_range", "quote", "source_name"):
            if field not in citation or citation.get(field) in (None, "", []):
                errors.append(f"citation_{index}_{field}_missing")
        page_range = citation.get("page_range")
        if (not isinstance(page_range, list) or len(page_range) != 2
                or not all(isinstance(value, int) and value >= 1 for value in page_range)
                or isinstance(citation.get("page"), int) and not page_range[0] <= citation["page"] <= page_range[1]):
            errors.append(f"citation_{index}_page_range_invalid")
    claims = payload.get("claims")
    if not isinstance(claims, list):
        errors.append("claims_required")
    else:
        mapped_ids = set()
        allowed_claim_fields = {"claim_id", "text", "type", "citation_ids"}
        for index, claim in enumerate(claims):
            if not isinstance(claim, dict):
                continue
            unknown = set(claim) - allowed_claim_fields
            errors.extend(f"claim_{index}_unknown_{field}" for field in sorted(unknown))
            ids = claim.get("citation_ids")
            if not isinstance(ids, list) or not ids:
                errors.append(f"claim_{index}_citation_missing")
                continue
            unknown = [item for item in ids if item not in citation_ids]
            if unknown:
                errors.append(f"claim_{index}_citation_unknown")
            mapped_ids.update(ids)
        unclaimed = citation_ids - mapped_ids
        if unclaimed:
            errors.append("citation_without_claim_mapping")
    if not payload.get("abstained") and payload.get("abstention_reason") is not None:
        errors.append("unexpected_abstention_reason")
    return not errors, tuple(dict.fromkeys(errors))
