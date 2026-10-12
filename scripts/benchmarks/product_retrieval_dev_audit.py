"""Measure the real product WSGI retrieval path on the existing 829 dev rows.

No new corpus, fitting, primary reads or provider calls. Preserve failed and
changed cases against the existing measured comparator, including request
transformation differences. A dev pass alone is not C7-02 primary acceptance.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from unittest.mock import patch

from evaluation.benchmarks.dev_inheritance import rows_at
from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence
from evaluation.common.artifact_store import resolve_artifact
from evaluation.common.release_artifacts import read_json, sha256, source_identity, write_json
from evaluation.retrieval.evaluate_candidate_coverage import audit_outputs, coverage_errors
from evaluation.reranker.optimize_reranker_dev import summarize
from campusai.rag.context import benchmark_request, benchmark_retrieval_request
from campusai.rag.service import retrieval_query
from scripts.benchmarks.product_quality_pilot import (ROOT, BASE, DEV, PROFILE, profile_environment,
    disable_answer_cache, wsgi_request)
from scripts.operations.serve import build_application
from campusai.web import make_wsgi_app

COMPARATOR = Path('.release/reranker/studies/phase7-current-field-intent-gpu-dev-20261008-v1')


def compact(audit):
    return {k: v for k, v in audit.items() if k not in {'per_query', 'coverage_per_query'}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    before = source_identity(ROOT)
    old_report = read_json(COMPARATOR / 'dev_baseline_report.json')
    raw_path = COMPARATOR / 'raw_dev_baseline.json.gz'
    assert sha256(raw_path) == old_report['raw_sha256']
    assert old_report['dev_sha256'] == sha256(DEV)
    assert old_report['index_sha256'] == sha256(Path(PROFILE['CAMPUSAI_INDEX_DIR']) / 'manifest.json')
    assert old_report['phase6_calibration_sha256'] == sha256(Path(PROFILE['CAMPUSAI_RETRIEVAL_CALIBRATION']))
    with gzip.open(resolve_artifact(raw_path), 'rt', encoding='utf8') as stream:
        old_raw = json.load(stream)
    old = {o['qid']: o for o in old_raw['observations']}
    del old_raw
    rows = rows_at(DEV)
    assert len(rows) == 829 and all(r['split'] == 'dev' for r in rows)
    assert set(old) == {r['qid'] for r in rows}
    docs = read_json(Path(PROFILE['CAMPUSAI_INDEX_DIR']) / 'manifest.json')['documents']
    evidence = frozen_evidence(Path(PROFILE['CAMPUSAI_INDEX_DIR']))
    baseline, candidates, observations = {}, {}, []
    with profile_environment(), patch('scripts.operations.serve.create_llm', return_value=None):
        import torch
        torch.set_num_threads(8)
        app = build_application()
        disable_answer_cache(app)
        web = make_wsgi_app(app)
        try:
            assert not app.query_service.retriever.phase7_enabled
            for n, row in enumerate(rows, 1):
                request = benchmark_request(row, docs)
                response = wsgi_request(web, request)
                assert response['status'] == '200 OK' and response['body']['ok'], row['qid']
                found = [x.to_dict() for x in app.query_service.last_retrieval]
                candidate_request = benchmark_retrieval_request(row, docs)
                candidate_request['query'] = retrieval_query(candidate_request['query'])
                pool = [x.to_dict() for x in app.query_service.retriever.generate_candidates(
                    **candidate_request, top_k=40, mode='auto')]
                baseline[row['qid']], candidates[row['qid']] = found, pool
                coordinates = lambda values: [(x['doc_id'], x['chunk_id'], x['page']) for x in values]
                observations.append({'qid': row['qid'], 'request': request,
                    'actual_retrieval_request': candidate_request, 'baseline': found, 'candidates': pool,
                    'prior_request': old[row['qid']]['actual_request'],
                    'baseline_coordinates_changed': coordinates(found) != coordinates(old[row['qid']]['baseline'])})
                if n % 100 == 0:
                    print(json.dumps({'completed_dev_requests': n, 'total': len(rows)}), flush=True)
        finally:
            app.close()
    after = source_identity(ROOT)
    assert before == after
    quality = summarize(rows, baseline)
    old_quality = summarize(rows, {qid: o['baseline'] for qid, o in old.items()})
    coverage = audit_outputs(rows, candidates, docs, 40, evidence)
    head_coverage = audit_outputs(rows, baseline, docs, 5, evidence)
    violations = coverage_errors(coverage, .95)
    for part in (coverage, head_coverage):
        for key in ('provenance_errors', 'scope_errors', 'duplicate_result_sets'):
            if part[key]: violations.append(key)
    for metric in ('recall5', 'mrr', 'ndcg5', 'all_gold_coverage5'):
        if quality[metric] < old_quality[metric] - 1e-12:
            violations.append(metric + '_dev_regression')
    if quality['recall5'] < .98: violations.append('dev_recall_below_98pct')
    raw = args.output_dir / 'raw.json.gz'
    with gzip.open(raw, 'wt', encoding='utf8') as stream:
        json.dump({'source_identity': before, 'profile': PROFILE, 'observations': observations,
                   'new_provider_calls': 0, 'test_or_holdout_read': False}, stream, ensure_ascii=False)
    report = {'schema_version': 1, 'status': 'DEV_PASS_PRIMARY_STILL_REQUIRED' if not violations else 'DEV_FAILURE',
        'source_identity': before, 'profile': PROFILE, 'queries': len(rows), 'quality': quality,
        'comparator_quality': old_quality, 'candidate_coverage': compact(coverage),
        'top5_coverage': compact(head_coverage), 'violations': violations,
        'changed_coordinates': sum(o['baseline_coordinates_changed'] for o in observations),
        'request_transform_changes': sum(o['actual_retrieval_request']['query'] != o['prior_request']['query'] for o in observations),
        'bindings': {'dev': sha256(DEV), 'index': sha256(Path(PROFILE['CAMPUSAI_INDEX_DIR']) / 'manifest.json'),
            'calibration': sha256(Path(PROFILE['CAMPUSAI_RETRIEVAL_CALIBRATION'])),
            'raw': sha256(raw), 'comparator_raw': sha256(raw_path), 'runner': sha256(Path(__file__))},
        'new_provider_calls': 0, 'test_or_holdout_read': False, 'c7_02_complete': False,
        'limits': ['Dev only. Primary test/holdout acceptance still required.',
                   'LLM disabled for retrieval measurement; no live quality or latency claim.']}
    write_json(args.output_dir / 'summary.json', report)
    print(json.dumps({k: report[k] for k in ('status', 'quality', 'changed_coordinates', 'request_transform_changes', 'violations')}))
    if violations:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
