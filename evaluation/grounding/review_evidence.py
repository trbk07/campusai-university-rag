"""Verify independent human or explicitly authorized AI/owner review evidence."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

from evaluation.grounding.repair_benchmark import stable_hash

AI_REVIEW_POLICY = "phase5-ai-owner-v1"
PHASE5_ACCEPTANCE = "phase5_acceptance"


def _exposure_exception(exposure: object, signoff: dict, acceptance_scope: str) -> bool:
    """Owner acceptance of exposure is never evidence of a fresh holdout."""
    owner = signoff.get("owner_approval") or {}
    return (acceptance_scope == PHASE5_ACCEPTANCE
            and signoff.get("review_type") == "independent_ai_owner" and isinstance(exposure, dict)
            and exposure.get("acceptance_scope") == PHASE5_ACCEPTANCE
            and exposure.get("holdout_fresh") is False
            and exposure.get("exposure_status") == "previously_exposed"
            and exposure.get("fresh_holdout_required_for_public_release") is True
            and exposure.get("reviewer_id") == owner.get("owner_id")
            and _text(exposure.get("decision_reference"))
            and _text(exposure.get("decision_quote"))
            and _dated(exposure.get("signed_at")))


def review_bundle_sha256(signoff: dict) -> str:
    """Bind the concrete review, excluding the later owner approval itself."""
    return stable_hash({field: signoff.get(field) for field in (
        "review_policy", "benchmark_sha256", "creator_ids", "reviewers",
        "row_decisions", "review_artifacts", "exposure_review", "owner_authorization")})


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _dated(value: object) -> bool:
    if not _text(value):
        return False
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


def _bound_path(root: Path, value: object) -> Path | None:
    if not _text(value):
        return None
    path = (root / value).resolve()
    return path if path.is_relative_to(root.resolve()) and path.is_file() else None


def annotation_sha256(row: dict) -> str:
    return stable_hash({field: row.get(field) for field in (
        "id", "question", "answerable", "gold_claims", "gold_abstention_reason", "source_group")})


def _empty_request_scope_errors(source_review: dict, row: dict, root: Path | None) -> list[str]:
    """An explicitly empty user scope is proved by the request, not a fake PDF."""
    from evaluation.grounding.collect_native_predictions import inference_request

    request = inference_request(row)
    scope = source_review.get("request_scope")
    if (row.get("answerable") is not False or row.get("category") != "no_evidence"
            or row.get("gold_abstention_reason") != "no_evidence_found"
            or row.get("gold_claims") != [] or request.get("doc_ids") != []
            or request.get("history") not in (None, [])
            or request.get("selected_text") not in (None, "")
            or source_review.get("scope") != "retrieval_scope"
            or source_review.get("sources") != []
            or not isinstance(scope, dict)
            or scope.get("finding") != "empty_selected_document_scope"
            or scope.get("request_sha256") != stable_hash(request)):
        return ["independent_ai_empty_request_scope_invalid"]
    if root is None:
        return ["independent_ai_physical_evidence_root_missing"]
    artifact = _bound_path(root, scope.get("path"))
    if artifact is None or hashlib.sha256(artifact.read_bytes()).hexdigest() != scope.get("sha256"):
        return ["independent_ai_request_scope_binding_missing_or_stale"]
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    if payload != {"id": row["id"], "request": request}:
        return ["independent_ai_request_scope_content_invalid"]
    return []


def validate_independent_review(signoff: object, rows: list[dict], *,
                                benchmark_sha256: str | None = None,
                                root: Path | None = None,
                                acceptance_scope: str = "public_release") -> list[str]:
    try:
        return _validate_independent_review(signoff, rows, benchmark_sha256=benchmark_sha256, root=root,
                                           acceptance_scope=acceptance_scope)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RuntimeError):
        return ["independent_review_evidence_invalid"]


def _validate_independent_review(signoff: object, rows: list[dict], *,
                                 benchmark_sha256: str | None, root: Path | None,
                                 acceptance_scope: str) -> list[str]:
    if not isinstance(signoff, dict):
        return ["independent_annotation_signoff_missing"]
    errors = []
    if benchmark_sha256 is not None and signoff.get("benchmark_sha256") != benchmark_sha256:
        errors.append("independent_review_benchmark_checksum_mismatch")
    ai_review = signoff.get("review_type") == "independent_ai_owner"
    if not ai_review and any(field in signoff for field in ("review_policy", "review_artifacts", "owner_authorization")):
        errors.append("annotation_review_type_evidence_mismatch")
    if signoff.get("status") != "approved" or (not ai_review and signoff.get("review_type") != "independent_human"):
        errors.append("independent_ai_approval_missing" if ai_review else "independent_human_approval_missing")
    if ai_review and signoff.get("review_policy") != AI_REVIEW_POLICY:
        errors.append("independent_ai_review_policy_invalid")
    count = len(rows)
    for field in ("records_total", "records_reviewed", "records_approved"):
        if type(signoff.get(field)) is not int or signoff[field] != count:
            errors.append(f"annotation_{field}_population_mismatch")
    creators = signoff.get("creator_ids")
    if not isinstance(creators, list) or not creators or any(not isinstance(item, str) or not item.strip() for item in creators):
        errors.append("annotation_creator_ids_missing")
        creators = []
    reviewers = signoff.get("reviewers")
    approved_reviewers = set()
    if not isinstance(reviewers, list) or not reviewers:
        errors.append("annotation_reviewers_missing")
        reviewers = []
    for reviewer in reviewers:
        if (not isinstance(reviewer, dict) or not isinstance(reviewer.get("id"), str)
                or not reviewer["id"].strip() or reviewer.get("reviewer_type") != ("ai" if ai_review else "human")
                or reviewer.get("independent") is not True
                or not isinstance(reviewer.get("attestation"), str) or not reviewer["attestation"].strip()
                or not isinstance(reviewer.get("signed_at"), str) or not reviewer["signed_at"].strip()):
            errors.append("annotation_reviewer_not_independently_attested")
            continue
        if ai_review and (not _text(reviewer.get("task_id")) or not _text(reviewer.get("model_id"))
                          or reviewer.get("source_audit_independent") is not True
                          or not _dated(reviewer.get("signed_at"))):
            errors.append("independent_ai_reviewer_identity_or_source_audit_missing")
        if reviewer["id"] in creators:
            errors.append("annotation_creator_reviewer_overlap")
        if reviewer["id"] in approved_reviewers:
            errors.append("annotation_reviewer_duplicate")
        approved_reviewers.add(reviewer["id"])
        if not ai_review and any(field in reviewer for field in ("model_id", "source_audit_independent")):
            errors.append("annotation_review_type_evidence_mismatch")
    exposure = signoff.get("exposure_review")
    exposed_acceptance = _exposure_exception(exposure, signoff, acceptance_scope)
    holdout_ids = sorted(row["id"] for row in rows if row.get("split") == "holdout")
    if (not isinstance(exposure, dict) or exposure.get("status") != "approved"
            or (exposure.get("holdout_fresh") is not True and not exposed_acceptance)
            or exposure.get("holdout_ids_sha256") != stable_hash(holdout_ids)
            or not isinstance(exposure.get("reviewer_id"), str)
            or (exposure.get("reviewer_id") not in approved_reviewers and not exposed_acceptance)
            or not isinstance(exposure.get("signed_at"), str) or not exposure["signed_at"].strip()
            or not isinstance(exposure.get("evidence_reference"), str) or not exposure["evidence_reference"].strip()):
        errors.append("independent_holdout_exposure_review_missing_or_stale")
    decisions = signoff.get("row_decisions")
    if not isinstance(decisions, list):
        return sorted(set(errors + ["independent_row_decisions_missing"]))
    expected = {row["id"]: annotation_sha256(row) for row in rows}
    seen = set()
    for decision in decisions:
        if not isinstance(decision, dict) or not isinstance(decision.get("id"), str):
            errors.append("independent_row_decision_invalid")
            continue
        identifier = decision["id"]
        if identifier in seen:
            errors.append("independent_row_decision_duplicate")
        seen.add(identifier)
        if (decision.get("status") != "approved" or not isinstance(decision.get("reviewer_id"), str)
                or decision.get("reviewer_id") not in approved_reviewers
                or not isinstance(decision.get("signed_at"), str) or not decision["signed_at"].strip()
                or decision.get("annotation_sha256") != expected.get(identifier)):
            errors.append("independent_row_decision_unapproved_or_stale")
    if seen != set(expected):
        errors.append("independent_row_decision_population_mismatch")
    if ai_review:
        errors.extend(_validate_ai_evidence(signoff, rows, root, acceptance_scope))
    return sorted(set(errors))


def _validate_ai_evidence(signoff: dict, rows: list[dict], root: Path | None,
                          acceptance_scope: str) -> list[str]:
    errors = []
    benchmark_hash = signoff.get("benchmark_sha256")
    if (not isinstance(benchmark_hash, str) or len(benchmark_hash) != 64
            or any(char not in "0123456789abcdef" for char in benchmark_hash)):
        errors.append("independent_ai_benchmark_checksum_invalid")
    authorization = signoff.get("owner_authorization")
    if (not isinstance(authorization, dict) or authorization.get("status") != "authorized"
            or authorization.get("review_policy") != AI_REVIEW_POLICY
            or authorization.get("scope") != "replace_independent_human_with_ai_owner"
            or not _text(authorization.get("owner_id"))
            or not _text(authorization.get("decision_reference"))
            or not _dated(authorization.get("authorized_at"))):
        errors.append("independent_ai_owner_policy_authorization_missing")
        authorization = {}
    approval = signoff.get("owner_approval")
    if (not isinstance(approval, dict) or approval.get("status") != "approved"
            or not _text(approval.get("owner_id")) or approval.get("owner_id") != authorization.get("owner_id")
            or not _text(approval.get("decision_reference"))
            or approval.get("decision_reference") == authorization.get("decision_reference")
            or not _dated(approval.get("signed_at"))
            or approval.get("benchmark_sha256") != signoff.get("benchmark_sha256")
            or approval.get("review_bundle_sha256") != review_bundle_sha256(signoff)):
        errors.append("independent_ai_owner_final_approval_missing_or_stale")
    elif (datetime.fromisoformat(approval["signed_at"].replace("Z", "+00:00"))
          < datetime.fromisoformat(authorization["authorized_at"].replace("Z", "+00:00"))):
        errors.append("independent_ai_owner_approval_predates_authorization")
    elif any(_dated(decision.get("signed_at")) and
             datetime.fromisoformat(approval["signed_at"].replace("Z", "+00:00")) <
             datetime.fromisoformat(decision["signed_at"].replace("Z", "+00:00"))
             for decision in signoff.get("row_decisions", [])):
        errors.append("independent_ai_owner_approval_predates_review")

    row_by_id = {row["id"]: row for row in rows}
    for decision in signoff.get("row_decisions", []):
        row = row_by_id.get(decision.get("id"))
        if row is None:
            continue
        factual = row.get("answerable") is True
        source_review = decision.get("source_review")
        if (decision.get("decision_type") != ("factual" if factual else "abstention")
                or not _dated(decision.get("signed_at")) or not isinstance(source_review, dict)
                or source_review.get("status") != "verified"
                or source_review.get("finding") != ("supports_gold" if factual else "supports_abstention")
                or source_review.get("scope") not in {"cited_pages", "retrieval_scope", "full_documents"}
                or not _text(source_review.get("rationale"))):
            errors.append("independent_ai_row_source_finding_unresolved")
            continue
        if (row.get("gold_abstention_reason") == "document_does_not_mention"
                and source_review.get("scope") != "full_documents"):
            errors.append("independent_ai_absence_scope_insufficient")
        sources = source_review.get("sources")
        if sources == [] and "request_scope" in source_review:
            errors.extend(_empty_request_scope_errors(source_review, row, root))
            continue
        if not isinstance(sources, list) or not sources:
            errors.append("independent_ai_row_sources_missing")
            continue
        coordinates = set()
        for source in sources:
            if (not isinstance(source, dict) or not _text(source.get("doc_id"))
                    or not _text(source.get("finding")) or not isinstance(source.get("pages"), list)
                    or not source["pages"] or any(type(page) is not int or page < 1 for page in source["pages"])):
                errors.append("independent_ai_source_binding_invalid")
                continue
            coordinates.update((source["doc_id"], page) for page in source["pages"])
            if root is not None:
                path = _bound_path(root, source.get("path"))
                if path is None or hashlib.sha256(path.read_bytes()).hexdigest() != source.get("sha256"):
                    errors.append("independent_ai_source_checksum_mismatch")
                elif path.suffix.lower() == ".pdf":
                    import pymupdf
                    with pymupdf.open(path) as pdf:
                        if (max(source["pages"]) > len(pdf) or
                                (source_review["scope"] == "full_documents"
                                 and set(source["pages"]) != set(range(1, len(pdf) + 1)))):
                            errors.append("independent_ai_source_page_scope_invalid")
        gold_coordinates = {(evidence["doc_id"], evidence["page"])
                            for claim in row.get("gold_claims", []) for evidence in claim.get("evidence", [])}
        if factual and (not gold_coordinates or not gold_coordinates <= coordinates):
            errors.append("independent_ai_gold_source_coverage_missing")
        if row.get("category") == "temporal/stale_source":
            temporal = decision.get("temporal_review")
            abstention_resolves_scope = (not factual and isinstance(temporal, dict)
                and temporal.get("effective_date_status") == "not_determinable_for_question"
                and temporal.get("conclusion") == "abstention_supported")
            if (isinstance(temporal, dict) and temporal.get("effective_date_status")
                    == "not_established_for_requested_period"):
                requested = temporal.get("requested_period")
                requested_years = set(re.findall(r"\b(?:19|20|21)\d{2}\b", requested)) if _text(requested) else set()
                question_years = set(re.findall(r"\b(?:19|20|21)\d{2}\b", str(row.get("question", ""))))
                period = temporal.get("source_period")
                period_state = temporal.get("source_period_status")
                source_scope_known = (
                    period_state == "established_in_source" and _text(period)
                    and not any(marker in period.casefold() for marker in ("unknown", "unverified", "review_required")))
                source_scope_undated = period_state == "undated_in_reviewed_source" and period is None
                period_abstention = (not factual and source_review.get("scope") == "full_documents"
                    and temporal.get("conclusion") == "abstention_supported"
                    and requested_years and requested_years <= question_years
                    and (source_scope_known or source_scope_undated))
                if not period_abstention:
                    errors.append("independent_ai_temporal_period_scope_invalid")
                abstention_resolves_scope = bool(period_abstention)
            if (not isinstance(temporal, dict) or temporal.get("status") != "resolved"
                    or not _text(temporal.get("basis"))
                    or (not factual and not abstention_resolves_scope)
                    or (not abstention_resolves_scope and
                        (not _text(temporal.get("effective_date"))
                         or any(marker in temporal["effective_date"].casefold()
                                for marker in ("unknown", "unverified", "review_required"))))):
                errors.append("independent_ai_temporal_review_unresolved")

    if root is None:
        errors.append("independent_ai_physical_evidence_root_missing")
        return errors
    exposure = signoff.get("exposure_review")
    audit_path = _bound_path(root, exposure.get("evidence_reference")) if isinstance(exposure, dict) else None
    if audit_path is None or hashlib.sha256(audit_path.read_bytes()).hexdigest() != exposure.get("evidence_sha256"):
        errors.append("independent_ai_exposure_audit_binding_missing_or_stale")
    else:
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        exposed_acceptance = (_exposure_exception(exposure, signoff, acceptance_scope)
                              and _exposure_exception(audit, signoff, acceptance_scope)
                              and all(audit.get(key) == exposure.get(key) for key in
                                      ("decision_reference", "decision_quote", "signed_at")))
        holdout_ids = sorted(row["id"] for row in rows if row.get("split") == "holdout")
        if (not isinstance(audit, dict) or audit.get("status") != "approved"
                or audit.get("benchmark_sha256") != signoff.get("benchmark_sha256")
                or audit.get("reviewer_id") != exposure.get("reviewer_id")
                or (audit.get("holdout_fresh") is not True and not exposed_acceptance)
                or audit.get("holdout_ids") != holdout_ids
                or audit.get("holdout_ids_sha256") != stable_hash(holdout_ids)
                or (audit.get("used_for_tuning") is not False and not exposed_acceptance)
                or not isinstance(audit.get("evidence_references"), list) or not audit["evidence_references"]
                or any(not _text(value) for value in audit["evidence_references"])):
            errors.append("independent_ai_exposure_audit_content_invalid")
    artifacts = signoff.get("review_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return errors + ["independent_ai_review_artifacts_missing"]
    reviewers = {reviewer["id"]: reviewer for reviewer in signoff.get("reviewers", [])}
    bound_reviewers = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict) or artifact.get("reviewer_id") not in reviewers:
            errors.append("independent_ai_review_artifact_invalid")
            continue
        reviewer_id = artifact["reviewer_id"]
        if reviewer_id in bound_reviewers:
            errors.append("independent_ai_review_artifact_duplicate")
        bound_reviewers.add(reviewer_id)
        path = _bound_path(root, artifact.get("path"))
        if path is None or hashlib.sha256(path.read_bytes()).hexdigest() != artifact.get("sha256"):
            errors.append("independent_ai_review_artifact_checksum_mismatch")
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        reviewer = reviewers[reviewer_id]
        decisions = [decision for decision in signoff.get("row_decisions", []) if decision.get("reviewer_id") == reviewer_id]
        if (not isinstance(payload, dict) or payload.get("schema_version") != "phase5-ai-source-review-v1"
                or payload.get("review_policy") != AI_REVIEW_POLICY
                or payload.get("benchmark_sha256") != signoff.get("benchmark_sha256")
                or payload.get("reviewer_id") != reviewer_id or payload.get("task_id") != reviewer.get("task_id")
                or payload.get("model_id") != reviewer.get("model_id")
                or payload.get("row_decisions") != decisions or not decisions):
            errors.append("independent_ai_review_artifact_content_mismatch")
    if bound_reviewers != set(reviewers):
        errors.append("independent_ai_review_artifact_population_mismatch")
    return errors
