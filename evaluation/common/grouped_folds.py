"""Deterministic class-balanced folds without breaking connected families."""
from collections import Counter, defaultdict
import hashlib


def stratified_group_folds(groups: list[str], labels: list[int], *, max_folds: int = 5) -> list[int]:
    """Balance class counts, using targets only for conventional stratification.

    No predictions, quality metrics or threshold searches affect allocation.
    Whole connected groups always remain in one validation fold.
    """
    if not groups or len(groups) != len(labels) or max_folds < 2:
        raise ValueError('matching groups and labels and at least two folds required')
    counts = defaultdict(Counter)
    for group, label in zip(groups, labels):
        counts[group][label] += 1
    folds = min(max_folds, len(counts))
    if folds < 2:
        raise ValueError('at least two independent groups required')
    total = Counter(labels)
    # Groups holding a large share of a rare class are placed first. Hashes
    # resolve ties without depending on input order, language or query ids.
    ordered = sorted(counts, key=lambda group: (
        -max(counts[group][label] / total[label] for label in total),
        -sum(counts[group].values()), hashlib.sha256(group.encode()).hexdigest()))
    allocated = [Counter() for _ in range(folds)]
    group_fold = {}
    for number, group in enumerate(ordered):
        available = [number] if number < folds else range(folds)
        def cost(fold):
            increase = sum(((allocated[fold][label] + counts[group][label]) ** 2
                            - allocated[fold][label] ** 2) / total[label] ** 2 for label in total)
            return increase, sum(allocated[fold].values()), fold
        chosen = min(available, key=cost)
        allocated[chosen].update(counts[group])
        group_fold[group] = chosen
    return [group_fold[group] for group in groups]
