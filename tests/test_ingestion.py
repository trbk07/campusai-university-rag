"""Tests for the Task 1 document ingestion pipeline."""
import json
import subprocess
import sys
import pymupdf
from agentic_rag.ingestion.chunker import chunk_text
from agentic_rag.ingestion.pdf_parser import parse_pdf
from agentic_rag.ingestion.table_extractor import normalize_rows
import agentic_rag.ingestion.pdf_parser as pdf_parser
from agentic_rag.ingestion.ocr import available_languages, resolve_tesseract


def make_pdf(path):
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "REVENUE\nRevenue increased across the reporting period.")
    doc.save(path)
    doc.close()


def test_parse_text_has_page_and_metadata(tmp_path):
    path = tmp_path / "report.pdf"
    make_pdf(path)
    parsed = parse_pdf(path, doc_id="report_2024")
    assert parsed.pages == 1
    assert parsed.chunks
    assert parsed.chunks[0].metadata.doc_id == "report_2024"
    assert parsed.chunks[0].metadata.page == 1
    assert parsed.chunks[0].metadata.section == "REVENUE"
    assert parsed.chunks[0].metadata.content_type == "text"


def test_chunking_splits_at_word_boundary():
    chunks = chunk_text("word " * 100, doc_id="x", page=2, section="S", max_chars=40)
    assert len(chunks) > 1
    assert all(chunk.metadata.page == 2 for chunk in chunks)
    assert all(not chunk.text.endswith(" ") for chunk in chunks)


def test_parse_pdf_without_tables_is_supported(tmp_path):
    path = tmp_path / "no_table.pdf"
    make_pdf(path)
    assert parse_pdf(path).tables == []


def test_merged_cell_rows_are_normalized_and_schema_is_stable():
    frame = normalize_rows([["Period", "Revenue", "Revenue"], ["2024", "100", None], ["2025", None, "120"]])
    assert list(frame.columns) == ["Period", "Revenue", "Revenue_1"]
    assert frame.shape == (2, 3)


def test_empty_table_is_discarded():
    assert normalize_rows([[None, ""], [None, None]]) is None


def test_cli_end_to_end(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    make_pdf(input_dir / "sample.pdf")
    result = subprocess.run([sys.executable, "scripts/ingest_documents.py", "--input-dir", str(input_dir), "--output-dir", str(output_dir)],
                            capture_output=True, text=True, check=True)
    assert result.returncode == 0
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest[0]["doc_id"] == "sample"
    assert (output_dir / "chunks.jsonl").read_text(encoding="utf-8").strip()


def test_ocr_resolver_accepts_explicit_executable(tmp_path):
    executable = tmp_path / "tesseract.exe"
    executable.write_text("stub")
    assert resolve_tesseract(str(executable)) == str(executable)


def test_ocr_language_parser_returns_list(monkeypatch):
    monkeypatch.setattr(pdf_parser, "ocr_page", lambda page, **kwargs: "OCR revenue text")
    assert isinstance(available_languages("C:\\missing\\tesseract.exe"), list)


def test_ocr_fallback_adds_chunk_for_image_only_page(tmp_path, monkeypatch):
    path = tmp_path / "image_only.pdf"
    doc = pymupdf.open()
    doc.new_page()
    doc.save(path)
    doc.close()
    monkeypatch.setattr(pdf_parser, "ocr_page", lambda page, **kwargs: "OCR revenue text")
    parsed = parse_pdf(path, use_ocr=True)
    assert parsed.chunks[0].text == "OCR revenue text"
    assert parsed.chunks[0].metadata.page == 1
    assert parsed.warnings == []


def test_ocr_failure_is_recorded(tmp_path, monkeypatch):
    path = tmp_path / "image_only.pdf"
    doc = pymupdf.open()
    doc.new_page()
    doc.save(path)
    doc.close()
    def fail(*args, **kwargs):
        raise RuntimeError("Tesseract executable is not installed")
    monkeypatch.setattr(pdf_parser, "ocr_page", fail)
    parsed = parse_pdf(path, use_ocr=True)
    assert "OCR failed" in parsed.warnings[0]


def test_section_is_carried_to_next_page(tmp_path):
    path = tmp_path / "multi_page.pdf"
    doc = pymupdf.open()
    first = doc.new_page()
    first.insert_text((72, 72), "OPERATING RESULTS\nFirst page contains revenue results.")
    second = doc.new_page()
    second.insert_text((72, 72), "Second page contains operating expenses.")
    doc.save(path)
    doc.close()
    parsed = parse_pdf(path)
    assert parsed.chunks[-1].metadata.section == "OPERATING RESULTS"


