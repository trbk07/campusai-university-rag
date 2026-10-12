"""Reuse exact measured dev logits after a retrieval-order change, with hashes.

This performs zero model calls. Every candidate's scored query/text must be
byte-identical to its measured ancestor. It establishes no new runtime latency.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

from campusai.retrieval.reranker_inputs import scoring_text, QUERY_MAX_CHARS, CONTENT_MAX_CHARS
from evaluation.common.artifact_store import resolve_artifact
from evaluation.common.release_artifacts import read_json, sha256, source_identity, write_json

ROOT = Path(__file__).resolve().parents[2]


def transfer(measured, current, input_format):
    old = {x['qid']: x for x in measured}
    ids = [x['qid'] for x in current]
    if len(old) != len(measured) or len(ids) != len(set(ids)) or set(old) != set(ids):
        raise ValueError('requires exactly paired unique dev queries')
    output = []
    for obs in current:
        ancestor = old[obs['qid']]
        if obs['actual_request'] != ancestor['actual_request']:
            raise ValueError('resolved request changed; actual rescoring required')
        query = obs['actual_request']['query'][:QUERY_MAX_CHARS]
        if hashlib.sha256(query.encode()).hexdigest() != ancestor['scoring_query_sha256']:
            raise ValueError('scored query bytes changed')
        pool = obs['candidates']
        if len({x['chunk_id'] for x in pool}) != len(pool):
            raise ValueError('duplicate candidate identity')
        prior_pool = {x['chunk_id']: x for x in ancestor['pool']}
        hashes, scores = {}, {}
        for item in pool:
            key = item['chunk_id']
            previous = prior_pool.get(key)
            if previous is None or any(item[field] != previous[field] for field in ('doc_id', 'page', 'content')):
                raise ValueError('candidate provenance/content changed or was not measured')
            text = scoring_text(item['content'], input_format, query)[:CONTENT_MAX_CHARS]
            digest = hashlib.sha256(text.encode()).hexdigest()
            value = ancestor['scores'].get(key)
            if (digest != ancestor['scoring_input_sha256'].get(key)
                    or type(value) not in (float, int) or not math.isfinite(value)):
                raise ValueError('missing/different measured scoring input or invalid logit')
            hashes[key], scores[key] = digest, value
        output.append({'qid': obs['qid'], 'actual_request': obs['actual_request'], 'baseline': obs['baseline'],
            'pool': pool, 'scores': scores, 'scoring_input_sha256': hashes,
            'resolved_query_sha256': ancestor['resolved_query_sha256'],
            'scoring_query_sha256': ancestor['scoring_query_sha256'],
            'latency_ms': None, 'provider_call': {'inference_started': False, 'offline_score_reuse': True}})
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('measured-scores', 'measured-report', 'current-baseline-raw', 'current-baseline-report',
                 'dev-revision-manifest', 'output-dir'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists() or not args.output_dir.resolve().is_relative_to(ROOT / '.release/reranker/studies'):
        raise ValueError('use a new isolated dev replay directory')
    old_report, baseline_report, revision = (read_json(p) for p in
        (args.measured_report, args.current_baseline_report, args.dev_revision_manifest))
    if sha256(args.measured_scores) != old_report['raw_scores_sha256'] or sha256(args.current_baseline_raw) != baseline_report['raw_sha256']:
        raise ValueError('raw report binding mismatch')
    with gzip.open(resolve_artifact(args.measured_scores), 'rt', encoding='utf8') as stream:
        measured = json.load(stream)
    with gzip.open(resolve_artifact(args.current_baseline_raw), 'rt', encoding='utf8') as stream:
        current = json.load(stream)
    if (current['dev_sha256'] != revision['parent_dev_sha256']
            or measured['dev_revision_manifest_sha256'] != sha256(args.dev_revision_manifest)
            or measured['parent_dev_sha256'] != revision['parent_dev_sha256']
            or any(measured[key] != current[key] for key in ('index_sha256', 'f0_signoff_sha256', 'phase6_calibration_sha256'))
            or any(x.get('test_used') is not False or x.get('holdout_used') is not False
                   or x.get('source_identity_before') != x.get('source_identity_after') for x in (current, measured))
            or baseline_report.get('source_stable') is not True or old_report.get('source_stable') is not True):
        raise ValueError('requires stable, dev-only source and unchanged index/F0/calibration/revision')
    before = source_identity(ROOT)
    observations = transfer(measured['observations'], current['observations'], measured['input_format'])
    if source_identity(ROOT) != before:
        raise ValueError('source changed during offline transfer')
    bindings = {key: measured[key] for key in ('dev_sha256', 'index_sha256', 'phase6_calibration_sha256',
        'f0_signoff_sha256', 'model_identity', 'model_identity_sha256', 'model_origin', 'input_format',
        'dev_revision_manifest_sha256', 'parent_dev_sha256')}
    bindings.update({'source_identity_before': before, 'source_identity_after': before, 'source_stable': True,
        'release_eligible': False, 'test_used': False, 'holdout_used': False, 'llm_called': False,
        'model_calls_this_replay': 0, 'measurements_real': False, 'ancestor_score_measurements_real': True,
        'measured_scores_sha256': sha256(args.measured_scores), 'measured_report_sha256': sha256(args.measured_report),
        'current_baseline_raw_sha256': sha256(args.current_baseline_raw), 'current_baseline_report_sha256': sha256(args.current_baseline_report),
        'current_baseline_source_identity': current['source_identity_before'],
        'ancestor_model_scoring_source_identity': measured['source_identity_before'],
        'runner_sha256': sha256(Path(__file__)), 'baseline_identity_note': 'Current enhanced retrieval, not the unmodified frozen Phase 6 algorithm.'})
    args.output_dir.mkdir(parents=True)
    raw_path = args.output_dir / 'raw_dev_scores.json.gz'
    with gzip.open(raw_path, 'xt', encoding='utf8') as stream:
        json.dump({**bindings, 'observations': observations}, stream, ensure_ascii=False, allow_nan=False)
    write_json(args.output_dir / 'dev_ranking_report.json', {**bindings,
        'status': 'EXACT_MEASURED_LOGITS_TRANSFERRED_OFFLINE_NOT_NEW_INFERENCE',
        'raw_scores_sha256': sha256(raw_path), 'queries': len(observations),
        'transferred_candidate_pairs': sum(len(x['scores']) for x in observations),
        'limitations': ['Every scored query/text/provenance hash is checked; changed ranks are an offline replay.',
                       'Zero new model calls; old GPU timings are not transferred into the new runtime.',
                       'Current baseline and candidate ordering changed; old nested choices need fresh train-only replay.',
                       'No three-class evidence, answer, serving, F1 or release gate acceptance.']})
    print('Exact scored inputs transferred;', len(observations), 'dev queries; 0 new model calls')


if __name__ == '__main__':
    main()
