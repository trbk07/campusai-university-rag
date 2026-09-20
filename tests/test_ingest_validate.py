import fitz
import pytest

from finrag.ingestion.metadata_detector import detect_metadata
from finrag.ingestion.numeric_normalizer import normalize_number
from finrag.ingestion.pipeline import ingest_document
from finrag.ingestion.table_extractor import extract_tables
from finrag.ingestion.validate import ValidationError, validate_pdf
from finrag.schemas import Chunk, Table


def pdf(path, text="Revenue 2024 2023\n1,234.5 1.000,0\n"):
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(path)
    document.close()


def test_ingest_and_cache(tmp_path):
    source = tmp_path / "a.pdf"
    pdf(source, "Báo cáo hợp nhất 2024\nDoanh thu | 2024 | 2023\n1.234,5 | 1.000,0")
    first = ingest_document(source, tmp_path / "store")
    second = ingest_document(source, tmp_path / "store")
    assert first.doc_id == second.doc_id
    assert second.cached is True
    assert isinstance(second.chunks[0], Chunk)
    assert isinstance(second.tables[0], Table)
    assert (tmp_path / "store" / first.doc_id / "parsed.md").exists()


def test_invalid_and_scan(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not pdf")
    with pytest.raises(ValidationError):
        validate_pdf(bad)
    scan = tmp_path / "scan.pdf"
    document = fitz.open()
    document.new_page()
    document.save(scan)
    document.close()
    result = validate_pdf(scan)
    assert not result.has_text and result.warnings


def test_numeric_formats():
    assert normalize_number("1.234,5") == 1234.5
    assert normalize_number("1,234.5") == 1234.5
    assert normalize_number("(123)") == -123
    assert normalize_number("−1 234,50") == -1234.5
    assert normalize_number("N/A") is None


def test_metadata_supports_unicode_and_mojibake():
    metadata = detect_metadata("Báo cáo hợp nhất, đơn vị: triệu đồng, năm 2024")
    assert metadata["language"] == "vi"
    assert metadata["currency"] == "VND"
    assert metadata["units"] == ["million"]
    assert metadata["consolidation"] == "consolidated"
    assert 2024 in metadata["fiscal_years"]


def test_table_extractor_merges_continuations_and_keeps_warnings():
    pages = [
        {"page": 1, "text": "Khoản mục | 2024 | 2023\nDoanh thu | 10 | 9"},
        {"page": 2, "text": "Khoản mục | 2024 | 2023\nChi phí | 4 | 3"},
    ]
    tables = extract_tables(pages, "doc")
    assert len(tables) == 1
    assert tables[0].pages == [1, 2]
    assert tables[0].rows[-1][0] == "Chi phí"
    assert tables[0].schema["raw_preserved"] is True
