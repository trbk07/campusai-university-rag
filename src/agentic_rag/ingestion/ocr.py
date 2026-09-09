"""Optional Tesseract OCR adapter for image-only PDF pages."""
import os
from pathlib import Path
from typing import Any


_DEFAULT_WINDOWS_COMMAND = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Tesseract-OCR" / "tesseract.exe"


def _resolve_tesseract(command: str | None) -> str | None:
    if command:
        return command
    if _DEFAULT_WINDOWS_COMMAND.exists():
        return str(_DEFAULT_WINDOWS_COMMAND)
    return None


def ocr_page(page: Any, *, language: str = "eng", dpi: int = 200, tesseract_cmd: str | None = None) -> str:
    """Render a PyMuPDF page and return OCR text using the local Tesseract engine."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("OCR requires the optional dependency: uv sync --extra ocr") from exc
    resolved_command = _resolve_tesseract(tesseract_cmd)
    if resolved_command:
        pytesseract.pytesseract.tesseract_cmd = resolved_command
    pixmap = page.get_pixmap(matrix=__import__("pymupdf").Matrix(dpi / 72, dpi / 72), alpha=False)
    image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
    try:
        return pytesseract.image_to_string(image, lang=language).strip()
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError("Tesseract executable is not installed or not on PATH") from exc
