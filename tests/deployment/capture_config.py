"""Bind cloud configuration preparation to source, tests and local model evidence."""
import argparse
from contextlib import redirect_stdout
import io
import hashlib
import json
from pathlib import Path
import zipfile

from tests.deployment.capture_recovery import counts, sha

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT/'docs/deployment/phase13/evidence'
RECEIPT = EVIDENCE/'cloud-config-receipt.json'


def verify():
    receipt = json.loads(RECEIPT.read_text(encoding='utf-8'))
    assert receipt['status'] == 'PASS'
    assert receipt['cloud_deployed'] is False
    for group in ('sources_sha256','artifacts_sha256'):
        for name,digest in receipt[group].items():
            assert sha(ROOT/name) == digest, name
    print('PASS: cloud configuration preparation bindings; no provider calls')


def capture():
    focused = counts(EVIDENCE/'cloud-runtime-focused.xml')
    regression = counts(EVIDENCE/'cloud-config-regression.xml')
    assert not any(result[key] for result in (focused,regression) for key in ('failures','errors'))
    native = json.loads((EVIDENCE/'dense-model/offline-windows.json').read_text(encoding='utf-8'))
    assert native['status'] == 'PASS' and native['platform']['system'] == 'Windows'
    assert native['actual_encoder_instances'] == 1 and not native['network_connection_attempts']
    for name,digest in native['sources_sha256'].items():
        assert sha(ROOT/name) == digest, name
    template = json.loads((EVIDENCE/'cloud-preflight-template.json').read_text(encoding='utf-8'))
    assert template['exit_code'] == 2 and template['report']['status'] == 'NOT_READY'
    from setuptools.build_meta import build_wheel
    output = ROOT/'.tmp/cloud-config-wheel'
    output.mkdir(parents=True,exist_ok=True)
    with redirect_stdout(io.StringIO()):
        wheel = output/build_wheel(str(output))
    with zipfile.ZipFile(wheel) as archive:
        for name in ('campusai/deployment/config/settings.py','campusai/deployment/config/preflight.py',
                     'campusai/deployment/runtime/models.py'):
            assert archive.read(name) == (ROOT/'src'/name).read_bytes()
        assets = {name:hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist() if name.startswith('campusai/ui/')}
        expected = {p.relative_to(ROOT/'src').as_posix():sha(p) for p in (ROOT/'src/campusai/ui').rglob('*') if p.is_file()}
        assert assets == expected and len(assets) == 11
        assert all(not name.endswith(('.yaml','.pdf','.sqlite','.db')) for name in archive.namelist())
    packaging = {'status':'PASS','wheel_sha256':sha(wheel),'ui_assets_sha256':assets,
                 'cloud_configuration_modules_included':True,'private_material_included':False,
                 'not_an_arm64_install_check':True}
    (EVIDENCE/'cloud-config-packaging.json').write_text(json.dumps(packaging,indent=2)+'\n',encoding='utf-8')
    sources = [p for p in (ROOT/'src/campusai').rglob('*') if p.is_file() and p.suffix in {'.py','.js','.html','.css'}]
    sources += [p for p in (ROOT/'configs/deployment').rglob('*') if p.is_file()]
    sources += [ROOT/name for name in ('pyproject.toml','README.md','configs/product_llm.yaml',
        'scripts/operations/preflight.py','scripts/operations/model_manifest.py',
        'scripts/operations/diagnostics/offline_dense.py','scripts/operations/serve.py',
        'scripts/operations/local.py','tests/deployment/test_cloud_configuration.py',
        'tests/deployment/test_pinned_retrieval.py','tests/deployment/capture_config.py',
        'tests/test_local_launcher.py','tests/test_ingestion_jobs.py','tests/test_hybrid_retrieval.py')]
    artifacts = [p for p in EVIDENCE.glob('cloud-*.xml')]
    artifacts += [EVIDENCE/'cloud-config-packaging.json',EVIDENCE/'cloud-preflight-template.json',
                  EVIDENCE/'dense-model/dense-manifest.json',EVIDENCE/'dense-model/offline-windows.json']
    receipt = {'status':'PASS','scope':'C13-02 portable configuration/preflight and opt-in pinned CPU indexing/query; local verification only',
        'date':'2026-10-15','reviewer':'Codex — Automated AI Review','focused_tests':focused,
        'regression_tests':regression,'live_provider_calls':0,'cloud_deployed':False,
        'native_model_check':{'platform':native['platform'],'status':'PASS',
            'actual_encoder_instances':1,'embedding_dimension':native['embedding_dimension'],
            'elapsed_ms':native['elapsed_ms'],'network_connection_attempts':0},
        'sources_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(sources))},
        'artifacts_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(artifacts))},
        'limits':['Synthetic unit platform/package/quota fixtures are not cloud evidence.',
                  'Real native model run is Windows AMD64; ARM64/Python 3.12 install unverified.',
                  'Production entrypoint does not yet consume this profile; durable jobs/budgets and VM gates remain open.',
                  'Owner confirmed Oracle registration is pending and will provide information later.',
                  'No default model, local user index or cloud release requirement was changed.'],
        'R-01':'DEFERRED — NOT PASSED','R-02':'DEFERRED — NOT PASSED'}
    RECEIPT.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    verify()
    print(json.dumps({key:receipt[key] for key in ('status','focused_tests','regression_tests','native_model_check','cloud_deployed')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',action='store_true')
    args = parser.parse_args()
    verify() if args.verify else capture()
