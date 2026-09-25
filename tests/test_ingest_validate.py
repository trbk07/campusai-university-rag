import fitz
import pytest

from campusai.ingestion.metadata_detector import detect_metadata
from campusai.ingestion.numeric_normalizer import normalize_number
from campusai.ingestion.pipeline import ingest_document
from campusai.ingestion.table_extractor import extract_tables
from campusai.ingestion.validate import ValidationError, validate_pdf
from campusai.schemas import Chunk, Table


def pdf(path, text="Course 2024 2023\n3 2\n"):
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(path)
    document.close()


def test_ingest_and_cache(tmp_path):
    source = tmp_path / "a.pdf"
    pdf(source, "Quy che dao tao 2024\nMa hoc phan | Hoc ky | Tin chi\nCS101 | 1 | 3")
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
    assert normalize_number("-1 234,50") == -1234.5
    assert normalize_number("N/A") is None


def test_metadata_supports_university_documents():
    metadata = detect_metadata(
        "Quy chế đào tạo năm học 2024-2025, học kỳ 1, "
        "học phí 1 triệu đồng và 3 tín chỉ."
    )
    assert metadata["domain"] == "academic"
    assert metadata["language"] == "vi"
    assert metadata["currency"] == "VND"
    assert metadata["units"] == ["credit", "million"]
    assert metadata["academic_years"] == [2024, 2025]
    assert metadata["semesters"] == ["1"]


def test_table_extractor_merges_continuations_and_keeps_warnings():
    pages = [
        {"page": 1, "text": "Hoc phan | 2024 | 2023\nCS101 | 3 | 3"},
        {"page": 2, "text": "Hoc phan | 2024 | 2023\nCS102 | 4 | 4"},
    ]
    tables = extract_tables(pages, "doc")
    assert len(tables) == 1
    assert tables[0].pages == [1, 2]
    assert tables[0].rows[-1][0] == "CS102"
    assert tables[0].schema["raw_preserved"] is True
