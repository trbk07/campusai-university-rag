"""Capture/verify natural-conversation fixes without new provider inference."""
import argparse
from collections import Counter
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sqlite3
from urllib.request import Request, urlopen
import zipfile

from tests.deployment.capture_model_selection import test_counts

ROOT = Path(__file__).resolve().parents[2]
PHASE = ROOT/'docs/deployment/phase13/evidence/natural-conversation-20261016'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(name, value):
    (PHASE/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def runtime():
    def accounting():
        with sqlite3.connect('file:data/operations/flash-lite-quota.sqlite3?mode=ro', uri=True) as db:
            scope = 'gemini:owner:gemini-3.5-flash-lite'
            return (db.execute('SELECT count(*) FROM quota_attempts WHERE scope=?', (scope,)).fetchone()[0],
                    json.loads(db.execute('SELECT policy FROM quota_state WHERE scope=?', (scope,)).fetchone()[0]))
    before, policy = accounting()
    assert policy['requests_per_minute'] == 10 and policy['max_in_flight'] == 1
    rows = []
    def local(path, body=None):
        request = Request('http://127.0.0.1:8000'+path, data=None if body is None else json.dumps(body).encode(),
                          headers={'Content-Type':'application/json'})
        with urlopen(request, timeout=10) as response:
            assert response.status == 200
            return json.load(response)
    assert local('/health')['service'] == 'campusai'
    assert local('/ready')['status'] == 'ready'
    docs = local('/api/documents')['documents']
    doc_id = 'b9b9e88d93fdc12e1a0d4ec6ad30f86980fb2d95610ecdbfb2a284da224e64fb'
    selected = next(d for d in docs if d['doc_id'] == doc_id and d['ready'])
    with urlopen('http://127.0.0.1:8000/api/documents/'+doc_id+'/file', timeout=10) as response:
        data = response.read()
    assert hashlib.sha256(data).hexdigest() == doc_id
    import fitz
    with fitz.open(stream=data, filetype='pdf') as pdf:
        physical_pages = len(pdf)
    for question in ('tài liệu có mấy trang', 'tai lieu nay co bn trang', 'What is the page count?', 'alo', 'asdfghjkl'):
        body = {'question': question, 'doc_ids':[doc_id], 'language':'vi',
                'history':[{'role':'user','content':'Tổng hợp phần stack trong tài liệu'}]}
        value = local('/api/query', body)
        if 'document_info' in value:
            assert value['document_info']['documents'][0]['page_count'] == physical_pages == selected['page_count']
            assert not value['answer']['abstained']
        else:
            assert value['answer']['abstained']
        rows.append({'question': question, 'response': value})
    after, _ = accounting()
    assert before == after
    write('runtime-smoke.json', {'status':'PASS', 'physical_pdf_pages':physical_pages,
        'profile_sha256':sha(ROOT/'configs/free_llm.yaml'), 'provider_reservations_before':before,
        'provider_reservations_after':after, 'additional_provider_posts':0, 'policy':policy, 'results':rows})
    print('PASS: running corrected app, PDF page counts match physical PDF, no extra provider sends')


def package():
    from setuptools.build_meta import build_wheel
    destination = ROOT/'.local_artifacts/natural-conversation-20261016-package'
    destination.mkdir(parents=True, exist_ok=True)
    assert not list(destination.glob('*.whl'))
    with redirect_stdout(io.StringIO()):
        wheel = destination/build_wheel(str(destination))
    files = {p.relative_to(ROOT/'src').as_posix():sha(p) for p in (ROOT/'src/campusai').rglob('*')
             if p.is_file() and '__pycache__' not in p.parts and (p.suffix == '.py' or 'ui' in p.parts)}
    with zipfile.ZipFile(wheel) as archive:
        for name, digest in files.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest, name
        assert not any(n.endswith(('.pdf','.yaml','.sqlite3','.env','.db')) for n in archive.namelist())
    write('packaging.json', {'status':'PASS','wheel':wheel.relative_to(ROOT).as_posix(), 'wheel_sha256':sha(wheel),
                           'packaged_source_and_ui_sha256':files, 'private_material_included':False})
    print('PASS: current source/UI packaged without private data')


def audit():
    old = read(PHASE/'previous-source-archive.json')
    assert sha(ROOT/old['previous_receipt']) == old['previous_receipt_sha256']
    assert sha(ROOT/old['source_archive']) == old['source_archive_sha256']
    receipt = read(ROOT/old['previous_receipt'])
    with zipfile.ZipFile(ROOT/old['source_archive']) as archive:
        for name,digest in receipt['sources_sha256'].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest
    for name,digest in receipt['artifacts_sha256'].items():
        assert sha(ROOT/name) == digest, name
    runs = [('live-initial','initial-source',6), ('live-corrected','corrected-source',1),
            ('live-source-protocol','source-protocol-source',8), ('live-translation-guard',None,1)]
    for run,snapshot,count in runs:
        report = read(PHASE/run/'report.json')
        assert len(report['calls']) == report['actual_provider_attempts'] == count
        for name,digest in report['sources_sha256'].items():
            source = Path(name)
            relative = source.relative_to(ROOT) if source.is_absolute() else source
            path = PHASE/snapshot/relative if snapshot else ROOT/relative
            assert sha(path) == digest, (run,name)
        for number, call in enumerate(report['calls'],1):
            assert call['http_status'] == 200
            assert sha(PHASE/run/f'provider-request-{number:02d}.json') == call['request_sha256']
            assert sha(PHASE/run/f'provider-response-{number:02d}.json') == call['response_sha256']
    primary = read(PHASE/'live-source-protocol/report.json')
    assert primary['status'] == 'NOT_PASSED' and len(primary['results']) == 19
    assert all(r['passed'] for r in primary['results'][:16])
    final = read(PHASE/'live-translation-guard/report.json')
    assert final['status'] == 'PASS' and len(final['results']) == 3 and all(r['passed'] for r in final['results'])
    assert 'ít nhất' not in final['results'][0]['response']['answer']['answer']
    replay = read(PHASE/'replay.json')
    assert replay['status'] == 'PASS' and replay['external_provider_calls'] == 0
    assert len(replay['results']) == 24 and all(r['passed'] for r in replay['results'])
    assert Counter(r['kind'] for r in replay['results']) == {'generated':8,'cached':8,'negative':8}
    for name,digest in replay['sources_sha256'].items():
        assert sha(ROOT/name) == digest, name
    full = test_counts(PHASE/'acceptance-regression.xml')
    assert full['passed'] == 1827 and full['skipped'] == 2
    ui = read(PHASE/'ui-final/browser-results.json')
    assert ui['status'] == 'PASS' and len(ui['checks']) == 39 and not ui['browserErrors']
    assert read(PHASE/'validator-integrity.json')['status'] == 'PASS'
    assert read(PHASE/'runtime-smoke.json')['additional_provider_posts'] == 0
    assert read(PHASE/'quality-review.json')['status'] == 'PASS_WITH_RECORDED_HISTORY'
    package_record = read(PHASE/'packaging.json')
    assert sha(ROOT/package_record['wheel']) == package_record['wheel_sha256']
    for name,digest in package_record['packaged_source_and_ui_sha256'].items():
        assert sha(ROOT/'src'/name) == digest
    assert sha(ROOT/'configs/product_llm.yaml') == 'b9a1062728e8644423d0c57d4a4e105943940b4fb1a106e0cb422a3f249215cd'
    assert read(PHASE/'completion-checks.json')['status'] == 'PASS'
    return {'status':'BOUNDED_NATURAL_QUALITY_PASS','date':'2026-10-16', 'reviewer':'Codex - Automated AI Review',
        'scope':'Local uploaded-PDF page facts, natural section synthesis and conversational continuity; bounded happy/adversarial coverage',
        'full_regression':full,'browser_checks':39,'actual_provider_posts_this_phase':16,
        'native_evidence':'Eight source-protocol generated answers; final one-POST terminology+gibberish check. Failed/incomplete live sequences remain NOT_PASSED.',
        'offline_replay_turns':24,'offline_replay_external_posts':0,
        'limits':['Not exhaustive of every human question or every PDF.','Replay is not new native generation or a live SLO.',
                  'Free tier owner-attested; no billing changes. TPM/RPD still unknown.','Cloud/R-01/R-02 unchanged.']}


def capture():
    assert not (PHASE/'receipt.json').exists()
    result = audit()
    sources = [p for folder in ('src/campusai','scripts','tests') for p in (ROOT/folder).rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and 'node_modules' not in p.parts
        and p.suffix in {'.py','.js','.cjs','.css','.html'}]
    sources += [ROOT/name for name in ('plan.md','README.md','configs/free_llm.yaml','configs/product_llm.yaml',
        'docs/deployment/phase13/natural-conversation.md','tests/ui/package.json','tests/ui/package-lock.json')]
    artifacts = [p for p in PHASE.rglob('*') if p.is_file() and p.name != 'receipt.json'
                 and p.suffix in {'.json','.xml','.png','.py','.ps1','.sqlite3'}]
    artifacts += [ROOT/read(PHASE/'packaging.json')['wheel']]
    result['sources_sha256'] = {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(sources))}
    result['artifacts_sha256'] = {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(artifacts))}
    write('receipt.json',result)
    verify()


def verify():
    result = read(PHASE/'receipt.json')
    for group in ('sources_sha256','artifacts_sha256'):
        for name,digest in result[group].items():
            assert sha(ROOT/name) == digest, name
    assert all(result[key] == value for key,value in audit().items())
    print('PASS: current source/config, native history, replay, tests, UI, package and runtime bindings; zero new inference')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',action='store_true')
    parser.add_argument('--package',action='store_true')
    parser.add_argument('--verify',action='store_true')
    args = parser.parse_args()
    runtime() if args.runtime else package() if args.package else verify() if args.verify else capture()
