"""Capture/verify local degraded-source UX without making provider requests."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen
import zipfile

from tests.deployment.capture_recovery import counts, sha

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT/'docs/deployment/phase13/evidence'
RECEIPT = EVIDENCE/'source-excerpts-receipt.json'


def package():
    from setuptools.build_meta import build_wheel
    output = ROOT/'.tmp/source-excerpts-wheel'
    output.mkdir(parents=True, exist_ok=True)
    wheel = output/build_wheel(str(output))
    with zipfile.ZipFile(wheel) as archive:
        assets = {name: hashlib.sha256(archive.read(name)).hexdigest()
                  for name in archive.namelist() if name.startswith('campusai/ui/')}
        expected = {p.relative_to(ROOT/'src').as_posix(): sha(p)
                    for p in (ROOT/'src/campusai/ui').rglob('*') if p.is_file()}
        assert assets == expected and len(assets) == 11
        assert 'campusai/rag/excerpts.py' in archive.namelist()
        assert all(not name.endswith(('.yaml','.pdf','.sqlite','.db')) for name in archive.namelist())
    report = {'status':'PASS', 'ui_assets_sha256':assets, 'wheel_sha256':sha(wheel),
              'source_excerpt_module_included':True, 'private_material_included':False,
              'recipe':'.venv/Scripts/python.exe -m tests.deployment.capture_excerpts --package'}
    (EVIDENCE/'source-excerpts-packaging.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def verify():
    receipt = json.loads(RECEIPT.read_text(encoding='utf-8'))
    assert receipt['status'] == 'PASS'
    for group in ('sources_sha256','artifacts_sha256'):
        for name, digest in receipt[group].items():
            assert sha(ROOT/name) == digest, name
    print('PASS: source-excerpt verification bindings; no provider calls')


def capture():
    focused = counts(EVIDENCE/'ui-polling-focused-final.xml')
    regression = counts(EVIDENCE/'ui-polling-regression.xml')
    browser = json.loads((EVIDENCE/'source-excerpts-browser/browser-results.json').read_text(encoding='utf-8'))
    packaging = json.loads((EVIDENCE/'source-excerpts-packaging.json').read_text(encoding='utf-8'))
    assert not any(result[k] for result in (focused,regression) for k in ('failures','errors'))
    assert browser['status'] == packaging['status'] == 'PASS'
    assert all(sha(ROOT/'src'/name) == digest for name,digest in packaging['ui_assets_sha256'].items())
    def get(path):
        with urlopen('http://127.0.0.1:8000'+path, timeout=3) as response:
            return response.read()
    assert json.loads(get('/ready'))['status'] == 'ready'
    for name in ('features/chat.js','features/excerpts.js'):
        assert hashlib.sha256(get('/assets/'+name)).hexdigest() == sha(ROOT/'src/campusai/ui'/name)
    names = ['src/campusai/api.py','src/campusai/web.py','src/campusai/rag/excerpts.py',
        'src/campusai/rag/grounding.py','src/campusai/rag/cache.py',
        'src/campusai/llm/client.py','src/campusai/llm/overload.py','src/campusai/llm/failures.py',
        'scripts/operations/serve.py','scripts/operations/local.py','configs/product_llm.yaml',
        'src/campusai/web_documents.py','tests/deployment/test_source_excerpts.py',
        'tests/deployment/test_provider_recovery.py','tests/deployment/capture_excerpts.py',
        'tests/ui/browser_smoke.cjs','tests/ui/serve_fixture.py','pyproject.toml']
    sources = [ROOT/name for name in names]
    sources += [p for p in (ROOT/'src/campusai/ui').rglob('*') if p.is_file()]
    artifacts = [EVIDENCE/name for name in ('source-excerpts-focused.xml',
        'source-excerpts-focused-final.xml','source-excerpts-regression.xml',
        'ui-polling-focused.xml','ui-polling-focused-final.xml','ui-polling-regression.xml','source-excerpts-packaging.json')]
    artifacts += [p for p in (EVIDENCE/'source-excerpts-browser').rglob('*') if p.is_file()]
    receipt = {'status':'PASS','date':'2026-10-15','reviewer':'Codex — Automated AI Review',
        'scope':'Local provider-failure source view and responsive read-only HTTP polling; no synthesized-answer availability claim',
        'focused_tests':focused,'regression_tests':regression,'browser_checks':len(browser['checks']),
        'offline_fault_sequence':'20 HTTP lookups, one injected 503; 19 cooldown lookups without provider calls; subsequent real-transport stub recovery and cache reuse',
        'live_provider_calls_for_this_verification':0,
        'model_candidate_failure':'Separate live Flash-Lite qualification returned two answers then 503 on case 3; not resumed or activated',
        'local_runtime':{'ready':True,'served_ui_matches_source':True},
        'polling_fixture_failure':'New readiness check initially expected 200 from an intentionally unconfigured provider fixture; corrected to assert its truthful fast 503. Initial XML retained.',
        'sources_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(sources))},
        'artifacts_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(artifacts))},
        'initial_focused_failure':'Default pytest temp root denied by sandbox; switched to workspace basetemp. Corrected frozen test fixture using dataclasses.replace. Initial XML retained.',
        'limits':['Source excerpts do not replace generated answers or count as answer-quality success.',
                  'Gemini Free Tier outage/quota remains external; no unlimited quota or provider SLO proven.',
                  'Cloud account/provisioning, ARM64 and remaining Phase 13 gates pending.',
                  'Earlier Phase 12/provider-recovery receipts are historical source identities.'],
        'R-01':'DEFERRED — NOT PASSED','R-02':'DEFERRED — NOT PASSED'}
    RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    verify()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--package', action='store_true')
    args = parser.parse_args()
    package() if args.package else verify() if args.verify else capture()
