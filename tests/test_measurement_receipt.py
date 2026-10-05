from pathlib import Path
from types import SimpleNamespace
import subprocess

import pytest

from evaluation.common import measurement_receipt as module
from evaluation.common.release_artifacts import read_json, sha256, write_json


def setup(tmp_path, monkeypatch):
    identity = {'commit': 'fixture', 'source_sha256': 'a'*64, 'runtime_sha256': 'b'*64}
    monkeypatch.setattr(module, 'source_identity', lambda root: dict(identity))
    return {'env': {'GEMINI_API_KEY': 'SECRET_FIXTURE'}, 'results_dir': tmp_path,
            'cycle_id': 'fixture-cycle', 'stage': 'fixture-stage', 'root': tmp_path}, identity


def receipts(tmp_path):
    return [read_json(p) for p in (tmp_path/'raw/measurement_receipts').glob('*.json')]


def test_receipt_binds_actual_artifacts_times_command_and_public_inputs(tmp_path, monkeypatch):
    args, identity = setup(tmp_path, monkeypatch)
    config = tmp_path/'input.yaml'
    config.write_text('model: fixture', encoding='utf-8')
    secret = tmp_path/'gemini.yaml'
    secret.write_text('api_key: SECRET_FIXTURE', encoding='utf-8')
    def run(command, **kwargs):
        assert kwargs['env']['GEMINI_API_KEY'] == 'SECRET_FIXTURE'
        write_json(tmp_path/'output.json', {'status': 'conditional'})
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(module.subprocess, 'run', run)
    command = ['python', '-m', 'fixture', '--input', str(config), '--key-file', str(secret)]
    assert module.run_recorded(command, **args).returncode == 0
    receipt, = receipts(tmp_path)
    assert receipt['command'] == command and receipt['source_before'] == identity
    assert receipt['inputs'] == [{'path': config.as_posix(), 'sha256': sha256(config)}]
    assert receipt['changed_artifacts'] == [{'path': 'output.json', 'sha256': sha256(tmp_path/'output.json')}]
    assert receipt['quality_gate_status'] == 'not_assessed_by_receipt'
    from datetime import datetime
    assert datetime.fromisoformat(receipt['started_at']).tzinfo is not None
    assert datetime.fromisoformat(receipt['ended_at']) >= datetime.fromisoformat(receipt['started_at'])
    assert 'SECRET_FIXTURE' not in str(receipt)


def test_failed_process_retains_receipt_and_original_exit_code(tmp_path, monkeypatch):
    args, _ = setup(tmp_path, monkeypatch)
    monkeypatch.setattr(module.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=7))
    assert module.run_recorded(['python', '-m', 'fixture'], **args).returncode == 7
    receipt, = receipts(tmp_path)
    assert receipt['execution_status'] == 'fail' and receipt['exit_code'] == 7


def test_oserror_retains_sanitized_type_without_environment_or_error_text(tmp_path, monkeypatch):
    args, _ = setup(tmp_path, monkeypatch)
    def fail(*a, **k):
        raise OSError('SECRET_FIXTURE')
    monkeypatch.setattr(module.subprocess, 'run', fail)
    with pytest.raises(OSError):
        module.run_recorded(['python', '-m', 'fixture'], **args)
    receipt, = receipts(tmp_path)
    assert receipt['error_type'] == 'OSError' and receipt['exit_code'] is None
    assert 'SECRET_FIXTURE' not in str(receipt)


def test_source_mutation_fails_even_when_child_returns_zero(tmp_path, monkeypatch):
    args, identity = setup(tmp_path, monkeypatch)
    def mutate(*a, **k):
        identity['source_sha256'] = 'c'*64
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(module.subprocess, 'run', mutate)
    with pytest.raises(ValueError, match='source changed'):
        module.run_recorded(['python', '-m', 'fixture'], **args)
    receipt, = receipts(tmp_path)
    assert receipt['execution_status'] == 'fail' and receipt['source_stable'] is False


def test_receipt_records_removed_artifacts_and_does_not_hash_itself(tmp_path, monkeypatch):
    args, _ = setup(tmp_path, monkeypatch)
    old = tmp_path/'old.json'
    write_json(old, {'value': 1})
    def remove(*a, **k):
        old.unlink()
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(module.subprocess, 'run', remove)
    module.run_recorded(['python', '-m', 'fixture'], **args)
    receipt, = receipts(tmp_path)
    assert receipt['removed_artifacts'] == ['old.json'] and receipt['changed_artifacts'] == []


def test_secret_command_is_rejected_before_any_execution(tmp_path, monkeypatch):
    args, _ = setup(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match='credentials'):
        module.run_recorded(['python', '--api-key', 'SECRET_FIXTURE'], **args)
    assert receipts(tmp_path) == []
