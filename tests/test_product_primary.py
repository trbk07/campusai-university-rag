"""Paired acceptance controls reject protocol drift before starting a provider."""
from copy import deepcopy
from pathlib import Path
import pytest

from evaluation.common.release_artifacts import read_json, sha256, write_json
from scripts.benchmarks import product_primary as primary


@pytest.fixture
def packet(monkeypatch):
    value = read_json(primary.BASE / 'product-primary-egress-packet-20261009-v3.json')
    value['rubric'] = {'path': str(primary.RUBRIC), 'sha256': sha256(primary.RUBRIC)}
    # Historical zero-retry packets remain testable against their own config.
    monkeypatch.setattr(primary, 'read_json_config', lambda: deepcopy(value['llm_config']))
    return deepcopy(value)


def test_frozen_source_population_and_serialized_limits_are_consistent(packet):
    primary.validate_packet(packet)


def test_primary_retry_bundle_binds_exact_packet_and_configured_token_cap(tmp_path, monkeypatch):
    monkeypatch.setattr(primary, 'ROOT', tmp_path)
    monkeypatch.setattr(primary, 'validate_packet', lambda _packet: None)
    body_a = {'contents': [{'parts': [{'text': 'short'}]}]}
    body_b = {'contents': [{'parts': [{'text': 'longer'}]}]}
    packet_path = tmp_path / 'packet.json'
    write_json(packet_path, {
        'source_identity': {'source_sha256': 'fixture'},
        'max_provider_calls': 2,
        'prompt_chars': 11,
        'provider_bodies': [body_a, body_b],
        'max_retries': 1,
        'retry_only_http_status': 503,
        'minimum_provider_start_interval_seconds': 30,
        'output_dir': str(tmp_path / 'live'),
        'llm_config': {'max_retries': 1, 'retry_only_503': True,
                       'generation_config': {'maxOutputTokens': 1024}},
    })
    manifest_path = tmp_path / 'retry-manifest.json'
    state_path = tmp_path / 'retry-state.json'

    result = primary.bind_retry_bundle(packet_path, manifest_path, state_path, 'fixture')

    bound_packet = read_json(packet_path)
    manifest = read_json(manifest_path)
    assert bound_packet['retry_budget'] == manifest['retry_budget']
    assert manifest['packets'] == [{'path': str(packet_path.resolve()),
                                    'sha256': sha256(packet_path)}]
    assert result['maximum_external_post_requests'] == 3
    assert result['maximum_new_prompt_characters'] == 17
    assert result['maximum_total_output_tokens'] == 3072
    assert manifest['maximum_output_tokens_per_request'] == 1024
    assert not state_path.exists()  # Budget is initialized only at execution time.


def test_provider_http_error_keeps_only_bounded_redacted_diagnostic():
    import io
    import json
    from urllib.error import HTTPError
    from scripts.benchmarks.product_primary_worker import provider_error_diagnostic

    prompt = "private clinical prompt"
    api_key = "private-api-key"
    body = json.dumps({"error": {
        "status": "INVALID_ARGUMENT",
        "message": f"Bad input {prompt}; credential {api_key}",
        "details": [{"reason": "API_KEY_INVALID", "private": "omit"}],
    }}).encode()
    error = HTTPError("https://provider.invalid", 400, "bad request", {}, io.BytesIO(body))
    diagnostic = provider_error_diagnostic(error, prompt=prompt, api_key=api_key)

    assert diagnostic == {
        "provider_error_status": "INVALID_ARGUMENT",
        "provider_error_message": "Bad input [REDACTED]; credential [REDACTED]",
        "provider_error_reasons": ["API_KEY_INVALID"],
    }
    assert prompt not in json.dumps(diagnostic)
    assert api_key not in json.dumps(diagnostic)


@pytest.mark.parametrize('change', ['order', 'request', 'gold', 'retry', 'cap', 'settings', 'omit'])
def test_paired_changes_fail_closed(packet, change):
    row = packet['rows'][0]
    qid = row['qid']
    if change == 'order':
        packet['schedule'][:2] = reversed(packet['schedule'][:2])
    elif change == 'request':
        row['request']['question'] += ' Answer is 3.'
        for arm in packet['cases'].values():
            arm[qid]['request'] = deepcopy(row['request'])
    elif change == 'gold':
        row['benchmark_row']['answerable'] = not row['benchmark_row']['answerable']
    elif change == 'retry':
        packet['max_retries'] = 1
    elif change == 'cap':
        packet['max_provider_calls'] += 1
    elif change == 'settings':
        case = next(c for c in packet['cases']['baseline'].values() if c['provider_body'])
        case['provider_body']['generationConfig']['maxOutputTokens'] += 1
    else:
        del packet['cases']['current'][qid]
    with pytest.raises(ValueError):
        primary.validate_packet(packet)


