"""Lock and collect a dev grounding pilot with hard/multihop/negative controls.

Retrieval arms are measured baseline and nested OOF BGE evidence, not serving
acceptance. Negative prechecks do not send an unnecessary provider request.
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
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
from scripts.benchmarks.phase7_dev_answer_pilot import results

ROOT = Path(__file__).resolve().parents[2]
REVISION = ROOT / 'data/benchmark/phase7_dev_gold_revision_20261007/packet'
REPLAY = ROOT / '.release/reranker/studies/phase7-primary-course-tables-window-nested-20261007-v1'
RUBRIC = ROOT / 'evaluation/results/phase7-completion-20261004/p7-06-dev-source-rubric-20261007-v2.json'
QIDS = tuple(f'human-candidate-{n:04d}' for n in (156, 159, 165, 178, 63, 64, 1, 45))


def bound_sources():
    paths = [Path(__file__), ROOT / 'scripts/benchmarks/phase7_dev_answer_pilot.py',
             ROOT / 'evaluation/reranker/collect_paired_answers.py']
    for name in ('rag', 'llm'):
        paths.extend((ROOT / 'src/campusai' / name).glob('*.py'))
    return {p.relative_to(ROOT).as_posix(): sha256(p) for p in sorted(paths)}


class Preflight:
    """Inspect routing without inventing a provider completion or quality result."""
    def __init__(self):
        self.prompts = []

    def generate_json(self, prompt, **options):
        self.prompts.append(prompt)
        from campusai.llm.client import LLMResponseError
        raise LLMResponseError('offline preflight; no provider response')


def validate_packet(packet):
    pairs = packet['pairs']
    keys = {(p['qid'], p['arm']) for p in pairs}
    expected = {(qid, arm) for qid in QIDS for arm in ('current_enhanced_baseline', 'official_bge_nested_oof_replay')}
    if (len(pairs) != 16 or keys != expected or len(keys) != len(pairs)
            or packet.get('max_provider_calls') != 12 or packet.get('max_retries') != 0
            or packet.get('endpoint_host') != 'generativelanguage.googleapis.com'
            or packet.get('minimum_call_start_interval_seconds') != 30
            or packet.get('release_eligible') is not False or packet.get('test_or_holdout_read') is not False):
        raise ValueError('pilot scope or call protocol changed')
    if sum(p['planned_provider_call'] for p in pairs) != 12:
        raise ValueError('planned call count changed')
    for p in pairs:
        if type(p['answerable']) is not bool or type(p['planned_provider_call']) is not bool:
            raise ValueError('explicit answer/call labels required')
        if p['planned_provider_call']:
            if not p['answerable'] or not p['gold_claims'] or not p['evidence'] or hashlib.sha256(p['prompt'].encode()).hexdigest() != p['prompt_sha256']:
                raise ValueError('positive prompt/gold binding changed')
        elif p['answerable'] or p['evidence'] or p['prompt'] is not None or p['gold_claims']:
            raise ValueError('negative control must be an actual empty-evidence precheck')
    for qid in QIDS:
        arms = [p for p in pairs if p['qid']==qid]
        for field in ('question','answerable','tags','difficulty','gold_evidence','gold_claims'):
            if arms[0][field] != arms[1][field]:
                raise ValueError('paired inputs differ')


def prepare(output):
    if output.exists():
        raise FileExistsError(output)
    manifest = read_json(REVISION / 'manifest.json')
    for name, digest in manifest['outputs'].items():
        if sha256(REVISION / name) != digest:
            raise ValueError('dev revision changed')
    rows = {r['qid']: r for r in rows_at(REVISION / 'human_retrieval_dev.jsonl')}
    rubric = read_json(RUBRIC)
    report = read_json(REPLAY / 'nested_dev_report.json')
    decisions = REPLAY / 'nested_oof_decisions.json.gz'
    if (report['dev_sha256'] != sha256(REVISION / 'human_retrieval_dev.jsonl')
            or report['decisions_sha256'] != sha256(decisions) or report['test_used'] or report['holdout_used']
            or report['release_eligible'] or rubric['test_or_holdout_read']):
        raise ValueError('requires source-reviewed dev and bound replay')
    with gzip.open(resolve_artifact(decisions), 'rt', encoding='utf8') as stream:
        observations = {o['qid']: o for o in json.load(stream)}
    pairs, rng = [], random.Random(7)
    for qid in QIDS:
        row, obs = rows[qid], observations[qid]
        if row['split'] != 'dev' or row['release_eligible']:
            raise ValueError('dev-only pilot required')
        arms = {'current_enhanced_baseline': obs['baseline'], 'official_bge_nested_oof_replay': obs['results']}
        order = list(arms)
        rng.shuffle(order)
        for arm in order:
            selected = results(arms[arm])
            preflight = Preflight()
            generator = GroundedAnswerGenerator(preflight, max_context_chars=12000, max_context_tokens=2500)
            offline = generator.answer(row['question'], selected)
            planned = bool(preflight.prompts)
            if len(preflight.prompts) > 1 or planned != row['answerable']:
                raise ValueError('pilot precheck blocks a positive or calls provider for an empty negative')
            prompt = preflight.prompts[0] if planned else None
            pairs.append({'qid':qid, 'arm':arm, 'question':row['question'], 'answerable':row['answerable'],
                'tags':row['tags'], 'difficulty':row['difficulty'], 'evidence':arms[arm],
                'gold_evidence':row['gold_evidence'], 'gold_claims':rubric['claims'][qid],
                'planned_provider_call':planned, 'prompt':prompt,
                'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest() if planned else None,
                'negative_precheck_reason':offline.reason if not planned else None,
                'preflight_status':'NO_PROVIDER_OR_QUALITY_MEASUREMENT'})
    packet = {'schema_version':1, 'status':'PREPARED_AWAITING_EXACT_PACKET_EGRESS_AUTHORIZATION',
        'endpoint_host':'generativelanguage.googleapis.com', 'model':'gemini-3-flash-preview',
        'max_provider_calls':12, 'max_retries':0, 'minimum_call_start_interval_seconds':30,
        'generation_config':{'temperature':0, 'maxOutputTokens':4096, 'thinkingConfig':{'thinkingLevel':'low'}},
        'context_budget':{'max_chars':12000,'max_tokens':2500}, 'prompt_chars':sum(len(p['prompt'] or '') for p in pairs),
        'benchmark_queries':8, 'positive_queries':6, 'negative_queries':2, 'multihop_queries':2,
        'pairs':pairs, 'bound_sources':bound_sources(), 'prepared_source_identity':source_identity(ROOT),
        'rubric_path':RUBRIC.relative_to(ROOT).as_posix(),'rubric_sha256':sha256(RUBRIC),
        'revision_manifest_sha256':sha256(REVISION/'manifest.json'),
        'replay_report_sha256':sha256(REPLAY/'nested_dev_report.json'),'replay_decisions_sha256':sha256(decisions),
        'release_eligible':False,'test_or_holdout_read':False,'current_serving_measurement':False,
        'output_token_ceiling':49152,'actual_charge_status':'unknown',
        'pricing_reference':'p7-06-gemini-pricing-reference-20261007.json',
        'limitations':['Dev diagnostic using measured retrieval/replay evidence; not frozen serving or heldout acceptance.',
            'Negative controls use actual empty retrieval; this pilot does not establish rejection of misleading nonempty negative contexts.',
            'Owner-delegated AI source review does not claim independent human review.']}
    validate_packet(packet)
    write_json(output,packet)
    print(json.dumps({'path':output.relative_to(ROOT).as_posix(),'sha256':sha256(output),'prompt_chars':packet['prompt_chars'],'maximum_calls':12}))


def validate_authorization(packet_path, packet, consent):
    validate_packet(packet)
    if (consent.get('packet_sha256') != sha256(packet_path) or consent.get('max_provider_calls') != 12
            or consent.get('max_retries') != 0 or consent.get('explicit_user_authorization') is not True
            or consent.get('endpoint_host') != packet['endpoint_host']):
        raise ValueError('explicit authorization for this exact twelve-prompt packet required')


def collect(packet_path, authorization, config_path, output):
    if output.exists():
        raise FileExistsError('receipt already consumed; retain output and never restart')
    packet = read_json(packet_path)
    validate_authorization(packet_path,packet,read_json(authorization))
    if packet['bound_sources'] != bound_sources():
        raise ValueError('prepared source changed')
    for path, field in [(RUBRIC,'rubric_sha256'),(REVISION/'manifest.json','revision_manifest_sha256'),
                        (REPLAY/'nested_dev_report.json','replay_report_sha256'),
                        (REPLAY/'nested_oof_decisions.json.gz','replay_decisions_sha256')]:
        if sha256(path) != packet[field]:
            raise ValueError('prepared dev/rubric/replay binding changed')
    import yaml
    from campusai.llm.client import GeminiClient
    config = yaml.safe_load(config_path.read_text(encoding='utf8'))
    key = os.environ.get('GEMINI_API_KEY') or config.get('api_key')
    if not key:
        raise ValueError('credential missing')
    client = GeminiClient(key,model=packet['model'],cache=None,max_retries=0,timeout=60)
    calls = []
    client.generate = recording_generate(client.generate,calls)
    original = client.generate_json
    client.generate_json = lambda prompt, **options: original(prompt,generationConfig=packet['generation_config'],**options)
    generator = GroundedAnswerGenerator(client,max_context_chars=12000,max_context_tokens=2500)
    before = source_identity(ROOT)
    record = {'schema_version':1,'status':'IN_PROGRESS','packet_path':packet_path.relative_to(ROOT).as_posix(),
        'packet_sha256':sha256(packet_path),'authorization_sha256':sha256(authorization),'release_eligible':False,
        'live_provider':True,'answer_cache_enabled':False,'llm_cache_enabled':False,
        'source_identity_before':before,'attempted_calls':0,'observations':[]}
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf8') as stream:
        json.dump(record,stream,ensure_ascii=False,allow_nan=False)
    previous_start = None
    try:
        for pair in packet['pairs']:
            selected = results(pair['evidence'])
            if pair['planned_provider_call']:
                if generator.prompt(pair['question'],selected) != pair['prompt']:
                    raise ValueError('authorized prompt changed')
                if previous_start is not None:
                    remaining = 30 - (time.monotonic()-previous_start)
                    if remaining > 0:
                        time.sleep(remaining)
                previous_start = time.monotonic()
            calls.clear()
            answer = generator.answer(pair['question'],selected)
            record['attempted_calls'] += len(calls)
            public = answer.to_public_dict()
            record['observations'].append({'qid':pair['qid'],'arm':pair['arm'],'answer':public,
                'grounding_diagnostics':answer.to_dict(),'llm_calls':list(calls),
                'observed_at':datetime.now(timezone.utc).isoformat(),
                'review':{'status':'pending','answer_sha256':answer_digest(public)}})
            record['status'] = 'PENDING_SEMANTIC_REVIEW'
            write_json(output,record)
            print(json.dumps({'observed_arms':len(record['observations']),'provider_calls':record['attempted_calls'],
                'abstained':answer.abstained,'reason':answer.reason}),flush=True)
            if (len(calls) != int(pair['planned_provider_call']) or record['attempted_calls'] > 12
                    or any(c['provider_status'] != 'completed' or c['cached'] for c in calls)):
                record['status'] = 'PARTIAL_PROVIDER_OR_PRECHECK_FAILURE'
                return 1
    finally:
        record['source_identity_after'] = source_identity(ROOT)
        record['source_stable'] = before == record['source_identity_after']
        write_json(output,record)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','collect'))
    for name in ('packet','authorization','config','output'):
        parser.add_argument('--'+name,type=Path,required=name=='packet')
    args = parser.parse_args()
    if args.action=='prepare':
        prepare(args.packet.resolve())
        return 0
    if not all((args.authorization,args.config,args.output)):
        parser.error('collect requires authorization/config/output')
    return collect(args.packet.resolve(),args.authorization,args.config,args.output)


if __name__=='__main__':
    raise SystemExit(main())
