"""Explicit owner delegation with an AI analyst, never a human-review claim."""
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from evaluation.common.release_artifacts import read_json, sha256
from evaluation.benchmarks.dev_inheritance import safe_reference

DELEGATED_FIELDS = ('owner_authority', 'review_authorization_sha256', 'review_scope',
                    'review_index_sha256', 'owner_manual_review_claim',
                    'independent_human_review_claim')


@dataclass(frozen=True)
class DelegatedReview:
    owner: str
    analyst: str
    authorization_sha256: str
    index_sha256: str
    recorded_at: str
    scopes: tuple[str, ...]


def load_delegation(policy: dict, *, root: Path, index_sha256: str,
                    scope: str) -> DelegatedReview | None:
    if policy.get('owner_delegated_ai_review_allowed') is not True:
        return None
    if (policy.get('schema_version') != 2
            or policy.get('project_scope') != 'single_owner_personal_project'
            or policy.get('independent_review_claim') is not False
            or policy.get('owner_manual_review_claim') is not False
            or scope not in ('dataset', 'semantic')):
        raise ValueError('explicit delegated AI policy and scope required')
    binding = policy['delegated_review_authorization']
    path = safe_reference(root, binding['path'])
    if sha256(path) != binding['sha256']:
        raise ValueError('delegated authorization changed')
    auth = read_json(path)
    stamp = datetime.fromisoformat(auth['recorded_at'])
    owner, analyst = policy.get('owner_identity'), policy.get('decision_analyst')
    if (not isinstance(owner, str) or not owner.strip()
            or not isinstance(analyst, str) or not analyst.strip()
            or analyst.casefold() == owner.casefold()
            or auth.get('owner_identity') != owner or auth.get('decision_analyst') != analyst
            or not isinstance(auth.get('delegated_decision_approval_statement'), str)
            or not auth['delegated_decision_approval_statement'].strip()
            or auth.get('owner_manual_row_review_claim') is not False
            or auth.get('independent_human_review_claim') is not False
            or auth.get('index_sha256') != index_sha256
            or stamp.tzinfo is None or stamp > datetime.now(timezone.utc)):
        raise ValueError('delegated authorization identity, time or index mismatch')
    scopes = policy.get('delegated_review_scopes')
    if (not isinstance(scopes, list) or not scopes or len(set(scopes)) != len(scopes)
            or any(s not in ('dataset', 'semantic') for s in scopes) or scope not in scopes):
        raise ValueError('review scope is not delegated')
    return DelegatedReview(owner, analyst, binding['sha256'], index_sha256,
                           auth['recorded_at'], tuple(scopes))


def delegated_role_error(review: dict, delegation: DelegatedReview | None,
                         scope: str) -> str | None:
    if not isinstance(delegation, DelegatedReview) or scope not in delegation.scopes:
        return 'explicit_owner_delegation_required'
    if (review.get('reviewer') != delegation.analyst
            or review.get('owner_authority') != delegation.owner
            or review.get('review_authorization_sha256') != delegation.authorization_sha256
            or review.get('review_scope') != scope
            or review.get('review_index_sha256') != delegation.index_sha256
            or review.get('owner_manual_review_claim') is not False
            or review.get('independent_human_review_claim') is not False):
        return 'delegated_review_identity_or_binding_mismatch'
    try:
        stamp = datetime.fromisoformat(review['reviewed_at'].replace('Z', '+00:00'))
        if (stamp.tzinfo is None or stamp < datetime.fromisoformat(delegation.recorded_at)
                or stamp > datetime.now(timezone.utc)):
            raise ValueError('review precedes authorization or is in the future')
    except (KeyError, TypeError, ValueError, AttributeError):
        return 'delegated_review_timestamp_invalid'
    return None
