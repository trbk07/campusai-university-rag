"""Bind local operational verification; never invokes the answer provider."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT/'docs/deployment/phase13/evidence'
RECEIPT = EVIDENCE/'provider-recovery-receipt.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def counts(path):
    suite = ET.parse(path).getroot().find('testsuite')
    return {key:int(suite.attrib.get(key,0)) for key in ('tests','failures','errors','skipped')}


def verify():
    receipt = json.loads(RECEIPT.read_text(encoding='utf-8'))
    for group in ('sources_sha256','artifacts_sha256'):
        for name,digest in receipt[group].items():
            assert sha(ROOT/name) == digest, name
    assert receipt['status'] == 'PASS'
    print('PASS: recovery receipt bindings; no provider calls')


def capture():
    focused = counts(EVIDENCE/'provider-recovery-tests.xml')
    regression = counts(EVIDENCE/'provider-recovery-regression-final.xml')
    browser = json.loads((EVIDENCE/'provider-recovery-browser/browser-results.json').read_text(encoding='utf-8'))
    package = json.loads((EVIDENCE/'provider-recovery-packaging.json').read_text(encoding='utf-8'))
    assert not any(value[key] for value in (focused,regression) for key in ('failures','errors'))
    assert browser['status'] == package['status'] == 'PASS'
    assert all(sha(ROOT/'src'/name) == digest for name,digest in package['ui_assets_sha256'].items())
    def get(path):
        with urlopen('http://127.0.0.1:8000'+path,timeout=3) as response:
            return response.read()
    health, ready, documents = [json.loads(get(path)) for path in ('/health','/ready','/api/documents')]
    assert health['status'] == 'ok' and ready['status'] == 'ready'
    assert documents['runtime']['ai_configured']
    assert hashlib.sha256(get('/assets/features/chat.js')).hexdigest() == sha(ROOT/'src/campusai/ui/features/chat.js')
    names = ['src/campusai/api.py','src/campusai/web.py','src/campusai/llm/client.py',
        'src/campusai/llm/overload.py','src/campusai/llm/failures.py','src/campusai/rag/grounding.py',
        'src/campusai/rag/cache.py','src/campusai/rag/schemas.py','scripts/operations/local.py',
        'scripts/operations/serve.py','configs/product_llm.yaml','tests/deployment/test_provider_recovery.py',
        'tests/deployment/capture_recovery.py','tests/test_local_launcher.py','tests/ui/browser_smoke.cjs']
    sources = [ROOT/name for name in names]
    sources += list((ROOT/'src/campusai/deployment').glob('*.py'))
    sources += [p for p in (ROOT/'src/campusai/ui').rglob('*') if p.is_file()]
    artifacts = [p for p in EVIDENCE.glob('provider-recovery-*.xml')]
    artifacts += [EVIDENCE/'provider-recovery-packaging.json']
    artifacts += [p for p in (EVIDENCE/'provider-recovery-browser').rglob('*') if p.is_file()]
    receipt = {'status':'PASS','scope':'local provider error/UX recovery and bounded loopback HTTP transport',
        'date':'2026-10-15','timezone':'Asia/Bangkok','reviewer':'Codex — Automated AI Review',
        'focused_tests':focused,'regression_tests':regression,'browser_checks':len(browser['checks']),
        'live_provider_calls':0,'provider_faults':'deterministic transport injection; real WSGI/HTTP/SQLite',
        'local_runtime':{'health':health['status'],'ready':ready['status'],
            'ready_documents':sum(doc['ready'] for doc in documents['documents']),
            'ai_configured':True,'served_ui_matches_source':True},
        'sources_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(sources))},
        'artifacts_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(artifacts))},
        'initial_regression_failure':'Historical measurement transport inherited the new local admission cap; fixed by explicit local deployment configuration, preserving benchmark concurrency. Initial XML retained.',
        'browser_preflight_failure':'First attempt used the old fixture PDF path; parameterized UI_FIXTURE_DIR and reran successfully.',
        'limits':['No new live inference or provider availability/SLO measurement.',
                  'No cloud/ARM64 deployment verification. Cloud account/capacity pending.',
                  'Persistent per-day token/call budgets and production WSGI belong to remaining Phase 13 tasks.',
                  'Historical Phase 12 receipt retains its original source bindings.'],
        'R-01':'DEFERRED — NOT PASSED','R-02':'DEFERRED — NOT PASSED'}
    RECEIPT.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    verify()
    print(json.dumps({key:receipt[key] for key in ('status','focused_tests','regression_tests','browser_checks','live_provider_calls','local_runtime')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',action='store_true')
    args = parser.parse_args()
    verify() if args.verify else capture()
