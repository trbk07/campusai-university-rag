"""Prepare and collect one explicitly authorized dev pilot after grounding repair.

Paired evidence comes from measured current retrieval and official BGE nested
OOF replay. It is a grounding diagnostic, not frozen serving acceptance.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import gzip
import json
import os
from pathlib import Path
import random
import time

from campusai.rag.grounding import GroundedAnswerGenerator
from evaluation.benchmarks.dev_inheritance import rows_at
from evaluation.common.artifact_store import resolve_artifact
from evaluation.common.release_artifacts import read_json, sha256, source_identity, write_json
from evaluation.reranker.collect_paired_answers import recording_generate
from evaluation.reranker.paired_answer_quality import answer_digest
from scripts.benchmarks.phase7_dev_answer_pilot import results, QIDS

ROOT = Path(__file__).resolve().parents[2]
REVISION = ROOT / 'data/benchmark/phase7_dev_gold_revision_20261007/packet'
REPLAY = ROOT / '.release/reranker/studies/phase7-primary-course-tables-window-nested-20261007-v1'


def bound_sources():
    paths = [Path(__file__), ROOT / 'scripts/benchmarks/phase7_dev_answer_pilot.py',
             ROOT / 'evaluation/reranker/collect_paired_answers.py']
    for folder in ('rag', 'llm'):
        paths.extend((ROOT / 'src/campusai' / folder).glob('*.py'))
    return {p.relative_to(ROOT).as_posix(): sha256(p) for p in sorted(paths)}


def prepare(path):
    if path.exists():
        raise FileExistsError(path)
    manifest = read_json(REVISION / 'manifest.json')
    for name, digest in manifest['outputs'].items():
        if sha256(REVISION / name) != digest:
            raise ValueError('reviewed dev revision changed')
    rows = {row['qid']: row for row in rows_at(REVISION / 'human_retrieval_dev.jsonl')}
    rubric = read_json(REVISION / 'rubric.partial.json')
    report = read_json(REPLAY / 'nested_dev_report.json')
    raw_path = REPLAY / 'nested_oof_decisions.json.gz'
    if (report['decisions_sha256'] != sha256(raw_path) or report['test_used'] or report['holdout_used']
            or report['release_eligible'] or report['dev_sha256'] != sha256(REVISION / 'human_retrieval_dev.jsonl')
            or report['model_identity']['model_name'] != 'BAAI/bge-reranker-v2-m3'):
        raise ValueError('requires reviewed dev-only official BGE replay')
    with gzip.open(resolve_artifact(raw_path), 'rt', encoding='utf8') as stream:
        observations = {part['qid']: part for part in json.load(stream)}
    generator = GroundedAnswerGenerator(max_context_chars=12000, max_context_tokens=2500)
    pairs = []
    rng = random.Random(7)
    for qid in QIDS:
        row, observed = rows[qid], observations[qid]
        if row['split'] != 'dev' or row['release_eligible'] or qid not in rubric['claims']:
            raise ValueError('requires source-reviewed dev')
        arms = {'current_enhanced_baseline': observed['baseline'], 'official_bge_nested_oof_replay': observed['results']}
        order = list(arms)
        rng.shuffle(order)
        for arm in order:
            evidence = arms[arm]
            prompt = generator.prompt(row['question'], results(evidence))
            pairs.append({'qid': qid, 'arm': arm, 'question': row['question'],
                'evidence': evidence, 'prompt': prompt, 'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
                'gold_claims': rubric['claims'][qid], 'route_selected': observed['route_selected'],
                'actual_arm': arm})
    packet = {'schema_version': 1, 'status': 'PREPARED_AWAITING_EXACT_PACKET_EGRESS_AUTHORIZATION',
        'endpoint_host': 'generativelanguage.googleapis.com', 'provider': 'Gemini',
        'model': 'gemini-3-flash-preview', 'max_provider_calls': 8, 'max_retries': 0,
        'generation_config': {'temperature': 0, 'maxOutputTokens': 4096, 'thinkingConfig': {'thinkingLevel': 'low'}},
        'minimum_call_start_interval_seconds': 30, 'context_budget': {'max_chars': 12000, 'max_tokens': 2500},
        'benchmark_queries': 4, 'prompt_chars': sum(len(p['prompt']) for p in pairs), 'seed': 7,
        'release_eligible': False, 'test_or_holdout_read': False, 'current_serving_measurement': False,
        'pairs': pairs,
        'source_identity': source_identity(ROOT), 'runner_sha256': sha256(__file__),
        'bound_sources': bound_sources(),
        'grounding_source_sha256': sha256(ROOT / 'src/campusai/rag/grounding.py'),
        'rubric_sha256': sha256(REVISION / 'rubric.partial.json'),
        'revision_manifest_sha256': sha256(REVISION / 'manifest.json'),
        'replay_report_sha256': sha256(REPLAY / 'nested_dev_report.json'), 'replay_decisions_sha256': sha256(raw_path),
        'billing_status': 'tier_and_actual_charge_unknown',
        'output_token_ceiling': 32768, 'pricing_reference': 'p7-06-gemini-pricing-reference-20261007.json',
        'paid_list_price_equivalent_output_ceiling_usd': 0.098304,
        'limits': ['Four positive course-name/credit questions only: no negative or multi-hop quality denominator.',
                   'Replay evidence, not serving, latency or complete P7-06 acceptance.']}
    write_json(path, packet)
    print(json.dumps({'packet': path.relative_to(ROOT).as_posix(), 'sha256': sha256(path),
                      'prompt_chars': packet['prompt_chars'], 'maximum_calls': 8}))


def collect(packet_path, authorization, config_path, output):
    if output.exists():
        raise FileExistsError(output)
    packet, consent = read_json(packet_path), read_json(authorization)
    if (consent.get('packet_sha256') != sha256(packet_path) or consent.get('max_provider_calls') != 8
            or consent.get('max_retries') != 0 or consent.get('explicit_user_authorization') is not True
            or consent.get('endpoint_host') != packet['endpoint_host']):
        raise ValueError('requires explicit consent for this exact eight-prompt packet')
    if (packet['bound_sources'] != bound_sources() or packet['runner_sha256'] != sha256(__file__)
            or packet['grounding_source_sha256'] != sha256(ROOT / 'src/campusai/rag/grounding.py')
            or len(packet['pairs']) != 8 or packet['max_provider_calls'] != 8):
        raise ValueError('prepared source or call ceiling changed')
    import yaml
    from campusai.llm.client import GeminiClient
    config = yaml.safe_load(config_path.read_text(encoding='utf8'))
    key = os.environ.get('GEMINI_API_KEY') or config.get('api_key')
    if not key:
        raise ValueError('credential missing')
    client = GeminiClient(key, model=packet['model'], cache=None, max_retries=0, timeout=60)
    calls = []
    client.generate = recording_generate(client.generate, calls)
    original = client.generate_json
    client.generate_json = lambda prompt, **options: original(prompt, generationConfig=packet['generation_config'], **options)
    generator = GroundedAnswerGenerator(client, max_context_chars=12000, max_context_tokens=2500)
    before = source_identity(ROOT)
    record = {'schema_version': 1, 'status': 'IN_PROGRESS', 'release_eligible': False,
        'packet_path': packet_path.relative_to(ROOT).as_posix(), 'packet_sha256': sha256(packet_path),
        'authorization_sha256': sha256(authorization), 'live_provider': True, 'answer_cache_enabled': False,
        'llm_cache_enabled': False, 'attempted_calls': 0, 'observations': [], 'cost': None, 'cost_status': 'unknown',
        'source_identity_before': before, 'prepared_source_identity': packet['source_identity']}
    # Exclusive journal creation consumes this receipt before any transmission.
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf8') as stream:
        json.dump(record, stream, ensure_ascii=False, allow_nan=False)
    previous_start = None
    try:
        for pair in packet['pairs']:
            evidence = results(pair['evidence'])
            if generator.prompt(pair['question'], evidence) != pair['prompt']:
                raise ValueError('prepared prompt changed')
            if previous_start is not None:
                remaining = packet['minimum_call_start_interval_seconds'] - (time.monotonic() - previous_start)
                if remaining > 0:
                    time.sleep(remaining)
            previous_start = time.monotonic()
            calls.clear()
            answer = generator.answer(pair['question'], evidence)
            public = answer.to_public_dict()
            record['attempted_calls'] += len(calls)
            record['observations'].append({'qid': pair['qid'], 'arm': pair['arm'], 'answer': public,
                'grounding_diagnostics': answer.to_dict(), 'llm_calls': list(calls),
                'observed_at': datetime.now(timezone.utc).isoformat(),
                'review': {'status': 'pending', 'answer_sha256': answer_digest(public)}})
            record['status'] = 'PENDING_SEMANTIC_REVIEW'
            write_json(output, record)
            print(json.dumps({'completed_arms': len(record['observations']), 'provider_calls': record['attempted_calls'],
                              'abstained': answer.abstained, 'reason': answer.reason}), flush=True)
            if len(calls) != 1 or any(c['provider_status'] != 'completed' or c['cached'] for c in calls):
                record['status'] = 'PROVIDER_OR_GROUNDING_PRECHECK_PARTIAL'
                write_json(output, record)
                return 1
    finally:
        client.close()
        record['source_identity_after'] = source_identity(ROOT)
        record['source_stable'] = record['source_identity_after'] == before
        write_json(output, record)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'collect'))
    parser.add_argument('--packet', type=Path, required=True)
    parser.add_argument('--authorization', type=Path)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare(args.packet.resolve())
        return 0
    if not all((args.authorization, args.config, args.output)):
        parser.error('collect requires authorization/config/output')
    return collect(args.packet.resolve(), args.authorization, args.config, args.output)


if __name__ == '__main__':
    raise SystemExit(main())
