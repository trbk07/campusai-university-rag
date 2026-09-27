import json
import subprocess
import sys

import pytest

from campusai.retrieval.dense_index import (
    DenseIndex,
    HashEmbeddingProvider,
    IndexCorruptError,
    IndexCorpusMismatchError,
    IndexNotFoundError,
    IndexVersionMismatchError,
    corpus_hash,
)
from campusai.retrieval.index_builder import build_document_indexes
from campusai.schemas import Chunk, Document


def records():
    return [
        {"chunk_id": "a", "doc_id": "doc", "content": "hoc phan tien quyet", "page": 1},
        {"chunk_id": "b", "doc_id": "doc", "content": "tuition and fees", "page": 2},
    ]


def test_hash_provider_is_deterministic_and_normalized():
    provider = HashEmbeddingProvider()
    left = provider.encode_query("Điều kiện tốt nghiệp")
    right = provider.encode_query("Điều kiện tốt nghiệp")
    assert left == right
    assert len(left) == 256
    assert sum(value * value for value in left) == pytest.approx(1.0)


def test_dense_index_manifest_and_atomic_reload(tmp_path):
    items = records()
    index = DenseIndex(model_name="fallback-hash-256")
    index.build(items, corpus_id="university-2026", document_id="doc")
    path = tmp_path / "dense.json"
    index.save(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["manifest"]["schema_version"] == 2
    assert data["manifest"]["embedding_dimension"] == 256
    assert data["manifest"]["corpus_hash"] == corpus_hash(items)
    restored = DenseIndex.load(path, expected_model_name="fallback-hash-256", expected_corpus_hash=corpus_hash(items))
    assert restored.search("tien quyet", 2) == index.search("tien quyet", 2)


def test_dense_index_fails_closed_for_missing_corrupt_and_mismatch(tmp_path):
    path = tmp_path / "dense.json"
    with pytest.raises(IndexNotFoundError):
        DenseIndex.load(path)
    index = DenseIndex(records())
    index.build(records())
    index.save(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["vectors"][0] = [0.0]
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(IndexCorruptError):
        DenseIndex.load(path)
    index.save(path)
    with pytest.raises(IndexVersionMismatchError):
        DenseIndex.load(path, expected_model_name="other-model")
    with pytest.raises(IndexCorpusMismatchError):
        DenseIndex.load(path, expected_corpus_hash="0" * 64)


def test_dense_index_survives_real_process_restart(tmp_path):
    path = tmp_path / "dense.json"
    index = DenseIndex(records())
    index.build(records())
    index.save(path)
    script = (
        "from campusai.retrieval.dense_index import DenseIndex; "
        "import sys; print(DenseIndex.load(sys.argv[1]).search('tien quyet', 2))"
    )
    result = subprocess.run([sys.executable, "-c", script, str(path)], capture_output=True, text=True, check=True)
    assert "'a'" in result.stdout


def test_document_build_writes_corpus_manifest(tmp_path):
    doc_id = "d" * 64
    document = Document(doc_id, "source.pdf", 1, chunks=[Chunk("chunk", doc_id, 1, "course")])
    target = build_document_indexes(document, tmp_path / "index")
    manifest = json.loads((tmp_path / "index" / "manifest.json").read_text(encoding="utf-8"))
    assert target.name == doc_id
    assert manifest["schema_version"] == 2
    assert manifest["documents"] == [doc_id]


def test_corpus_manifest_hash_covers_all_documents(tmp_path):
    root = tmp_path / "index"
    for letter in ("a", "b"):
        doc_id = letter * 64
        document = Document(doc_id, "source.pdf", 1, chunks=[Chunk(f"chunk-{letter}", doc_id, 1, f"course {letter}")])
        build_document_indexes(document, root)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert [item["document_id"] for item in manifest["document_manifests"]] == ["a" * 64, "b" * 64]
    assert manifest["corpus_hash"]