def test_wrong_consent_never_starts_child_or_opens_packet(tmp_path, monkeypatch):
    path = tmp_path / 'packet.json'
    path.write_text('{}')
    monkeypatch.setattr(primary.subprocess, 'Popen', lambda *_a, **_k: pytest.fail('child started'))
    with pytest.raises(ValueError, match='authorization'):
        primary.collect(path, '0' * 64)


def test_baseline_tamper_rejected_before_application_import(tmp_path, monkeypatch):
    import zipfile
    tree = tmp_path / 'baseline'
    tree.mkdir()
    (tree / 'app.py').write_text('modified')
    archive = tmp_path / 'source.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('app.py', 'original')
    monkeypatch.setattr(primary, 'BASELINE_TREE', tree)
    with pytest.raises(ValueError, match='baseline source changed'):
        primary.verify_baseline({'path': str(archive), 'sha256': sha256(archive)})


def test_seeded_order_is_balanced_per_question_and_uses_both_orders(packet):
    schedule = primary.paired_schedule(packet['rows'])
    pairs = [schedule[i:i+2] for i in range(0, len(schedule), 2)]
    assert all(p[0]['qid'] == p[1]['qid'] and {v['arm'] for v in p} == {'baseline', 'current'} for p in pairs)
    assert {p[0]['arm'] for p in pairs} == {'baseline', 'current'}
    assert schedule == primary.paired_schedule(packet['rows'])


def test_free_tier_primary_shards_preserve_all_qid_pairs_under_daily_cap():
    packet = read_json(primary.BASE / 'product-primary-egress-packet-20261010-v28.json')
    groups = primary.quota_shard_groups(packet)
    flattened = [qid for group in groups for qid in group]
    assert len(groups) >= 5
    assert len(flattened) == len(set(flattened)) == 68
    assert set(flattened) == {row['qid'] for row in packet['rows']}
    for group in groups:
        planned = sum(bool(packet['cases'][arm][qid]['provider_body'])
                      for arm in ('baseline', 'current') for qid in group)
        assert planned <= 14
        schedule = primary.paired_schedule([row for row in packet['rows'] if row['qid'] in group])
        assert all(schedule[i]['qid'] == schedule[i + 1]['qid']
                   and {schedule[i]['arm'], schedule[i + 1]['arm']} == {'baseline', 'current'}
                   for i in range(0, len(schedule), 2))


def test_quota_shard_must_match_hash_bound_parent_exactly(packet, tmp_path):
    from evaluation.common.release_artifacts import write_json
    parent_path = tmp_path / 'parent.json'
    write_json(parent_path, packet)
    qids = [row['qid'] for row in packet['rows'][:7]]
    selected = set(qids)
    child = deepcopy(packet)
    child['rows'] = [row for row in packet['rows'] if row['qid'] in selected]
    child['cases'] = {arm: {qid: packet['cases'][arm][qid] for qid in qids}
                      for arm in ('baseline', 'current')}
    child['schedule'] = primary.paired_schedule(child['rows'])
    child['max_provider_calls'] = sum(bool(child['cases'][arm][qid]['provider_body'])
        for arm in ('baseline', 'current') for qid in qids)
    child['prompt_chars'] = sum(len(child['cases'][arm][qid]['provider_body']['contents'][0]['parts'][0]['text'])
        for arm in ('baseline', 'current') for qid in qids
        if child['cases'][arm][qid]['provider_body'])
    child['quota_shard'] = {'parent_path': str(parent_path), 'parent_sha256': sha256(parent_path),
                            'qids': qids}
    primary.validate_packet(child)
    child['cases']['current'][qids[0]]['evidence'] = []
    with pytest.raises(ValueError, match='frozen parent'):
        primary.validate_packet(child)


