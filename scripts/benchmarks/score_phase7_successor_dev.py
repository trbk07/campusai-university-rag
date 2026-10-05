"""Score the exact F0 dev pools with real uncached, context-aligned inference.

Cap 40 is a diagnostic collection pool, never a release rerank configuration.
Raw calls are journaled before ranking analysis; no LLM or held-out calls run.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import time

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('TRANSFORMERS_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_TELEMETRY', '1')

from campusai.rag.context import benchmark_retrieval_request
from campusai.retrieval.cross_encoder_provider import (
    ModelIdentity, OfflineCrossEncoderReranker, snapshot_sha256,
)
from evaluation.benchmarks.connected_groups import connected_groups
from evaluation.benchmarks.dev_inheritance import rows_at
from evaluation.common.release_artifacts import read_json, sha256, source_identity, write_json
from evaluation.reranker.optimize_reranker_dev import rank_fusion, score_observation, summarize
from evaluation.reranker.reranker_probe_inputs import FORMATS, probe_loader

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('dev', 'index-dir', 'calibration', 'f0-signoff', 'candidate-raw', 'model-dir', 'output-dir'):
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--input-format', choices=FORMATS, default='body')
    parser.add_argument('--dtype', choices=('float32', 'float16', 'bfloat16'), default='float32')
    parser.add_argument('--batch-size', type=int, default=8)
    parser.add_argument('--torch-threads', type=int, choices=(1, 2, 4, 8, 16), default=1)
    args = parser.parse_args()
    if not args.output_dir.resolve().is_relative_to(ROOT / '.release/reranker/studies'):
        raise ValueError('diagnostic scores require an isolated study')
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    rows = rows_at(args.dev)
    f0 = read_json(args.f0_signoff)
    expected = {qid for qid, split in f0['split_assignments'].items() if split == 'dev'}
    if (not rows or any(row['split'] != 'dev' for row in rows)
            or len(rows) != len(expected) or {row['qid'] for row in rows} != expected
            or f0['f0_split_frozen'] is not True
            or f0['index_sha256'] != sha256(args.index_dir / 'manifest.json')):
        raise ValueError('scores require the exact authorized F0 dev and index')
    for name, digest in f0['benchmark_files'].items():
        if sha256(ROOT / f0['benchmark_dir'] / name) != digest:
            raise ValueError('F0 input changed')
    with gzip.open(args.candidate_raw, 'rt', encoding='utf8') as stream:
        raw = json.load(stream)
    candidate_report = read_json(args.candidate_raw.parent / 'dev_baseline_report.json')
    if (candidate_report.get('raw_sha256') != sha256(args.candidate_raw)
            or candidate_report.get('measurements_real') is not True
            or candidate_report.get('source_stable') is not True
            or any(candidate_report['coverage'][key] for key in
                   ('provenance_errors', 'scope_errors', 'duplicate_result_sets'))):
        raise ValueError('candidate raw data must match the verified actual measurement report')
    if (raw.get('dev_sha256') != sha256(args.dev)
            or raw.get('index_sha256') != f0['index_sha256']
            or raw.get('phase6_calibration_sha256') != sha256(args.calibration)
            or raw.get('f0_signoff_sha256') != sha256(args.f0_signoff)
            or raw.get('test_used') is not False or raw.get('holdout_used') is not False
            or raw.get('release_eligible') is not False or raw.get('measurements_real') is not True
            or raw.get('source_identity_before') != raw.get('source_identity_after')):
        raise ValueError('candidate data must be actual stable F0 dev observations')
    pools = {o['qid']: o for o in raw['observations']}
    if len(pools) != len(raw['observations']) or set(pools) != expected:
        raise ValueError('candidate observations must pair every unique dev input')
    docs = read_json(args.index_dir / 'manifest.json')['documents']
    for row in rows:
        if pools[row['qid']]['actual_request'] != benchmark_retrieval_request(row, docs):
            raise ValueError('context resolution differs from measured retrieval input')
    model_hash = snapshot_sha256(args.model_dir)
    if (args.model_dir.name != '1427fd652930e4ba29e8149678df786c240d8825'
            or model_hash != '23d9d1c4b424f03958bdb9f73b7ad43adb12b5a1bcf937dbe7eafd35ed56d24b'):
        raise ValueError('this experiment requires the recorded pinned BGE reranker')
    identity = ModelIdentity('BAAI/bge-reranker-v2-m3', args.model_dir.name, model_hash,
                             args.model_dir.name, device='cuda:0', dtype=args.dtype,
                             max_length=512, batch_size=args.batch_size, input_format=args.input_format)
    import torch
    torch.set_num_threads(args.torch_threads)
    before = source_identity(ROOT)
    bindings = {'dev_sha256': sha256(args.dev), 'index_sha256': f0['index_sha256'],
                'phase6_calibration_sha256': sha256(args.calibration),
                'f0_signoff_sha256': sha256(args.f0_signoff),
                'candidate_raw_sha256': sha256(args.candidate_raw),
                'candidate_source_identity': raw['source_identity_before'],
                'scoring_source_identity': before, 'runner_sha256': sha256(Path(__file__)),
                'release_eligible': False, 'calibration_split': 'dev',
                'test_used': False, 'holdout_used': False, 'llm_called': False,
                'model_identity': identity.to_dict(), 'model_identity_sha256': identity.fingerprint,
                'input_format': args.input_format, 'score_cache_size': 0,
                'collection_cap': 40, 'measurements_real': True,
                'torch_num_threads': torch.get_num_threads()}
    args.output_dir.mkdir(parents=True)
    write_json(args.output_dir / 'study_manifest.json', {
        **bindings, 'status': 'REGISTERED_DEV_SCORE_COLLECTION',
        'recorded_at': datetime.now(timezone.utc).isoformat(),
        'purpose': 'actual context-aligned successor dev scores and ranking-only diagnostics'})
    provider = OfflineCrossEncoderReranker(identity, args.model_dir, timeout_ms=60000,
        candidate_cap=40, score_cache_size=0, model_loader=probe_loader(args.model_dir, identity, args.input_format))
    observations = []
    started = time.perf_counter()
    journal = args.output_dir / 'actual_score_calls.jsonl.gz'
    try:
        provider.warm_up()
        with gzip.open(journal, 'xt', encoding='utf8') as stream:
            for number, row in enumerate(rows, 1):
                pool = pools[row['qid']]
                observation = score_observation(provider, row['qid'], pool['actual_request'],
                    pool['baseline'], pool['candidates'], args.input_format)
                observations.append(observation)
                stream.write(json.dumps(observation, ensure_ascii=False, allow_nan=False) + '\n')
                stream.flush()
                if number % 50 == 0:
                    print(json.dumps({'scored_dev_queries': number, 'total': len(rows)}), flush=True)
        provider.drain()
        statistics = provider.metrics_snapshot()
    except Exception as error:
        write_json(args.output_dir / 'failure.json', {
            **bindings, 'status': 'FAILED_REAL_DEV_SCORE_COLLECTION',
            'completed_observations': len(observations), 'error_type': type(error).__name__,
            'error': str(error), 'partial_calls_sha256': sha256(journal) if journal.exists() else None})
        raise
    finally:
        provider.close()
        provider.drain()
    after = source_identity(ROOT)
    if before != after:
        raise ValueError('source/runtime changed during score collection')
    scored = args.output_dir / 'raw_dev_scores.json.gz'
    with gzip.open(scored, 'xt', encoding='utf8') as stream:
        json.dump({**bindings, 'source_identity_before': before, 'source_identity_after': after,
                   'observations': observations}, stream, ensure_ascii=False, allow_nan=False)
    base = {o['qid']: o['baseline'] for o in observations}
    groups = connected_groups(rows)
    inherited = {qid for parent in read_json(args.dev.parent / 'phase7_dev_inheritance.json')['parents']
                 for qid in parent['qids']}
    cohorts = {'all_dev': rows, 'consumed_parent_dev': [r for r in rows if r['qid'] in inherited],
               'new_source_dev': [r for r in rows if r['qid'] not in inherited]}
    baseline = {name: {'records': len(part), 'groups': len({groups[r['qid']] for r in part}),
                      'metrics': summarize(part, base)} for name, part in cohorts.items()}
    trials = []
    for cap in (8, 10, 12, 16, 20, 40):
        for weight in (0., .1, .25, .5, .75, 1.):
            output = {o['qid']: rank_fusion(o['pool'], o['scores'], weight, cap)[:5]
                      for o in observations}
            quality = {name: summarize(part, output) for name, part in cohorts.items()}
            trials.append({'cap': cap, 'rank_weight': weight, 'metrics_by_cohort': quality,
                           'release_cap_allowed': cap <= 20,
                           'relative_uplift': {name: {key: quality[name][key] / baseline[name]['metrics'][key] - 1
                               if baseline[name]['metrics'][key] else None for key in ('mrr', 'ndcg5')}
                               for name in cohorts}})
    report = {**bindings, 'status': 'MEASURED_RANKING_ONLY_DEV_DIAGNOSTIC',
              'source_identity_before': before, 'source_identity_after': after, 'source_stable': True,
              'queries': len(rows), 'baseline_by_cohort': baseline, 'ranking_trials': trials,
              'raw_scores_sha256': sha256(scored), 'actual_calls_sha256': sha256(journal),
              'provider_statistics': statistics, 'elapsed_seconds': time.perf_counter() - started,
              'limitations': ['Same-dev ranking comparisons are exploratory, not grouped OOF or held-out acceptance.',
                'Cap 40 collection is diagnostic only; permitted release rerank caps remain <=20.',
                'All pools are scored independently of routing; no joint route/evidence/answer policy is claimed.',
                'Score timings include a diagnostic cap-40 call, not a same-config serving HTTP/latency measurement.',
                'No successor M0/M2/M4/M5/M6/S3/S4/S5 PASS is established.']}
    write_json(args.output_dir / 'dev_ranking_report.json', report)
    best = max(trials, key=lambda t: (t['metrics_by_cohort']['all_dev']['mrr'],
                                     t['metrics_by_cohort']['all_dev']['ndcg5']))
    print(json.dumps({'status': report['status'], 'queries': len(rows),
                      'baseline': baseline, 'best_exploratory_trial': best}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
