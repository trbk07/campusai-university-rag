"""Fictional review fixtures; these are not owner approval or benchmark evidence."""
from copy import deepcopy
import hashlib
import json

import pytest

from evaluation.grounding.repair_benchmark import stable_hash
from evaluation.grounding.review_evidence import (
    AI_REVIEW_POLICY, annotation_sha256, review_bundle_sha256, validate_independent_review,
)


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def ai_review(tmp_path):
    source = tmp_path / "fictional-source.txt"
    source.write_text("Unit source: the fictional course has 3 credits.", encoding="utf-8")
    rows = [{"id": "fictional-unit", "question": "How many credits?", "split": "holdout",
             "answerable": True, "category": "answerable", "source_group": "fictional-doc",
             "gold_claims": [{"text": "3 credits", "evidence": [
                 {"doc_id": "fictional-doc", "page": 1, "quote": "3 credits"}]}]}]
    benchmark = tmp_path / "fictional-benchmark.jsonl"
    benchmark.write_text(json.dumps(rows[0]) + "\n", encoding="utf-8")
    reviewer = {"id": "fictional-ai-reviewer", "reviewer_type": "ai", "independent": True,
        "task_id": "/fictional/independent-review", "model_id": "fictional-unit-model",
        "source_audit_independent": True, "attestation": "Fictional unit evidence only.",
        "signed_at": "2026-10-16T12:00:00Z", "records_reviewed": 1}
    decision = {"id": rows[0]["id"], "status": "approved", "reviewer_id": reviewer["id"],
        "annotation_sha256": annotation_sha256(rows[0]), "signed_at": reviewer["signed_at"],
        "decision_type": "factual", "source_review": {"status": "verified", "finding": "supports_gold",
            "scope": "cited_pages", "rationale": "Fictional statement explicitly gives the count.",
            "sources": [{"doc_id": "fictional-doc", "path": source.name, "sha256": checksum(source),
                         "pages": [1], "finding": "Explicit credit count."}]}}
    signoff = {"status": "approved", "review_type": "independent_ai_owner", "review_policy": AI_REVIEW_POLICY,
        "benchmark_sha256": checksum(benchmark), "creator_ids": ["fictional-other-author"],
        "records_total": 1, "records_reviewed": 1, "records_approved": 1, "reviewers": [reviewer],
        "row_decisions": [decision], "exposure_review": {"status": "approved", "holdout_fresh": True,
            "holdout_ids_sha256": stable_hash([rows[0]["id"]]), "reviewer_id": reviewer["id"],
            "signed_at": reviewer["signed_at"], "evidence_reference": "fictional-exposure.json"},
        "owner_authorization": {"status": "authorized", "review_policy": AI_REVIEW_POLICY,
            "scope": "replace_independent_human_with_ai_owner", "owner_id": "fictional-unit-owner",
            "decision_reference": "fictional-policy-decision", "authorized_at": "2026-10-16T11:00:00Z"}}
    exposure = tmp_path / "fictional-exposure.json"
    exposure.write_text(json.dumps({"status": "approved", "benchmark_sha256": signoff["benchmark_sha256"],
        "reviewer_id": reviewer["id"], "holdout_fresh": True, "holdout_ids": [rows[0]["id"]],
        "holdout_ids_sha256": stable_hash([rows[0]["id"]]), "used_for_tuning": False,
        "evidence_references": ["Fictional sealed unit-case history; no real exposure attested."]}), encoding="utf-8")
    signoff["exposure_review"]["evidence_sha256"] = checksum(exposure)
    freeze_review(signoff, tmp_path)
    return tmp_path, rows, signoff


def freeze_review(signoff, root):
    reviewer = signoff["reviewers"][0]
    artifact = root / "fictional-ai-audit.json"
    artifact.write_text(json.dumps({"schema_version": "phase5-ai-source-review-v1",
        "review_policy": AI_REVIEW_POLICY, "benchmark_sha256": signoff["benchmark_sha256"],
        "reviewer_id": reviewer["id"], "task_id": reviewer["task_id"], "model_id": reviewer["model_id"],
        "row_decisions": signoff["row_decisions"]}), encoding="utf-8")
    signoff["review_artifacts"] = [{"path": artifact.name, "sha256": checksum(artifact), "reviewer_id": reviewer["id"]}]
    signoff["owner_approval"] = {"status": "approved", "owner_id": "fictional-unit-owner",
        "decision_reference": "fictional-final-decision", "signed_at": "2026-10-16T13:00:00Z",
        "benchmark_sha256": signoff["benchmark_sha256"], "review_bundle_sha256": review_bundle_sha256(signoff)}


