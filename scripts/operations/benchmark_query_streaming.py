"""Measure sealed, uncached app queries; never inject evaluation gold into RAG.

Requires an existing prepared packet/index and explicit --live. Each provider
POST is journalled before transport. No retries, key rotation or quota resets.
"""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import threading
import time
import urllib.error
import urllib.request

from campusai.deployment.local_server import make_local_server
from campusai.web import make_wsgi_app
from scripts.operations.serve import build_application
from scripts.operations.with_gemini_key import read_key


ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def runtime_digest():
    h = sha256()
    for path in sorted((ROOT/'src/campusai').rglob('*.py')):
        h.update(path.relative_to(ROOT).as_posix().encode() + b'\0' + path.read_bytes() + b'\0')
    return h.hexdigest()


def append(path, value):
    with path.open('a', encoding='utf8') as output:
        output.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + '\n')
        output.flush()
        os.fsync(output.fileno())


def percentile(values, fraction=.95):
    if not values or any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in values):
        raise ValueError('missing/non-finite latency observations')
    return sorted(values)[math.ceil(len(values)*fraction)-1]


def censored_percentile(values, fraction=.95):
    """No first token/reply is +infinity, never a dropped/fast error sample."""
    if not values or any(v is not None and (type(v) not in (int,float)
            or not math.isfinite(v) or v<0) for v in values):
        raise ValueError('invalid censored latency observations')
    value=sorted(math.inf if v is None else v for v in values)[math.ceil(len(values)*fraction)-1]
    return value if math.isfinite(value) else None


