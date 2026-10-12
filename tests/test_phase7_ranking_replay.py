"""Reject unmeasured evidence and heldout/group leakage in diagnostic replay."""
import pytest

from scripts.benchmarks.analyze_phase7_ranking_replay import fold_assignments, ordered_pool


def test_connected_family_never_crosses_validation_boundary():
    rows = [{'qid': str(i), 'question': f'Question number {i}', 'split': 'dev',
             'paraphrase_group': 'linked' if i < 3 else str(i)} for i in range(8)]
    groups, folds = fold_assignments(rows)
    assert len({folds[str(i)] for i in range(3)}) == 1
    for group in set(groups.values()):
        assert len({folds[qid] for qid, name in groups.items() if name == group}) == 1


@pytest.mark.parametrize('split', ['test', 'holdout'])
def test_heldout_rows_rejected_before_analysis(split):
    with pytest.raises(ValueError, match='dev rows'):
        fold_assignments([{'qid': 'a', 'split': split}])


def test_missing_baseline_cannot_be_assigned_a_fabricated_model_score():
    observation = {'baseline': [{'chunk_id': 'unmeasured'}], 'pool': [{'chunk_id': 'measured'}]}
    with pytest.raises(ValueError, match='measured candidates'):
        ordered_pool(observation, 'baseline_priority')


def test_duplicate_physical_candidate_rejected():
    observation = {'baseline': [{'chunk_id': 'a'}], 'pool': [{'chunk_id': 'a'}, {'chunk_id': 'a'}]}
    with pytest.raises(ValueError, match='unique measured candidates'):
        ordered_pool(observation, 'baseline_priority')
