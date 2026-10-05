"""Shared schema rules for human benchmark answer expectations and review roles."""
from __future__ import annotations

EXPECTED_BEHAVIORS = frozenset({
    "answer_grounded",
    "phase6_fallback",
    "abstain",
    "ask_clarification",
})
REVIEWER_ROLES = frozenset({"independent_reviewer", "project_owner"})


def expected_behavior_error(row: dict) -> str | None:
    behavior = row.get("expected_behavior")
    if behavior not in EXPECTED_BEHAVIORS:
        return "invalid_expected_behavior"
    if behavior == "phase6_fallback":
        if row.get("evaluation_kind") != "provider_failure":
            return "phase6_fallback_only_for_provider_failure"
        return None
    if row.get("answerable") is True and behavior != "answer_grounded":
        return "answerable_requires_answer_grounded"
    if row.get("answerable") is False and behavior not in {"abstain", "ask_clarification"}:
        return "unanswerable_requires_abstain_or_clarification"
    return None

def review_role_error(row: dict, owner_identity: str | None = None) -> str | None:
    role = row.get("reviewer_role")
    reviewer = row.get("reviewer")
    author = row.get("author")
    if role not in REVIEWER_ROLES or not isinstance(reviewer, str) or not reviewer.strip():
        return "independent_human_review_required"
    if role == "independent_reviewer":
        if isinstance(author, str) and reviewer.strip().casefold() == author.strip().casefold():
            return "independent_human_review_required"
        return None
    if (not isinstance(owner_identity, str) or not owner_identity.strip()
            or reviewer.strip().casefold() != owner_identity.strip().casefold()):
        return "owner_review_identity_mismatch"
    return None
