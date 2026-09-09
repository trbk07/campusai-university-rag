"""Optional Tesseract OCR adapter for image-only PDF pages."""
from pathlib import Path
from typing import Any


def ocr_page(page: Any, *, language: str = "eng", dpi: int = 200, tesseract_cmd: str | None = None) -> str:
    """Render a PyMuPDF page and return OCR text using the local Tesseract engine."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("OCR requires the optional dependency: uv sync --extra ocr") from exc
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    pixmap = page.get_pixmap(matrix=__import__("pymupdf").Matrix(dpi / 72, dpi / 72), alpha=False)
    image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
    try:
        return pytesseract.image_to_string(image, lang=language).strip()
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError("Tesseract executable is not installed or not on PATH") from exc
