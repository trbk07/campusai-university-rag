"""Run the historical Phase 6 source in an isolated import tree on dev only.

The original Git object, archive bytes, benchmark, calibration and index are
verified. This measures current-environment compatibility, never rewrites an
old report or runs primary successor heldout inputs.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
COMMIT = '8e3a331838fbccaa16b4dd00381b9ed4738e958f'
for name in ('HF_HUB_OFFLINE', 'TRANSFORMERS_OFFLINE', 'HF_HUB_DISABLE_TELEMETRY'):
    os.environ.setdefault(name, '1')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_tree(archive, destination):
    if not destination.resolve().is_relative_to(ROOT / '.local_artifacts/experiment_runs'):
        raise ValueError('isolated source must stay inside experiment_runs')
    with zipfile.ZipFile(archive) as stream:
        if stream.comment.decode() != COMMIT:
            raise ValueError('archive must identify the actual frozen Phase 6 commit')
        files = {}
        members = [member for member in stream.infolist() if not member.is_dir()]
        names = [member.filename for member in members]
        expected_names = subprocess.check_output(
            ['git', 'ls-tree', '-r', '--name-only', COMMIT, '--', 'src'], cwd=ROOT).decode('utf8').splitlines()
        if len(names) != len(set(names)) or set(names) != set(expected_names):
            raise ValueError('archive must contain the complete unique frozen source set')
        prepared = []
        for member in members:
            name = member.filename
            if (not name.startswith('src/') or '..' in Path(name).parts or Path(name).is_absolute()
                    or (member.external_attr >> 16) & 0o170000 == 0o120000):
                raise ValueError('unsafe source archive member')
            data = stream.read(member)
            expected = subprocess.check_output(['git', 'show', COMMIT + ':' + name], cwd=ROOT)
            if data != expected:
                raise ValueError('archive differs from the original Git source: ' + name)
            target = (destination / name).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise ValueError('source extraction escapes isolated tree')
            if target.exists():
                if target.read_bytes() != data:
                    raise ValueError('isolated source changed')
            prepared.append((target, data))
            files[name] = hashlib.sha256(data).hexdigest()
        # Verify the entire archive and every existing target before writing.
        for target, data in prepared:
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('dev', 'index-dir', 'calibration', 'source-zip', 'output-dir'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists() or not args.output_dir.resolve().is_relative_to(ROOT / '.release/reranker/studies'):
        raise ValueError('use a new isolated study output')
    rows = [json.loads(line) for line in args.dev.read_text(encoding='utf8').splitlines() if line]
    calibration = json.loads(args.calibration.read_text(encoding='utf8'))
    if (not rows or any(row['split'] != 'dev' for row in rows)
            or digest(args.dev) != calibration['benchmark_sha256']
            or digest(args.index_dir / 'manifest.json') != calibration['index_sha256']):
        raise ValueError('requires the exact historical dev and index')
    isolated = ROOT / '.local_artifacts/experiment_runs/phase6-frozen-source-8e3a331-20261007'
    source_files = source_tree(args.source_zip, isolated)
    if any(name == 'campusai' or name.startswith('campusai.') for name in sys.modules):
        raise ValueError('current CampusAI code was imported before isolation')
    sys.path.insert(0, str(isolated / 'src'))
    from campusai.retrieval.hybrid import HybridRetriever
    from campusai.retrieval.calibration import RetrievalPolicy
    from campusai.retrieval.model_runtime import retrieval_runtime
    import torch
    torch.set_num_threads(1)
    policy = RetrievalPolicy.from_report(args.calibration)
    retriever = HybridRetriever(args.index_dir, query_cache_size=0, policies={'hybrid_rrf': policy})
    documents = json.loads((args.index_dir / 'manifest.json').read_text(encoding='utf8'))['documents']
    bindings = {'source_commit': COMMIT, 'source_archive_sha256': digest(args.source_zip),
        'source_files': source_files, 'runner_sha256': digest(Path(__file__)),
        'dev_sha256': digest(args.dev), 'index_sha256': digest(args.index_dir / 'manifest.json'),
        'calibration_sha256': digest(args.calibration), 'request_document_scope': documents,
        'source_isolated': True, 'release_eligible': False, 'test_used': False, 'holdout_used': False,
        'reranker_called': False, 'llm_called': False,
        'runtime': {'python': sys.version, **{name: version(name) for name in ('torch', 'transformers', 'sentence-transformers', 'numpy')}}}
    observations = []
    started = time.perf_counter()
    args.output_dir.mkdir(parents=True)
    (args.output_dir / 'attempt.json').write_text(json.dumps(bindings, indent=2) + '\n', encoding='utf8')
    try:
        for number, row in enumerate(rows, 1):
            request = {'query': row['question'], 'doc_ids': documents, 'filters': row.get('filters'), 'top_k': 5, 'mode': 'auto'}
            values = [item.to_dict() for item in retriever.search(**request)]
            hit = any(item['doc_id'] == gold['doc_id'] and item['chunk_id'] == gold['chunk_id']
                      and item['page'] in gold.get('pages', [gold.get('page')])
                      for item in values for gold in row['gold_evidence'])
            observations.append({'qid': row['qid'], 'answerable': row['answerable'], 'actual_request': request,
                                 'results': values, 'recall5': float(hit) if row['answerable'] else None})
            if number % 35 == 0:
                print(json.dumps({'frozen_phase6_dev': number, 'total': len(rows)}), flush=True)
    except Exception as error:
        (args.output_dir / 'failure.json').write_text(json.dumps({**bindings, 'status': 'FAILED_ACTUAL_FROZEN_SOURCE_MEASUREMENT',
            'completed': len(observations), 'error_type': type(error).__name__}, indent=2) + '\n', encoding='utf8')
        raise
    for name, expected in source_files.items():
        if digest(isolated / name) != expected:
            raise ValueError('frozen source changed during measurement')
    for name, module in list(sys.modules.items()):
        if (name == 'campusai' or name.startswith('campusai.')) and getattr(module, '__file__', None):
            if not Path(module.__file__).resolve().is_relative_to(isolated):
                raise ValueError('mixed current and frozen imports')
    raw_path = args.output_dir / 'frozen_source_dev_observations.json.gz'
    with gzip.open(raw_path, 'xt', encoding='utf8') as stream:
        json.dump({**bindings, 'observations': observations}, stream, ensure_ascii=False, allow_nan=False)
    positive = [item for item in observations if item['answerable']]
    negative = [item for item in observations if not item['answerable']]
    recall, fpr = sum(item['recall5'] for item in positive) / len(positive), sum(bool(item['results']) for item in negative) / len(negative)
    report = {**bindings, 'status': 'MEASURED_FROZEN_PHASE6_DEV_COMPATIBILITY_NOT_M0',
        'positive_hits': sum(item['recall5'] for item in positive), 'positive': len(positive), 'negative': len(negative),
        'recall5': recall, 'negative_fpr': fpr, 'historical_dev_recall5': calibration['result']['answerable_recall_at_5'],
        'historical_rounded_metric_matches': round(recall, 6) == calibration['result']['answerable_recall_at_5'],
        'raw_sha256': digest(raw_path), 'elapsed_seconds': time.perf_counter()-started,
        'runtime_loaded_models': retrieval_runtime().loaded_models(),
        'limitations': ['Dev/current-environment compatibility only; no official M0 test/holdout reruns or expanded-index release baseline.',
                        'Frozen source must not be substituted for current production evidence without an explicit architecture/identity binding.']}
    (args.output_dir / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
    print(json.dumps({key: report[key] for key in ('status', 'positive_hits', 'positive', 'recall5', 'negative_fpr', 'historical_rounded_metric_matches')}), flush=True)


if __name__ == '__main__':
    main()
