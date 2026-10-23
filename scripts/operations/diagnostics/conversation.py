"""Bounded, source-bound HTTP conversation qualification (explicit live opt-in).

Use an existing user document. Never upload, rotate credentials, retry a failed
request, or overwrite a previous run. Provider failures stop the run immediately.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from scripts.operations.local import configure_local
from scripts.operations.serve import build_application
from campusai.deployment.local_server import make_local_server
from campusai.web import make_wsgi_app


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    if not args.live:
        parser.error('Live provider calls require --live')
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    cases = manifest['cases']
    if not 1 <= len(cases) <= 10:
        parser.error('A run must contain 1–10 predetermined cases')
    args.output.mkdir(parents=True, exist_ok=False)
    os.environ['CAMPUSAI_LLM_CONFIG'] = str(args.profile.resolve())
    configured = configure_local()
    app = build_application()
    client = app.query_service.answer_generator.llm
    original = client.generate
    provider_calls, results, traces = [], [], []
    report = {'model': configured['model'], 'profile_sha256': sha(args.profile),
        'manifest_sha256': sha(args.manifest), 'manifest': manifest,
        'source_sha256': {str(p): sha(p) for p in [
            Path(__file__), Path('src/campusai/rag/grounding.py'),
            Path('src/campusai/llm/client.py'), Path('scripts/operations/serve.py'),
            Path('src/campusai/web.py')]},
        'calls': provider_calls, 'results': results, 'traces': traces,
        'scope': 'One local full-application HTTP sequence, existing user PDF; not a cloud, quality, or availability SLO',
        'auto_retry': False, 'credential_rotation': False}

    def generate(prompt, **kwargs):
        row = {'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
               'prompt_chars': len(prompt)}
        provider_calls.append(row)
        try:
            response = original(prompt, **kwargs)
            row.update(usage=response.usage, latency_ms=response.latency_ms,
                       cached=response.cached, finish_reason=response.finish_reason,
                       model_version=response.model_version, final_text=response.text)
            return response
        except Exception as error:
            cause = error.__cause__
            row.update(error_type=type(error).__name__,
                       upstream_status=cause.code if isinstance(cause, HTTPError) else None)
            raise

    client.generate = generate
    history = []
    previous = 0
    try:
        with make_local_server('127.0.0.1', 0,
                make_wsgi_app(app, telemetry_hook=traces.append, max_concurrent_queries=1)) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                base = f'http://127.0.0.1:{server.server_port}'
                for case in cases:
                    # At most ten new provider requests per minute, also across
                    # cases that returned immediately without provider inference.
                    time.sleep(max(0, 6 - (time.monotonic() - previous)))
                    previous = time.monotonic()
                    question = case['question']
                    payload = {'question': question, 'doc_ids': manifest['doc_ids'],
                               'language': case['language'], 'history': history[-12:]}
                    request = Request(base+'/api/query',
                        data=json.dumps(payload, ensure_ascii=False).encode(),
                        headers={'Content-Type':'application/json'})
                    started = time.perf_counter()
                    call_start = len(provider_calls)
                    try:
                        response = urlopen(request, timeout=40)
                    except HTTPError as error:
                        response = error
                    with response:
                        value = json.load(response)
                        row = {'id': case['id'], 'question': question,
                            'http_status': response.code,
                            'request_id': response.headers.get('X-Request-ID'),
                            'latency_ms': (time.perf_counter()-started)*1000,
                            'provider_call_indices': list(range(call_start, len(provider_calls))),
                            'response': value}
                    results.append(row)
                    answer = value.get('answer', {})
                    print(json.dumps({'case':case['id'], 'status':row['http_status'],
                        'abstained':answer.get('abstained'),
                        'reason':answer.get('abstention_reason', value.get('error_code')),
                        'latency_ms':round(row['latency_ms'])}), flush=True)
                    if not value.get('ok'):
                        break
                    if not answer.get('abstained'):
                        history.extend([{'role':'user','content':question},
                                        {'role':'assistant','content':answer['answer']}])
            finally:
                server.shutdown()
                worker.join()
    finally:
        app.close()
        report['status'] = 'PASS' if len(results) == len(cases) and all(
            r['http_status'] == 200 and r['response'].get('ok') and
            not r['response'].get('answer', {}).get('abstained') for r in results) else 'NOT_PASSED'
        report['actual_provider_attempts'] = sum(not r.get('cached', False) for r in provider_calls)
        (args.output/'report.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'status':report['status'], 'cases':len(results),
                      'actual_provider_attempts':report['actual_provider_attempts']}), flush=True)
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
