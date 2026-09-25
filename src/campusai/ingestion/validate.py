"""Input validation for user-provided PDF files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz


@dataclass
class PDFValidation:
    """Facts collected during PDF validation."""

    path: str
    size_bytes: int
    pages: int
    encrypted: bool
    has_text: bool | None
    warnings: list[str]


class ValidationError(ValueError):
    """Raised when a PDF cannot safely enter the ingestion pipeline."""


def validate_pdf(
    path: str | Path,
    max_mb: int = 50,
    max_pages: int = 218,
    check_text: bool = True,
    upload_root: str | Path | None = None,
) -> PDFValidation:
    """Validate a PDF without modifying it.

    A scan-only PDF is not rejected here. It is returned with a warning so a
    later OCR step can decide whether and how to process it. Callers that will
    parse every page anyway can defer the text probe with ``check_text=False``.
    """

    if max_mb <= 0:
        raise ValueError("max_mb phải lớn hơn 0")
    if max_pages <= 0:
        raise ValueError("max_pages phải lớn hơn 0")
    pdf_path = Path(path)

    if not pdf_path.is_file():
        raise ValidationError(f"PDF không tồn tại: {pdf_path}")

    if pdf_path.is_symlink():
        raise ValidationError("Không chấp nhận symlink làm file upload")

    resolved_path = pdf_path.resolve()
    if upload_root is not None:
        root = Path(upload_root).resolve()
        try:
            resolved_path.relative_to(root)
        except ValueError as error:
            raise ValidationError("File nằm ngoài upload root") from error

    if pdf_path.suffix.lower() != ".pdf":
        raise ValidationError("Input phải là file PDF")

    try:
        with pdf_path.open("rb") as handle:
            if handle.read(5) != b"%PDF-":
                raise ValidationError("File không có PDF magic bytes hợp lệ")
    except OSError as error:
        raise ValidationError(f"Không thể đọc file upload: {error}") from error

    size_bytes = pdf_path.stat().st_size
    max_bytes = max_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise ValidationError(f"PDF vượt giới hạn {max_mb} MB")

    try:
        document = fitz.open(str(pdf_path))
    except Exception as error:
        raise ValidationError(f"PDF hỏng hoặc không đọc được: {error}") from error

    try:
        if document.is_encrypted:
            raise ValidationError(
                "PDF được mã hóa; hãy cung cấp bản có quyền đọc"
            )

        page_count = len(document)
        if page_count == 0:
            raise ValidationError("PDF không có trang")

        if page_count > max_pages:
            raise ValidationError(f"PDF vượt giới hạn {max_pages} trang")

        has_text = (
            any(page.get_text("text").strip() for page in document)
            if check_text
            else None
        )
    finally:
        document.close()

    warnings = [] if has_text else ["PDF không có text; cần OCR"]
    if has_text is None:
        warnings = []
    return PDFValidation(
        path=str(pdf_path),
        size_bytes=size_bytes,
        pages=page_count,
        encrypted=False,
        has_text=has_text,
        warnings=warnings,
    )
