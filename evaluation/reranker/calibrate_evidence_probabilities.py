"""Dev-only grouped calibration of observable evidence classes.

The three targets are absence, incomplete evidence, and complete gold coverage.
Neither labels nor paraphrase groups are runtime features. OOF predictions keep
paraphrases together, and both OOF and fitted-policy quality must pass M5.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json

from campusai.retrieval.evidence_policy import (
    CLASSES, FEATURES, VERSION, EvidenceProbabilityModel, evidence_features,
)

FIT_REGULARIZATION = .05
FIT_ITERATIONS = 5000


def proposal_features(row: dict, baseline: list, proposal: dict) -> dict:
    inputs = proposal["evidence_inputs"]
    return evidence_features(row["question"], baseline, inputs["ranked_candidates"], inputs["scores"])


def target_class(row: dict, proposal: dict) -> int:
    if not row["answerable"]:
        return 0
    gold = row["gold_evidence"]
    if not gold:
        raise ValueError("positive evidence target requires gold")
    results = proposal["results"][:5]
    def get(item, key):
        return item.get(key) if isinstance(item, dict) else getattr(item, key)
    complete = all(any(get(item, "doc_id") == g["doc_id"] and get(item, "chunk_id") == g["chunk_id"]
                      and get(item, "page") in g.get("pages", [g.get("page", get(item, "page"))])
                      for item in results) for g in gold)
    return 2 if complete else 1


def _fit(features: list[dict], labels: list[int]) -> EvidenceProbabilityModel:
    import numpy as np
    if set(labels) != {0, 1, 2}:
        raise ValueError("every training fold needs all three evidence classes")
    x = np.array([[row[key] for key in FEATURES] for row in features], dtype=np.float64)
    means, scales = x.mean(axis=0), np.maximum(x.std(axis=0), .1)
    x = (x - means) / scales
    # Bias is regularized too: strict convexity, deterministic fixed settings.
    x = np.column_stack((x, np.ones(len(x))))
    target = np.eye(3)[labels]
    weights = np.zeros((x.shape[1], 3))
    step = 1 / (.5 * np.linalg.norm(x, ord=2) ** 2 / len(x) + FIT_REGULARIZATION)
    converged = False
    for _ in range(FIT_ITERATIONS):
        logits = x @ weights
        exp = np.exp(logits - logits.max(axis=1, keepdims=True))
        probs = exp / exp.sum(axis=1, keepdims=True)
        gradient = x.T @ (probs - target) / len(x) + FIT_REGULARIZATION * weights
        if np.max(np.abs(gradient)) <= 1e-8:
            converged = True
            break
        weights -= step * gradient
    if not converged:
        raise ValueError("evidence fit did not converge")
    return EvidenceProbabilityModel(VERSION, FEATURES, CLASSES, tuple(means.tolist()), tuple(scales.tolist()),
                                    tuple(tuple(row) for row in weights[:-1].T.tolist()), tuple(weights[-1].tolist()))


def _diagnostics(labels: list[int], probabilities: list[dict | None]) -> dict:
    import math
    scored = [(label, p) for label, p in zip(labels, probabilities) if p is not None]
    return {"records": len(labels), "scored": len(scored), "out_of_domain": len(labels) - len(scored),
            "log_loss": -sum(math.log(max(1e-15, p[CLASSES[label]])) for label, p in scored) / max(1, len(scored)),
            "brier": sum(sum((p[key] - float(i == label)) ** 2 for i, key in enumerate(CLASSES))
                         for label, p in scored) / max(1, len(scored))}


def _fold_groups(items: list[dict]) -> list[str]:
    """Keep paraphrases, source families and templates out of each other's folds."""
    parents = list(range(len(items)))
    def find(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index
    def union(left, right):
        parents[find(left)] = find(right)
    first = {}
    for index, row in enumerate(items):
        for field in ("paraphrase_group", "source_group", "template_group"):
            value = row.get(field)
            if field == "paraphrase_group" and (not isinstance(value, str) or not value.strip()):
                raise ValueError("probability calibration needs a paraphrase group for every scored query")
            if isinstance(value, str) and value.strip():
                key = (field, value.strip())
                if key in first:
                    union(index, first[key])
                else:
                    first[key] = index
    members = {}
    for index, row in enumerate(items):
        members.setdefault(find(index), []).append(row["qid"])
    names = {root: min(qids) for root, qids in members.items()}
    return [names[find(index)] for index in range(len(items))]


def calibrate_probabilities(rows: list[dict], baseline: dict, proposals: dict) -> tuple[dict, dict]:
    from evaluation.reranker.calibrate_reranker_scores import _quality, calibrated_outputs
    if not rows or any(row.get("split") != "dev" for row in rows):
        raise ValueError("probability calibration accepts only explicit dev rows")
    if len({row["qid"] for row in rows}) != len(rows) or set(baseline) != {row["qid"] for row in rows} or not set(proposals) <= set(baseline):
        raise ValueError("probability calibration query scope mismatch")
    items = [row for row in rows if row["qid"] in proposals]
    groups = _fold_groups(items)
    if len(set(groups)) < 2:
        raise ValueError("probability calibration requires at least two independent query families")
    features = [proposal_features(row, baseline[row["qid"]], proposals[row["qid"]]) for row in items]
    labels = [target_class(row, proposals[row["qid"]]) for row in items]
    counts = {key: labels.count(i) for i, key in enumerate(CLASSES)}
    if len(items) < 30 or min(counts.values()) < 5:
        raise ValueError("probability calibration needs 30 scored dev queries and five of each evidence class")
    # Deterministic group round-robin; assigning each whole group prevents leakage.
    ordered = sorted(set(groups), key=lambda group: hashlib.sha256(group.encode()).hexdigest())
    fold_count = min(5, len(ordered))
    group_fold = {group: i % fold_count for i, group in enumerate(ordered)}
    folds = [group_fold[group] for group in groups]
    oof = [None] * len(items)
    for fold in range(fold_count):
        train = [i for i in range(len(items)) if folds[i] != fold]
        model = _fit([features[i] for i in train], [labels[i] for i in train])
        for i in range(len(items)):
            if folds[i] == fold:
                oof[i] = model.probabilities(features[i])
    fitted = _fit(features, labels)
    base = _quality(rows, baseline)
    def outputs_for(probabilities, accept, abstain):
        outputs = dict(baseline)
        for row, p in zip(items, probabilities):
            if p is not None and p["sufficient_evidence"] >= accept:
                outputs[row["qid"]] = proposals[row["qid"]]["results"]
            elif p is not None and p["no_evidence"] >= abstain:
                outputs[row["qid"]] = []
        return outputs
    selected = None
    actual_probabilities = [fitted.probabilities(feature) for feature in features]
    # OOF chooses thresholds; fitted-model replay cannot rescue a failed OOF gate.
    for accept in (.6, .7, .8, .9, .95, .99):
        for abstain in (.6, .7, .8, .9, .95, .99):
            held = _quality(rows, outputs_for(oof, accept, abstain))
            actual = _quality(rows, outputs_for(actual_probabilities, accept, abstain))
            feasible = all(q["answerable_recall_at_5"] >= max(.95, base["answerable_recall_at_5"] - .005)
                           and q["negative_fpr"] <= .01 for q in (held, actual))
            if feasible:
                key = (held["mrr"] + held["ndcg_at_5"], held["answerable_recall_at_5"], accept + abstain)
                if selected is None or key > selected[0]:
                    selected = key, accept, abstain, held
    accept, abstain = (selected[1:3] if selected else (.9, .95))
    fitted = replace(fitted, accept_probability=accept, abstain_probability=abstain)
    policy = {"threshold": 0.0, "margin_threshold": 0.0, "low_score_action": "phase6",
              "evidence_model": fitted.to_dict()}
    # Replay derives features from raw observations rather than accepting stored probabilities.
    selected_quality = _quality(rows, calibrated_outputs(baseline, proposals, policy, rows=rows))
    diagnostics = {"baseline": base, "selected": selected_quality, "feasible": selected is not None,
                   "out_of_fold_quality": _quality(rows, outputs_for(oof, accept, abstain)),
                   "fit": {"regularization": FIT_REGULARIZATION, "iterations_limit": FIT_ITERATIONS},
                   "classes": counts, "fold_count": fold_count,
                   "out_of_fold": _diagnostics(labels, oof), "fitted": _diagnostics(labels, actual_probabilities),
                   "observations": [{"qid": row["qid"], "group": group, "fold": fold, "target": CLASSES[label],
                                     "features": feature, "probabilities": p}
                                    for row, group, fold, label, feature, p in zip(items, groups, folds, labels, features, oof)]}
    # Require a round-trip safe artifact rather than numpy-derived scalars.
    return json.loads(json.dumps(policy)), json.loads(json.dumps(diagnostics))
