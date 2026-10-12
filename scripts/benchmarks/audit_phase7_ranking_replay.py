"""Recompute diagnostic OOF metrics and physical provenance with the release comparator."""
import argparse
import gzip
import json
from pathlib import Path

from evaluation.benchmarks.dev_inheritance import rows_at
from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence
from evaluation.common.artifact_store import resolve_artifact
from evaluation.common.release_artifacts import read_json, sha256, source_identity, write_json
from evaluation.retrieval.compare_retrieval_quality import compare_split

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('dev', 'index-dir', 'replay-report', 'output-dir'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists() or not args.output_dir.resolve().is_relative_to(ROOT / '.release/reranker/studies'):
        raise ValueError('use a new isolated audit output')
    prior = read_json(args.replay_report)
    if (prior.get('dev_sha256') != sha256(args.dev) or prior.get('release_eligible') is not False
            or prior.get('test_used') is not False or prior.get('holdout_used') is not False):
        raise ValueError('only the exact reviewed dev replay is eligible')
    scores = read_json(Path(prior['scores_path']).parent / 'dev_ranking_report.json')
    if (sha256(Path(prior['scores_path'])) != prior['scores_sha256']
            or scores['index_sha256'] != sha256(args.index_dir / 'manifest.json')):
        raise ValueError('score/index binding mismatch')
    decisions_path = args.replay_report.parent / 'nested_oof_decisions.json.gz'
    if sha256(decisions_path) != prior['decisions_sha256']:
        raise ValueError('replayed paired decisions changed')
    with gzip.open(resolve_artifact(decisions_path), 'rt', encoding='utf8') as stream:
        decisions = json.load(stream)
    baseline = {item['qid']: item['baseline'] for item in decisions}
    outputs = {item['qid']: item['results'] for item in decisions}
    rows = rows_at(args.dev)
    if (len(baseline) != len(decisions) or any(row.get('split') != 'dev' for row in rows)):
        raise ValueError('duplicate paired decisions or heldout input')
    before = source_identity(ROOT)
    result = compare_split(rows, baseline, outputs, frozen_evidence(args.index_dir),
                           read_json(args.index_dir / 'manifest.json')['documents'], seed=20261007)
    expected = prior['quality_by_cohort']['all_dev']
    for old_key, key in [('baseline', 'baseline'), ('reranked', 'phase7')]:
        for metric in ('recall5', 'mrr', 'ndcg5', 'negative_fpr'):
            if abs(result[key][metric] - expected[old_key][metric]) > 1e-12:
                raise ValueError('independent comparator metric mismatch')
        if abs(result[key]['all_gold_recall5'] - expected[old_key]['all_gold_coverage5']) > 1e-12:
            raise ValueError('independent all-gold metric mismatch')
    if source_identity(ROOT) != before:
        raise ValueError('source changed during audit')
    args.output_dir.mkdir(parents=True)
    raw = args.output_dir / 'independent_comparison.json.gz'
    with gzip.open(raw, 'xt', encoding='utf8') as stream:
        json.dump(result, stream, ensure_ascii=False, allow_nan=False)
    violations = {key: result[key] for key in ('provenance_leakage', 'scope_leakage', 'invalid_citation', 'duplicate_results')}
    report = {'status': 'PASS_DEV_METRIC_RECOMPUTATION' if not any(violations.values()) else 'FAIL_DEV_PROVENANCE',
        'release_eligible': False, 'heldout_used': False, 'llm_called': False,
        'source_identity': before, 'runner_sha256': sha256(Path(__file__)),
        'replay_report_path': args.replay_report.as_posix(), 'replay_report_sha256': sha256(args.replay_report),
        'dev_sha256': sha256(args.dev), 'index_sha256': sha256(args.index_dir / 'manifest.json'),
        'raw_path': raw.resolve().relative_to(ROOT).as_posix(), 'raw_sha256': sha256(raw),
        'metric_match_tolerance': 1e-12, 'metrics_match': True, 'violations': violations,
        'baseline': result['baseline'], 'phase7': result['phase7'], 'hard_queries': result['hard_queries'],
        'release_comparator_mrr_ci95': result['paired_statistics']['mrr']['ci95'],
        'improved_queries': len(result['improvement_qids']), 'regressed_queries': len(result['regression_qids']),
        'limitations': ['Dev diagnostic; no release gate, source review or heldout acceptance.',
            'Comparator bootstrap uses Python random.Random; original replay uses NumPy default_rng. Both use 10,000 connected-group draws and seed 20261007, but finite-sample intervals differ.']}
    write_json(args.output_dir / 'audit_report.json', report)
    print(json.dumps({key: report[key] for key in ('status', 'metrics_match', 'violations', 'release_comparator_mrr_ci95', 'improved_queries', 'regressed_queries')}), flush=True)
    return 0 if not any(violations.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
