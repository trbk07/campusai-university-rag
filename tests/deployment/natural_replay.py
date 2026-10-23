"""Current app regression against captured public responses; no external network."""
import hashlib
import io
import json
import os
from pathlib import Path
import threading
import urllib.request
from urllib.request import Request

from campusai.deployment.local_server import make_local_server
from campusai.llm.factory import _read_config
from campusai.web import make_wsgi_app
from scripts.operations.local import configure_local
from scripts.operations.serve import build_application

ROOT = Path(__file__).resolve().parents[2]
PHASE = ROOT / 'docs/deployment/phase13/evidence/natural-conversation-20261016'
GLOSSARY = ('\nTranslation terminology only, not source evidence: "most recently added" '
    'means "được thêm sau cùng"; "least recently added" means "được thêm đầu tiên". '
    'Preserve chronological order; do not translate recency as quantity such as "ít nhất".')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    output = PHASE / 'replay.json'
    assert not output.exists(), 'Evidence immutable; do not overwrite'
    original = json.loads((PHASE/'live-source-protocol/report.json').read_text(encoding='utf-8'))
    final = json.loads((PHASE/'live-translation-guard/report.json').read_text(encoding='utf-8'))
    assert final['status'] == 'PASS' and len(final['calls']) == 1
    generated = {row['id']: row for row in original['results'] if row['kind'] == 'generated'}
    assert len(generated) == 8 and all(row['passed'] for row in generated.values())
    profile = _read_config(ROOT/'configs/free_llm.yaml')
    # Separate diagnostic state; do not reset or spend the owner's counters.
    work = ROOT / '.tmp/natural-conversation-replay'
    work.mkdir(parents=True, exist_ok=True)
    profile['llm']['quota']['state_path'] = str(work/'quota.sqlite3')
    profile['llm']['quota']['scope'] = 'offline-public-replay'
    profile['llm']['requests_per_minute'] = 0
    profile['llm']['overload_circuit_path'] = str(work/'health.sqlite3')
    replay_config = PHASE/'replay-profile.json'
    replay_config.write_text(json.dumps(profile, indent=2)+'\n', encoding='utf-8')
    os.environ.update(HF_HUB_OFFLINE='1', GEMINI_API_KEY='offline-replay-placeholder',
        CAMPUSAI_LLM_CONFIG=str(replay_config), CAMPUSAI_RAG_CACHE_PATH=str(work/'answers.sqlite3'),
        CAMPUSAI_JOB_DB=str(work/'jobs.sqlite3'))
    configure_local()
    app = build_application()
    original_urlopen = urllib.request.urlopen
    current_id = None
    calls, rows = [], []
    def transport(request, **kwargs):
        if request.full_url == app.query_service.answer_generator.llm.endpoint:
            assert len(calls) < 8 and current_id in generated
            number = int(current_id.rsplit('-', 1)[1])
            base = PHASE/'live-source-protocol'
            target = base/f'provider-request-{number:02d}.json'
            response = base/f'provider-response-{number:02d}.json'
            current = json.loads(request.data)
            expected = json.loads(target.read_bytes())
            exact = current == expected
            if number == 3:
                target = PHASE/'live-translation-guard/provider-request-01.json'
                response = PHASE/'live-translation-guard/provider-response-01.json'
                expected = json.loads(target.read_bytes())
                exact = current == expected
                assert exact
            elif not exact:
                text = current['contents'][0]['parts'][0]['text']
                assert text.count(GLOSSARY) == 1
                current['contents'][0]['parts'][0]['text'] = text.replace(GLOSSARY, '', 1)
                assert current == expected, current_id
            if exact:
                assert hashlib.sha256(request.data).hexdigest() == sha(target)
            calls.append({'case': current_id, 'native_request': target.relative_to(ROOT).as_posix(),
                'native_request_sha256': sha(target), 'native_response': response.relative_to(ROOT).as_posix(),
                'native_response_sha256': sha(response), 'exact_request': exact,
                'only_difference': None if exact else 'explicit Vietnamese chronological-terminology glossary'})
            return io.BytesIO(response.read_bytes())
        if request.full_url.startswith('http://127.0.0.1:'):
            return original_urlopen(request, **kwargs)
        raise AssertionError('External network forbidden during replay')
    urllib.request.urlopen = transport
    try:
        with make_local_server('127.0.0.1', 0, make_wsgi_app(app)) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                for case in original['manifest']['cases']:
                    current_id = case['id']
                    if case['kind'] in {'generated', 'cached'}:
                        payload = generated[case.get('repeat_of', case['id'])]['request']
                    else:
                        payload = {'question': case['question'], 'language': case['language'],
                                   'doc_ids': original['manifest']['doc_ids'], 'history': []}
                    before = len(calls)
                    request = Request(f'http://127.0.0.1:{server.server_port}/api/query',
                        data=json.dumps(payload, ensure_ascii=False).encode(), headers={'Content-Type':'application/json'})
                    with transport(request, timeout=30) as response:
                        value = json.load(response)
                        assert response.status == 200 and value.get('ok')
                    answer = value['answer']
                    if case['kind'] == 'negative':
                        assert answer['abstained'] and len(calls) == before
                    else:
                        assert not answer['abstained'] and answer['citations']
                        assert len(calls) - before == (1 if case['kind'] == 'generated' else 0)
                        if case['kind'] == 'cached':
                            assert value['cache_hit']
                    rows.append({'id': case['id'], 'kind': case['kind'], 'passed': True,
                                 'response': value, 'replayed_provider_responses': len(calls)-before})
            finally:
                server.shutdown()
                thread.join(2)
    finally:
        urllib.request.urlopen = original_urlopen
        app.close()
    report = {'status': 'PASS', 'scope': 'Current full app with captured public model outputs; NOT a new live generation, latency or quota result',
        'external_provider_calls': 0, 'replayed_responses': len(calls), 'input_compatibility': calls,
        'results': rows, 'current_profile_sha256': sha(ROOT/'configs/free_llm.yaml'),
        'sources_sha256': {p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'src/campusai').rglob('*.py')}}
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('PASS: 24 current-app replay turns, eight captured responses, zero external provider calls')


if __name__ == '__main__':
    main()
