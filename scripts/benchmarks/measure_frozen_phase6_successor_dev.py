"""Controlled dev comparison: frozen Phase 6 retrieval, existing request resolution.

The historical algorithm is isolated, not installed into production. Replaying
the measured input requests holds context/scope resolution constant. The fixed
threshold is an offline experiment, not a forged expanded-index calibration.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import subprocess
import sys
import time

from evaluation.common.artifact_store import resolve_artifact
from evaluation.common.release_artifacts import read_json, sha256, write_json
from evaluation.benchmarks.dev_inheritance import file_bindings, preserved_index, rows_at
from scripts.benchmarks.measure_frozen_phase6_dev import COMMIT, ROOT, source_tree


def current_source_identity():
    # Current identity code imports a module absent from Phase 6. Run it in a
    # separate interpreter so it cannot contaminate the isolated import tree.
    code = 'import json; from pathlib import Path; from evaluation.common.release_artifacts import source_identity; print(json.dumps(source_identity(Path.cwd())))'
    return json.loads(subprocess.check_output([sys.executable, '-c', code], cwd=ROOT))


def validate_inputs(rows, revision, raw, report, index_hash, f0_hash):
    ids = [row['qid'] for row in rows]
    observations = raw['observations']
    observed = [item['qid'] for item in observations]
    if (not rows or any(row.get('split') != 'dev' or row.get('release_eligible') is not False for row in rows)
            or len(ids) != len(set(ids)) or len(observed) != len(set(observed)) or set(ids) != set(observed)
            or raw.get('dev_sha256') != revision['parent_dev_sha256']
            or any(raw.get(key) != report.get(key) for key in
                   ('dev_sha256', 'index_sha256', 'f0_signoff_sha256', 'phase6_calibration_sha256'))
            or raw.get('index_sha256') != index_hash or raw.get('f0_signoff_sha256') != f0_hash
            or raw.get('test_used') is not False or raw.get('holdout_used') is not False
            or raw.get('measurements_real') is not True or report.get('source_stable') is not True
            or raw.get('source_identity_before') != raw.get('source_identity_after')):
        raise ValueError('requires unique, exactly paired reviewed dev and frozen measured requests')
    by_id = {row['qid']: row for row in rows}
    for item in observations:
        request = item['actual_request']
        if (set(request) != {'query', 'doc_ids', 'filters'} or not isinstance(request['query'], str)
                or request['doc_ids'] != by_id[item['qid']]['doc_ids']):
            raise ValueError('measured request shape or document scope changed')
    return {item['qid']: item['actual_request'] for item in observations}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('dev', 'revision-manifest', 'index-dir', 'original-index', 'historical-calibration',
                 'request-raw', 'request-report', 'f0-signoff', 'source-zip', 'output-dir'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists() or not args.output_dir.resolve().is_relative_to(ROOT / '.release/reranker/studies'):
        raise ValueError('use a new isolated study output')
    revision = read_json(args.revision_manifest)
    for name, digest in revision['outputs'].items():
        if sha256(args.revision_manifest.parent / name) != digest:
            raise ValueError('reviewed dev packet changed')
    if sha256(args.dev) != revision['outputs']['human_retrieval_dev.jsonl']:
        raise ValueError('dev differs from reviewed revision')
    calibration = read_json(args.historical_calibration)
    if (sha256(args.original_index / 'manifest.json') != calibration['index_sha256']
            or calibration['rrf'] != {'k': 3, 'bm25_weight': 1.0, 'dense_weight': 1.2, 'candidate_limit': 40}):
        raise ValueError('original calibration/index binding or numerical parameters changed')
    preserved_index(args.original_index, args.index_dir, file_bindings(args.original_index))
    f0 = read_json(args.f0_signoff)
    if f0.get('f0_split_frozen') is not True or f0['index_sha256'] != sha256(args.index_dir / 'manifest.json'):
        raise ValueError('requires exact successor F0 index')
    for name, digest in f0['benchmark_files'].items():
        if sha256(ROOT / f0['benchmark_dir'] / name) != digest:
            raise ValueError('F0 bytes changed')
    rows, report = rows_at(args.dev), read_json(args.request_report)
    if sha256(args.request_raw) != report['raw_sha256']:
        raise ValueError('request raw hash mismatch')
    with gzip.open(resolve_artifact(args.request_raw), 'rt', encoding='utf8') as stream:
        raw = json.load(stream)
    requests = validate_inputs(rows, revision, raw, report, f0['index_sha256'], sha256(args.f0_signoff))
    if set(requests) != {qid for qid, split in f0['split_assignments'].items() if split == 'dev'}:
        raise ValueError('request set differs from F0 dev authorization')
    isolated = ROOT / '.local_artifacts/experiment_runs/phase6-frozen-source-8e3a331-20261007'
    source_files = source_tree(resolve_artifact(args.source_zip), isolated)
    if any(name == 'campusai' or name.startswith('campusai.') for name in sys.modules):
        raise ValueError('current CampusAI imported before isolation')
    sys.path.insert(0, str(isolated / 'src'))
    from campusai.retrieval.hybrid import HybridRetriever
    from campusai.retrieval.model_runtime import retrieval_runtime
    from evaluation.retrieval.compare_retrieval_quality import query_metrics
    import torch
    torch.set_num_threads(1)
    before = current_source_identity()
    bindings = {'dev_sha256': sha256(args.dev), 'revision_manifest_sha256': sha256(args.revision_manifest),
        'index_sha256': f0['index_sha256'], 'historical_calibration_sha256': sha256(args.historical_calibration),
        'original_index_sha256': calibration['index_sha256'], 'f0_signoff_sha256': sha256(args.f0_signoff),
        'request_raw_sha256': sha256(args.request_raw), 'request_report_sha256': sha256(args.request_report),
        'source_commit': COMMIT, 'source_archive_sha256': sha256(args.source_zip), 'source_files': source_files,
        'runner_sha256': sha256(Path(__file__)), 'release_eligible': False, 'test_used': False, 'holdout_used': False,
        'llm_called': False, 'reranker_called': False, 'source_isolated': True,
        'threshold': calibration['result']['threshold'], 'request_resolution': 'Exact requests replayed from bound current-runtime raw; not historical contextual handling.'}
    args.output_dir.mkdir(parents=True)
    write_json(args.output_dir / 'attempt.json', bindings)
    retriever = HybridRetriever(args.index_dir, query_cache_size=0)
    observations = []
    started = time.perf_counter()
    try:
        for number, row in enumerate(rows, 1):
            request = {**requests[row['qid']], 'top_k': 5, 'mode': 'auto', 'score_threshold': bindings['threshold']}
            results = [item.to_dict() for item in retriever.search(**request)]
            observations.append({'qid': row['qid'], 'actual_request': request, 'baseline': results,
                                 'metrics': query_metrics(row, results) if row['answerable'] else None})
            if number % 100 == 0:
                print(json.dumps({'frozen_phase6_successor_dev': number, 'total': len(rows)}), flush=True)
    except Exception as error:
        write_json(args.output_dir / 'failure.json', {**bindings, 'completed': len(observations), 'error_type': type(error).__name__})
        raise
    after = current_source_identity()
    if before != after or any(sha256(isolated / name) != digest for name, digest in source_files.items()):
        raise ValueError('source changed during measurement')
    for name, module in list(sys.modules.items()):
        if (name == 'campusai' or name.startswith('campusai.')) and getattr(module, '__file__', None):
            if not Path(module.__file__).resolve().is_relative_to(isolated):
                raise ValueError('mixed current and frozen CampusAI imports')
    positive = [item['metrics'] for item in observations if item['metrics'] is not None]
    negatives = [item for item in observations if item['metrics'] is None]
    quality = {key: sum(item[key] for item in positive) / len(positive) for key in ('recall5', 'mrr', 'ndcg5', 'all_gold_recall5')}
    quality.update({'positive': len(positive), 'negative': len(negatives),
                    'negative_fpr': sum(bool(item['baseline']) for item in negatives) / len(negatives)})
    output = args.output_dir / 'frozen_source_successor_dev_observations.json.gz'
    with gzip.open(output, 'xt', encoding='utf8') as stream:
        json.dump({**bindings, 'observations': observations, 'source_identity_before': before, 'source_identity_after': after}, stream, ensure_ascii=False, allow_nan=False)
    write_json(args.output_dir / 'report.json', {**bindings, 'status': 'MEASURED_FROZEN_RETRIEVAL_SUCCESSOR_DEV_NOT_RELEASE',
        'source_identity_before': before, 'source_identity_after': after, 'source_stable': True,
        'raw_sha256': sha256(output), 'quality': quality, 'runtime_loaded_models': retrieval_runtime().loaded_models(),
        'elapsed_seconds': time.perf_counter() - started,
        'limitations': ['Controlled algorithm comparison only; not a current serving baseline or expanded-index M0.',
                       'Context/scope resolver held constant via requests; historical retrieval plus current request resolution is not the full historical stack.',
                       'No model scores fabricated or reranker/LLM called. No baseline/gate floor changed.']})
    print(json.dumps({'status': 'MEASURED_FROZEN_RETRIEVAL_SUCCESSOR_DEV_NOT_RELEASE', 'quality': quality}), flush=True)


if __name__ == '__main__':
    main()
