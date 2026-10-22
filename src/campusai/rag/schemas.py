"""Strict Phase 5 response contract."""

from __future__ import annotations

import math
from typing import NotRequired, TypedDict

from .abstention import CANONICAL_ABSTENTION_REASONS

PUBLIC_SCHEMA_VERSION = "grounding-public-v2"
SCHEMA_VERSION = "grounding-internal-v2"
PUBLIC_FIELDS = {"answer", "citations", "confidence", "abstained", "claims", "abstention_reason", "schema_version"}
INTERNAL_FIELDS = {
    "reason", "cache_hit", "evidence_status", "confidence_score", "raw_confidence_score",
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
    if "schema_version" in payload and (not isinstance(payload["schema_version"], str) or payload["schema_version"] not in allowed_schema_versions):
        errors.append("schema_version_invalid")
    if include_internal and (not isinstance(payload.get("schema_version"), str) or payload.get("schema_version") not in allowed_schema_versions):
        errors.append("internal_schema_version_invalid")
    if not isinstance(payload.get("answer"), str) or not payload.get("answer", "").strip():
        errors.append("answer_invalid")
    if not isinstance(payload.get("citations"), list):
        errors.append("citations_invalid")
    if not isinstance(payload.get("confidence"), str) or payload["confidence"] not in {"high", "medium", "low"}:
        errors.append("confidence_invalid")
    if not isinstance(payload.get("abstained"), bool):
        errors.append("abstained_invalid")
    if isinstance(payload.get("citations"), list):
        for index, citation in enumerate(payload["citations"]):
            if (not isinstance(citation, dict)
                    or not isinstance(citation.get("chunk_id"), str)
                    or not citation.get("chunk_id", "").strip()
                    or type(citation.get("page")) is not int
                    or citation.get("page", 0) < 1):
                errors.append(f"citation_{index}_invalid")
    if "abstained" in payload:
        if payload["abstained"] and not payload.get("abstention_reason") and not (include_internal and payload.get("reason")):
            errors.append("abstention_reason_missing")
        if not payload["abstained"] and payload.get("abstention_reason"):
            errors.append("unexpected_abstention_reason")
        if payload["abstained"] and (not isinstance(payload.get("abstention_reason"), str) or payload.get("abstention_reason") not in CANONICAL_ABSTENTION_REASONS):
            errors.append("abstention_reason_invalid")
    if payload.get("abstention_reason") is not None and not isinstance(payload["abstention_reason"], str):
        errors.append("abstention_reason_invalid")
    if "claims" in payload and not isinstance(payload["claims"], list):
        errors.append("claims_invalid")
    if isinstance(payload.get("claims"), list):
        citation_values = payload.get("citations")
        citation_ids = {
            item.get("chunk_id") for item in citation_values if isinstance(item, dict) and isinstance(item.get("chunk_id"), str)
        } if isinstance(citation_values, list) else set()
        for index, claim in enumerate(payload["claims"]):
            if not isinstance(claim, dict) or not isinstance(claim.get("text"), str) or not claim.get("text", "").strip():
                errors.append(f"claim_{index}_invalid")
                continue
            ids = claim.get("citation_ids", [])
            if not isinstance(ids, list):
                errors.append(f"claim_{index}_citations_invalid")
            elif any(not isinstance(item, str) or not item.strip() for item in ids):
                errors.append(f"claim_{index}_citation_id_invalid")
            elif claim.get("status") == "supported" and not ids:
                errors.append(f"claim_{index}_citation_missing")
            if claim.get("status") is not None and (not isinstance(claim["status"], str) or claim["status"] not in {"supported", "partial", "partially_supported", "unsupported", "contradicted", "ambiguous"}):
                errors.append(f"claim_{index}_status_invalid")
            if not include_internal and isinstance(ids, list) and any(not isinstance(item, str) or item not in citation_ids for item in ids):
                errors.append(f"claim_{index}_citation_unknown")
    for field in ("confidence_score", "raw_confidence_score"):
        value = payload.get(field)
        if value is not None and (type(value) not in {int, float} or not math.isfinite(value) or not 0 <= value <= 1):
            errors.append(f"{field}_invalid")
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
        if isinstance(chunk_id, str) and chunk_id in citation_ids:
            errors.append(f"citation_{index}_duplicate")
        if isinstance(chunk_id, str):
            citation_ids.add(chunk_id)
        for field in ("doc_id", "page_range", "quote", "source_name"):
            if field not in citation or citation.get(field) in (None, "", []):
                errors.append(f"citation_{index}_{field}_missing")
        for field in ("chunk_id", "doc_id", "quote", "source_name"):
            if field in citation and (not isinstance(citation.get(field), str) or not citation[field].strip()):
                errors.append(f"citation_{index}_{field}_invalid")
        for field in ("section_path", "table_id"):
            if field in citation and not isinstance(citation[field], str):
                errors.append(f"citation_{index}_{field}_invalid")
        page_range = citation.get("page_range")
        if (not isinstance(page_range, list) or len(page_range) != 2
                or not all(type(value) is int and value >= 1 for value in page_range)
                or page_range[0] > page_range[1]
                or type(citation.get("page")) is int and not page_range[0] <= citation["page"] <= page_range[1]):
            errors.append(f"citation_{index}_page_range_invalid")
    claims = payload.get("claims")
    if not isinstance(claims, list):
        errors.append("claims_required")
    else:
        mapped_ids = set()
        claim_ids = set()
        allowed_claim_fields = {"claim_id", "text", "type", "citation_ids"}
        for index, claim in enumerate(claims):
            if not isinstance(claim, dict):
                continue
            if "type" in claim and not isinstance(claim["type"], str):
                errors.append(f"claim_{index}_type_invalid")
            claim_id = claim.get("claim_id")
            if not isinstance(claim_id, str) or not claim_id.strip():
                errors.append(f"claim_{index}_id_invalid")
            elif claim_id in claim_ids:
                errors.append(f"claim_{index}_duplicate")
            else:
                claim_ids.add(claim_id)
            unknown = set(claim) - allowed_claim_fields
            errors.extend(f"claim_{index}_unknown_{field}" for field in sorted(unknown))
            ids = claim.get("citation_ids")
            if not isinstance(ids, list) or not ids or any(not isinstance(item, str) or not item.strip() for item in ids):
                errors.append(f"claim_{index}_citation_missing")
                continue
            unknown = [item for item in ids if item not in citation_ids]
            if unknown:
                errors.append(f"claim_{index}_citation_unknown")
            mapped_ids.update(ids)
        unclaimed = citation_ids - mapped_ids
        if unclaimed:
            errors.append("citation_without_claim_mapping")
        if payload.get("abstained") is False and (not claims or not citations):
            errors.append("answered_without_evidence")
        if payload.get("abstained") is True and (claims or citations):
            errors.append("abstention_publishes_evidence")
    if not payload.get("abstained") and payload.get("abstention_reason") is not None:
        errors.append("unexpected_abstention_reason")
    return not errors, tuple(dict.fromkeys(errors))
