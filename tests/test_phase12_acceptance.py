import json
import time
from pathlib import Path

import fitz

from campusai.ingestion.chunker import _MAX_CHARS, make_chunks
from campusai.schemas import Chunk, Document, Table
from campusai.ingestion.jobs import IngestionJobManager
from campusai.ingestion.metadata_detector import detect_metadata
from campusai.ingestion.table_extractor import extract_tables
from campusai.ingestion.pipeline import delete_document_full
from campusai.retrieval.index_builder import build_document_indexes, remove_document_from_index


FIXTURES = Path(__file__).parent / "fixtures" / "phase12"


def test_academic_metadata_contract_has_normalized_entities_and_effective_date():
    metadata = detect_metadata(
        "Institution: Campus University\n"
        "Program: Computer Engineering\nCourse code: CS201\n"
        "Version: 2.0\nEffective date: 01/09/2025\n"
        "Curriculum 2025-2026, semester 1, 3 credits"
    )
    assert metadata["document_type"] == "curriculum"
    assert metadata["effective_date"] == "2025-09-01"
    assert metadata["academic_metadata"]["institution"] == "Campus University"
    assert metadata["academic_metadata"]["program"] == "Computer Engineering"
    assert metadata["academic_metadata"]["course"] == "CS201"
    assert metadata["academic_metadata"]["version"] == "2.0"


def test_all_supported_document_types_are_detected():
    examples = {
        "regulation": "Quy che dao tao va regulation",
        "curriculum": "Chuong trinh dao tao curriculum",
        "syllabus": "De cuong mon hoc syllabus",
        "handbook": "Cam nang sinh vien handbook",
        "course_catalog": "Danh muc hoc phan course catalog",
    }
    for expected, text in examples.items():
        metadata = detect_metadata(text)
        assert metadata["document_type"] == expected
        assert expected in metadata["document_type_evidence"]


def test_graduation_golden_fixture_keeps_section_and_citation_page():
    fixture = json.loads((FIXTURES / "graduation_conditions.json").read_text(encoding="utf-8"))
    chunks = make_chunks(
        fixture["document"]["pages"],
        fixture["document"]["doc_id"],
        fixture["document"]["metadata"],
    )
    target = next(chunk for chunk in chunks if "Điều kiện tốt nghiệp" in chunk.heading_path)
    assert target.page == fixture["expected"]["citation_page"]
    assert list(target.page_range) == fixture["expected"]["page_range"]
    assert all(value in target.content for value in fixture["expected"]["contains"])
    assert all(value not in target.content for value in fixture["expected"]["does_not_contain"])
    assert target.citation["page"] == 1


def test_prerequisite_golden_fixture_preserves_table_header_and_section_boundary():
    fixture = json.loads((FIXTURES / "prerequisites.json").read_text(encoding="utf-8"))
    tables = extract_tables(fixture["document"]["pages"], fixture["document"]["doc_id"])
    chunks = make_chunks(
        fixture["document"]["pages"],
        fixture["document"]["doc_id"],
        fixture["document"]["metadata"],
        tables,
    )
    table_chunk = next(chunk for chunk in chunks if chunk.content_type == "table")
    assert table_chunk.heading_path == fixture["expected"]["section"]
    assert table_chunk.page == fixture["expected"]["citation_page"]
    assert all(value in table_chunk.content for value in fixture["expected"]["table_header_contains"])
    assert "CS310" not in table_chunk.content


def test_heading_variant_golden_fixtures():
    for name in (
        "heading_split_across_lines.json",
        "heading_across_page_break.json",
        "roman_numeral_heading.json",
        "uppercase_title_edge_case.json",
    ):
        fixture = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
        chunks = make_chunks(
            fixture["document"]["pages"],
            fixture["document"]["doc_id"],
            fixture["document"]["metadata"],
        )
        expected = fixture["expected"]
        if expected.get("heading"):
            assert any(expected["heading"] in chunk.heading_path for chunk in chunks)
        if expected.get("not_heading"):
            assert all(expected["not_heading"] not in chunk.heading_path for chunk in chunks)
        assert any(expected["contains"] in chunk.content for chunk in chunks)


def test_chunk_diagnostics_bound_size_empty_pages_and_heading_errors():
    diagnostics = {}
    chunks = make_chunks(
        [
            {"page": 1, "text": "1. Section\n" + ("long evidence " * 500)},
            {"page": 2, "text": ""},
        ],
        "doc",
        {"document_type": "regulation"},
        diagnostics=diagnostics,
    )
    assert chunks
    assert not diagnostics["chunks_over_limit"]
    assert diagnostics["empty_pages"] == [2]
    assert all(len(chunk.content) <= _MAX_CHARS + 200 for chunk in chunks)
    assert any(first.content[-50:] in second.content for first, second in zip(chunks, chunks[1:]))


def test_oversized_table_cell_keeps_json_valid():
    diagnostics = {}
    table = Table("doc_p1_t1", "doc", [1], ["Code", "Description"], [["CS101", "x" * 5000]])
    chunks = make_chunks([{"page": 1, "text": "Table"}], "doc", {}, [table], diagnostics)
    table_chunk = next(chunk for chunk in chunks if chunk.content_type == "table")
    payload = table_chunk.content.split("\n\n", 1)[1]
    parsed = json.loads(payload)
    assert parsed["truncated"] is True
    assert parsed["original_columns"] == 2
    assert table_chunk.content.startswith("[Page: 1]")


def test_document_index_artifacts_can_be_removed(tmp_path):
    doc_id = "a" * 64
    chunk = Chunk("chunk-1", doc_id, 1, "prerequisite course", metadata={})
    document = Document(doc_id, str(tmp_path / "source.pdf"), 1, chunks=[chunk])
    target = build_document_indexes(document, tmp_path / "index")
    assert (target / "bm25.json").exists()
    assert (target / "dense.json").exists()
    assert remove_document_from_index(doc_id, tmp_path / "index") is True
    assert not target.exists()
    assert remove_document_from_index(doc_id, tmp_path / "index") is True


def test_delete_document_full_reports_store_and_index(tmp_path):
    doc_id = "b" * 64
    store = tmp_path / "store"
    artifact = store / doc_id
    artifact.mkdir(parents=True)
    (artifact / "metadata.json").write_text("{}", encoding="utf-8")
    index = tmp_path / "index" / doc_id
    index.mkdir(parents=True)
    result = delete_document_full(doc_id, store_dir=store, index_dir=tmp_path / "index")
    assert result == {"store": True, "index": True}
    assert not artifact.exists() and not index.exists()


def test_scan_job_finishes_as_review_required_with_ocr_reason(tmp_path):
    scan = tmp_path / "scan.pdf"
    document = fitz.open()
    document.new_page()
    document.save(scan)
    document.close()
    manager = IngestionJobManager(max_workers=1)
    try:
        job_id = manager.submit(scan, store_dir=tmp_path / "store")
        deadline = time.time() + 3
        status = manager.get(job_id)
        while status and status["state"] not in {"succeeded", "failed", "review_required"} and time.time() < deadline:
            time.sleep(0.01)
            status = manager.get(job_id)
        assert status is not None
        assert status["state"] == "review_required"
        assert status["stage"] == "review_required"
        assert status["error"] == "ocr_required"
    finally:
        manager.shutdown()
