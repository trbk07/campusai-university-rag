"""Historical source and replay inputs cannot silently change or omit bytes."""
from copy import deepcopy
from pathlib import Path
import warnings
import zipfile
import pytest

from scripts.benchmarks import measure_frozen_phase6_dev as frozen
from scripts.benchmarks.measure_frozen_phase6_successor_dev import validate_inputs


def archive(tmp_path, monkeypatch, entries, *, comment=None):
    monkeypatch.setattr(frozen, 'ROOT', tmp_path)
    original = {'src/campusai/a.py': b'original\n', 'src/campusai/b.py': b'unchanged\n'}
    def git_bytes(command, **_options):
        if command[1] == 'ls-tree':
            return '\n'.join(original).encode()
        return original[command[-1].split(':', 1)[1]]
    monkeypatch.setattr(frozen.subprocess, 'check_output', git_bytes)
    path = tmp_path / 'source.zip'
    with zipfile.ZipFile(path, 'w') as stream:
        stream.comment = (frozen.COMMIT if comment is None else comment).encode()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            for name, value in entries:
                stream.writestr(name, value)
    return path, tmp_path / '.local_artifacts/experiment_runs/frozen'


def test_exact_source_is_complete_verified_and_repeatable(tmp_path, monkeypatch):
    path, target = archive(tmp_path, monkeypatch, [('src/campusai/a.py', b'original\n'), ('src/campusai/b.py', b'unchanged\n')])
    hashes = frozen.source_tree(path, target)
    assert len(hashes) == 2 and frozen.source_tree(path, target) == hashes
    (target / 'src/campusai/b.py').write_bytes(b'tampered\n')
    with pytest.raises(ValueError, match='isolated source changed'):
        frozen.source_tree(path, target)


@pytest.mark.parametrize('entries', [
    [('src/campusai/a.py', b'original\n')],
    [('src/campusai/a.py', b'original\n'), ('src/campusai/a.py', b'original\n')],
    [('src/campusai/a.py', b'original\n'), ('src/campusai/b.py', b'unchanged\r\n')],
])
def test_omitted_duplicate_or_eol_changed_source_rejected_before_any_extraction(tmp_path, monkeypatch, entries):
    path, target = archive(tmp_path, monkeypatch, entries)
    with pytest.raises(ValueError):
        frozen.source_tree(path, target)
    assert not target.exists()


def test_wrong_frozen_commit_is_rejected(tmp_path, monkeypatch):
    path, target = archive(tmp_path, monkeypatch, [], comment='unrelated')
    with pytest.raises(ValueError, match='actual frozen Phase 6 commit'):
        frozen.source_tree(path, target)


def inputs():
    rows = [{'qid': 'dev-1', 'split': 'dev', 'release_eligible': False, 'doc_ids': ['doc']}]
    raw = {'dev_sha256': 'parent', 'index_sha256': 'index', 'f0_signoff_sha256': 'f0',
           'phase6_calibration_sha256': 'calibration', 'test_used': False, 'holdout_used': False,
           'measurements_real': True, 'source_identity_before': {}, 'source_identity_after': {},
           'observations': [{'qid': 'dev-1', 'actual_request': {'query': 'resolved user query', 'doc_ids': ['doc'], 'filters': {}}}]}
    report = {**deepcopy(raw), 'source_stable': True}
    return rows, {'parent_dev_sha256': 'parent'}, raw, report


def test_measured_context_request_is_preserved_without_using_gold():
    rows, revision, raw, report = inputs()
    assert validate_inputs(rows, revision, raw, report, 'index', 'f0')['dev-1']['query'] == 'resolved user query'


@pytest.mark.parametrize('mutation', ['heldout', 'duplicate', 'scope', 'raw_hash_binding', 'request_gold', 'source_drift'])
def test_frozen_successor_measurement_rejects_unpaired_or_changed_inputs(mutation):
    rows, revision, raw, report = inputs()
    if mutation == 'heldout': rows[0]['split'] = 'holdout'
    if mutation == 'duplicate': raw['observations'] *= 2
    if mutation == 'scope': raw['observations'][0]['actual_request']['doc_ids'] = ['other']
    if mutation == 'raw_hash_binding': raw['index_sha256'] = 'other'
    if mutation == 'request_gold': raw['observations'][0]['actual_request']['gold_evidence'] = []
    if mutation == 'source_drift': raw['source_identity_after'] = {'changed': True}
    with pytest.raises(ValueError):
        validate_inputs(rows, revision, raw, report, 'index', 'f0')
