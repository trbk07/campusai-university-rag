"""Audit a complete public-source qualification without provider requests."""
import argparse
from collections import Counter
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
from xml.etree import ElementTree as ET
import zipfile

from campusai.llm.factory import _read_config

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/deployment/phase13/evidence/model-selection-20261016'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_counts(path):
    suites = ET.parse(path).getroot().findall('testsuite')
    counts = {key: sum(int(s.get(key, 0)) for s in suites)
              for key in ('tests', 'failures', 'errors', 'skipped')}
    counts['passed'] = counts['tests'] - counts['failures'] - counts['errors'] - counts['skipped']
    assert counts['failures'] == counts['errors'] == 0
    return counts


def audit_live():
    directory = EVIDENCE / 'flash-lite-capacity-http'
    report = json.loads((directory / 'report.json').read_text(encoding='utf-8'))
    assert report['status'] == 'PASS'
    assert len(report['calls']) == report['actual_provider_attempts'] == 10
    assert len(report['results']) == 30 and all(r['passed'] for r in report['results'])
    assert Counter(r['kind'] for r in report['results']) == {'generated': 10, 'cached': 10, 'negative': 10}
    for name, digest in report['sources_sha256'].items():
        assert sha(ROOT / name) == digest, name
    for i, call in enumerate(report['calls'], 1):
        assert call['http_status'] == 200
        request = directory / f'provider-request-{i:02d}.json'
        response = directory / f'provider-response-{i:02d}.json'
        assert sha(request) == call['request_sha256'] == call['body_sha256']
        assert sha(response) == call['response_sha256']
        body = json.loads(request.read_bytes())
        assert 'tools' not in body and body['generationConfig']['maxOutputTokens'] <= 1536
        assert json.loads(response.read_bytes())['usageMetadata'] == call['usage']
    starts = [c['started_at_utc'] for c in report['calls']]
    assert all(b - a >= 5.95 for a, b in zip(starts, starts[1:]))
    for row in report['results']:
        assert row['provider_attempts'] == (1 if row['kind'] == 'generated' else 0)
    return report


def package():
    from setuptools.build_meta import build_wheel
    destination = ROOT / '.local_artifacts/model-selection-20261016'
    destination.mkdir(parents=True, exist_ok=True)
    assert not list(destination.glob('*.whl')), 'Retain the historical wheel; use --verify'
    with redirect_stdout(io.StringIO()):
        wheel = destination / build_wheel(str(destination))
    files = {p.relative_to(ROOT / 'src').as_posix(): sha(p)
             for p in (ROOT / 'src/campusai').rglob('*')
             if p.is_file() and (p.suffix == '.py' or 'ui' in p.parts)}
    files = {name: digest for name, digest in files.items() if '__pycache__' not in name}
    with zipfile.ZipFile(wheel) as archive:
        for name, digest in files.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest, name
        assert not any(n.endswith(('.yaml', '.pdf', '.sqlite', '.sqlite3', '.db', '.env'))
                       for n in archive.namelist())
    result = {'status': 'PASS', 'wheel_sha256': sha(wheel), 'wheel_artifact': wheel.relative_to(ROOT).as_posix(),
              'packaged_source_and_ui_sha256': files, 'private_material_included': False}
    (EVIDENCE / 'packaging.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')


def capture():
    assert not (EVIDENCE / 'receipt.json').exists(), 'Receipt is immutable; use --verify'
    report = audit_live()
    assert _read_config(ROOT / 'configs/free_llm.yaml') == _read_config(ROOT / 'configs/candidates/flash-lite-capacity.yaml')
    assert sha(ROOT / 'configs/product_llm.yaml') == 'b9a1062728e8644423d0c57d4a4e105943940b4fb1a106e0cb422a3f249215cd'
    old = ROOT / 'docs/deployment/phase13/evidence/model-selection-20261015'
    regression = test_counts(EVIDENCE / 'verified-regression.xml')
    activation = test_counts(EVIDENCE / 'activation-tests.xml')
    packaging = json.loads((EVIDENCE / 'packaging.json').read_text(encoding='utf-8'))
    assert packaging['status'] == 'PASS'
    assert sha(ROOT / packaging['wheel_artifact']) == packaging['wheel_sha256']
    sources = list((ROOT / 'src/campusai').rglob('*.py')) + list((ROOT / 'tests').rglob('*.py'))
    sources += [ROOT / name for name in ('scripts/operations/local.py', 'scripts/operations/serve.py',
        'scripts/operations/diagnostics/model_qualification.py', 'tests/deployment/capture_model_selection.py',
        'scripts/operations/diagnostics/context_budget.py',
        'tests/deployment/test_persistent_answer_cache.py', 'tests/test_local_launcher.py',
        'configs/free_llm.yaml', 'configs/candidates/flash-lite-capacity.yaml', 'configs/product_llm.yaml',
        '.env.example', 'README.md', 'plan.md')]
    artifacts = [p for root in (old, EVIDENCE) for p in root.rglob('*')
                 if p.is_file() and p.suffix in {'.json', '.xml', '.log'} and p.name != 'receipt.json']
    artifacts += [ROOT / packaging['wheel_artifact']]
    artifacts += [p for root in (old, EVIDENCE) for p in root.rglob('answer-cache.sqlite3')]
    result = {'status': 'BOUNDED_LIVE_PASS', 'date': '2026-10-16',
        'reviewer': 'Codex - Automated AI Review', 'model': report['model'],
        'scope': 'One owner, one public-source VI/EN conversation, local full application, operator ten RPM; no cloud or unlimited-capacity claim',
        'new_answers': 10, 'exact_context_cache_hits': 10, 'deterministic_negatives': 10,
        'provider_attempts_this_run': 10, 'prior_selection_attempts_retained': 27,
        'free_tier': 'owner confirmed; independent Console verification unavailable',
        'account_numerical_quota': 'UNKNOWN', 'goal_complete': False,
        'full_regression': regression, 'activation_tests': activation,
        'resources': report['resources'],
        'regression_scope': 'Full runtime and selected-default activation tests; live calls are separate from injected provider faults.',
        'sources_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in sources},
        'artifacts_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in artifacts}}
    (EVIDENCE / 'receipt.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    verify()


def verify():
    result = json.loads((EVIDENCE / 'receipt.json').read_text(encoding='utf-8'))
    for group in ('sources_sha256', 'artifacts_sha256'):
        for name, digest in result[group].items():
            assert sha(ROOT / name) == digest, name
    audit_live()
    print('PASS: current source/config, native public responses, HTTP results, tests and package bindings; zero new provider calls')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', action='store_true')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    package() if args.package else verify() if args.verify else capture()
