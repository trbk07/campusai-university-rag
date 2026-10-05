"""Measure applicability of unchanged Phase 6 parameters on the expanded index.

This creates new dev observations and a new index qualification, never changes
the historical report's bytes or fabricates a replacement historical baseline.
Official M0/reference/reruns remain a separate prerequisite before F1.
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

from campusai.retrieval.calibration import RetrievalPolicy
from campusai.retrieval.confidence import LEGACY_CONFIDENCE_MODEL
from campusai.retrieval.hybrid import HybridRetriever
from campusai.retrieval.model_runtime import retrieval_runtime
from evaluation.benchmarks.dev_inheritance import rows_at
from evaluation.common.release_artifacts import read_json, sha256, source_identity, write_json
from evaluation.retrieval.compare_retrieval_quality import query_metrics

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('dev', 'index-dir', 'historical-calibration', 'output-dir'):
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    original_hash = sha256(args.historical_calibration)
    original = read_json(args.historical_calibration)
    policy = RetrievalPolicy.from_report(args.historical_calibration)
    rows = rows_at(args.dev)
    if (not rows or any(row['split'] != 'dev' for row in rows)
            or sha256(args.dev) != original['benchmark_sha256']
            or policy.confidence_model != LEGACY_CONFIDENCE_MODEL
            or original['rrf'] != {'k': 3, 'bm25_weight': 1.0, 'dense_weight': 1.2, 'candidate_limit': 40}):
        raise ValueError('requires exact historical dev inputs and unchanged legacy Phase 6 parameters')
    positive = sum(row['answerable'] for row in rows)
    negative = len(rows) - positive
    if not positive or not negative:
        raise ValueError('dev qualification needs both classes')
    args.output_dir.mkdir(parents=True)
    before = source_identity(ROOT)
    import torch
    torch.set_num_threads(1)
    manifest = read_json(args.index_dir / 'manifest.json')
    retriever = HybridRetriever(args.index_dir, query_cache_size=0)
    # The production policy retains its old fingerprint. Direct score_threshold
    # is the supported uncalibrated measurement interface: fixed threshold/model,
    # actual new index, and no policy artifact is loaded with a forged fingerprint.
    observations = []
    started = time.perf_counter()
    for number, row in enumerate(rows, 1):
        arguments = {'query': row['question'], 'doc_ids': manifest['documents'],
                     'filters': row.get('filters'), 'top_k': 5, 'mode': 'auto'}
        unfiltered = retriever.search(**arguments)
        filtered = retriever.search(**arguments, score_threshold=policy.threshold)
        observations.append({'qid': row['qid'], 'answerable': row['answerable'],
                             'unthresholded': [item.to_dict() for item in unfiltered],
                             'fixed_threshold_results': [item.to_dict() for item in filtered],
                             'unthresholded_metrics': query_metrics(row, [item.to_dict() for item in unfiltered]) if row['answerable'] else None,
                             'fixed_threshold_metrics': query_metrics(row, [item.to_dict() for item in filtered]) if row['answerable'] else None})
        if number % 35 == 0:
            print(json.dumps({'measured_phase6_dev': number, 'total': len(rows)}), flush=True)
    unthresholded_recall = sum(item['unthresholded_metrics']['recall5'] for item in observations if item['answerable']) / positive
    recall = sum(item['fixed_threshold_metrics']['recall5'] for item in observations if item['answerable']) / positive
    fpr = sum(bool(item['fixed_threshold_results']) for item in observations if not item['answerable']) / negative
    drop = unthresholded_recall - recall
    constraints = original['constraints']
    valid = fpr <= constraints['max_false_positive_rate'] and drop <= constraints['max_answerable_recall_drop']
    after = source_identity(ROOT)
    if before != after or sha256(args.historical_calibration) != original_hash:
        raise ValueError('code/runtime/historical calibration changed during measurement')
    raw_path = args.output_dir / 'phase6_successor_dev_observations.json.gz'
    with gzip.open(raw_path, 'xt', encoding='utf8') as stream:
        json.dump({'dev_sha256': sha256(args.dev), 'index_sha256': sha256(args.index_dir / 'manifest.json'),
                   'historical_calibration_sha256': original_hash, 'observations': observations,
                   'release_eligible': False, 'test_used': False, 'holdout_used': False}, stream, ensure_ascii=False)
    report = {'schema_version': 2, 'phase': 6, 'mode': 'hybrid_rrf',
              'status': 'pass' if valid else 'fail', 'release_eligible': False,
              'purpose': 'Measured dev applicability of unchanged historical Phase 6 parameters to successor index',
              'recorded_at': datetime.now(timezone.utc).isoformat(), 'calibration_split': 'dev',
              'test_used': False, 'holdout_used': False, 'parameters_refitted': False,
              'historical_calibration_sha256': original_hash, 'historical_calibration_unchanged': True,
              'benchmark_sha256': sha256(args.dev), 'training_split_sha256': sha256(args.dev),
              'index_sha256': sha256(args.index_dir / 'manifest.json'),
              'model': manifest['model_name'], 'model_revision': manifest['model_revision'],
              'confidence_model': policy.confidence_model.to_dict(),
              'confidence_model_sha256': policy.confidence_model.fingerprint,
              'rrf': original['rrf'], 'constraints': constraints,
              'population': {'total': len(rows), 'answerable': positive, 'negative': negative},
              'baseline_answerable_recall_at_5': unthresholded_recall,
              'result': {'threshold': policy.threshold, 'answerable_recall_at_5': recall,
                         'false_positive_rate': fpr, 'recall_drop': drop} if valid else None,
              'actual_fixed_parameter_observation': {'threshold': policy.threshold,
                         'answerable_recall_at_5': recall, 'false_positive_rate': fpr, 'recall_drop': drop},
              'source_identity_before': before, 'source_identity_after': after, 'source_stable': True,
              'raw_observations_sha256': sha256(raw_path), 'runner_sha256': sha256(Path(__file__)),
              'runtime_loaded_models': retrieval_runtime().loaded_models(), 'torch_num_threads': torch.get_num_threads(),
              'elapsed_seconds': time.perf_counter() - started,
              'limitation': 'This is new dev evidence, not an M0 historical/reference/rerun or official baseline freeze.'}
    write_json(args.output_dir / 'hybrid_retrieval_calibration.json', report)
    print(json.dumps({'status': report['status'], 'actual_fixed_parameter_observation': report['actual_fixed_parameter_observation']}), flush=True)
    return 0 if valid else 1


if __name__ == '__main__':
    raise SystemExit(main())
