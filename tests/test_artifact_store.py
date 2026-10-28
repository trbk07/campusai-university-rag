"""External evidence must retain byte identity and fail closed on corruption."""
import gzip
import hashlib
import json
from pathlib import Path

import pytest

from evaluation.common import artifact_store as store
from evaluation.common.release_artifacts import read_json, sha256
from evaluation.reranker.supplemental_gates import raw_reference


def test_repository_catalog_keys_are_safe_and_match_logical_identity():
    for key, record in store.entries().items():
        assert store.safe_relative(key).as_posix() == key
        assert record.get('identity', key) == key


@pytest.fixture
def archived(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    content = b'{"observations": [1, 2], "measured": true}\r\n'
    digest = hashlib.sha256(content).hexdigest()
    blob = external / "objects" / (digest + ".gz")
    blob.parent.mkdir()
    blob.write_bytes(gzip.compress(content, mtime=0))
    logical = repo / "evaluation/results/cycle/raw/observations.json"
    key = logical.relative_to(repo).as_posix()
    record = {"sha256": digest, "bytes": len(content), "encoding": "gzip",
              "local_or_external_uri": blob.relative_to(external).as_posix(),
              "storage_sha256": store.file_sha256(blob), "storage_bytes": blob.stat().st_size}
    catalog = repo / "manifest.json"
    catalog.write_text(json.dumps({"schema_version": 1, "artifacts": {key: record}}), encoding="utf8")
    monkeypatch.setattr(store, "ROOT", repo)
    monkeypatch.setattr(store, "MANIFEST", catalog)
    monkeypatch.setenv("CAMPUSAI_ARTIFACT_ROOT", str(external))
    return logical, blob, content, digest, record, catalog


def test_external_raw_works_with_legacy_validator_reference_and_preserves_crlf(archived):
    logical, _, content, digest, *_ = archived
    target = raw_reference(logical.parent.parent, {"path": "raw/observations.json", "sha256": digest})
    assert target.read_bytes() == content
    assert sha256(logical) == digest
    assert read_json(logical)["observations"] == [1, 2]
    assert not logical.exists()
    assert store.artifact_paths(logical.parent, "*.json") == [logical]


@pytest.mark.parametrize('tampered', [False, True])
def test_live_runtime_reads_bound_preflight_and_rejects_corruption(archived, tampered):
    from evaluation.phase8.measure_live_runtime import read
    logical, blob, content, *_ = archived
    if tampered:
        blob.write_bytes(gzip.compress(b'{"measured": false}', mtime=0))
        with pytest.raises(ValueError):
            read(logical)
    else:
        assert read(logical) == json.loads(content)
    assert not logical.exists()


@pytest.mark.parametrize("mutation", ["missing", "blob", "cache", "wrong_raw_hash", "wrong_size", "traversal"])
def test_missing_or_corrupt_external_raw_cannot_pass(archived, mutation):
    logical, blob, _, digest, record, catalog = archived
    cache = store.resolve_artifact(logical)
    if mutation == "missing":
        blob.unlink()
    elif mutation == "blob":
        blob.write_bytes(b"corrupt")
    elif mutation == "cache":
        cache.write_bytes(b"corrupt")
    else:
        if mutation == "wrong_raw_hash":
            record["sha256"] = "0" * 64
        elif mutation == "wrong_size":
            record["bytes"] += 1
        else:
            record["local_or_external_uri"] = "../outside.gz"
        data = json.loads(catalog.read_text())
        data["artifacts"][logical.relative_to(store.ROOT).as_posix()] = record
        catalog.write_text(json.dumps(data))
    with pytest.raises((OSError, ValueError)):
        raw_reference(logical.parent.parent, {"path": "raw/observations.json", "sha256": digest})


def test_summary_cannot_substitute_for_missing_raw(archived):
    logical, blob, *_ = archived
    blob.unlink()
    logical.parent.mkdir(parents=True)
    logical.with_name("observations.storage-summary.json").write_text('{"status":"pass"}')
    with pytest.raises(FileNotFoundError):
        read_json(logical)


def test_mismatched_report_hash_is_rejected_even_with_intact_store(archived):
    logical, *_ = archived
    with pytest.raises(ValueError, match="changed raw"):
        raw_reference(logical.parent.parent, {"path": "raw/observations.json", "sha256": "f" * 64})


def test_unregistered_file_is_never_replaced_with_empty_evidence(archived):
    logical, *_ = archived
    with pytest.raises(FileNotFoundError):
        read_json(logical.with_name("missing.json"))
