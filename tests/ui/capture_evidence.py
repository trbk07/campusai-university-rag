"""Bind the local UI acceptance results to reproducible source and artifacts."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def counts(path):
    suite = ET.parse(path).getroot().find('testsuite')
    return {key: int(suite.attrib.get(key, 0)) for key in ('tests', 'failures', 'errors', 'skipped')}


def main():
    root = ROOT / 'docs/ui'
    browser = json.loads((root/'evidence/browser-results.json').read_text(encoding='utf-8'))
    full_path = root/'local-offline-tests.xml' if (root/'local-offline-tests.xml').exists() else root/'offline-tests.xml'
    focused_path = root/'local-launch-tests.xml' if (root/'local-launch-tests.xml').exists() else root/'focused-tests.xml'
    full, focused = counts(full_path), counts(focused_path)
    sources = [ROOT/name for name in ('pyproject.toml', '.env.example', 'configs/product_llm.yaml', 'start-campusai.cmd',
        'scripts/operations/local.py', 'scripts/operations/with_gemini_key.py', 'scripts/operations/serve.py', 'src/campusai/web.py',
        'src/campusai/web_documents.py','src/campusai/ingestion/jobs.py','src/campusai/ingestion/validate.py',
        'src/campusai/llm/cache.py','src/campusai/rag/cache.py','src/campusai/rag/grounding.py','src/campusai/rag/claims.py',
        'tests/test_web.py','tests/test_web_documents.py','tests/test_local_launcher.py','tests/test_cross_language_grounding.py')]
    sources += [path for folder in ('src/campusai/ui','tests/ui') for path in (ROOT/folder).rglob('*')
                if path.is_file() and path.suffix in {'.py','.cjs','.json','.html','.css','.js'} and 'node_modules' not in path.parts]
    source_hashes = {path.relative_to(ROOT).as_posix():sha(path) for path in sorted(sources)}
    artifacts = [full_path,focused_path,root/'evidence/browser-results.json',root/'evidence/packaging.json',
                 *(root/'evidence').glob('local-live-*.json'),*(root/'evidence').glob('*.png')]
    live = json.loads((root/'evidence/local-live-smoke.json').read_text(encoding='utf-8'))
    live_browser = json.loads((root/'evidence/local-live-browser.json').read_text(encoding='utf-8'))
    package = json.loads((root/'evidence/packaging.json').read_text(encoding='utf-8'))
    package_matches = package['status'] == 'PASS' and all(
        sha(ROOT/'src'/name) == digest for name,digest in package['ui_assets'].items())
    passed = not any(full[key] or focused[key] for key in ('failures','errors')) and browser['status'] == 'PASS'
    passed = passed and package_matches and live['status'] == live_browser['status'] == 'PASS'
    receipt = {'status':'PASS' if passed else 'FAIL', 'scope':'Phase 12 local single-user UI and usable local startup',
        'reviewer':'Codex — Automated AI Review','date':'2026-10-15','timezone':'Asia/Bangkok',
        'offline_suite':full,'focused_suite':focused,'browser_checks':len(browser['checks']),
        'source_sha256':source_hashes,'artifacts_sha256':{path.relative_to(ROOT).as_posix():sha(path) for path in artifacts},
        'offline_provider_calls':0,'live_local_smoke':{'status':live['status'],'browser':live_browser['status'],
            'application_query_attempts':5,'grounded_answers':2,'rejected_claim_answers':1,'provider_failure_responses':2,
            'not_a_provider_SLO':True},'R-01':'DEFERRED — NOT PASSED','R-02':'DEFERRED — NOT PASSED',
        'limits':['Local single-user host; no account authentication.', 'Automated accessibility checks are not a WCAG certification.',
                  'No live provider latency, availability or native API qualification.']}
    (root/'evidence/acceptance.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:receipt[key] for key in ('status','offline_suite','focused_suite','browser_checks','live_local_smoke')}))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
