"""Dev-only nested routing/rank replay; no model, provider or heldout calls.

Frozen raw inference is reused for candidate subsets. This is exploratory
ranking evidence, not evidence-probability, serving or answer acceptance.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

from campusai.retrieval.route_probability import RouteProbabilityModel, route_observations
from evaluation.benchmarks.connected_groups import connected_groups
from evaluation.benchmarks.dev_inheritance import rows_at
from evaluation.common.artifact_store import resolve_artifact
from evaluation.common.release_artifacts import read_json, sha256, source_identity, write_json
from evaluation.reranker.calibrate_route_probabilities import fit_route_probabilities, metrics_from_selection
from evaluation.reranker.optimize_reranker_dev import rank_fusion, summarize
from evaluation.retrieval.compare_retrieval_quality import query_metrics

ROOT = Path(__file__).resolve().parents[2]
CAPS = (8, 10, 12, 16, 20)
WEIGHTS = (0., .1, .25, .5, .75, 1.)


def ordered_pool(observation: dict, order: str) -> list[dict]:
    pool = observation['pool']
    if order == 'native':
        return pool
    if order != 'baseline_priority':
        raise ValueError('unknown candidate ordering')
    by_id = {item['chunk_id']: item for item in pool}
    baseline_ids = [item['chunk_id'] for item in observation['baseline']]
    if len(by_id) != len(pool) or not set(baseline_ids) <= set(by_id):
        raise ValueError('baseline priority requires unique measured candidates containing the baseline')
    head = [by_id[item_id] for item_id in baseline_ids]
    return [{**item, 'rank': rank} for rank, item in enumerate(
        head + [item for item in pool if item['chunk_id'] not in set(baseline_ids)], 1)]


def eligible(observation: dict) -> bool:
    baseline = observation['baseline']
    return len(baseline) >= 2 and baseline[0]['retrieval_mode'] == 'hybrid_rrf'


def baseline_covered(observation: dict) -> bool:
    return {item['chunk_id'] for item in observation['baseline']} <= {item['chunk_id'] for item in observation['pool']}


def fold_assignments(rows: list[dict], count: int = 3) -> tuple[dict, dict]:
    if not rows or any(row.get('split') != 'dev' for row in rows):
        raise ValueError('ranking replay requires only dev rows')
    groups = connected_groups(rows)
    unique = sorted(set(groups.values()), key=lambda group: hashlib.sha256(group.encode()).hexdigest())
    if len(unique) < count:
        raise ValueError('insufficient independent dev groups')
    assignments = {group: index % count for index, group in enumerate(unique)}
    return groups, {qid: assignments[group] for qid, group in groups.items()}


def group_bootstrap(rows, baseline, outputs, groups, *, seed=20261007, resamples=10000):
    positives = [row for row in rows if row['answerable']]
    names = sorted({groups[row['qid']] for row in positives})
    buckets = {name: [] for name in names}
    for row in positives:
        b, r = query_metrics(row, baseline[row['qid']]), query_metrics(row, outputs[row['qid']])
        buckets[groups[row['qid']]].append((b['mrr'], r['mrr']))
    sizes = np.array([len(buckets[name]) for name in names])
    sums = np.array([np.sum(buckets[name], axis=0) for name in names])
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(names), size=(resamples, len(names)))
    means = sums[indices].sum(axis=1) / sizes[indices].sum(axis=1)[:, None]
    absolute = means[:, 1] - means[:, 0]
    relative = absolute / means[:, 0]
    return {'sampling_unit': 'connected_group', 'positive_groups': len(names),
            'bootstrap_resamples': resamples, 'seed': seed,
            'absolute_mrr_ci95': np.quantile(absolute, [.025, .975]).tolist(),
            'relative_mrr_ci95': np.quantile(relative, [.025, .975]).tolist()}


def analyze(rows, observations, inherited):
    groups, folds = fold_assignments(rows)
    obs = {item['qid']: item for item in observations}
    if len(obs) != len(observations) or set(obs) != {row['qid'] for row in rows}:
        raise ValueError('scores must pair every unique dev query')
    baseline = {qid: item['baseline'] for qid, item in obs.items()}
    features = {qid: route_observations(item['actual_request']['query'], []) for qid, item in obs.items()}
    proposals = {}
    for order in ('native', 'baseline_priority'):
        pools = {qid: ordered_pool(item, order) for qid, item in obs.items()
                 if order == 'native' or baseline_covered(item)}
        for cap in CAPS:
            for weight in WEIGHTS:
                proposals[(order, cap, weight)] = {
                    qid: rank_fusion(pools[qid], item['scores'], weight, cap)[:5]
                    if qid in pools and not (order == 'baseline_priority' and weight == 0.) else baseline[qid]
                    for qid, item in obs.items()}
    # Weight zero plus baseline priority must reproduce the measured baseline
    # coordinates exactly. This isolates retrieval-pool ordering from model effects.
    for qid, items in baseline.items():
        if [item['chunk_id'] for item in proposals[('baseline_priority', 8, 0.)][qid]] != [item['chunk_id'] for item in items]:
            raise ValueError('zero-weight baseline-priority replay does not reproduce baseline')
    oof, selected_oof, fold_reports = {}, {}, []
    for fold in range(3):
        train = [row for row in rows if folds[row['qid']] != fold]
        valid = [row for row in rows if folds[row['qid']] == fold]
        samples = [{**features[row['qid']], 'qid': row['qid'], 'difficulty': row['difficulty']}
                   for row in train if eligible(obs[row['qid']]) and row['difficulty'] in ('hard', 'easy')]
        model_data, diagnostics, route_feasible = fit_route_probabilities(samples, train)
        model = RouteProbabilityModel.from_dict(model_data)
        selections = {qid: eligible(item) and model.selects(features[qid]) for qid, item in obs.items()}
        base = summarize(train, baseline)
        trials = []
        for key, proposed in proposals.items():
            outputs = {row['qid']: proposed[row['qid']] if selections[row['qid']] else baseline[row['qid']] for row in train}
            quality = summarize(train, outputs)
            feasible = (quality['recall5'] >= .95 and quality['negative_fpr'] <= .01
                        and quality['all_gold_coverage5'] >= base['all_gold_coverage5'])
            trials.append({'order': key[0], 'cap': key[1], 'rank_weight': key[2],
                           'train_metrics': quality, 'ranking_feasible': feasible})
        candidates = [trial for trial in trials if trial['ranking_feasible']]
        chosen = max(candidates or trials, key=lambda trial: (
            trial['train_metrics']['mrr'], trial['train_metrics']['ndcg5'],
            -trial['rank_weight'], -trial['cap'], trial['order'] == 'baseline_priority'))
        key = (chosen['order'], chosen['cap'], chosen['rank_weight'])
        for row in valid:
            qid = row['qid']
            selected_oof[qid] = selections[qid]
            oof[qid] = proposals[key][qid] if selections[qid] else baseline[qid]
        assessed = [row for row in valid if eligible(obs[row['qid']]) and row['difficulty'] in ('hard', 'easy')]
        fold_reports.append({'fold': fold, 'training_groups': sorted({groups[row['qid']] for row in train}),
            'validation_groups': sorted({groups[row['qid']] for row in valid}),
            'route_model': model_data, 'route_train_feasible': route_feasible,
            'route_inner_oof': diagnostics['out_of_fold_metrics'], 'selected': chosen,
            'validation_metrics': summarize(valid, oof), 'trials': trials,
            'route_validation': metrics_from_selection(assessed, [selected_oof[row['qid']] for row in assessed])})
    cohorts = {'all_dev': rows, 'consumed_parent_dev': [row for row in rows if row['qid'] in inherited],
               'new_source_dev': [row for row in rows if row['qid'] not in inherited]}
    assessed = [row for row in rows if eligible(obs[row['qid']]) and row['difficulty'] in ('hard', 'easy')]
    quality = {}
    for name, part in cohorts.items():
        b, r = summarize(part, baseline), summarize(part, oof)
        quality[name] = {'records': len(part), 'groups': len({groups[row['qid']] for row in part}),
                         'baseline': b, 'reranked': r,
                         'relative_uplift': {key: r[key] / b[key] - 1 for key in ('mrr', 'ndcg5')},
                         'paired_bootstrap': group_bootstrap(part, baseline, oof, groups)}
    decisions = [{'qid': row['qid'], 'group': groups[row['qid']], 'fold': folds[row['qid']],
                  'route_selected': selected_oof[row['qid']], 'baseline': baseline[row['qid']],
                  'results': oof[row['qid']]} for row in rows]
    return {'baseline_priority_zero_weight_exact': True,
            'incomplete_pool_baseline_fallback_qids': [qid for qid, item in obs.items() if not baseline_covered(item)],
            'quality_by_cohort': quality,
            'route_outer_oof': metrics_from_selection(assessed, [selected_oof[row['qid']] for row in assessed]),
            'folds': fold_reports}, decisions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('dev', 'scores', 'score-report', 'inheritance', 'output-dir'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists() or not args.output_dir.resolve().is_relative_to(ROOT / '.release/reranker/studies'):
        raise ValueError('use a new isolated study output')
    report = read_json(args.score_report)
    if (report.get('raw_scores_sha256') != sha256(args.scores) or report.get('source_stable') is not True
            or report.get('dev_sha256') != sha256(args.dev) or report.get('test_used') is not False
            or report.get('holdout_used') is not False or report.get('release_eligible') is not False):
        raise ValueError('invalid dev score report binding')
    with gzip.open(resolve_artifact(args.scores), 'rt', encoding='utf8') as stream:
        raw = json.load(stream)
    if (raw.get('source_identity_before') != raw.get('source_identity_after')
            or any(raw.get(key) != report.get(key) for key in ('dev_sha256', 'index_sha256',
                'phase6_calibration_sha256', 'model_identity_sha256', 'model_origin'))):
        raise ValueError('raw scores do not match the stable measured identity')
    inherited = {qid for parent in read_json(args.inheritance)['parents'] for qid in parent['qids']}
    before = source_identity(ROOT)
    result, decisions = analyze(rows_at(args.dev), raw['observations'], inherited)
    if source_identity(ROOT) != before:
        raise ValueError('source changed during analysis')
    args.output_dir.mkdir(parents=True)
    decisions_path = args.output_dir / 'nested_oof_decisions.json.gz'
    with gzip.open(decisions_path, 'xt', encoding='utf8') as stream:
        json.dump(decisions, stream, ensure_ascii=False, allow_nan=False)
    result.update({'status': 'MEASURED_NESTED_DEV_RANK_REPLAY_NOT_RELEASE', 'release_eligible': False,
        'test_used': False, 'holdout_used': False, 'llm_called': False, 'source_identity': before,
        'runner_sha256': sha256(Path(__file__)), 'scores_path': args.scores.as_posix(),
        'scores_sha256': sha256(args.scores), 'score_report_sha256': sha256(args.score_report),
        'dev_sha256': sha256(args.dev), 'inheritance_sha256': sha256(args.inheritance),
        'model_identity': raw['model_identity'], 'decisions_sha256': sha256(decisions_path),
        'selection_protocol': 'Three connected-group outer folds; inner-OOF route fit and train-only ordering/cap/weight selection. No validation quality enters selection.',
        'limitations': ['Exploratory dev comparisons after prior dev exposure, not fresh confirmation.',
            'Baseline-priority replay keeps Phase 6 when the measured pool lacks a baseline chunk; this assumed fallback has not been measured in serving.',
            'Baseline-priority weight zero is the exact measured Phase 6 control, including partial/empty result sets.',
            'Reused diagnostic cap40 scores; subset replay does not establish same-cap GPU timings or serving equivalence.',
            'Medium-label eligible requests use the train-only model but have no fabricated binary route label.',
            'No three-class evidence policy, paired answers, live HTTP, resource acceptance, F1 or heldout gate PASS.']})
    write_json(args.output_dir / 'nested_dev_report.json', result)
    print(json.dumps({key: result[key] for key in ('status', 'quality_by_cohort', 'route_outer_oof')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
