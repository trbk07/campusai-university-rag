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


def _confidence(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _ocr_data_result(data: dict[str, Any]) -> dict[str, Any]:
    """Convert Tesseract TSV output into stable diagnostics."""
    texts = data.get("text", [])
    raw_confidences = data.get("conf", [])
    words = []
    confidences = []
    for index, raw_text in enumerate(texts):
        text = str(raw_text).strip()
        if not text:
            continue
        raw_confidence = raw_confidences[index] if index < len(raw_confidences) else None
        confidence = _confidence(raw_confidence)
        if confidence is not None:
            confidences.append(confidence)
        bbox = []
        for key in ("left", "top", "width", "height"):
            values = data.get(key, [])
            try:
                bbox.append(int(values[index]) if index < len(values) else None)
            except (TypeError, ValueError):
                bbox.append(None)
        words.append({"text": text, "confidence": confidence, "bbox": bbox})
    text = " ".join(word["text"] for word in words).strip()
    printable = sum(char.isprintable() and not char.isspace() for char in text)
    suspicious = sum(not (char.isalnum() or char.isspace() or char in ".,;:!?%()/-+đĐ") for char in text)
    return {"text": text, "words": words, "word_count": len(words),
            "mean_confidence": (sum(confidences) / len(confidences) if confidences else None),
            "low_confidence_words": sum(c < 60 for c in confidences),
            "suspicious_ratio": suspicious / printable if printable else 1.0}


def _ocr_candidates(pytesseract: Any, image: Any, *, language: str) -> list[dict[str, Any]]:
    """Run preprocessing, orientation, and PSM candidates with stable diagnostics."""
    candidates = []
    orientations = [(0, image)]
    for angle in (90, 180, 270):
        orientations.append((angle, image.rotate(angle, expand=True)))
    for angle, oriented in orientations:
        for variant in [oriented, *_preprocessed_variants(oriented)]:
            for psm in (3, 6, 11, 12):
                data = pytesseract.image_to_data(variant, lang=language, config=f"--psm {psm}",
                                                 output_type=pytesseract.Output.DICT)
                result = _ocr_data_result(data)
                result["psm"] = psm
                result["orientation"] = angle
                candidates.append(result)
    return candidates


def _legacy_ocr_candidates(pytesseract: Any, image: Any, *, language: str) -> list[dict[str, Any]]:
    """Compatibility helper retained for adapters that patch the old runner."""
    candidates = []
    for variant in [image, *_preprocessed_variants(image)]:
        for psm in (3, 6, 11, 12):
            data = pytesseract.image_to_data(variant, lang=language, config=f"--psm {psm}",
                                             output_type=pytesseract.Output.DICT)
            result = _ocr_data_result(data)
            result["psm"] = psm
            candidates.append(result)
    return candidates


# The public internal name remains _ocr_candidates; the implementation above is intentional.


def _result_score(result: dict[str, Any]) -> tuple[float, int, int]:
    """Prefer confident, useful OCR while penalizing suspicious output."""
    mean = result.get("mean_confidence")
    confidence = mean if mean is not None else -1.0
    coverage = min(result.get("word_count", 0), 200)
    suspicious_penalty = result.get("suspicious_ratio", 1.0) * 25
    score = confidence - suspicious_penalty + min(coverage / 20, 10)
    return (score, result.get("word_count", 0), len(result.get("text", "")))


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


def _render_page(page: Any, dpi: int) -> Any:
    from PIL import Image
    pixmap = page.get_pixmap(matrix=__import__("pymupdf").Matrix(dpi / 72, dpi / 72), alpha=False)
    return Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)


def _configure_tesseract(tesseract_cmd: str | None) -> Any:
    try:
        import pytesseract
    except ImportError as exc:
        raise RuntimeError("OCR requires the optional dependency: uv sync --extra ocr") from exc
    resolved_command = resolve_tesseract(tesseract_cmd)
    if not resolved_command:
        raise RuntimeError("Tesseract is not installed. Run scripts\\setup_ocr_windows.ps1 or install it manually.")
    pytesseract.pytesseract.tesseract_cmd = resolved_command
    return pytesseract


def ocr_page_with_data(page: Any, *, language: str = "eng", dpi: int = 200,
                       tesseract_cmd: str | None = None) -> dict[str, Any]:
    """OCR a page and return text plus word confidences and bounding boxes.

    Confidence is Tesseract's signal, not a calibrated probability. Empty and
    non-numeric confidence values are excluded from aggregate statistics.
    """
    pytesseract = _configure_tesseract(tesseract_cmd)
    image = _render_page(page, dpi)
    candidates = _ocr_candidates(pytesseract, image, language=language)
    best = max(candidates, key=_result_score, default={"text": "", "words": [], "word_count": 0,
                                                        "mean_confidence": None, "suspicious_ratio": 1.0})
    if dpi < 300 and (not best["text"] or (best.get("mean_confidence") is not None and best["mean_confidence"] < 60)):
        high_res = _ocr_candidates(pytesseract, _render_page(page, 300), language=language)
        best = max([best, *high_res], key=_result_score)
    return best


def ocr_page(page: Any, *, language: str = "eng", dpi: int = 200, tesseract_cmd: str | None = None) -> str:
    """Render a PyMuPDF page and return OCR text using the local Tesseract engine."""
    pytesseract = _configure_tesseract(tesseract_cmd)
    try:
        return ocr_page_with_data(page, language=language, dpi=dpi, tesseract_cmd=tesseract_cmd)["text"]
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError("Tesseract executable is not installed or not on PATH") from exc
