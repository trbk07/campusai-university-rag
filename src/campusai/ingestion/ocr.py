"""Bounded, local OCR worker for scan-only university PDFs."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

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
    page_numbers: list[int] | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> OCRDocument:
    """OCR a bounded number of pages using the local RapidOCR ONNX backend."""

    if max_pages <= 0 or timeout_seconds <= 0 or scale <= 0:
        raise ValueError("OCR limits must be positive")
    started = time.perf_counter()
    pages: list[dict[str, object]] = []
    confidences: list[float] = []
    with fitz.open(Path(path)) as document:
        selected = list(range(1, document.page_count + 1)) if page_numbers is None else list(page_numbers)
        if (not selected or any(type(number) is not int or not 1 <= number <= document.page_count for number in selected)
                or len(set(selected)) != len(selected)):
            raise ValueError('OCR page numbers must be unique physical pages in the PDF')
        if len(selected) > max_pages:
            raise OCRLimitExceeded(
                f"OCR page limit exceeded: {len(selected)}>{max_pages}"
            )
        if progress is not None:
            progress(0,len(selected))
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError as error:  # pragma: no cover - environment dependent
            raise OCRUnavailable("install rapidocr-onnxruntime to enable OCR") from error
        # Each document already occupies an ingestion worker. ONNX's default
        # per-model pools multiply across detector/classifier/recognizer and
        # concurrent documents, starving each other and interactive requests.
        engine = RapidOCR(intra_op_num_threads=1, inter_op_num_threads=1)
        for completed,page_number in enumerate(selected,1):
            if time.perf_counter() - started > timeout_seconds:
                raise OCRLimitExceeded("OCR time limit exceeded")
            pixmap = document[page_number - 1].get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
                pixmap.height, pixmap.width, pixmap.n
            )
            text, confidence = _recognize(engine, image)
            pages.append({"page": page_number, "text": text, "confidence": confidence})
            if confidence:
                confidences.append(confidence)
            # The ingestion callback also checks cancellation. Do not start
            # another expensive page after the user cancelled/deleted a PDF.
            if progress is not None:
                progress(completed,len(selected))
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
