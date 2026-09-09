"""Tests for the Task 1 document ingestion pipeline."""
import json
import subprocess
import sys
import pymupdf
from agentic_rag.ingestion.chunker import chunk_text
from agentic_rag.ingestion.pdf_parser import parse_pdf
from agentic_rag.ingestion.table_extractor import normalize_rows, table_diagnostics
import agentic_rag.ingestion.pdf_parser as pdf_parser
from agentic_rag.ingestion.ocr import available_languages, resolve_tesseract
from agentic_rag.ingestion.ocr import _ocr_data_result, _result_score
from agentic_rag.ingestion.numeric import financial_invariants, parse_numeric
from scripts.benchmark_ingestion import classify_warnings


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


def test_numeric_parser_preserves_raw_and_handles_financial_formats():
    assert parse_numeric("(1,234.50)").value == -1234.5
    assert parse_numeric("1.234,50").value == 1234.5
    assert parse_numeric("12.5%").is_percent is True
    assert parse_numeric("—").status == "missing"


def test_table_diagnostics_preserve_ambiguity_without_mutating_values():
    diagnostics = table_diagnostics([["Period", "Revenue", "Revenue"], ["2024", "100", None]])
    assert diagnostics["merged_cell_suspected"] is True
    assert diagnostics["duplicate_headers"] == ["Revenue"]
    assert diagnostics["raw_rows"] == 2


def test_financial_invariant_warns_without_mutating_values():
    import pandas as pd
    frame = pd.DataFrame([[100, 70, 20]], columns=["Assets", "Liabilities", "Equity"])
    findings = financial_invariants(frame)
    assert findings[0]["invariant"] == "assets_equals_liabilities_plus_equity"
    assert findings[0]["status"] == "warning"
    assert frame.iloc[0, 0] == 100


def test_numeric_diagnostics_are_additive_to_table_diagnostics():
    diagnostics = table_diagnostics([["Year", "Revenue"], ["2024", "1,234.50"]])
    assert diagnostics["numeric_parsed"] >= 2
    assert diagnostics["raw_rows"] == 2


def test_benchmark_warning_categories_are_deterministic():
    categories = classify_warnings(["page 1: OCR failed", "table has ambiguous header", "PDF structural preflight failed"])
    assert categories == {"ocr": 1, "table": 1, "pdf": 1, "numeric": 0, "other": 0}


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


def test_ocr_tsv_diagnostics_are_tolerant_of_missing_fields():
    result = _ocr_data_result({"text": ["Revenue", ""], "conf": ["91"]})
    assert result["text"] == "Revenue"
    assert result["mean_confidence"] == 91.0
    assert result["words"][0]["bbox"] == [None, None, None, None]


def test_ocr_result_score_prefers_confidence_then_coverage():
    confident = {"mean_confidence": 90.0, "word_count": 2, "text": "OK"}
    longer = {"mean_confidence": 80.0, "word_count": 20, "text": "long"}
    assert _result_score(confident) > _result_score(longer)


def test_ocr_resolver_accepts_explicit_executable(tmp_path):
    executable = tmp_path / "tesseract.exe"
    executable.write_text("stub")
    assert resolve_tesseract(str(executable)) == str(executable)


def test_pdf_preflight_is_optional_without_pikepdf(tmp_path, monkeypatch):
    path = tmp_path / "report.pdf"
    make_pdf(path)
    monkeypatch.setitem(sys.modules, "pikepdf", None)
    assert pdf_parser._pdf_preflight(str(path)) == []


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


def test_no_text_layer_warning_is_recorded_without_ocr(tmp_path):
    path = tmp_path / "image_only.pdf"
    doc = pymupdf.open()
    doc.new_page()
    doc.save(path)
    doc.close()
    parsed = parse_pdf(path, use_ocr=False)
    assert parsed.warnings == ["page 1: no usable text layer; OCR required"]


def test_ocr_quality_warning_is_recorded(tmp_path, monkeypatch):
    path = tmp_path / "image_only.pdf"
    doc = pymupdf.open()
    doc.new_page()
    doc.save(path)
    doc.close()
    monkeypatch.setattr(pdf_parser, "ocr_page", lambda page, **kwargs: "x")
    parsed = parse_pdf(path, use_ocr=True)
    assert "very short" in parsed.warnings[0]


def test_ocr_confidence_is_recorded(tmp_path, monkeypatch):
    path = tmp_path / "image_only.pdf"
    doc = pymupdf.open()
    doc.new_page()
    doc.save(path)
    doc.close()
    monkeypatch.setattr(pdf_parser, "ocr_page_with_data", lambda page, **kwargs: {
        "text": "OCR revenue text", "words": [{"text": "OCR", "confidence": 55}],
        "word_count": 3, "mean_confidence": 55.0, "low_confidence_words": 1,
    })
    parsed = parse_pdf(path, use_ocr=True, collect_ocr_confidence=True)
    assert parsed.ocr_diagnostics["1"]["mean_confidence"] == 55.0
    assert any("mean confidence" in warning for warning in parsed.warnings)


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


def test_dynamic_margin_header_is_detected():
    pages = [[{"text": "Báo cáo | Trang 1", "bbox": (0, 0, 100, 10)}],
             [{"text": "Báo cáo | Trang 2", "bbox": (0, 0, 100, 10)}]]
    assert pdf_parser._repeated_margin_text(pages) == {"Báo cáo | Trang 1", "Báo cáo | Trang 2"}


def test_continuation_headers_ignore_units_and_case():
    assert pdf_parser._same_header(["Revenue (VND)", "COST"], ["revenue vnd", "cost"])


def test_two_column_blocks_are_read_column_by_column():
    blocks = [
        {"text": "L1", "bbox": (40, 20, 240, 40), "size": 10},
        {"text": "R1", "bbox": (360, 20, 560, 40), "size": 10},
        {"text": "L2", "bbox": (40, 60, 240, 80), "size": 10},
        {"text": "R2", "bbox": (360, 60, 560, 80), "size": 10},
    ]
    assert [item["text"] for item in pdf_parser._order_blocks(blocks, 600)] == ["L1", "L2", "R1", "R2"]


def test_heading_detection_respects_margin_for_normal_case():
    assert not pdf_parser._looks_like_heading("Báo cáo thường niên", font_size=10, body_size=10, y=20, page_height=800)
    assert pdf_parser._looks_like_heading("1. Kết quả kinh doanh", font_size=10, body_size=10, y=20, page_height=800)


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