def errors(fixture):
    root, rows, signoff = fixture
    return validate_independent_review(signoff, rows, benchmark_sha256=signoff["benchmark_sha256"], root=root)


def test_complete_ai_contract_with_physical_review_and_distinct_owner_approval(ai_review):
    assert errors(ai_review) == []


def exposed_owner_acceptance(fixture):
    root, rows, signoff = fixture
    exposure = signoff["exposure_review"]
    exposure.update(acceptance_scope="phase5_acceptance", holdout_fresh=False,
        exposure_status="previously_exposed", fresh_holdout_required_for_public_release=True,
        reviewer_id="fictional-unit-owner", signed_at="2026-10-16T13:00:00Z",
        decision_reference="fictional-exposure-decision", decision_quote="Accept exposure for Phase 5 only.")
    path = root / exposure["evidence_reference"]
    audit = json.loads(path.read_text(encoding="utf-8"))
    audit.update({key: value for key, value in exposure.items() if key not in
                  {"evidence_reference", "evidence_sha256"}})
    audit["used_for_tuning"] = True
    path.write_text(json.dumps(audit), encoding="utf-8")
    exposure["evidence_sha256"] = checksum(path)
    signoff["owner_approval"]["review_bundle_sha256"] = review_bundle_sha256(signoff)


def test_exposed_owner_acceptance_requires_explicit_scope_and_stays_blocked_for_public(ai_review):
    exposed_owner_acceptance(ai_review)
    root, rows, signoff = ai_review
    assert validate_independent_review(signoff, rows, root=root, acceptance_scope="phase5_acceptance") == []
    assert "independent_holdout_exposure_review_missing_or_stale" in errors(ai_review)
    from evaluation.grounding.validate_grounding_release import validate
    report = {"acceptance_scope": "phase5_acceptance", "annotation_signoff": signoff,
              "benchmark_sha256": signoff["benchmark_sha256"], "rows": []}
    assert "phase5_acceptance_is_not_public_release" in validate(report)
    assert "working_tree_dirty" in validate(report, acceptance_scope="phase5_acceptance")
    from evaluation.benchmarks.benchmark_schema import validate_release_records
    rows[0].update(fresh_holdout=False, exposure_status="previously_exposed")
    assert "row_0_holdout_previously_exposed" in validate_release_records(rows)
    assert "row_0_holdout_previously_exposed" not in validate_release_records(rows, acceptance_scope="phase5_acceptance")
    from evaluation.benchmarks.benchmark_schema import validate_release_records
    rows[0].update(fresh_holdout=False, exposure_status="previously_exposed")
    assert "row_0_holdout_previously_exposed" in validate_release_records(rows)
    assert "row_0_holdout_previously_exposed" not in validate_release_records(rows, acceptance_scope="phase5_acceptance")


@pytest.mark.parametrize("mutation", ["owner", "quote", "public-fresh", "physical", "bundle"])
def test_exposure_exception_cannot_replace_owner_or_physical_evidence(ai_review, mutation):
    exposed_owner_acceptance(ai_review)
    root, rows, signoff = ai_review
    exposure = signoff["exposure_review"]
    if mutation == "owner": exposure["reviewer_id"] = "fictional-unknown"
    elif mutation == "quote": exposure["decision_quote"] = ""
    elif mutation == "public-fresh": exposure["fresh_holdout_required_for_public_release"] = False
    elif mutation == "physical": (root / exposure["evidence_reference"]).unlink()
    elif mutation == "bundle": signoff["owner_approval"]["review_bundle_sha256"] = "stale"
    assert validate_independent_review(signoff, rows, root=root, acceptance_scope="phase5_acceptance")