def test_shard_aggregate_rejects_wrong_manifest_digest_before_reading(tmp_path, monkeypatch):
    path = tmp_path / 'manifest.json'
    path.write_text('{}', encoding='utf8')
    monkeypatch.setattr(primary, 'read_json', lambda *_: pytest.fail('manifest read before digest check'))
    with pytest.raises(ValueError, match='authorization'):
        primary.aggregate_quota_shards(path, '0' * 64, tmp_path / 'aggregate.json')


def test_shard_aggregate_requires_complete_paired_union_and_same_model(tmp_path, monkeypatch):
    from evaluation.common.release_artifacts import write_json
    qids = [f'q{i:02d}' for i in range(68)]
    parent_path = tmp_path / 'parent.json'
    write_json(parent_path, {'rows': [{'qid': q, 'split': 'test' if i < 35 else 'holdout'}
        for i, q in enumerate(qids)], 'rubric': {'path': 'rubric.json', 'sha256': 'rubric'}})
    identity = {'source_sha256': 'aggregate-test'}
    state_path = tmp_path / 'budget.json'
    budget = {'path': str(state_path), 'bundle_id': 'aggregate-test', 'max_extra_attempts': 1}
    packets, packet_bindings, claims = [], [], []
    total_calls = 0
    for index in range(5):
        group = qids[index * 14:(index + 1) * 14] if index < 4 else qids[56:]
        packet = {'source_identity': identity, 'quota_shard': {'parent_path': str(parent_path)},
            'rows': [{'qid': q} for q in group], 'cases': {
                'baseline': {q: {'provider_body': None} for q in group},
                'current': {q: {'provider_body': {'contents': [{'parts': [{'text': 'q'}]}]}}
                    for q in group}},
            'schedule': [{'arm': arm, 'qid': q} for q in group for arm in ('baseline', 'current')],
            'max_provider_calls': len(group), 'prompt_chars': len(group),
            'retry_budget': budget, 'output_dir': str(tmp_path / f'live-{index}')}
        ppath = tmp_path / f'packet-{index}.json'
        write_json(ppath, packet)
        binding = {'path': str(ppath), 'sha256': sha256(ppath)}
        packet_bindings.append(binding)
        claims.append({'packet_sha256': binding['sha256'], 'pacific_date': f'2026-10-{index + 1:02d}'})
        summary_path = tmp_path / f'summary-{index}.json'
        arm_bindings, shard_calls, steps = {}, 0, []
        for row in packet['schedule']:
            steps.append({**row, 'valid': True})
        for arm in ('baseline', 'current'):
            raw_path = tmp_path / f'raw-{index}-{arm}.json'
            observations = [{'qid': q, 'interface_valid': True,
                'provider_model_version': 'gemini-3.8-flash-001' if arm == 'current' else None} for q in group]
            external = len(group) if arm == 'current' else 0
            write_json(raw_path, {'observations': observations, 'external_provider_calls': external})
            arm_bindings[arm] = {'path': str(raw_path), 'sha256': sha256(raw_path)}
            shard_calls += external
        total_calls += shard_calls
        write_json(summary_path, {'status': 'PENDING_INDEPENDENT_PAIRED_SOURCE_REVIEW',
            'packet_sha256': binding['sha256'], 'source_identity': identity, 'source_stable': True,
            'completed_steps': steps, 'arms': arm_bindings})
        (tmp_path / f'live-{index}').mkdir()
        write_json(tmp_path / f'live-{index}' / 'summary.json', read_json(summary_path))
        packets.append(packet)
    manifest_path = tmp_path / 'manifest.json'
    manifest = {'retry_budget': budget, 'source_identity': identity,
        'quota_window_policy': {'provider': 'gemini_free_tier'},
        'packets': packet_bindings}
    write_json(manifest_path, manifest)
    write_json(state_path, {'manifest_sha256': sha256(manifest_path), 'stopped': False,
        'provider_model_version': 'gemini-3.8-flash-001', 'attempts': [{}] * total_calls,
        'retry_reservations': [], 'quota_window_claims': claims})
    monkeypatch.setattr(primary, 'validate_packet', lambda _packet: None)
    monkeypatch.setattr(primary, 'verify_inputs', lambda _packet: None)
    report = primary.aggregate_quota_shards(manifest_path, sha256(manifest_path), tmp_path / 'aggregate.json')
    assert report['status'] == 'PENDING_INDEPENDENT_PAIRED_SOURCE_REVIEW'
    assert report['complete_pairs'] == 68 and report['external_provider_calls'] == 68


