"""Grouped dev-only fitting for the observable Phase 7 hard-query router."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json

from campusai.retrieval.route_probability import FEATURES, VERSION, RouteProbabilityModel, validate_observations
from evaluation.reranker.calibrate_evidence_probabilities import _fold_groups

REGULARIZATION = .05
ITERATIONS = 5000


def _fit(samples: list[dict]) -> RouteProbabilityModel:
    import numpy as np
    if {row["difficulty"] for row in samples} != {"hard", "easy"}:
        raise ValueError("every routing fold needs hard and easy questions")
    x = np.array([[validate_observations(row)[key] for key in FEATURES] for row in samples], dtype=np.float64)
    means, scales = x.mean(axis=0), np.maximum(x.std(axis=0), .1)
    x = np.column_stack(((x - means) / scales, np.ones(len(x))))
    target = np.array([row["difficulty"] == "hard" for row in samples], dtype=np.float64)
    weights = np.zeros(x.shape[1])
    step = 1 / (.25 * np.linalg.norm(x, ord=2) ** 2 / len(x) + REGULARIZATION)
    converged = False
    for _ in range(ITERATIONS):
        scores = np.clip(x @ weights, -40, 40)
        p = 1 / (1 + np.exp(-scores))
        gradient = x.T @ (p - target) / len(x) + REGULARIZATION * weights
        if np.max(np.abs(gradient)) <= 1e-8:
            converged = True
            break
        weights -= step * gradient
    if not converged:
        raise ValueError("routing fit did not converge")
    return RouteProbabilityModel(VERSION, FEATURES, tuple(means.tolist()), tuple(scales.tolist()),
                                 tuple(weights[:-1].tolist()), float(weights[-1]))


def metrics_from_selection(samples: list[dict], selected: list[bool]) -> dict:
    if len(samples) != len(selected) or not samples:
        raise ValueError("invalid routing observations")
    hard = [choice for sample, choice in zip(samples, selected) if sample["difficulty"] == "hard"]
    easy = [choice for sample, choice in zip(samples, selected) if sample["difficulty"] == "easy"]
    if not hard or not easy:
        raise ValueError("routing observations require both difficulty classes")
    total = sum(selected)
    return {"eligible": len(samples), "selected": total, "coverage": total / len(samples),
            "hard_recall": sum(hard) / len(hard),
            "easy_unnecessary_rerank_rate": sum(easy) / len(easy),
            "selection_precision": sum(hard) / total if total else 0.0,
            "false_skip_rate": 1 - sum(hard) / len(hard),
            "hard_count": len(hard), "easy_count": len(easy)}


def fit_route_probabilities(samples: list[dict], rows: list[dict]) -> tuple[dict, dict, bool]:
    if not rows or any(row.get("split") != "dev" for row in rows):
        raise ValueError("routing fit accepts dev rows only")
    by_id = {row["qid"]: row for row in rows}
    if len(by_id) != len(rows) or len({sample["qid"] for sample in samples}) != len(samples) or any(
            sample["qid"] not in by_id or sample["difficulty"] != by_id[sample["qid"]]["difficulty"]
            for sample in samples):
        raise ValueError("routing samples do not match dev labels")
    # Medium difficulty has no hard/easy release target. Serve it with the
    # fitted model, but do not assign it a fabricated binary training label.
    samples = [sample for sample in samples if sample["difficulty"] in {"hard", "easy"}]
    if (len(samples) < 30 or sum(sample["difficulty"] == "hard" for sample in samples) < 10
            or sum(sample["difficulty"] == "easy" for sample in samples) < 10):
        raise ValueError("routing fit needs at least 30 queries and 10 per difficulty")
    sampled_rows = [by_id[sample["qid"]] for sample in samples]
    groups = _fold_groups(sampled_rows)
    unique = sorted(set(groups), key=lambda group: hashlib.sha256(group.encode()).hexdigest())
    if len(unique) < 2:
        raise ValueError("routing fit needs two independent query families")
    fold_count = min(5, len(unique))
    group_fold = {group: index % fold_count for index, group in enumerate(unique)}
    folds = [group_fold[group] for group in groups]
    oof = [None] * len(samples)
    for fold in range(fold_count):
        model = _fit([sample for sample, assignment in zip(samples, folds) if assignment != fold])
        for index, assignment in enumerate(folds):
            if assignment == fold:
                oof[index] = model.probability(samples[index])
    fitted = _fit(samples)
    actual = [fitted.probability(sample) for sample in samples]
    candidates = sorted({value for value in oof + actual if value is not None})
    best = None
    for threshold in candidates:
        oof_metrics = metrics_from_selection(samples, [p is not None and p >= threshold for p in oof])
        fitted_metrics = metrics_from_selection(samples, [p is not None and p >= threshold for p in actual])
        if all(m["hard_recall"] >= .95 and m["easy_unnecessary_rerank_rate"] <= .20
               for m in (oof_metrics, fitted_metrics)):
            key = (-oof_metrics["coverage"], oof_metrics["selection_precision"], threshold)
            if best is None or key > best[0]:
                best = (key, threshold, oof_metrics, fitted_metrics)
    if best is None:
        # Explicit conditional candidate; never silently promote an infeasible fit.
        threshold = .5
        oof_metrics = metrics_from_selection(samples, [p is not None and p >= threshold for p in oof])
        fitted_metrics = metrics_from_selection(samples, [p is not None and p >= threshold for p in actual])
    else:
        _, threshold, oof_metrics, fitted_metrics = best
    fitted = replace(fitted, threshold=threshold)
    diagnostics = {"fold_count": fold_count, "regularization": REGULARIZATION,
                   "iterations_limit": ITERATIONS, "out_of_fold_metrics": oof_metrics,
                   "fitted_metrics": fitted_metrics,
                   "observations": [{"qid": row["qid"], "group": group, "fold": fold,
                                     "probability": probability}
                                    for row, group, fold, probability in zip(sampled_rows, groups, folds, oof)]}
    return json.loads(json.dumps(fitted.to_dict())), json.loads(json.dumps(diagnostics)), best is not None