def empty_scope_review(fixture):
    """Fictional owner/reviewer fixtures only, never real acceptance evidence."""
    from evaluation.grounding.collect_native_predictions import inference_request
    root, rows, signoff = fixture
    rows[0].update(question="Using only selected documents, what is the application fee?",
        answerable=False, category="no_evidence", selected_doc_ids=[], context=[],
        selected_text=None, gold_claims=[], gold_abstention_reason="no_evidence_found")
    request = inference_request(rows[0])
    path = root / "fictional-request.json"
    path.write_text(json.dumps({"id": rows[0]["id"], "request": request}), encoding="utf-8")
    decision = signoff["row_decisions"][0]
    decision.update(annotation_sha256=annotation_sha256(rows[0]), decision_type="abstention")
    decision["source_review"].update(finding="supports_abstention", scope="retrieval_scope",
        sources=[], rationale="The user selected no documents and supplied no contextual evidence.",
        request_scope={"finding": "empty_selected_document_scope", "request_sha256": stable_hash(request),
                       "path": path.name, "sha256": checksum(path)})
    freeze_review(signoff, root)
    return fixture


def test_empty_selected_scope_review_binds_actual_request_without_inventing_pdf(ai_review):
    assert errors(empty_scope_review(ai_review)) == []


@pytest.mark.parametrize("mutation", ["all-documents", "one-document", "history", "selected-text",
                                    "absence-reason", "factual", "wrong-scope", "wrong-hash"])
def test_empty_scope_review_cannot_bypass_source_audit(ai_review, mutation):
    root, rows, signoff = empty_scope_review(ai_review)
    row = rows[0]; review = signoff["row_decisions"][0]["source_review"]
    if mutation == "all-documents": row.pop("selected_doc_ids")
    elif mutation == "one-document": row["selected_doc_ids"] = ["fictional-doc"]
    elif mutation == "history": row["context"] = [{"role": "user", "content": "Previously supplied facts"}]
    elif mutation == "selected-text": row["selected_text"] = "Evidence supplied by the user"
    elif mutation == "absence-reason": row["gold_abstention_reason"] = "document_does_not_mention"
    elif mutation == "factual":
        row["answerable"] = True
        signoff["row_decisions"][0]["decision_type"] = "factual"
        review["finding"] = "supports_gold"
    elif mutation == "wrong-scope": review["scope"] = "full_documents"
    else: review["request_scope"]["request_sha256"] = "0" * 64
    signoff["row_decisions"][0]["annotation_sha256"] = annotation_sha256(row)
    freeze_review(signoff, root)
    assert "independent_ai_empty_request_scope_invalid" in errors(ai_review)


@pytest.mark.parametrize("mutation,expected", [
    ("missing", "independent_ai_request_scope_binding_missing_or_stale"),
    ("changed", "independent_ai_request_scope_binding_missing_or_stale"),
    ("rehashed", "independent_ai_request_scope_content_invalid"),
])
def test_empty_scope_requires_exact_physical_request_artifact(ai_review, mutation, expected):
    root, _rows, signoff = empty_scope_review(ai_review)
    path = root / "fictional-request.json"
    if mutation == "missing": path.unlink()
    else:
        path.write_text(json.dumps({"id": "another-case", "request": {"doc_ids": []}}), encoding="utf-8")
        if mutation == "rehashed":
            signoff["row_decisions"][0]["source_review"]["request_scope"]["sha256"] = checksum(path)
            freeze_review(signoff, root)
    assert expected in errors(ai_review)


@pytest.mark.parametrize("mutation,expected", [
    ("policy", "independent_ai_review_policy_invalid"),
    ("authorization", "independent_ai_owner_policy_authorization_missing"),
    ("blanket-approval", "independent_ai_owner_final_approval_missing_or_stale"),
    ("stale-owner", "independent_ai_owner_final_approval_missing_or_stale"),
    ("reviewer-human", "annotation_reviewer_not_independently_attested"),
    ("overlap", "annotation_creator_reviewer_overlap"),
    ("unresolved", "independent_ai_row_source_finding_unresolved"),
    ("wrong-page", "independent_ai_gold_source_coverage_missing"),
    ("artifact", "independent_ai_review_artifact_checksum_mismatch"),
    ("source", "independent_ai_source_checksum_mismatch"),
    ("exposed", "independent_holdout_exposure_review_missing_or_stale"),
])
def test_ai_contract_fails_closed_on_missing_stale_or_mislabeled_evidence(ai_review, mutation, expected):
    root, rows, signoff = ai_review
    if mutation == "policy": signoff["review_policy"] = "unapproved-policy"
    elif mutation == "authorization": signoff["owner_authorization"] = None
    elif mutation == "blanket-approval": signoff["owner_approval"]["decision_reference"] = "fictional-policy-decision"
    elif mutation == "stale-owner": signoff["owner_approval"]["review_bundle_sha256"] = "stale"
    elif mutation == "reviewer-human": signoff["reviewers"][0]["reviewer_type"] = "human"
    elif mutation == "overlap": signoff["creator_ids"] = [signoff["reviewers"][0]["id"]]
    elif mutation == "unresolved": signoff["row_decisions"][0]["source_review"]["status"] = "review_required"
    elif mutation == "wrong-page": signoff["row_decisions"][0]["source_review"]["sources"][0]["pages"] = [2]
    elif mutation == "artifact": (root / "fictional-ai-audit.json").write_text('{}')
    elif mutation == "source": (root / "fictional-source.txt").write_text('changed')
    elif mutation == "exposed": signoff["exposure_review"]["holdout_fresh"] = False
    assert expected in errors(ai_review)


