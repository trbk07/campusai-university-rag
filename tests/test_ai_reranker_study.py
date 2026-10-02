"""Research must retain source integrity and never fabricate release evidence."""
import json
from pathlib import Path

import pytest

from evaluation.benchmarks.build_ai_reranker_benchmark import compile_rows, main as build_main
from evaluation.benchmarks.freeze_human_benchmark import validate_rows
from evaluation.common.release_artifacts import sha256
from evaluation.reranker.run_ai_reranker_study import complete_gold_coverage, validate_dataset


@pytest.fixture
def source(tmp_path):
    doc = "a" * 64
    (tmp_path / doc).mkdir()
    item = {"doc_id": doc, "chunk_id": doc + "_p1_s1_c1", "page": 1, "content": "Actual frozen evidence"}
    (tmp_path / "manifest.json").write_text(json.dumps({"documents": [doc]}), encoding="utf-8")
    (tmp_path / doc / "bm25.json").write_text(json.dumps({"items": [item]}), encoding="utf-8")
    corpus = {"documents": [{"filename": "uet_masters_admission_2022.pdf", "sha256": doc,
                             "benchmark_split": "holdout", "source_url": "https://example.org/source.pdf"}]}
    return tmp_path, corpus, item


def test_compiler_preserves_original_split_and_cannot_pass_as_human(source):
    directory, corpus, item = source
    rows = compile_rows("admission|0|hard|fact|A natural question?|A source answer.", corpus, directory)
    assert rows[0]["split"] == "holdout"
    assert rows[0]["gold_evidence"][0]["quote"] == item["content"]
    assert rows[0]["release_eligible"] is False
    assert rows[0]["author_type"] == "ai"
    assert not {"author", "reviewer", "review_checks"} & rows[0].keys()
    review = validate_rows(rows, {(item["doc_id"], item["chunk_id"]): item})
    assert any("independent_human_review_required" in error for error in review["errors"])


@pytest.mark.parametrize("line", [
    "admission|0|easy|negative|Q?|No.",
    "admission||easy|fact|Q?|Yes.",
    "admission|-1|easy|fact|Q?|Yes.",
    "admission|99|easy|fact|Q?|Yes.",
    "admission|0,0|easy|fact|Q?|Yes.",
])
def test_compiler_rejects_false_or_invalid_gold(source, line):
    directory, corpus, _ = source
    with pytest.raises(ValueError):
        compile_rows(line, corpus, directory)


def test_compiler_rejects_duplicate_questions(source):
    directory, corpus, _ = source
    with pytest.raises(ValueError, match="duplicate"):
        compile_rows("admission|0|easy|fact|Q?|A.\nadmission|0|hard|fact|q?|B.", corpus, directory)


def test_ai_compiler_cannot_overwrite_official_gate_evidence(tmp_path):
    with pytest.raises(ValueError, match="isolated studies"):
        build_main(["--output-dir", str(tmp_path / "evaluation/results")])


def test_dataset_validation_detects_chunk_tampering(source):
    directory, _, item = source
    dataset = directory / "dataset"
    dataset.mkdir()
    for split in ("dev", "test", "holdout"):
        (dataset / f"{split}.jsonl").write_text("{}\n", encoding="utf-8")
    manifest = {"evidence_type": "ai_authored_pdf_research", "release_eligible": False,
                "review_status": "not_human_reviewed", "index_sha256": sha256(directory / "manifest.json"),
                "dataset_sha256": {split: sha256(dataset / f"{split}.jsonl") for split in ("dev", "test", "holdout")},
                "chunk_sha256": {item["doc_id"]: sha256(directory / item["doc_id"] / "bm25.json")}}
    (dataset / "dataset_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    validate_dataset(dataset, directory)
    (directory / item["doc_id"] / "bm25.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="chunk checksum"):
        validate_dataset(dataset, directory)


def test_multihop_coverage_requires_all_gold_not_just_one_hit():
    one, two = {"doc_id": "doc", "chunk_id": "one"}, {"doc_id": "doc", "chunk_id": "two"}
    rows = [{"qid": "q", "answerable": True, "gold_evidence": [one, two]}]
    assert complete_gold_coverage(rows, {"q": [one]}) == 0
    assert complete_gold_coverage(rows, {"q": [one, two]}) == 1
