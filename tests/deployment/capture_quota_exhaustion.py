"""Offline audit of the bounded Free-quota probe; never sends provider requests."""
import argparse
from collections import Counter
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sqlite3
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import zipfile

from campusai.llm.factory import _read_config
from campusai.llm.quota_hints import google_quota_hints
from tests.deployment.capture_model_selection import test_counts

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/deployment/phase13/evidence/quota-exhaustion-20261016'
OLD = ROOT / 'docs/deployment/phase13/evidence/model-selection-20261016'
FROZEN = 'b9a1062728e8644423d0c57d4a4e105943940b4fb1a106e0cb422a3f249215cd'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(name, value):
    (EVIDENCE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def old_qualification():
    record = read(EVIDENCE / 'previous-source-archive.json')
    assert sha(ROOT / record['previous_receipt']) == record['previous_receipt_sha256']
    assert sha(ROOT / record['source_archive']) == record['source_archive_sha256']
    receipt = read(ROOT / record['previous_receipt'])
    with zipfile.ZipFile(ROOT / record['source_archive']) as archive:
        for name, digest in receipt['sources_sha256'].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest, name
    log = read(EVIDENCE / 'historical-log-audit.json')
    for name, digest in receipt['artifacts_sha256'].items():
        if name == log['historical_artifact']:
            assert digest == log['receipt_sha256'] == sha(ROOT / log['exact_prefix_artifact'])
            assert sha(ROOT / name) == log['current_full_log_sha256']
            assert (ROOT / name).read_bytes().startswith((ROOT / log['exact_prefix_artifact']).read_bytes())
        else:
            assert sha(ROOT / name) == digest, name
    report = read(OLD / 'flash-lite-capacity-http/report.json')
    assert report['status'] == 'PASS' and len(report['calls']) == 10
    assert len(report['results']) == 30 and all(r['passed'] for r in report['results'])
    assert Counter(r['kind'] for r in report['results']) == {'generated': 10, 'cached': 10, 'negative': 10}
    for call in report['calls']:
        assert call['http_status'] == 200
    return {'status': 'PASS', 'source_identity': 'exact archived source; original receipt unchanged',
            'generated': 10, 'cache': 10, 'negative': 10, 'provider_posts': 10,
            'runtime_log': 'original exact hash-matching prefix retained separately; later access lines remain in full log'}


def audit_probe():
    initial = read(EVIDENCE / 'live/report.json')
    assert initial['status'] == 'STOPPED_LOCAL' and initial['actual_provider_attempts'] == 2
    initial_audit = read(EVIDENCE / 'initial-probe-audit.json')
    assert sha(ROOT / initial_audit['source_snapshot']) == initial_audit['source_sha256']
    assert initial_audit['source_sha256'] in initial['sources_sha256'].values()
    report = read(EVIDENCE / 'live-corrected/report.json')
    assert report['status'] == 'STOPPED_QUOTA'
    assert sha(EVIDENCE / 'protocol-corrected.json') == report['protocol_sha256']
    assert report['protocol'] == read(EVIDENCE / 'protocol-corrected.json')
    assert len(report['calls']) == report['actual_provider_attempts'] == 33
    assert Counter(c['http_status'] for c in report['calls']) == {200: 32, 429: 1}
    assert not report['auto_retry'] and not report['billing_changes'] and not report['credential_rotation']
    assert report['first_stop']['attempt'] == 33 and report['first_stop']['http_status'] == 429
    assert all(c['started_at_utc'] <= report['first_stop']['at_utc'] for c in report['calls'])
    assert report['quota_after']['reserved_attempts_today'] - report['quota_before']['reserved_attempts_today'] == 33
    assert report['quota_before']['reserved_attempts_today'] == initial['quota_after']['reserved_attempts_today']
    assert report['quota_after']['in_flight'] == 0
    assert report['quota_after']['observed_provider_limits']['requests_per_minute']['value'] == 15
    assert initial['actual_provider_attempts'] + report['actual_provider_attempts'] == 35 <= 60
    for source, digest in report['sources_sha256'].items():
        assert sha(ROOT / source) == digest, source
    known_requests = {c['request_sha256'] for c in read(OLD / 'flash-lite-capacity-http/report.json')['calls']}
    for run in (initial, report):
        for call in run['calls']:
            assert call['request_sha256'] in known_requests
            assert sha(ROOT / call['artifact']) == call['artifact_sha256']
    quota_call = report['calls'][-1]
    hints = google_quota_hints(read(ROOT / quota_call['artifact']))
    assert hints == quota_call['quota_hints']
    assert hints['violations'] == [{'kind': 'requests_per_minute', 'model': 'gemini-3.5-flash-lite', 'value': 15}]
    profile = _read_config(ROOT / 'configs/free_llm.yaml')['llm']
    assert profile['model'] == 'gemini-3.5-flash-lite' and profile['max_retries'] == 0
    assert profile['requests_per_minute'] == 10 < hints['violations'][0]['value']
    assert profile['quota']['max_in_flight'] == 1
    assert sha(ROOT / 'configs/product_llm.yaml') == FROZEN
    compatibility = read(EVIDENCE / 'request-compatibility.json')
    assert compatibility['status'] == 'PASS' and len(compatibility['cases']) == 10
    assert {r['request_sha256'] for r in compatibility['cases']} == known_requests
    assert all(r['matches_prior_native_request'] for r in compatibility['cases'])
    return {'phase_posts': 35, 'main_probe': {'http_200': 32, 'http_429': 1},
            'observed_free_rpm': 15, 'input_tpm': 'UNKNOWN', 'rpd': 'UNKNOWN',
            'stopped_at_first_quota_signal': True, 'no_post_started_after_stop': True}


def runtime_smoke():
    """Only local readiness and deterministic negatives, no model inference."""
    profile = _read_config(ROOT / 'configs/free_llm.yaml')['llm']
    def accounting():
        with sqlite3.connect(f'file:{(ROOT / profile["quota"]["state_path"]).as_posix()}?mode=ro', uri=True) as db:
            scope = profile['quota']['scope']
            policy = json.loads(db.execute('SELECT policy FROM quota_state WHERE scope=?', (scope,)).fetchone()[0])
            count = db.execute('SELECT count(*) FROM quota_attempts WHERE scope=?', (scope,)).fetchone()[0]
        return policy, count
    def local(path, body=None):
        request = Request('http://127.0.0.1:8000' + path,
            data=None if body is None else json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)
    policy, before = accounting()
    assert policy['requests_per_minute'] == 10 and policy['max_in_flight'] == 1
    checks = []
    for path in ('/health', '/ready', '/api/documents'):
        status, data = local(path)
        assert status == 200
        checks.append({'path': path, 'http_status': status})
        if path == '/api/documents':
            assert data['runtime']['ai_configured']
            ids = [d['doc_id'] for d in data['documents'] if d['ready']]
    public_id = 'b9b9e88d93fdc12e1a0d4ec6ad30f86980fb2d95610ecdbfb2a284da224e64fb'
    assert public_id in ids
    for question, doc_ids, expected in [('How many credits does ZZZ9900 have?', [public_id], 200),
            ('ambiguous scope', [], 400), ('missing scope', ['0' * 64], 404),
            ('c\u00e1i \u0111\u00f3', [public_id], 200)]:
        status, data = local('/api/query', {'question': question, 'doc_ids': doc_ids, 'language': 'vi', 'history': []})
        assert status == expected
        if status == 200:
            assert data['answer']['abstained'] and not data['answer']['citations']
        checks.append({'question': question, 'http_status': status, 'response': data})
    after_policy, after = accounting()
    assert policy == after_policy and before == after == 70
    write('runtime-smoke.json', {'status': 'PASS', 'scope': 'Running app; readiness and deterministic local negatives only',
        'model': profile['model'], 'profile_sha256': sha(ROOT / 'configs/free_llm.yaml'),
        'policy': policy, 'provider_reservations_before': before, 'provider_reservations_after': after,
        'additional_provider_attempts': 0, 'checks': checks})
    print('PASS: selected runtime 10 RPM / one sender, counters retained, zero provider calls')


def package():
    from setuptools.build_meta import build_wheel
    destination = ROOT / '.local_artifacts/quota-exhaustion-20261016-package'
    destination.mkdir(parents=True, exist_ok=True)
    assert not list(destination.glob('*.whl')), 'Historical wheel is immutable'
    with redirect_stdout(io.StringIO()):
        wheel = destination / build_wheel(str(destination))
    files = {p.relative_to(ROOT / 'src').as_posix(): sha(p) for p in (ROOT / 'src/campusai').rglob('*')
             if p.is_file() and '__pycache__' not in p.parts and (p.suffix == '.py' or 'ui' in p.parts)}
    with zipfile.ZipFile(wheel) as archive:
        for name, digest in files.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest, name
        assert not any(n.endswith(('.yaml', '.pdf', '.sqlite', '.sqlite3', '.db', '.env')) for n in archive.namelist())
    write('packaging.json', {'status': 'PASS', 'wheel': wheel.relative_to(ROOT).as_posix(), 'wheel_sha256': sha(wheel),
        'packaged_source_and_ui_sha256': files, 'private_material_included': False})
    print('PASS: package matches current Python/UI source and excludes private material')


def audit():
    prior, probe = old_qualification(), audit_probe()
    regression = test_counts(EVIDENCE / 'regression.xml')
    assert regression['passed'] == 1770 and regression['skipped'] == 2
    focused = test_counts(EVIDENCE / 'focused.xml')
    diagnostic = test_counts(EVIDENCE / 'probe-correction-tests.xml')
    assert focused['passed'] == 75 and diagnostic['passed'] == 18
    browser = read(EVIDENCE / 'ui/browser-results.json')
    assert browser['status'] == 'PASS' and not browser['browserErrors']
    assert all(c['passed'] for c in browser['checks'])
    assert any('daily quota permits manual local lookup' in c['name'] for c in browser['checks'])
    runtime = read(EVIDENCE / 'runtime-smoke.json')
    assert runtime['status'] == 'PASS' and runtime['additional_provider_attempts'] == 0
    package_record = read(EVIDENCE / 'packaging.json')
    assert sha(ROOT / package_record['wheel']) == package_record['wheel_sha256']
    for name, digest in package_record['packaged_source_and_ui_sha256'].items():
        assert sha(ROOT / 'src' / name) == digest, name
    checks = read(EVIDENCE / 'completion-checks.json')
    assert checks['status'] == 'PASS' and checks['plan_tracked']
    assert len(checks['temporary_paths_absent']) == 7 and checks['operational_state_retained']
    assert read(EVIDENCE / 'secret-scan.json')['status'] == 'PASS'
    return {'status': 'BOUNDED_FREE_CONTINUITY_PASS', 'date': '2026-10-16',
        'reviewer': 'Codex - Automated AI Review', 'goal_complete': True,
        'scope': 'Owner Free-tier local app, qualified ten-RPM conversation and empirical stop at first quota signal',
        'prior_native_qualification': prior, 'quota_probe': probe,
        'full_regression': regression, 'focused_tests': focused, 'diagnostic_tests': diagnostic,
        'test_scope': '1770 full regression before the diagnostic test was added; 18 focused tests include that new test. UI verified separately offline.',
        'browser_checks': len(browser['checks']), 'runtime_provider_calls': 0,
        'limits': ['Input TPM and RPD unmeasured; no further probe after owner stop condition.',
                   'Free tier owner-attested; no independent billing Console access or billing change.',
                   'No unlimited free usage, global highest-quota model, cloud availability or SLO claim.',
                   'Prior success bound to its archived source; current success-path requests match all ten native bodies.']}


def capture():
    assert not (EVIDENCE / 'receipt.json').exists(), 'Receipt immutable; use --verify'
    result = audit()
    sources = [p for folder in ('src/campusai', 'tests', 'scripts') for p in (ROOT / folder).rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and 'node_modules' not in p.parts
        and (p.suffix == '.py' or (folder == 'src/campusai' and 'ui' in p.parts))]
    sources += [ROOT / name for name in ('tests/ui/browser_smoke.cjs', 'tests/ui/package.json', 'tests/ui/package-lock.json',
        'configs/free_llm.yaml', 'configs/product_llm.yaml', 'plan.md', 'README.md', '.env.example', 'pyproject.toml',
        'docs/deployment/phase13/free-continuity-goal.md', 'docs/deployment/phase13/model-selection.md',
        'docs/deployment/phase13/repo-application-review.md', 'docs/deployment/phase13/quota-admission.md',
        'docs/deployment/phase13/quota-exhaustion.md')]
    artifacts = [p for p in EVIDENCE.rglob('*') if p.is_file() and p.name != 'receipt.json'
        and p.suffix in {'.json', '.xml', '.png', '.py', '.ps1'}]
    artifacts += [ROOT / read(EVIDENCE / 'packaging.json')['wheel']]
    artifacts += [EVIDENCE / 'historical-runtime-stderr-prefix.log']
    for run in ('live', 'live-corrected'):
        artifacts += [ROOT / c['artifact'] for c in read(EVIDENCE / run / 'report.json')['calls']]
    result['sources_sha256'] = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(set(sources))}
    result['artifacts_sha256'] = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(set(artifacts))}
    write('receipt.json', result)
    verify()


def verify():
    result = read(EVIDENCE / 'receipt.json')
    for group in ('sources_sha256', 'artifacts_sha256'):
        for name, digest in result[group].items():
            assert sha(ROOT / name) == digest, name
    current = audit()
    assert all(result[key] == value for key, value in current.items())
    print('PASS: current-source receipt, historical archive, real quota stop, tests, UI, package and runtime; zero provider calls')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-smoke', action='store_true')
    parser.add_argument('--package', action='store_true')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    runtime_smoke() if args.runtime_smoke else package() if args.package else verify() if args.verify else capture()