def summarize(observations, traces, attempts, expected_ids, runtime_unchanged):
    ids=[r['case_id'] for r in observations]
    trace_map={t['case_id']:t['trace'] for t in traces}
    posted=[a['case_id'] for a in attempts]
    complete=(len(expected_ids)==len(set(expected_ids))==20 and ids==expected_ids
        and len(trace_map)==len(traces)==20 and len(posted)==len(set(posted))
        and set(posted)<=set(ids) and runtime_unchanged)
    provider,client,verified=[],[],[]
    for row in observations:
        trace=trace_map.get(row['case_id'],{})
        calls=trace.get('model_stream',{}).get('calls',[])
        genuine=len(calls)==1 and row['case_id'] in posted
        if trace.get('cache_hit') is not False or len(calls)>1:complete=False
        first=calls[0].get('first_text_delta_ms') if genuine else None
        if row['client_first_model_progress_ms'] is not None and first is None:complete=False
        provider.append(first)
        client.append(row['client_first_model_progress_ms'] if first is not None else None)
        correct=row.get('verified_source_fact',False)
        verified.append(row['verified_answer_ms'] if correct and genuine else None)
        if correct and (not genuine or calls[0]['status']!='complete'):complete=False
    metrics={'sample_count':len(observations),'verified_source_facts':sum(r.get('verified_source_fact',False) for r in observations),
        'uncertified_published_answers':sum(r.get('response',{}).get('ok') is True
            and r.get('response',{}).get('answer',{}).get('abstained') is False
            and not r.get('verified_source_fact',False) for r in observations),
        'provider_first_text_censored':sum(v is None for v in provider),
        'verified_answer_censored':sum(v is None for v in verified)}
    for name,values in [('provider_first_text',provider),('client_first_model_progress',client),('verified_answer',verified)]:
        metrics[name+'_p95_ms']=censored_percentile(values) if complete else None
        metrics[name+'_max_ms']=None if not complete or any(v is None for v in values) else max(values)
        metrics[name+'_max_censored']=any(v is None for v in values)
    passed=(complete and metrics['verified_source_facts']>=18 and metrics['uncertified_published_answers']==0
        and all(metrics[name+'_p95_ms'] is not None and metrics[name+'_p95_ms']<=5000
                for name in ['provider_first_text','client_first_model_progress','verified_answer']))
    return metrics,passed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--run-dir', type=Path, help='Fresh execution directory; reuse the immutable source/index')
    parser.add_argument('--packet-sha256', required=True)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    if not args.live: parser.error('explicit --live is required')
    root = args.root.resolve()
    if not root.is_relative_to((ROOT/'.tmp').resolve()): parser.error('isolated workspace .tmp root required')
    run_dir = args.run_dir.resolve() if args.run_dir else root
    if not run_dir.is_relative_to(root): parser.error('execution directory must stay inside fixture root')
    packet_path = run_dir/'egress.json'
    assert digest(packet_path) == args.packet_sha256
    packet = json.loads(packet_path.read_text(encoding='utf8'))
    assert packet['runtime_sha256'] == runtime_digest()
    assert packet['profile_sha256'] == digest(ROOT/packet['profile_path'])
    assert packet['index_manifest_sha256'] == digest(root/'index/manifest.json')
    assert packet['cases_sha256'] == digest(root/'cases.json')
    assert packet['source_pdf_sha256'] == digest(root/'fictional-reading-rooms.pdf')
    assert packet['max_posts'] == len(packet['rows']) and packet['max_retries'] == 0
    observations, attempts, traces = [], [], []
    if packet.get('prefix'):
        prefix=packet['prefix'];directory=(ROOT/prefix['directory']).resolve()
        assert directory.is_relative_to(root) and directory!=run_dir
        for name,expected in prefix['sha256'].items():assert digest(directory/name)==expected
        prior=json.loads((directory/'egress.json').read_text(encoding='utf8'))
        for key in ['runtime_sha256','profile_sha256','index_manifest_sha256','key_name','model']:
            assert prior[key]==packet[key]
        def load(name):return [json.loads(line) for line in (directory/name).read_text(encoding='utf8').splitlines()]
        observations=load('public-predictions.jsonl');attempts=load('provider-attempts.jsonl');traces=load('query-traces.jsonl')
        assert [r['case_id'] for r in observations]==prefix['case_ids']
        assert [r['case_id'] for r in prior['rows'][:len(observations)]]==prefix['case_ids']
        assert all(r['body_sha256']==p['body_sha256'] for r,p in zip(packet['rows'],prior['rows'][len(observations):]))
    expected_ids=[r['case_id'] for r in observations]+[r['case_id'] for r in packet['rows']]
    assert len(expected_ids)==len(set(expected_ids))==20
    prefix_posts=len(attempts)
    runner_sha=digest(__file__)
    assert not (run_dir/'measurement-started.json').exists()
    (run_dir/'measurement-started.json').write_text(json.dumps({
        'packet_sha256': args.packet_sha256, 'started_at': datetime.now(timezone.utc).isoformat(),
        'runtime_sha256': runtime_digest(), 'runner_sha256':runner_sha,
        'prefix':packet.get('prefix'),'retry_failed_or_successful_case': False})+'\n', encoding='utf8')
    settings = {'CAMPUSAI_LLM_CONFIG': str(ROOT/packet['profile_path']),
        'GEMINI_API_KEY': read_key(ROOT/'configs/key.yaml', packet['key_name']),
        'CAMPUSAI_INDEX_DIR': str(root/'index'), 'CAMPUSAI_STORE_DIR': str(root/'store'),
        'CAMPUSAI_RAG_CACHE_PATH': str(run_dir/'measured-answers.sqlite3'),
        'CAMPUSAI_JOB_DB': str(run_dir/'operations/measured-jobs.sqlite3'),
        'CAMPUSAI_DEVICE': 'cuda', 'HF_HUB_OFFLINE': '1'}
    os.environ.update(settings)
    for name in ('CAMPUSAI_ANSWER_CALIBRATION', 'CAMPUSAI_ANSWER_CALIBRATION_SHA256',
                 'CAMPUSAI_RETRIEVAL_CALIBRATION'):
        os.environ.pop(name, None)  # Frozen calibrations do not bind this new fixture corpus.
    startup = time.perf_counter()
    application = build_application()
    startup = time.perf_counter() - startup
    client = application.query_service.answer_generator.llm
    assert client.model == packet['model'] and client.max_retries == 0
    assert packet['destination'] == f'https://generativelanguage.googleapis.com/v1beta/models/{client.model}:streamGenerateContent?alt=sse'
    before = client.quota_governor.snapshot()
    active = {}
    original_open = urllib.request.urlopen
    original_complete = client.complete

    def sealed(request, **kwargs):
        if request.full_url.startswith('https://generativelanguage.googleapis.com/'):
            row = active['row']
            if (len(attempts)-prefix_posts >= packet['max_posts'] or request.full_url != packet['destination']
                    or sha256(request.data).hexdigest() != row['body_sha256']
                    or any(a['case_id'] == row['case_id'] for a in attempts)):
                from campusai.llm.client import LLMProviderError
                active['sealed_violation']=True
                raise LLMProviderError('unsealed or repeated inference stopped before transport')
            attempt = {'case_id': row['case_id'], 'endpoint': request.full_url,
                'body_sha256': row['body_sha256'], 'at': datetime.now(timezone.utc).isoformat()}
            append(run_dir/'provider-attempts.jsonl', attempt)
            attempts.append(attempt)
        return original_open(request, **kwargs)

    def record_complete(prompt, **options):
        response = original_complete(prompt, **options)
        append(run_dir/'raw-model-predictions.jsonl', {'case_id': active['row']['case_id'], **asdict(response)})
        return response

    def telemetry(trace):
        retrieved = [asdict(r) for r in application.query_service.last_retrieval]
        record = {'case_id': active['row']['case_id'], 'trace': trace, 'retrieved_evidence': retrieved}
        append(run_dir/'query-traces.jsonl', record)
        traces.append(record)

    urllib.request.urlopen = sealed
    client.complete = record_complete
    state = 'INCOMPLETE'
    failure = None
    server = make_local_server('127.0.0.1', 0,
        make_wsgi_app(application, telemetry_hook=telemetry, max_concurrent_queries=1,
            enable_query_streaming=True))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    next_request = time.perf_counter()
    try:
        for row in packet['rows']:
            time.sleep(max(0, next_request-time.perf_counter()))
            active['row'] = row
            body = {k: row[k] for k in ('question', 'doc_ids', 'language')}
            request = urllib.request.Request(f'http://127.0.0.1:{server.server_port}/api/query',
                data=json.dumps(body).encode(), headers={'Content-Type':'application/json',
                    'Accept':'application/x-ndjson'})
            started = time.perf_counter()
            next_request = started + packet['request_interval_seconds']
            first = None
            try: response = original_open(request, timeout=45)
            except urllib.error.HTTPError as error: response = error
            with response:
                if response.headers.get('Content-Type','').startswith('application/x-ndjson'):
                    terminal = None
                    for line in response:
                        value = json.loads(line)
                        if value['type']=='progress' and value['phase']=='generating' and first is None:
                            first = (time.perf_counter()-started)*1000
                        if value['type']=='result': terminal = value
                    if terminal is None: raise ValueError('missing final response')
                    status, value = terminal['status'], terminal['value']
                else:
                    status, value = response.status, json.load(response)
            result = {'case_id':row['case_id'], 'http_status':status, 'response':value,
                'client_first_model_progress_ms':first, 'verified_answer_ms':(time.perf_counter()-started)*1000}
            observations.append(result)
            append(run_dir/'public-predictions.jsonl', result)
            print(json.dumps({'complete':len(observations),'total':20,'first_model_progress_ms':first,
                'verified_answer_ms':result['verified_answer_ms'],'http_status':status}),flush=True)
            code=value.get('error_code') or value.get('provider_status',{}).get('error_code')
            failed=status!=200 or not value.get('ok') or first is None
            if active.get('sealed_violation'):break
            if failed and not (packet.get('continue_operational_errors') and
                    code in {'provider_timeout','provider_unavailable'}):break
        if len(observations)==20: state='MEASURED'
    except Exception as error:
        failure = type(error).__name__  # No private provider/error strings.
    finally:
        server.shutdown(); thread.join(5); server.server_close()
        after = client.quota_governor.snapshot()
        application.close()
        urllib.request.urlopen = original_open
    # Evaluation annotations are opened only AFTER every inference/HTTP attempt.
    gold = {r['case_id']:r for r in json.loads((root/'cases.json').read_text(encoding='utf8'))}
    for result in observations:
        expected = gold[result['case_id']]
        answer = result['response'].get('answer', {})
        literal = expected['expected_literal']
        result['verified_source_fact'] = (not answer.get('abstained',True)
            and expected['expected_time'] in answer.get('answer','')
            and any(literal in c.get('quote','') and c.get('doc_id')==packet['source_pdf_sha256']
                    and c.get('page')==1 for c in answer.get('citations',[])))
    unchanged=(runtime_digest()==packet['runtime_sha256'] and digest(__file__)==runner_sha
               and not active.get('sealed_violation'))
    metrics,passed=summarize(observations,traces,attempts,expected_ids,unchanged)
    report = {'status':'PASS' if passed else 'NOT_PASSED','measurement_state':state,'failure_type':failure,
        'scope':'20 real uncached loopback RAG queries, controlled fictional one-page source, real BGE-M3 CUDA. Not representative AI/PDF quality or cold-start/public-release evidence.',
        'packet_sha256':args.packet_sha256,'runtime_sha256':runtime_digest(),
        'runner_sha256':runner_sha,'runner_unchanged':digest(__file__)==runner_sha,
        'credential_project_alias':packet['key_name'],'prefix':packet.get('prefix'),
        'runtime_unchanged':runtime_digest()==packet['runtime_sha256'], 'metrics':metrics,
        'model_startup_seconds_excluded':startup,'cold_observation_not_discarded':
            'Separate earlier connectivity probe14.59s; all20 app cases included without trimming.',
        'attempt_count':len(attempts),'observations':observations,'quota_before':before,'quota_after':after,
        'provider_retries':0,'key_rotation':False,'gold_used_by_inference':False,
        'raw_unverified_text_sent_to_browser':False,'nearest_rank_percentile':True,
        'sealed_violation':bool(active.get('sealed_violation')),
        'failure_censoring':'Every query retained. Missing first token/verified answer is +infinity (JSON null for an unbounded quantile/max); n20 p95 uses rank19. Never count an error as a correct negative or local text as a model token.'}
    (run_dir/'qualification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'status':report['status'],'attempts':len(attempts),'metrics':metrics}),flush=True)
    return 0 if passed and report['runtime_unchanged'] else 1


if __name__=='__main__': raise SystemExit(main())
