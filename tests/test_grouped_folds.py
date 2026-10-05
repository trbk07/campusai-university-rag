from collections import defaultdict

import pytest

from evaluation.common.grouped_folds import stratified_group_folds


def test_rare_classes_are_spread_without_breaking_groups():
    groups = ['negative-a'] * 5 + ['negative-b'] * 4 + ['negative-c'] * 2
    labels = [0] * len(groups)
    for label in (1, 2):
        for number in range(10):
            groups.extend([f'{label}-{number}'] * 3)
            labels.extend([label] * 3)
    folds = stratified_group_folds(groups, labels)
    by_group = defaultdict(set)
    for group, fold in zip(groups, folds):
        by_group[group].add(fold)
    assert all(len(values) == 1 for values in by_group.values())
    assert by_group['negative-a'] != by_group['negative-b']
    for fold in set(folds):
        assert {label for label, assigned in zip(labels, folds) if assigned != fold} == {0, 1, 2}
    reversed_folds = stratified_group_folds(list(reversed(groups)), list(reversed(labels)))
    assert folds == list(reversed(reversed_folds))


@pytest.mark.parametrize('groups,labels,max_folds', [([], [], 5), (['a'], [0], 5),
                                                   (['a', 'b'], [0], 5), (['a', 'b'], [0, 1], 1)])
def test_invalid_fold_inputs_rejected(groups, labels, max_folds):
    with pytest.raises(ValueError):
        stratified_group_folds(groups, labels, max_folds=max_folds)
