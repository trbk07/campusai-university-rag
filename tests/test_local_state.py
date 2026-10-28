"""Isolated local paths, persistent provider state, and read-only preflight."""
import json
from pathlib import Path
import socket
import sys
from types import SimpleNamespace

import pytest

from scripts.operations import local, local_state


def configured(tmp_path):
    root = tmp_path / 'read only app'
    root.mkdir()
    env = {'LOCALAPPDATA': str(tmp_path / 'user profile')}
    local_state.configure_paths(root, env)
    return root, env


def test_first_install_paths_are_outside_source_and_configuration_does_not_write(tmp_path):
    root, env = configured(tmp_path)
    assert not list(root.iterdir())
    assert not Path(env['CAMPUSAI_STATE_ROOT']).exists()
    assert env['HF_HUB_OFFLINE'] == '1'
    for key in local_state.STATE_PATHS:
        assert Path(env[key]).is_relative_to(Path(env['CAMPUSAI_STATE_ROOT']))
        assert not Path(env[key]).is_relative_to(root)
    local_state.prepare_state(env)
    assert all(p.is_dir() for p in local_state.writable_directories(env))
    assert not list(root.iterdir())
    assert not any(p.is_file() for p in Path(env['CAMPUSAI_STATE_ROOT']).rglob('*'))


def test_old_state_requires_explicit_choice_and_is_never_moved(tmp_path):
    root = tmp_path / 'old install'
    data = root / 'data/store'
    data.mkdir(parents=True)
    old = data / 'registry.json'
    old.write_text('owner data')
    with pytest.raises(ValueError, match='CAMPUSAI_STATE_ROOT'):
        local_state.configure_paths(root, {})
    env = {'CAMPUSAI_STATE_ROOT': str(root)}
    local_state.configure_paths(root, env)
    assert Path(env['CAMPUSAI_STORE_DIR']) == data
    assert old.read_text() == 'owner data'


def test_explicit_overrides_and_in_memory_cache_are_preserved(tmp_path):
    env = {'CAMPUSAI_STATE_ROOT': str(tmp_path / 'new state'),
           'CAMPUSAI_STORE_DIR': str(tmp_path / 'existing store'),
           'CAMPUSAI_JOB_DB': 'custom/jobs.sqlite3', 'CAMPUSAI_RAG_CACHE_PATH': ':memory:'}
    local_state.configure_paths(tmp_path, env)
    assert env['CAMPUSAI_STORE_DIR'] == str(tmp_path / 'existing store')
    assert env['CAMPUSAI_JOB_DB'] == str(tmp_path / 'new state/custom/jobs.sqlite3')
    assert env['CAMPUSAI_RAG_CACHE_PATH'] == ':memory:'
    with pytest.raises(ValueError, match='tuyệt đối'):
        local_state.configure_paths(tmp_path, {'CAMPUSAI_STATE_ROOT':'relative'})


def test_preflight_detects_missing_model_full_disk_busy_port_and_does_not_write(tmp_path, monkeypatch):
    root, env = configured(tmp_path)
    before = sorted(str(p) for p in tmp_path.rglob('*'))
    monkeypatch.setattr(local_state.shutil, 'disk_usage', lambda _: SimpleNamespace(free=0))
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        listener.listen()
        report = local_state.inspect_local(env, port=listener.getsockname()[1])
    codes = {c['code'] for c in report['checks']}
    assert {'insufficient_disk_space','port_in_use','dense_model_missing_run_setup'} <= codes
    assert report['status'] == 'NOT_READY'
    assert report['provider_calls'] == report['filesystem_writes'] == 0
    assert sorted(str(p) for p in tmp_path.rglob('*')) == before


def test_unwritable_state_fails_read_check_and_actual_start(tmp_path, monkeypatch):
    _, env = configured(tmp_path)
    monkeypatch.setattr(local_state.os, 'access', lambda *_: False)
    report = local_state.inspect_local(env, port=0)
    assert 'state_not_writable' in {c['code'] for c in report['checks']}
    def denied(*_a, **_kw):
        raise PermissionError('denied')
    monkeypatch.setattr(local_state.tempfile, 'TemporaryFile', denied)
    with pytest.raises(PermissionError):
        local_state.prepare_state(env)