def test_ai_review_requires_physical_verification_even_if_structurally_complete(ai_review):
    _root, rows, signoff = ai_review
    assert "independent_ai_physical_evidence_root_missing" in validate_independent_review(signoff, rows)


def test_ai_audit_cannot_be_relabeled_as_human_to_skip_owner_approval(ai_review):
    _root, _rows, signoff = ai_review
    signoff["review_type"] = "independent_human"
    signoff["reviewers"][0]["reviewer_type"] = "human"
    assert "annotation_review_type_evidence_mismatch" in errors(ai_review)


def test_owner_final_approval_cannot_predate_concrete_review(ai_review):
    _root, _rows, signoff = ai_review
    signoff["owner_approval"]["signed_at"] = "2026-10-16T11:30:00Z"
    assert "independent_ai_owner_approval_predates_review" in errors(ai_review)


def test_pending_ai_review_does_not_report_a_human_only_requirement(ai_review):
    _root, _rows, signoff = ai_review
    signoff["status"] = "pending"
    assert "independent_ai_approval_missing" in errors(ai_review)
    assert "independent_human_approval_missing" not in errors(ai_review)


def test_ai_exposure_audit_requires_physical_binding_and_true_freshness(ai_review):
    root, _rows, signoff = ai_review
    exposure = root / "fictional-exposure.json"
    payload = json.loads(exposure.read_text())
    payload["used_for_tuning"] = True
    exposure.write_text(json.dumps(payload))
    assert "independent_ai_exposure_audit_binding_missing_or_stale" in errors(ai_review)
    signoff["exposure_review"]["evidence_sha256"] = checksum(exposure)
    signoff["owner_approval"]["review_bundle_sha256"] = review_bundle_sha256(signoff)
    assert "independent_ai_exposure_audit_content_invalid" in errors(ai_review)


def test_review_artifact_content_cannot_be_changed_by_rehashing(ai_review):
    root, _rows, signoff = ai_review
    artifact = root / "fictional-ai-audit.json"
    payload = json.loads(artifact.read_text())
    payload["row_decisions"] = []
    artifact.write_text(json.dumps(payload))
    signoff["review_artifacts"][0]["sha256"] = checksum(artifact)
    signoff["owner_approval"]["review_bundle_sha256"] = review_bundle_sha256(signoff)
    assert "independent_ai_review_artifact_content_mismatch" in errors(ai_review)


def test_unresolved_temporal_gold_fails_but_reviewed_temporal_abstention_can_qualify(ai_review):
    root, rows, signoff = ai_review
    rows[0]["category"] = "temporal/stale_source"
    signoff["row_decisions"][0]["temporal_review"] = {"status": "resolved", "effective_date": "UNKNOWN", "basis": "No applicable date."}
    freeze_review(signoff, root)
    assert "independent_ai_temporal_review_unresolved" in errors(ai_review)
    rows[0].update(answerable=False, gold_claims=[], gold_abstention_reason="ambiguous_question")
    decision = signoff["row_decisions"][0]
    decision.update(annotation_sha256=annotation_sha256(rows[0]), decision_type="abstention",
        temporal_review={"status": "resolved", "effective_date": None,
            "effective_date_status": "not_determinable_for_question", "conclusion": "abstention_supported",
            "basis": "Question leaves the policy and cohort unspecified; abstention is justified."})
    decision["source_review"]["finding"] = "supports_abstention"
    freeze_review(signoff, root)
    assert errors(ai_review) == []


