"""Scope preservation must bind the historical index, independent of query gold."""
import json
from pathlib import Path

import pytest

from evaluation.benchmarks.dev_inheritance import file_bindings
from evaluation.common.release_artifacts import sha256
from scripts.benchmarks.qualify_phase6_policy_on_successor_dev import qualification_scope


def index(tmp_path: Path, name: str, documents: list[str]):
    root = tmp_path / name
    root.mkdir()
    (root / 'manifest.json').write_text(json.dumps({'documents': documents}))
    for doc in documents:
        (root / doc).mkdir()
        (root / doc / 'bm25.json').write_text('fixed source ' + doc)
    return root


def test_scope_is_original_corpus_without_removing_new_physical_documents(tmp_path):
    old = index(tmp_path, 'old', ['original'])
    expanded = index(tmp_path, 'expanded', ['original', 'new'])
    before = file_bindings(expanded)
    docs, receipt = qualification_scope(expanded, {'index_sha256': sha256(old / 'manifest.json')}, old)
    assert docs == ['original']
    assert receipt['physical_documents_preserved'] is True
    assert file_bindings(expanded) == before


def test_full_corpus_remains_default(tmp_path):
    expanded = index(tmp_path, 'expanded', ['original', 'new'])
    assert qualification_scope(expanded, {}, None) == (['original', 'new'], None)


def test_unrelated_scope_is_rejected(tmp_path):
    old = index(tmp_path, 'old', ['original'])
    expanded = index(tmp_path, 'expanded', ['original', 'new'])
    with pytest.raises(ValueError, match='historical calibration index'):
        qualification_scope(expanded, {'index_sha256': 'other'}, old)


def test_changed_historical_source_bytes_are_rejected(tmp_path):
    old = index(tmp_path, 'old', ['original'])
    expanded = index(tmp_path, 'expanded', ['original', 'new'])
    (expanded / 'original/bm25.json').write_text('changed')
    with pytest.raises(ValueError, match='historical document bytes changed'):
        qualification_scope(expanded, {'index_sha256': sha256(old / 'manifest.json')}, old)
