import json
from pathlib import Path
import shutil

import pytest

from evaluation.retrieval import validate_hybrid_release as release


@pytest.fixture
def evidence_root(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[1]
    for relative in release.REQUIRED:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / relative, target)
    fingerprint = tmp_path / 'evaluation/results/hybrid_release_manifest.json'
    shutil.copyfile(source / fingerprint.relative_to(tmp_path), fingerprint)
    monkeypatch.setattr(release, 'ROOT', tmp_path)
    monkeypatch.setattr(release.subprocess, 'check_call', lambda *_args, **_kwargs: None)
    return tmp_path


def test_historical_fingerprint_still_rejects_changed_paths(evidence_root):
    errors, _summary = release.validate()
    assert any(error.startswith('release_manifest_checksum:') for error in errors)
    errors, _summary = release.validate(verify_manifest=False)
    assert errors == []


def test_fingerprint_renewal_binds_current_paths_after_artifact_validation(evidence_root, monkeypatch):
    monkeypatch.setattr(release, '_git', lambda *args: '' if args[0] == 'status' else 'a' * 40)
    index_dir = evidence_root / 'index'
    index_dir.mkdir()
    (index_dir / 'manifest.json').write_text('{}', encoding='utf-8')
    output = evidence_root / 'renewed_manifest.json'
    manifest = release.write_manifest(output, index_dir)
    assert manifest['working_tree'] is False
    assert set(manifest['artifacts']) == set(release.REQUIRED)
    assert all(release._sha(evidence_root / name) == checksum
               for name, checksum in manifest['artifacts'].items())


def test_fingerprint_renewal_cannot_bypass_failed_quality_gates(evidence_root):
    path = evidence_root / 'evaluation/results/hybrid_holdout_report.json'
    report = json.loads(path.read_text(encoding='utf-8'))
    report['primary_test']['quality']['answerable_recall']['5'] = 0
    path.write_text(json.dumps(report), encoding='utf-8')
    output = evidence_root / 'renewed_manifest.json'
    with pytest.raises(SystemExit, match='cannot fingerprint failing release:.*test_recall_at_5'):
        release.write_manifest(output, evidence_root / 'index')
    assert not output.exists()