def test_document_absence_requires_full_source_scope(ai_review):
    root, rows, signoff = ai_review
    rows[0].update(answerable=False, gold_claims=[], gold_abstention_reason="document_does_not_mention")
    decision = signoff["row_decisions"][0]
    decision.update(annotation_sha256=annotation_sha256(rows[0]), decision_type="abstention")
    decision["source_review"]["finding"] = "supports_abstention"
    freeze_review(signoff, root)
    assert "independent_ai_absence_scope_insufficient" in errors(ai_review)


def requested_period_abstention(ai_review):
    root, rows, signoff = ai_review
    rows[0].update(question="Does this uploaded notice establish the policy for 2026?",
        category="temporal/stale_source", answerable=False, gold_claims=[],
        gold_abstention_reason="unsupported_claim")
    decision = signoff["row_decisions"][0]
    decision.update(annotation_sha256=annotation_sha256(rows[0]), decision_type="abstention",
        temporal_review={"status":"resolved", "effective_date":None,
            "effective_date_status":"not_established_for_requested_period",
            "requested_period":"2026", "source_period":"2022 round 2",
            "source_period_status":"established_in_source", "conclusion":"abstention_supported",
            "basis":"Fictional full-source audit establishes only the 2022 cycle; it cannot establish the requested 2026 policy."})
    decision["source_review"].update(finding="supports_abstention",scope="full_documents")
    freeze_review(signoff, root)
    return decision


def test_known_requested_period_can_support_abstention_without_inventing_effective_date(ai_review):
    requested_period_abstention(ai_review)
    assert errors(ai_review) == []


def test_undated_reviewed_source_can_leave_requested_period_unproved(ai_review):
    root, _rows, signoff = ai_review
    decision = requested_period_abstention(ai_review)
    decision["temporal_review"].update(source_period=None, source_period_status="undated_in_reviewed_source",
        basis="Fictional source has no date or applicability clause; full-source review does not establish 2026.")
    freeze_review(signoff, root)
    assert errors(ai_review) == []


@pytest.mark.parametrize("date_status", ["established_in_source", "issue_date_only"])
def test_negative_temporal_review_cannot_substitute_issue_date_for_scope_finding(ai_review, date_status):
    root, _rows, signoff = ai_review
    decision = requested_period_abstention(ai_review)
    decision["temporal_review"] = {"status": "resolved", "effective_date": "2022-07-15",
        "effective_date_status": date_status, "conclusion": "abstention_supported",
        "basis": "The source issue date is 2022-07-15; the requested year is not established."}
    freeze_review(signoff, root)
    assert "independent_ai_temporal_review_unresolved" in errors(ai_review)


@pytest.mark.parametrize("mutation", ["partial-scope", "missing-request", "wrong-request",
                                      "missing-source-period", "unknown-source-period", "factual", "wrong-conclusion"])
def test_requested_period_exception_fails_closed_on_insufficient_scope_or_binding(ai_review, mutation):
    root, rows, signoff = ai_review
    decision = requested_period_abstention(ai_review)
    temporal = decision["temporal_review"]
    if mutation == "partial-scope": decision["source_review"]["scope"] = "cited_pages"
    elif mutation == "missing-request": temporal.pop("requested_period")
    elif mutation == "wrong-request": temporal["requested_period"] = "2025"
    elif mutation == "missing-source-period": temporal.pop("source_period")
    elif mutation == "unknown-source-period": temporal["source_period"] = "UNKNOWN"
    elif mutation == "factual":
        rows[0].update(answerable=True,gold_claims=[{"text":"Fictional 2026 policy", "evidence":[{"doc_id":"fictional-doc","page":1}]}])
        decision.update(annotation_sha256=annotation_sha256(rows[0]),decision_type="factual")
        decision["source_review"]["finding"] = "supports_gold"
    elif mutation == "wrong-conclusion": temporal["conclusion"] = "policy_applies"
    # An arbitrary supplied date cannot bypass the special-status requirements.
    temporal["effective_date"] = "2022"
    freeze_review(signoff, root)
    assert "independent_ai_temporal_period_scope_invalid" in errors(ai_review)


@pytest.mark.parametrize("payload", [[], {"review_type": "independent_ai_owner", "reviewers": [None]},
                                     {"review_type": "independent_ai_owner", "creator_ids": [False]}])
def test_malformed_ai_evidence_returns_errors_without_crashing(payload):
    assert validate_independent_review(deepcopy(payload), [{"id": "fictional-unit"}])
