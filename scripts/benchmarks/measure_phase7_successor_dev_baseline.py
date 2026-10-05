"""Measure actual Phase 6 candidates on F0-authorized dev inputs only."""
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
from campusai.retrieval.calibration import RetrievalPolicy
from campusai.retrieval.hybrid import HybridRetriever
from campusai.retrieval.model_runtime import retrieval_runtime
from evaluation.benchmarks.dev_inheritance import rows_at
from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence
from evaluation.common.release_artifacts import read_json, sha256, source_identity, write_json
from evaluation.retrieval.evaluate_candidate_coverage import audit_outputs
from evaluation.reranker.optimize_reranker_dev import summarize

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('dev', 'index-dir', 'calibration', 'f0-signoff', 'output-dir'):
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--torch-threads', type=int, choices=(1, 2, 4, 8, 16), default=1)
    args = parser.parse_args()
    if not args.output_dir.resolve().is_relative_to(ROOT / '.release/reranker/studies'):
        raise ValueError('dev measurement requires an isolated study')
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    rows = rows_at(args.dev)
    f0 = read_json(args.f0_signoff)
    expected_dev = {qid for qid, split in f0['split_assignments'].items() if split == 'dev'}
    if (not rows or any(row['split'] != 'dev' for row in rows)
            or {row['qid'] for row in rows} != expected_dev
            or f0['index_sha256'] != sha256(args.index_dir / 'manifest.json')
            or f0['f0_split_frozen'] is not True):
        raise ValueError('measurement input differs from exact F0-authorized dev/index')
    for name, digest in f0['benchmark_files'].items():
        if sha256(ROOT / f0['benchmark_dir'] / name) != digest:
            raise ValueError('F0 input changed')
    args.output_dir.mkdir(parents=True)
    binding = {'dev_sha256': sha256(args.dev), 'index_sha256': f0['index_sha256'],
               'phase6_calibration_sha256': sha256(args.calibration),
               'f0_signoff_sha256': sha256(args.f0_signoff), 'runner_sha256': sha256(Path(__file__)),
               'release_eligible': False, 'calibration_split': 'dev',
               'test_used': False, 'holdout_used': False, 'torch_num_threads': args.torch_threads}
    write_json(args.output_dir / 'study_manifest.json', {
        **binding, 'recorded_at': datetime.now(timezone.utc).isoformat(),
        'purpose': 'actual successor dev Phase 6 baseline/candidate measurement before P7-09 tuning',
        'candidate_cap': 40, 'query_cache_size': 0, 'reranker_called': False,
        'llm_called': False, 'hf_network_access': False})
    before = source_identity(ROOT)
    import torch
    torch.set_num_threads(args.torch_threads)
    evidence = frozen_evidence(args.index_dir)
    docs = read_json(args.index_dir / 'manifest.json')['documents']
    retriever = HybridRetriever(args.index_dir, query_cache_size=0,
                               policies={'hybrid_rrf': RetrievalPolicy.from_report(args.calibration)})
    outputs, baseline, observations = {}, {}, []
    started = time.perf_counter()
    for number, row in enumerate(rows, 1):
        request = benchmark_retrieval_request(row, docs)
        request_started = time.perf_counter()
        ranked = retriever.search(**request, top_k=5, mode='auto')
        candidates = retriever.generate_candidates(**request, top_k=40, mode='auto')
        baseline[row['qid']] = [item.to_dict() for item in ranked]
        outputs[row['qid']] = [item.to_dict() for item in candidates]
        observations.append({'qid': row['qid'], 'actual_request': request,
                             'baseline': baseline[row['qid']], 'candidates': outputs[row['qid']],
                             'latency_ms': (time.perf_counter() - request_started) * 1000})
        if number % 50 == 0:
            print(json.dumps({'completed_dev_queries': number, 'total': len(rows)}), flush=True)
    after = source_identity(ROOT)
    if before != after:
        raise ValueError('source/runtime changed during actual measurement')
    coverage = audit_outputs(rows, outputs, docs, 40, evidence)
    quality = summarize(rows, baseline)
    raw = {**binding, 'source_identity_before': before, 'source_identity_after': after,
           'observations': observations, 'measurements_real': True}
    raw_path = args.output_dir / 'raw_dev_baseline.json.gz'
    with gzip.open(raw_path, 'xt', encoding='utf8') as stream:
        json.dump(raw, stream, ensure_ascii=False)
    report = {**binding, 'status': 'MEASURED_DEV_ONLY', 'measurements_real': True,
              'source_identity_before': before, 'source_identity_after': after,
              'source_stable': True, 'raw_sha256': sha256(raw_path),
              'queries': len(rows), 'quality': quality, 'coverage': coverage,
              'runtime_loaded_models': retrieval_runtime().loaded_models(),
              'torch_num_threads': torch.get_num_threads(), 'elapsed_seconds': time.perf_counter() - started}
    write_json(args.output_dir / 'dev_baseline_report.json', report)
    print(json.dumps({'status': report['status'], 'queries': len(rows), 'quality': quality,
                      'candidate_all_gold_recall': coverage['all_gold_recall']}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