def test_cli_check_missing_key_does_not_create_state_or_leak_key(tmp_path, monkeypatch, capsys):
    root = tmp_path / 'app'
    (root / 'configs').mkdir(parents=True)
    (root / 'configs/free_llm.yaml').write_text('llm: {provider: gemini, model: fixture}')
    monkeypatch.setattr(local, 'ROOT', root)
    monkeypatch.setattr(local.os, 'environ', {'LOCALAPPDATA':str(tmp_path/'profile')})
    monkeypatch.setattr(local, 'build_application', lambda: pytest.fail('no app in check'))
    assert local.main(['--check']) == 1
    report = json.loads(capsys.readouterr().out)
    assert 'GEMINI_API_KEY' in report['error']
    assert not (tmp_path/'profile').exists()


def test_provider_files_rebase_under_state_root_and_keep_policy(tmp_path):
    from campusai.llm.factory import create_llm
    profile = tmp_path / 'profile.json'
    profile.write_text(json.dumps({'llm':{
        'provider':'gemini','model':'fixture','max_retries':0,
        'cache_path':'data/cache/provider.sqlite3',
        'overload_circuit_path':'data/operations/health.sqlite3',
        'requests_per_minute':10, 'generation_config':{'maxOutputTokens':1536},
        'quota':{'state_path':'data/operations/quota.sqlite3',
                 'scope':'same-owner','max_in_flight':1,'max_wait_seconds':6}}}))
    state = tmp_path / 'user data'
    client = create_llm(profile, {'GEMINI_API_KEY':'fixture-only'}, state_root=state)
    try:
        assert (state/'data/cache/provider.sqlite3').is_file()
        assert (state/'data/operations/quota.sqlite3').is_file()
        assert (state/'data/operations/health.sqlite3').is_file()
        assert client.max_retries == 0
        reservation = client.quota_governor.reserve(100, 20, lease_seconds=30)
        client.quota_governor.finish(reservation)
        generation = client.overload_circuit.acquire(30)
        client.overload_circuit.failed(generation, overloaded=True)
    finally:
        client.close()
    reopened = create_llm(profile, {'GEMINI_API_KEY':'fixture-only'}, state_root=state)
    try:
        assert reopened.quota_governor.snapshot()['reserved_attempts_last_minute'] == 1
        assert reopened.overload_circuit.remaining_seconds() > 0
        assert reopened.quota_governor.scope == 'same-owner'
        assert reopened.quota_governor.max_wait_seconds == 6
    finally:
        reopened.close()


def test_gpu_falls_back_to_cpu_without_claiming_a_measured_slo(tmp_path, monkeypatch):
    _, env = configured(tmp_path)
    monkeypatch.setitem(sys.modules, 'torch', SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False)))
    env['CAMPUSAI_DEVICE'] = 'cuda'
    report = local_state.inspect_local(env, port=0)
    assert report['device'] == 'cpu'
    assert report['fallback'] == 'cuda_unavailable_using_cpu'
    assert env['CAMPUSAI_DEVICE'] == 'cuda'  # check never mutates the configuration
    env['CAMPUSAI_DEVICE'] = 'invalid'
    assert any(c['code'] == 'unsupported_device' for c in local_state.inspect_local(env, port=0)['checks'])


def test_explicit_ocr_missing_assets_are_reported_without_loading_a_model(tmp_path):
    _, env = configured(tmp_path)
    env['CAMPUSAI_OCR_BACKEND'] = 'vietocr'
    report = local_state.inspect_local(env, port=0)
    assert any(c['code'] == 'ocr_assets_missing_or_checksum_mismatch' for c in report['checks'])


def test_launcher_handles_other_service_on_port_without_traceback(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(local, 'ROOT', tmp_path)
    def occupied():
        raise ValueError('other service')
    monkeypatch.setattr(local, 'running_app', occupied)
    assert local.main([]) == 1
    assert 'port_in_use' in capsys.readouterr().out


def test_old_cooldown_cannot_silently_reset_on_upgrade(tmp_path):
    (tmp_path/'configs').mkdir()
    (tmp_path/'configs/free_llm.yaml').write_text('llm:\n  provider: gemini\n  model: fixture\n'
        '  overload_circuit_path: data/operations/gemini-provider-health.sqlite3\n')
    (tmp_path/'.tmp').mkdir()
    old = tmp_path/'.tmp/gemini-provider-health.sqlite3'
    old.write_bytes(b'preserve old cooldown')
    with pytest.raises(local.LocalSetupError, match='không reset cooldown'):
        local.configure_local(tmp_path, {'CAMPUSAI_STATE_ROOT':str(tmp_path),'GEMINI_API_KEY':'fake'})
    assert old.read_bytes() == b'preserve old cooldown'