@pytest.mark.parametrize('failure', ['http_timeout_after_provider', 'provider_503'])
def test_paid_attempt_survives_missing_http_trace_without_retry(tmp_path, monkeypatch, failure):
    """Exercise the real serializer/worker with intercepted transport, no API I/O."""
    import io
    import json
    import sys
    from datetime import datetime
    from types import SimpleNamespace
    from urllib.error import HTTPError
    from scripts.benchmarks import product_primary_worker as worker
    from scripts.operations import serve
    from campusai import web
    from evaluation.common.release_artifacts import write_json

    frozen = read_json(primary.BASE / 'product-primary-egress-packet-20261009-v4.json')
    case = next(c for c in frozen['cases']['current'].values() if c['provider_body'])
    row = next(r for r in frozen['rows'] if r['qid'] == case['qid'])
    out = tmp_path / 'run'
    out.mkdir()
    setup = {**frozen, 'rows': [row], 'cases': {'current': {row['qid']: case}},
             'schedule': [{'arm': 'current', 'qid': row['qid']}], 'output_dir': str(out)}
    setup_path = tmp_path / 'setup.json'
    write_json(setup_path, setup)
    token = sha256(setup_path)
    write_json(out / 'summary.json', {'packet_sha256': token, 'active_step': 0})
    monkeypatch.setenv('GEMINI_API_KEY', 'offline-unit-key-only')
    monkeypatch.setitem(sys.modules, 'torch', SimpleNamespace(
        set_num_threads=lambda _: None, cuda=SimpleNamespace(is_available=lambda: True)))
    holder = {}

    def build():
        holder['client'] = serve.create_llm()
        service = SimpleNamespace(cache=worker.NoAnswerCache(), last_retrieval=[],
                                  retriever=SimpleNamespace(phase7_enabled=False, query_cache_size=0))
        return SimpleNamespace(query_service=service, close=lambda: None)

    monkeypatch.setattr(serve, 'build_application', build)
    monkeypatch.setattr(web, 'make_wsgi_app', lambda *_a, **_k: lambda *_: [])
    sent = []

    def intercepted(request, **_options):
        sent.append(json.loads(request.data))
        if failure == 'provider_503':
            raise HTTPError(request.full_url, 503, 'private provider detail', {}, io.BytesIO())
        return io.BytesIO(json.dumps({'candidates': [{'content': {'parts': [{'text': 'OK'}]},
                                                     'finishReason': 'STOP'}]}).encode())

    monkeypatch.setattr('urllib.request.urlopen', intercepted)

    class Connection:
        def __init__(self, *_a, **_k):
            pass

        def request(self, *_a, **_k):
            body = case['provider_body']
            holder['client'].generate(body['contents'][0]['parts'][0]['text'],
                                      generationConfig=body['generationConfig'])

        def getresponse(self):
            raise TimeoutError('private connection detail')

        def close(self):
            pass

    monkeypatch.setattr(worker.http.client, 'HTTPConnection', Connection)
    command = {'qid': row['qid'], 'step': 0, 'digest': token, 'last_provider_start': 0}
    monkeypatch.setattr(sys, 'stdin', io.StringIO(json.dumps(command) + '\n'))
    output = out / 'current.json'
    monkeypatch.setattr(sys, 'argv', [worker.__file__, 'live', 'current', str(setup_path), str(output)])
    assert worker.main() == 1
    report = read_json(output)
    assert report['status'] == 'FAILURE_STOPPED'
    assert len(report['observations']) == len(sent) == report['external_provider_calls'] == 1
    observation = report['observations'][0]
    assert observation['provider_transport_attempts'] == 1 and not observation['interface_valid']
    assert observation['trace'] is None and observation['http_ms'] >= 0
    assert datetime.fromisoformat(observation['observed_at']).utcoffset().total_seconds() == 0
    assert observation['provider_attempt']['http_status'] == (503 if failure == 'provider_503' else None)
    assert observation['calls'][0]['provider_status'] == ('failed' if failure == 'provider_503' else 'completed')
    assert observation['error_type'] == ('LLMProviderError' if failure == 'provider_503' else 'TimeoutError')
    assert sent == [case['provider_body']]
    assert 'private' not in output.read_text(encoding='utf8')
    with pytest.raises(FileExistsError):
        worker.main()


