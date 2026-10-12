from copy import deepcopy
from pathlib import Path

import pytest

from evaluation.benchmarks.delegated_review import load_delegation, DELEGATED_FIELDS
from evaluation.benchmarks.human_record_contract import review_role_error
from evaluation.benchmarks.freeze_human_benchmark import validate_rows
from evaluation.common.release_artifacts import write_json, sha256
from evaluation.reranker.paired_answer_quality import evaluate_answer_observations
from tests.test_reranker_stage_gates import human_rows


def delegation_fixture(tmp_path):
    auth = {'owner_identity': 'Project Owner', 'decision_analyst': 'Codex AI assistant',
            'delegated_decision_approval_statement': 'Owner authorizes AI decisions for this phase.',
            'owner_manual_row_review_claim': False, 'independent_human_review_claim': False,
            'index_sha256': 'a' * 64, 'recorded_at': '2026-08-01T00:00:00+00:00'}
    write_json(tmp_path / 'auth.json', auth)
    policy = {'schema_version': 2, 'project_scope': 'single_owner_personal_project',
              'owner_identity': auth['owner_identity'], 'decision_analyst': auth['decision_analyst'],
              'owner_delegated_ai_review_allowed': True, 'independent_review_claim': False,
              'owner_manual_review_claim': False, 'delegated_review_scopes': ['dataset', 'semantic'],
              'delegated_review_authorization': {'path': 'auth.json', 'sha256': sha256(tmp_path / 'auth.json')}}
    context = load_delegation(policy, root=tmp_path, index_sha256='a' * 64, scope='semantic')
    fields = {'reviewer_role': 'owner_delegated_ai', 'reviewer': context.analyst,
              'owner_authority': context.owner, 'review_authorization_sha256': context.authorization_sha256,
              'review_index_sha256': context.index_sha256, 'review_scope': 'semantic',
              'owner_manual_review_claim': False, 'independent_human_review_claim': False,
              'reviewed_at': '2026-09-01T12:00:00+07:00'}
    return policy, context, fields


def test_delegation_is_opt_in_and_does_not_accept_old_owner_as_ai(tmp_path):
    policy, context, fields = delegation_fixture(tmp_path)
    assert load_delegation({'schema_version': 1}, root=tmp_path, index_sha256='a' * 64,
                           scope='semantic') is None
    assert review_role_error(fields, delegation=context, scope='semantic') is None
    assert review_role_error(fields, scope='semantic') == 'explicit_owner_delegation_required'
    assert review_role_error({**fields, 'reviewer': context.owner}, delegation=context,
                             scope='semantic') == 'delegated_review_identity_or_binding_mismatch'


@pytest.mark.parametrize('field,value', [
    ('review_authorization_sha256', 'b' * 64), ('review_index_sha256', 'b' * 64),
    ('independent_human_review_claim', True), ('owner_manual_review_claim', True),
    ('owner_authority', 'different owner'), ('review_scope', 'dataset'),
    ('reviewed_at', '2026-07-01T00:00:00Z'),
])
def test_delegated_review_rejects_wrong_binding_claim_or_time(tmp_path, field, value):
    _, context, fields = delegation_fixture(tmp_path)
    assert review_role_error({**fields, field: value}, delegation=context, scope='semantic')


@pytest.mark.parametrize('mutation', ['unsafe', 'hash', 'index', 'scope', 'future', 'owner'])
def test_delegation_loader_checks_physical_authorization(tmp_path, mutation):
    policy, _, _ = delegation_fixture(tmp_path)
    if mutation == 'unsafe':
        policy['delegated_review_authorization']['path'] = '../auth.json'
    elif mutation == 'scope':
        policy['delegated_review_scopes'] = ['dataset']
    elif mutation == 'index':
        with pytest.raises(ValueError):
            load_delegation(policy, root=tmp_path, index_sha256='b' * 64, scope='semantic')
        return
    else:
        import json
        auth = json.loads((tmp_path / 'auth.json').read_text())
        auth['owner_identity'] = 'wrong' if mutation == 'owner' else auth['owner_identity']
        auth['recorded_at'] = '2100-01-01T00:00:00Z' if mutation == 'future' else auth['recorded_at']
        auth['extra'] = 'changed bytes'
        write_json(tmp_path / 'auth.json', auth)
        if mutation != 'hash':
            policy['delegated_review_authorization']['sha256'] = sha256(tmp_path / 'auth.json')
    with pytest.raises(ValueError):
        load_delegation(policy, root=tmp_path, index_sha256='a' * 64, scope='semantic')


def test_dataset_role_is_disclosed_without_claiming_manual_owner_or_human_review(tmp_path):
    _, context, fields = delegation_fixture(tmp_path)
    rows = [{**r, **fields, 'review_scope': 'dataset'} for r in human_rows()]
    evidence = {('doc', 'c0'): {'page': 1, 'content': 'fixture MAI101'}}
    report = validate_rows(rows, evidence, delegation=context)
    assert report['review_complete']
    assert report['review_mode'] == 'owner_delegated_ai_review'
    assert report['delegated_ai_review_complete']
    assert not report['owner_review_complete'] and not report['independent_review_complete']
    assert not validate_rows(rows, evidence)['review_complete']


def test_semantic_metrics_use_exact_same_denominators_under_disclosed_ai_role(tmp_path):
    from tests.test_phase7_completion_contract import paired_answers
    observations = paired_answers()
    original = evaluate_answer_observations(observations)
    _, context, fields = delegation_fixture(tmp_path)
    changed = deepcopy(observations)
    for observation in changed:
        observation['review'].update(fields)
    reviewed = evaluate_answer_observations(changed, delegation=context)
    assert {k: v for k, v in reviewed.items() if k != 'review_summary'} == {
        k: v for k, v in original.items() if k != 'review_summary'}
    assert reviewed['review_summary']['review_mode'] == 'owner_delegated_ai_review'
    with pytest.raises(ValueError, match='role-declared'):
        evaluate_answer_observations(changed)
