"""Capture/verify offline admission evidence. Never calls an inference API."""
import argparse
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
from xml.etree import ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT/'docs/deployment/phase13/evidence'
RECEIPT = EVIDENCE/'quota-receipt.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def counts(path):
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == 'testsuite' else list(root.findall('testsuite'))
    result = {key:sum(int(suite.get(key,0)) for suite in suites)
              for key in ('tests','failures','errors','skipped')}
    result['passed'] = result['tests']-result['failures']-result['errors']-result['skipped']
    return result


def package():
    from setuptools.build_meta import build_wheel
    destination = ROOT/'.tmp/quota-wheel'
    destination.mkdir(parents=True,exist_ok=True)
    with redirect_stdout(io.StringIO()):
        wheel = destination/build_wheel(str(destination))
    modules = ('llm/quota.py','llm/client.py','llm/factory.py','llm/overload.py')
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        for module in modules:
            assert hashlib.sha256(archive.read('campusai/'+module)).hexdigest() == sha(ROOT/'src/campusai'/module)
        assets = {name:hashlib.sha256(archive.read(name)).hexdigest()
                  for name in names if name.startswith('campusai/ui/')}
        expected = {path.relative_to(ROOT/'src').as_posix():sha(path)
                    for path in (ROOT/'src/campusai/ui').rglob('*') if path.is_file()}
        assert assets == expected and len(assets) == 11
        assert not any(name.endswith(('.yaml','.pdf','.sqlite','.sqlite3','.db','.env')) for name in names)
    report = {'status':'PASS','modules_sha256':{module:sha(ROOT/'src/campusai'/module) for module in modules},
              'ui_assets_sha256':assets,'wheel_sha256':sha(wheel), 'private_material_included':False,
              'recipe':'.venv/Scripts/python.exe -X utf8 -m tests.deployment.capture_quota --package'}
    (EVIDENCE/'quota-packaging.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('PASS: four admission/client modules and eleven UI assets packaged; no private material')


def verify():
    receipt = json.loads(RECEIPT.read_text(encoding='utf-8'))
    assert receipt['status'] == 'OFFLINE_PASS' and receipt['live_provider_calls'] == 0
    assert receipt['goal_complete'] is False
    for group in ('sources_sha256','artifacts_sha256'):
        for name,digest in receipt[group].items():
            assert sha(ROOT/name) == digest, name
    for filename in ('quota-focused.xml','quota-regression.xml'):
        result = counts(EVIDENCE/filename)
        assert result['failures'] == result['errors'] == 0
    assert sha(ROOT/'configs/product_llm.yaml') == 'b9a1062728e8644423d0c57d4a4e105943940b4fb1a106e0cb422a3f249215cd'
    print('PASS: offline quota receipt, current source and historical profile bytes verified; no provider calls')


def capture():
    focused, regression = (counts(EVIDENCE/name) for name in ('quota-focused.xml','quota-regression.xml'))
    assert not any(result[key] for result in (focused,regression) for key in ('failures','errors'))
    packaging = json.loads((EVIDENCE/'quota-packaging.json').read_text(encoding='utf-8'))
    assert packaging['status'] == 'PASS'
    names = ['src/campusai/llm/'+name for name in ('quota.py','client.py','factory.py','overload.py','failures.py','cache.py')]
    names += ['src/campusai/ingestion/background/manager.py','src/campusai/api.py','src/campusai/web.py',
              'src/campusai/rag/grounding.py','src/campusai/rag/service.py','src/campusai/rag/cache.py',
              'src/campusai/deployment/config/preflight.py','src/campusai/deployment/config/settings.py',
              'scripts/operations/local.py','scripts/operations/serve.py',
              'configs/product_llm.yaml','configs/continuity_llm.yaml','configs/deployment/gemini-owner.example.yaml',
              'tests/test_quota.py','tests/test_gemini_overload.py','tests/test_local_launcher.py',
              'tests/test_ingestion_acceptance.py','tests/test_phase8_live_runtime.py',
              'tests/deployment/quota_host.py','tests/deployment/test_quota_http.py',
              'tests/deployment/test_cloud_configuration.py','tests/deployment/test_provider_recovery.py',
              'tests/deployment/capture_quota.py','pyproject.toml']
    artifacts = ['quota-focused.xml','quota-regression.xml','quota-regression-initial.xml',
                 'quota-focused-correction.xml','quota-packaging.json']
    receipt = {'status':'OFFLINE_PASS','date':'2026-10-15','reviewer':'Codex — Automated AI Review',
        'scope':'Durable single-host quota admission, separate 429/503 recovery, default continuity profile and frozen-profile preservation',
        'focused_tests':focused,'regression_tests':regression,'packaging':'PASS',
        'live_provider_calls':0,'goal_complete':False,'account_quota':'UNKNOWN',
        'local_runtime_restarted':False,
        'proofs':['Six independent subprocesses consume exactly three shared daily reservations.',
                  'Real loopback HTTP: one injected 429, twenty rejected requests, one transport attempt before cooldown.',
                  'Post-cooldown stub recovery, ten HTTP cache hits, daily budget rejection and fast health access.',
                  'Daily and rolling-minute counters survive reconstruction; Pacific reset includes DST.',
                  'Failed/crashed reservations remain charged; stale policy/corrupt state stop before transport.',
                  'Original frozen product profile bytes and legacy circuit INSERT shape preserved.'],
        'initial_failures':{'regression':counts(EVIDENCE/'quota-regression-initial.xml'),
                            'correction':counts(EVIDENCE/'quota-focused-correction.xml'),
                            'reason':'Frozen profile edit/line endings drifted historical hash; ingestion omitted legacy review error alias. Corrected without altering historical manifests.'},
        'limits':['No real provider availability or long-conversation success is established.',
                  'Local default enforces operator RPM/concurrency only; actual account TPM/RPD/tier remain unknown.',
                  'UTF-8 token reservation is conservative estimation, not an exact tokenizer/quota proof; overages can only be reconciled after response.',
                  'Counters exclude other apps/machines; SQLite is single-host. In-flight lease does not prove remote cancellation.',
                  'Existing owner process was not restarted; explicit profile selection still takes precedence.',
                  'Earlier receipts remain historical; cloud and R-01/R-02 qualification remain open.'],
        'sources_sha256':{name:sha(ROOT/name) for name in names},
        'artifacts_sha256':{(EVIDENCE/name).relative_to(ROOT).as_posix():sha(EVIDENCE/name) for name in artifacts}}
    RECEIPT.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    verify()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',action='store_true')
    parser.add_argument('--package',action='store_true')
    args = parser.parse_args()
    package() if args.package else verify() if args.verify else capture()
