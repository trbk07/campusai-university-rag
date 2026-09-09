"""Optional Tesseract OCR adapter for image-only PDF pages."""
import os
import shutil
from pathlib import Path
from typing import Any


def _preprocessed_variants(image: Any) -> list[Any]:
    """Return conservative OCR variants for faint, low-contrast, or scanned pages."""
    from PIL import ImageFilter, ImageOps
    gray = ImageOps.grayscale(image)
    gray = ImageOps.autocontrast(gray)
    enlarged = gray.resize((gray.width * 2, gray.height * 2))
    denoised = enlarged.filter(ImageFilter.MedianFilter(size=3))
    threshold = denoised.point(lambda pixel: 255 if pixel > 180 else 0)
    return [gray, denoised, threshold]


_DEFAULT_WINDOWS_COMMAND = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Tesseract-OCR" / "tesseract.exe"


def resolve_tesseract(command: str | None = None) -> str | None:
    """Resolve explicit config, environment config, PATH, or standard Windows install."""
    candidate = command or os.environ.get("TESSERACT_CMD")
    if candidate and Path(candidate).exists():
        return str(Path(candidate))
    if candidate and shutil.which(candidate):
        return shutil.which(candidate)
    on_path = shutil.which("tesseract")
    if on_path:
        return on_path
    if _DEFAULT_WINDOWS_COMMAND.exists():
        return str(_DEFAULT_WINDOWS_COMMAND)
    return None


def available_languages(command: str | None = None) -> list[str]:
    """Return installed Tesseract languages, or an empty list when unavailable."""
    resolved = resolve_tesseract(command)
    if not resolved:
        return []
    import subprocess
    output = subprocess.run([resolved, "--list-langs"], capture_output=True, text=True, check=False).stdout
    return [line.strip() for line in output.splitlines() if line.strip() and not line.startswith("List of available")]


def ocr_page(page: Any, *, language: str = "eng", dpi: int = 200, tesseract_cmd: str | None = None) -> str:
    """Render a PyMuPDF page and return OCR text using the local Tesseract engine."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("OCR requires the optional dependency: uv sync --extra ocr") from exc
    resolved_command = resolve_tesseract(tesseract_cmd)
    if not resolved_command:
        raise RuntimeError("Tesseract is not installed. Run scripts\\setup_ocr_windows.ps1 or install it manually.")
    if resolved_command:
        pytesseract.pytesseract.tesseract_cmd = resolved_command
    pixmap = page.get_pixmap(matrix=__import__("pymupdf").Matrix(dpi / 72, dpi / 72), alpha=False)
    image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
    try:
        text = pytesseract.image_to_string(image, lang=language, config="--psm 3").strip()
        if text:
            return text
        # Retry only empty results: preprocessing is substantially more expensive.
        retry_dpi = max(dpi, 300)
        if retry_dpi != dpi:
            pixmap = page.get_pixmap(matrix=__import__("pymupdf").Matrix(retry_dpi / 72, retry_dpi / 72), alpha=False)
            image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
        for variant in _preprocessed_variants(image):
            for psm in (6, 11, 12):
                text = pytesseract.image_to_string(variant, lang=language,
                                                   config=f"--psm {psm}").strip()
                if text:
                    return text
        return ""
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError("Tesseract executable is not installed or not on PATH") from exc
