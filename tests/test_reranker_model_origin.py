"""A hash-bound snapshot must also retain its actual upstream name/revision."""
import hashlib
import json

import pytest

from evaluation.common.release_artifacts import sha256, write_json
from evaluation.reranker.model_origin import verified_model_origin


@pytest.fixture
def snapshot(tmp_path):
    revision = "a" * 40
    model_dir = tmp_path / revision
    model_dir.mkdir()
    model_file = model_dir / "model.safetensors"
    model_file.write_bytes(b"test-only-weight-bytes")
    digest = sha256(model_file)
    entry = {"rfilename": model_file.name, "size": model_file.stat().st_size, "blobId": "blob-id",
             "lfs": {"sha256": digest, "size": model_file.stat().st_size}}
    metadata_path = tmp_path / "metadata.json"
    write_json(metadata_path, {"id": "organization/model", "sha": revision, "siblings": [entry]})
    receipt_path = tmp_path / "receipt.json"
    receipt = {"status": "PASS_PINNED_PUBLIC_FILE_HASHES", "model_name": "organization/model",
               "revision": revision, "metadata_path": str(metadata_path), "metadata_sha256": sha256(metadata_path),
               "metadata_url": f"https://huggingface.co/api/models/organization/model/revision/{revision}?blobs=true",
               "files": {model_file.name: {"sha256": digest, "bytes": entry["size"],
                                          "upstream_blob": entry["blobId"], "upstream_lfs": entry["lfs"]}}}
    write_json(receipt_path, receipt)
    return model_dir, receipt_path, receipt


def test_verifies_actual_upstream_name_and_weights(snapshot):
    model_dir, receipt_path, _ = snapshot
    result = verified_model_origin(model_dir, receipt_path)
    assert result["model_name"] == "organization/model"
    assert result["upstream_files_verified"] is True


def test_wrong_model_label_cannot_reuse_weight_manifest(snapshot):
    model_dir, receipt_path, receipt = snapshot
    receipt["model_name"] = "another/model"
    write_json(receipt_path, receipt)
    with pytest.raises(ValueError, match="model name/revision"):
        verified_model_origin(model_dir, receipt_path)


def test_changed_weight_bytes_rejected(snapshot):
    model_dir, receipt_path, _ = snapshot
    (model_dir / "model.safetensors").write_bytes(b"corrupted-weight-bytes")
    with pytest.raises(ValueError, match="model file"):
        verified_model_origin(model_dir, receipt_path)


def test_extra_unverified_model_file_rejected(snapshot):
    model_dir, receipt_path, _ = snapshot
    (model_dir / "config.json").write_text("{}", encoding="utf8")
    with pytest.raises(ValueError, match="physical model files"):
        verified_model_origin(model_dir, receipt_path)


def test_git_blob_bytes_checked_independently(snapshot):
    model_dir, receipt_path, receipt = snapshot
    data = (model_dir / "model.safetensors").read_bytes()
    info = {"rfilename": "model.safetensors", "size": len(data),
            "blobId": hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()}
    metadata_path = __import__("pathlib").Path(receipt["metadata_path"])
    write_json(metadata_path, {"id": receipt["model_name"], "sha": receipt["revision"], "siblings": [info]})
    receipt["metadata_sha256"] = sha256(metadata_path)
    receipt["files"]["model.safetensors"].update(upstream_blob=info["blobId"], upstream_lfs=None)
    write_json(receipt_path, receipt)
    assert verified_model_origin(model_dir, receipt_path)["upstream_files_verified"]
    info["blobId"] = "bad-blob"
    write_json(metadata_path, {"id": receipt["model_name"], "sha": receipt["revision"], "siblings": [info]})
    receipt["metadata_sha256"] = sha256(metadata_path)
    receipt["files"]["model.safetensors"]["upstream_blob"] = "bad-blob"
    write_json(receipt_path, receipt)
    with pytest.raises(ValueError, match="Git blob hash"):
        verified_model_origin(model_dir, receipt_path)


@pytest.fixture
def dual_origin(snapshot):
    model_dir, receipt_path, receipt = snapshot
    path = model_dir / 'modeling.py'
    path.write_bytes(b'# pinned custom implementation\n')
    data = path.read_bytes()
    blob = hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()
    metadata_path = model_dir.parent / 'implementation.json'
    revision = 'b' * 40
    write_json(metadata_path, {'id': 'organization/implementation', 'sha': revision,
        'siblings': [{'rfilename': path.name, 'size': len(data), 'blobId': blob}]})
    receipt['additional_origins'] = {'implementation': {
        'model_name': 'organization/implementation', 'revision': revision,
        'metadata_path': str(metadata_path), 'metadata_sha256': sha256(metadata_path),
        'metadata_url': f'https://huggingface.co/api/models/organization/implementation/revision/{revision}?blobs=true'}}
    receipt['files'][path.name] = {'sha256': sha256(path), 'bytes': len(data),
        'upstream_blob': blob, 'upstream_lfs': None, 'origin': 'implementation'}
    write_json(receipt_path, receipt)
    return model_dir, receipt_path, receipt


def test_verifies_separate_pinned_code_origin(dual_origin):
    model_dir, receipt_path, _ = dual_origin
    assert verified_model_origin(model_dir, receipt_path)['additional_origins']['implementation']['revision'] == 'b' * 40


@pytest.mark.parametrize('tamper', ['metadata_hash', 'revision', 'url', 'unknown_origin', 'code_bytes'])
def test_rejects_separate_origin_tampering(dual_origin, tamper):
    model_dir, receipt_path, receipt = dual_origin
    origin = receipt['additional_origins']['implementation']
    if tamper == 'metadata_hash':
        origin['metadata_sha256'] = '0' * 64
    elif tamper == 'revision':
        origin['revision'] = 'c' * 40
    elif tamper == 'url':
        origin['metadata_url'] = 'https://example.invalid/unpinned'
    elif tamper == 'unknown_origin':
        receipt['files']['modeling.py']['origin'] = 'unknown'
    else:
        (model_dir / 'modeling.py').write_bytes(b'# changed code\n')
    write_json(receipt_path, receipt)
    with pytest.raises(ValueError):
        verified_model_origin(model_dir, receipt_path)
