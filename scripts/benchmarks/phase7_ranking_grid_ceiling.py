"""Label-aware upper bounds for measured dev ranking grids, never deployable policies."""
import argparse
import gzip
import json
from pathlib import Path

from evaluation.benchmarks.dev_inheritance import rows_at
from evaluation.common.artifact_store import resolve_artifact
from evaluation.common.release_artifacts import read_json, sha256, source_identity, write_json
from evaluation.reranker.optimize_reranker_dev import rank_fusion
from evaluation.retrieval.compare_retrieval_quality import query_metrics
from scripts.benchmarks.analyze_phase7_ranking_replay import CAPS, WEIGHTS, ordered_pool, eligible, baseline_covered

ROOT = Path(__file__).resolve().parents[2]


def bound(rows, observations):
    if not rows or any(row.get('split') != 'dev' for row in rows):
        raise ValueError('only dev inputs are allowed')
    obs = {item['qid']: item for item in observations}
    if len(obs) != len(observations) or set(obs) != {row['qid'] for row in rows}:
        raise ValueError('measured scores must match every unique dev input')
    details = []
    for row in rows:
        if not row['answerable']:
            continue
        item = obs[row['qid']]
        base = query_metrics(row, item['baseline'])
        trials = [base]
        if eligible(item):
            for order in ('native', 'baseline_priority'):
                if order == 'baseline_priority' and not baseline_covered(item):
                    continue
                pool = ordered_pool(item, order)
                for cap in CAPS:
                    for weight in WEIGHTS:
                        trials.append(query_metrics(row, rank_fusion(pool, item['scores'], weight, cap)[:5]))
        keys = ('mrr', 'ndcg5', 'recall5', 'all_gold_recall5')
        details.append({'qid': row['qid'], 'rerank_eligible': eligible(item),
                        'baseline': {key: base[key] for key in keys},
                        'independent_metric_oracles': {key: max(trial[key] for trial in trials) for key in keys}})
    aggregate = {name: {key: sum(item[name][key] for item in details)/len(details)
                        for key in ('mrr', 'ndcg5', 'recall5', 'all_gold_recall5')}
                 for name in ('baseline', 'independent_metric_oracles')}
    return {**aggregate, 'relative_oracle_uplift': {
        key: aggregate['independent_metric_oracles'][key]/aggregate['baseline'][key] - 1
        for key in ('mrr', 'ndcg5')}, 'positive_queries': len(details),
        'potential_mrr_improvements': sum(item['independent_metric_oracles']['mrr'] > item['baseline']['mrr'] for item in details),
        'per_query': details}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dev', type=Path, required=True)
    parser.add_argument('--score-reports', nargs='+', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    rows = rows_at(args.dev)
    variants = {}
    before = source_identity(ROOT)
    for path in args.score_reports:
        report = read_json(path)
        raw_path = path.parent / 'raw_dev_scores.json.gz'
        if (report.get('dev_sha256') != sha256(args.dev) or report.get('raw_scores_sha256') != sha256(raw_path)
                or report.get('test_used') is not False or report.get('holdout_used') is not False
                or report.get('source_stable') is not True or report.get('release_eligible') is not False):
            raise ValueError('invalid measured dev score bindings')
        with gzip.open(resolve_artifact(raw_path), 'rt', encoding='utf8') as stream:
            raw = json.load(stream)
        if raw['dev_sha256'] != report['dev_sha256'] or raw['source_identity_before'] != raw['source_identity_after']:
            raise ValueError('invalid raw input identity')
        name = report['input_format']
        if name in variants:
            raise ValueError('duplicate input format')
        variants[name] = {'score_report_path': path.as_posix(), 'score_report_sha256': sha256(path),
                          'raw_scores_sha256': sha256(raw_path), **bound(rows, raw['observations'])}
    if before != source_identity(ROOT):
        raise ValueError('source changed during ceiling replay')
    write_json(args.output, {'status': 'LABEL_AWARE_DEV_FINITE_GRID_ORACLE_ONLY', 'release_eligible': False,
        'heldout_used': False, 'llm_called': False, 'source_identity': before,
        'dev_sha256': sha256(args.dev), 'runner_sha256': sha256(Path(__file__)), 'variants': variants,
        'limitations': ['Per-query gold-aware best-case bound, not trainable selection or OOF performance.',
            'Individual metric maxima can come from different configurations; they need not be jointly attainable.',
            'Exact/abstained/single-result requests keep Phase 6. All hybrid-eligible requests may rerank, making this looser than the fitted router.',
            'Bound applies only to this measured input-format/order/cap/weight grid; it does not rule out other models, inputs or ranking methods.']})
    print(json.dumps({name: {key: report[key] for key in ('relative_oracle_uplift', 'potential_mrr_improvements')}
                      for name, report in variants.items()}))


if __name__ == '__main__':
    main()
