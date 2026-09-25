"""Bounded, local OCR worker for scan-only university PDFs."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import fitz
import numpy as np


class OCRUnavailable(RuntimeError):
    """Raised when the configured OCR backend is not installed."""


class OCRLimitExceeded(RuntimeError):
    """Raised when the OCR page or time budget is exceeded."""


@dataclass(frozen=True)
class OCRDocument:
    pages: list[dict[str, object]]
    engine: str
    average_confidence: float
    elapsed_seconds: float


def _recognize(engine, image: np.ndarray) -> tuple[str, float]:
    result, _ = engine(image)
    if not result:
        return "", 0.0
    texts: list[str] = []
    confidences: list[float] = []
    for item in result:
        if len(item) < 3:
            continue
        text = str(item[1]).strip()
        if text:
            texts.append(text)
        try:
            confidences.append(float(item[2]))
        except (TypeError, ValueError):
            pass
    return "\n".join(texts), sum(confidences) / len(confidences) if confidences else 0.0


def ocr_pdf(
    path: str | Path,
    *,
    max_pages: int = 50,
    timeout_seconds: float = 120.0,
    scale: float = 1.5,
) -> OCRDocument:
    """OCR a bounded number of pages using the local RapidOCR ONNX backend."""

    if max_pages <= 0 or timeout_seconds <= 0 or scale <= 0:
        raise ValueError("OCR limits must be positive")
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as error:  # pragma: no cover - environment dependent
        raise OCRUnavailable("install rapidocr-onnxruntime to enable OCR") from error

    started = time.perf_counter()
    engine = RapidOCR()
    pages: list[dict[str, object]] = []
    confidences: list[float] = []
    with fitz.open(Path(path)) as document:
        if document.page_count > max_pages:
            raise OCRLimitExceeded(
                f"OCR page limit exceeded: {document.page_count}>{max_pages}"
            )
        for page_number, page in enumerate(document, start=1):
            if time.perf_counter() - started > timeout_seconds:
                raise OCRLimitExceeded("OCR time limit exceeded")
            pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
                pixmap.height, pixmap.width, pixmap.n
            )
            text, confidence = _recognize(engine, image)
            pages.append({"page": page_number, "text": text, "confidence": confidence})
            if confidence:
                confidences.append(confidence)
    elapsed = time.perf_counter() - started
    if elapsed > timeout_seconds:
        raise OCRLimitExceeded("OCR time limit exceeded")
    return OCRDocument(
        pages=pages,
        engine="rapidocr-onnxruntime",
        average_confidence=round(sum(confidences) / len(confidences), 6)
        if confidences else 0.0,
        elapsed_seconds=round(elapsed, 6),
    )
