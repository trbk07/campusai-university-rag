"""One Free-only quota ramp over locked public RAG prompts, no retries.

Production cache/concurrency are unchanged. Two diagnostic senders are needed
to measure RPM independently of one request's generation latency. At most one
request already in flight can finish after the first stop signal.
"""
import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import replace
import hashlib
import io
import json
import os
from pathlib import Path
import threading
import time
from urllib.error import HTTPError
import urllib.request

from scripts.operations.local import configure_local
from campusai.llm.factory import create_llm
from campusai.llm.quota import QuotaGovernor
from campusai.llm.quota_hints import google_quota_hints


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--raw-output', type=Path, required=True)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    assert args.live
    protocol = json.loads(args.protocol.read_text(encoding='utf-8'))
    assert protocol['stages'][:2] == [{'rpm':15,'count':15}, {'rpm':30,'count':30}]
    assert protocol['stages'][2]['rpm'] == 60 and 1 <= protocol['stages'][2]['count'] <= 15
    cap = protocol['provider_call_cap']
    assert sum(s['count'] for s in protocol['stages']) == cap <= 60
    assert cap + protocol.get('prior_phase_provider_attempts',0) <= protocol.get('phase_provider_attempt_cap',60)
    tier = json.loads(Path(protocol['tier_evidence']).read_text(encoding='utf-8'))
    assert tier['tier'] == 'free' and tier['existing_campusai_project'] is True
    proof = json.loads(Path(protocol['public_source_evidence']).read_text(encoding='utf-8'))
    assert proof['exact_public_source_match'] is True
    source = Path(protocol['qualified_run'])
    baseline = json.loads((source/'report.json').read_text(encoding='utf-8'))
    assert baseline['status'] == 'PASS' and baseline['manifest']['doc_ids'] == [proof['sha256']]
    bodies = []
    for i, row in enumerate(baseline['calls'], 1):
        path = source/f'provider-request-{i:02d}.json'
        assert sha(path) == row['body_sha256']
        body = json.loads(path.read_bytes())
        assert 'tools' not in body and body['generationConfig']['maxOutputTokens'] <= 1536
        bodies.append(body)
    assert len(bodies) == 10
    args.output.mkdir(parents=True, exist_ok=False)
    raw = args.raw_output.resolve()
    assert any(raw.is_relative_to(Path(p).resolve()) for p in ('.local_artifacts','.tmp'))
    raw.mkdir(parents=True, exist_ok=False)
    os.environ['CAMPUSAI_LLM_CONFIG'] = protocol['profile']
    configure_local()
    client = create_llm(os.environ['CAMPUSAI_LLM_CONFIG'])
    assert client.model == 'gemini-3.5-flash-lite'
    assert client.endpoint == 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent'
    client.cache.close()
    client.cache = None  # Diagnostic capacity, not production cache behavior.
    original = urllib.request.urlopen
    lock, stop = threading.RLock(), threading.Event()
    report = {'status':'RUNNING','protocol':protocol,'protocol_sha256':sha(args.protocol),
        'scope':'Direct native Gemini calls with frozen public CampusAI RAG prompts; repeated ten exposed prompts, no new question coverage or production concurrency claim',
        'auto_retry':False,'credential_rotation':False,'billing_changes':False,
        'calls':[],'results':[],'stages':[],'quota_before':client.quota_governor.snapshot(),
        'sources_sha256':{str(p):sha(p) for p in [Path(__file__),Path('src/campusai/llm/client.py'),
            Path('src/campusai/llm/quota.py'),Path('src/campusai/llm/quota_hints.py'),Path('src/campusai/llm/overload.py')]}}
    def save():
        # Call under lock: a complete pre-send journal always survives a crash.
        path = args.output/'report.json'
        temporary = path.with_suffix('.writing')
        temporary.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        os.replace(temporary,path)
    def transport(request, **kwargs):
        assert request.full_url == client.endpoint and request.get_method() == 'POST'
        with lock:
            if stop.is_set():
                raise RuntimeError('quota probe stopped before transport')
            assert len(report['calls']) < cap
            number = len(report['calls'])+1
            row = {'attempt':number,'started_at_utc':time.time(),
                   'request_sha256':hashlib.sha256(request.data).hexdigest()}
            report['calls'].append(row)
            save()
        try:
            with original(request, **kwargs) as response:
                data = response.read()
            payload = json.loads(data)
            path = raw/f'provider-response-{number:02d}.json'
            path.write_bytes(data)
            with lock:
                row.update(http_status=200,usage=payload.get('usageMetadata',{}),artifact=path.as_posix(),artifact_sha256=sha(path))
                save()
            return io.BytesIO(data)
        except HTTPError as error:
            data = error.read()
            path = raw/f'provider-error-{number:02d}.json'
            path.write_bytes(data)
            try: hints = google_quota_hints(json.loads(data))
            except (ValueError,UnicodeError): hints = {'retry_delay_seconds':None,'violations':[]}
            with lock:
                stop.set()
                report.setdefault('first_stop',{'attempt':number,'http_status':error.code,'at_utc':time.time()})
                row.update(http_status=error.code,quota_hints=hints,artifact=path.as_posix(),artifact_sha256=sha(path))
                save()
            raise HTTPError(error.url,error.code,error.msg,error.headers,io.BytesIO(data)) from error
        except Exception as error:
            with lock:
                stop.set()
                report.setdefault('first_stop',{'attempt':number,'error_type':type(error).__name__,'at_utc':time.time()})
                row['error_type'] = type(error).__name__
                save()
            raise
    urllib.request.urlopen = transport
    def run(index, rpm):
        body = bodies[index%len(bodies)]
        start = time.perf_counter()
        row = {'case':index+1,'source_prompt':index%10+1,'operator_rpm':rpm}
        try:
            value = client.complete(body['contents'][0]['parts'][0]['text'], generationConfig=body['generationConfig'])
            parsed = json.loads(value.text)
            row.update(status='NATIVE_RESPONSE',json_object=isinstance(parsed,dict),abstained=parsed.get('abstained'))
        except Exception as error:
            row.update(status='ERROR',error_type=type(error).__name__)
            stop.set()
        row['latency_ms'] = (time.perf_counter()-start)*1000
        with lock:
            report['results'].append(row)
            save()
        return row
    try:
        next_case = 0
        for stage in protocol['stages']:
            if stop.is_set(): break
            old = client.quota_governor
            client.quota_governor = QuotaGovernor(old.path,old.scope,
                replace(old.policy,requests_per_minute=stage['rpm'],max_in_flight=2),max_wait_seconds=6)
            with lock:
                report['stages'].append({'rpm':stage['rpm'],'planned':stage['count'],'started_at_utc':time.time()})
                save()
            submitted, pending = 0, set()
            next_submission = time.monotonic()
            with ThreadPoolExecutor(max_workers=2) as pool:
                while submitted < stage['count'] or pending:
                    now = time.monotonic()
                    if (not stop.is_set() and submitted < stage['count'] and len(pending)<2
                            and now >= next_submission):
                        pending.add(pool.submit(run,next_case,stage['rpm']))
                        next_case += 1; submitted += 1
                        next_submission = now + 60/stage['rpm']
                    if not pending:
                        if stop.is_set() or submitted >= stage['count']: break
                        stop.wait(min(0.1,max(0,next_submission-time.monotonic())))
                        continue
                    done,pending = wait(pending,timeout=0.1,return_when=FIRST_COMPLETED)
                    for future in done: future.result()
                    # Drain the at-most-one already running sender. Its
                    # pre-send stop gate prevents another provider POST.
            with lock:
                report['stages'][-1]['submitted'] = submitted
                save()
    finally:
        urllib.request.urlopen = original
        with lock:
            report['quota_after'] = client.quota_governor.snapshot()
            first = report.get('first_stop',{})
            report['status'] = ('STOPPED_QUOTA' if first.get('http_status')==429 else
                'STOPPED_PROVIDER_FAULT' if first else 'CAP_REACHED' if len(report['calls'])==cap else 'STOPPED_LOCAL')
            report['actual_provider_attempts'] = len(report['calls'])
            report['goal_complete'] = False
            save()
        client.close()
    print(json.dumps({'status':report['status'],'attempts':len(report['calls']),
        'first_stop':report.get('first_stop'),'observed_limits':report['quota_after'].get('observed_provider_limits',{})}),flush=True)


if __name__ == '__main__':
    main()