@pytest.mark.parametrize('fail_step', [None, 0])
def test_paired_parent_does_not_read_an_idle_workers_empty_output(packet, tmp_path, monkeypatch, fail_step):
    """Both children announce readiness before either has an HTTP observation."""
    import json
    from evaluation.common.release_artifacts import write_json

    packet['output_dir'] = str(tmp_path / 'paired')
    path = tmp_path / 'packet.json'
    write_json(path, packet)
    monkeypatch.setattr(primary, 'verify_inputs', lambda _: None)
    monkeypatch.setattr(primary, 'source_identity', lambda _: packet['source_identity'])
    workers = []

    class Lines:
        def __init__(self, ready):
            self.pending = [ready]

        def __iter__(self):
            return self

        def __next__(self):
            if not self.pending:
                raise StopIteration
            return 'PRIMARY_RESULT ' + json.dumps(self.pending.pop(0)) + '\n'

    class Child:
        def __init__(self, argv, **_options):
            self.arm, self.output = argv[3], Path(argv[-1])
            self.output.write_text('', encoding='utf8')
            self.stdout = Lines({'ready': True, 'arm': self.arm})
            self.stdin = self
            self.returncode = None
            self.count = 0
            workers.append(self)

        def write(self, line):
            command = json.loads(line)
            if command.get('stop'):
                self.returncode = 0
                return
            case = packet['cases'][self.arm][command['qid']]
            self.count += int(bool(case['provider_body']))
            write_json(self.output, {'external_provider_calls': self.count})
            self.stdout.pending.append({'qid': command['qid'], 'valid': command['step'] != fail_step,
                'last_provider_start': 0, 'external_provider_calls': self.count})

        def flush(self):
            pass

        def poll(self):
            return self.returncode

        def wait(self, **_options):
            return self.returncode

    monkeypatch.setattr(primary.subprocess, 'Popen', Child)
    monkeypatch.setattr(primary.time, 'sleep', lambda _: None)
    report = primary.collect(path, sha256(path))
    assert report['status'] == ('PENDING_INDEPENDENT_PAIRED_SOURCE_REVIEW' if fail_step is None
                                else 'PROVIDER_OR_INTERFACE_FAILURE_STOPPED')
    assert len(report['completed_steps']) == (136 if fail_step is None else fail_step + 1)
    assert report['external_provider_calls'] == (packet['max_provider_calls'] if fail_step is None else 0)
    assert len(workers) == 2 and all(c.returncode == 0 for c in workers)
    with pytest.raises(FileExistsError):
        primary.collect(path, sha256(path))


