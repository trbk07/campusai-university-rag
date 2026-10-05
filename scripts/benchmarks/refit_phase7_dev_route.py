"""Refit query-only routing features on archived dev observations, without heldout access."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from campusai.rag.context import benchmark_retrieval_request
from campusai.retrieval.route_probability import FEATURES, VERSION, route_observations
from evaluation.common.release_artifacts import read_json, sha256, source_identity, write_json
from evaluation.reranker.calibrate_hard_query_route import route_metrics
from evaluation.reranker.calibrate_route_probabilities import fit_route_probabilities
from scripts.benchmarks.measure_phase7_dev_candidates import dev_rows

ROOT = Path(__file__).resolve().parents[2]


def refit(dev: Path, observations: Path, index: Path, output: Path) -> dict:
    rows = dev_rows(dev)
    if output.exists():
        raise ValueError('use an absent diagnostic output, preserving prior attempts')
    prior = read_json(observations)
    if (prior.get('calibration_split') != 'dev' or prior.get('test_used') is not False
            or prior.get('holdout_used') is not False or prior.get('training_split_sha256') != sha256(dev)
            or prior.get('index_sha256') != sha256(index / 'manifest.json')):
        raise ValueError('observations do not bind these exact dev inputs and index')
    by_qid = {row['qid']: row for row in rows}
    samples = prior['samples']
    if (not samples or len({sample['qid'] for sample in samples}) != len(samples)
            or any(sample['qid'] not in by_qid or sample['difficulty'] != by_qid[sample['qid']]['difficulty']
                   for sample in samples)):
        raise ValueError('observations do not pair unique dev query labels')
    before = source_identity(ROOT)
    documents = read_json(index / 'manifest.json')['documents']
    revised = []
    changed = []
    for sample in samples:
        query = benchmark_retrieval_request(by_qid[sample['qid']], documents)['query']
        features = route_observations(query, [])
        revised.append({**sample, **features})
        if any(sample[key] != features[key] for key in FEATURES):
            changed.append({'qid': sample['qid'], 'before': {key: sample[key] for key in FEATURES},
                            'after': features})
    model, diagnostics, feasible = fit_route_probabilities(revised, rows)
    after = source_identity(ROOT)
    if before != after:
        raise ValueError('source changed during dev refit')
    report = {**{key: prior[key] for key in ('index_sha256', 'phase6_calibration_sha256', 'training_split_sha256',
                                            'bypass', 'deterministic', 'exact_code_count', 'abstention_count',
                                            'exact_code_rerank_rate', 'abstention_rerank_rate')},
              'schema_version': 1, 'status': 'conditional', 'release_eligible': False,
              'purpose': 'query-only feature refit; archived retrieval observations reused, no new inference or heldout access',
              'calibration_split': 'dev', 'test_used': False, 'holdout_used': False,
              'version': VERSION, **before, 'source_before': before, 'source_after': after,
              'source_stable': True, 'model_identity_sha256': None,
              'recorded_at': datetime.now(timezone.utc).isoformat(),
              'dev_path': dev.as_posix(), 'observation_path': observations.as_posix(),
              'observation_sha256': sha256(observations),
              'retrieval_observation_identity': {key: prior[key] for key in ('commit', 'source_sha256', 'runtime_sha256')},
              'easy_confidence_threshold': 1., 'easy_margin_threshold': 1.,
              'minimum_agreement': 0., 'constraint_threshold': 0,
              'route_model': model, 'route_diagnostics': diagnostics, 'dev_feasible': feasible,
              'routing_metrics': route_metrics(revised, 1., 1., route_model=model),
              'feature_allowlist': list(FEATURES), 'forbidden_features': ['language', 'template', 'difficulty', 'qid'],
              'feature_changes': changed, 'samples': revised}
    write_json(output, report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dev', type=Path, required=True)
    parser.add_argument('--observations', type=Path, required=True)
    parser.add_argument('--index-dir', type=Path, default=Path('.tmp/hybrid-index'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    report = refit(args.dev, args.observations, args.index_dir, args.output)
    print({key: report[key] for key in ('status', 'dev_feasible', 'routing_metrics')})
    print('out_of_fold:', report['route_diagnostics']['out_of_fold_metrics'])
    return 0 if report['dev_feasible'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