@pytest.mark.parametrize('sequence,expected_attempts,valid', [
    ([503, 200], 2, True), ([503, 503], 2, False), ([429], 1, False),
])
def test_worker_bounded_retry_retains_failures_and_full_http_time(tmp_path, monkeypatch, sequence, expected_attempts, valid):
    import io
    import json
    import sys
    from types import SimpleNamespace
    from urllib.error import HTTPError
    from scripts.benchmarks import product_primary_worker as worker, product_retry
    from scripts.operations import serve
    from campusai import web
    from evaluation.common.release_artifacts import write_json, source_identity

    frozen = read_json(primary.BASE / 'product-primary-egress-packet-20261009-v7.json')
    case = next(c for c in frozen['cases']['current'].values() if c['provider_body'])
    row = next(r for r in frozen['rows'] if r['qid'] == case['qid'])
    out = tmp_path / 'run'; out.mkdir()
    binding = {'path': str(out / 'budget.json'), 'bundle_id': 'worker-test', 'max_extra_attempts': 3}
    setup = {**frozen, 'source_identity': source_identity(primary.ROOT), 'rows': [row],
        'cases': {'current': {row['qid']: case}}, 'schedule': [{'arm': 'current', 'qid': row['qid']}],
        'max_provider_calls': 1,
        'prompt_chars': len(case['provider_body']['contents'][0]['parts'][0]['text']),
        'output_dir': str(out), 'max_retries': 1, 'retry_only_http_status': 503, 'retry_budget': binding,
        'llm_config': {**frozen['llm_config'], 'max_retries': 1, 'retry_only_503': True}}
    path = tmp_path / 'packet.json'; write_json(path, setup)
    packet_bindings = [{'path': str(path), 'sha256': sha256(path)}]
    for count in (54, 2):
        other = tmp_path / f'packet-{count}.json'
        body = {'contents': [{'parts': [{'text': 'q'}]}]}
        write_json(other, {**setup, 'schedule': [], 'cases': {},
            'max_provider_calls': count, 'prompt_chars': count,
            'provider_bodies': [body] * count})
        packet_bindings.append({'path': str(other), 'sha256': sha256(other)})
    manifest = tmp_path / 'manifest.json'
    total_chars = setup['prompt_chars'] + 56
    max_retry_chars = len(case['provider_body']['contents'][0]['parts'][0]['text']) + 2
    write_json(manifest, {'retry_budget': binding, 'source_identity': setup['source_identity'],
        'packets': packet_bindings, 'maximum_external_post_requests': 60,
        'max_retries': 1, 'maximum_new_prompt_characters': total_chars + max_retry_chars,
        'maximum_total_output_tokens': 60 * 4096})
    product_retry.initialize(manifest, sha256(manifest))
    write_json(out / 'summary.json', {'packet_sha256': sha256(path), 'active_step': 0})
    now = [1000.0]
    monkeypatch.setattr(worker.time, 'time', lambda: now[0])
    monkeypatch.setattr(worker.time, 'perf_counter', lambda: now[0])
    monkeypatch.setattr(worker.time, 'sleep', lambda delay: now.__setitem__(0, now[0] + delay))
    monkeypatch.setattr('random.random', lambda: 0)
    monkeypatch.setenv('GEMINI_API_KEY', 'offline-only')
    monkeypatch.setitem(sys.modules, 'torch', SimpleNamespace(set_num_threads=lambda _: None,
        cuda=SimpleNamespace(is_available=lambda: True)))
    holder, sent = {}, []
    def build():
        holder['client'] = serve.create_llm()
        service = SimpleNamespace(cache=worker.NoAnswerCache(),
            last_retrieval=[SimpleNamespace(to_dict=lambda e=e: e) for e in case['evidence']],
            retriever=SimpleNamespace(phase7_enabled=False, query_cache_size=0))
        return SimpleNamespace(query_service=service, close=lambda: None)
    monkeypatch.setattr(serve, 'build_application', build)
    def web_app(*args, telemetry_hook, **kwargs):
        holder['trace'] = telemetry_hook
        return lambda *_: []
    monkeypatch.setattr(web, 'make_wsgi_app', web_app)
    def transport(request, **kwargs):
        sent.append(json.loads(request.data))
        status = sequence[len(sent) - 1]
        if status != 200:
            raise HTTPError(request.full_url, status, 'synthetic', {}, io.BytesIO())
        return io.BytesIO(b'{"modelVersion":"gemini-3.8-flash-001","candidates":[{"content":{"parts":[{"text":"OK"}]}}]}')
    monkeypatch.setattr('urllib.request.urlopen', transport)
    class Connection:
        def __init__(self, *args, timeout, **kwargs):
            assert timeout == 195
        def request(self, *args, **kwargs):
            body = case['provider_body']
            holder['client'].generate(body['contents'][0]['parts'][0]['text'], generationConfig=body['generationConfig'])
            holder['trace']({})
        def getresponse(self):
            return SimpleNamespace(status=200, read=lambda: b'{"ok":true,"answer":{"answer":"OK"}}')
        def close(self): pass
    monkeypatch.setattr(worker.http.client, 'HTTPConnection', Connection)
    monkeypatch.setattr(sys, 'stdin', io.StringIO(json.dumps({'qid': row['qid'], 'step': 0,
        'digest': sha256(path), 'last_provider_start': 0}) + '\n'))
    output = out / 'current.json'
    monkeypatch.setattr(sys, 'argv', [worker.__file__, 'live', 'current', str(path), str(output)])
    assert worker.main() == (0 if valid else 1)
    report = read_json(output); observation = report['observations'][0]
    assert len(sent) == report['external_provider_calls'] == expected_attempts
    assert sent == [case['provider_body']] * expected_attempts
    assert observation['interface_valid'] == valid
    assert len(observation['provider_attempts']) == expected_attempts
    assert observation['provider_attempts'][0]['http_status'] == sequence[0]
    assert observation['http_ms'] >= (30000 if expected_attempts == 2 else 0)
    assert read_json(out / 'budget.json')['stopped'] != valid
