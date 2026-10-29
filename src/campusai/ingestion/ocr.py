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
    model_identity: dict | None = None


def _recognize(engine, image: np.ndarray):
    result, _ = engine(image)
    if not result:
        return "", 0.0, []
    texts: list[str] = []
    layout = []
    confidences: list[float] = []
    for item in result:
        if len(item) < 3:
            continue
        text = str(item[1]).strip()
        if text:
            texts.append(text)
            if item[0] is not None:
                points = np.asarray(item[0], dtype=float)
                if points.shape == (4, 2) and np.isfinite(points).all():
                    layout.append({'text': text, 'bbox': [float(points[:, 0].min()), float(points[:, 1].min()),
                                                         float(points[:, 0].max()), float(points[:, 1].max())]})
        try:
            confidences.append(float(item[2]))
        except (TypeError, ValueError):
            pass
    return "\n".join(texts), sum(confidences) / len(confidences) if confidences else 0.0, layout


def _numeric_tables(engine, image, layout, transform, scale, origin):
    """One bounded cell pass; an ordinary OCR page keeps its exact old output."""
    if len(layout) > 4096:
        return None
    import cv2
    from .ocr_numeric_tables import assemble_numeric_tables, read_cell_jobs, physical_tables
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    if gray.size > 20_000_000:
        return None
    def read_boxes(boxes):
        crops = [image[int(b):int(d), int(a):int(c)].copy() for a, b, c, d in boxes]
        output, _ = engine.text_rec(crops)
        return [(text, float(score)) for text, score in output]
    assembled = assemble_numeric_tables(gray, layout, lambda jobs: read_cell_jobs(gray, jobs, read_boxes))
    if not assembled['tables']:
        return None
    return {'words': assembled['words'],
            'tables': physical_tables(assembled['tables'], transform, scale, origin)}


def ocr_pdf(
    path: str | Path,
    *,
    max_pages: int = 50,
    timeout_seconds: float = 120.0,
    scale: float = 1.5,
    page_numbers: list[int] | None = None,
    progress: Callable[[int, int], None] | None = None,
    backend: str = 'rapidocr',
    data_dir: str | Path | None = None,
    include_layout: bool = False,
    hybrid_regions: dict | None = None,
) -> OCRDocument:
    """OCR a bounded number of pages using the local RapidOCR ONNX backend."""

    import math
    if (type(max_pages) is not int or max_pages <= 0
            or isinstance(timeout_seconds, bool) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0
            or isinstance(scale, bool) or not math.isfinite(scale) or not 0 < scale <= 4):
        raise ValueError("OCR limits must be positive")
    if backend not in {'rapidocr', 'tesseract', 'vietocr'}:
        raise ValueError('unsupported OCR backend')
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
        if backend in {'tesseract','vietocr'}:
            from .tesseract_process import recognize_pdf
            options = {'backend':backend,'page_bounds':{n:list(document[n-1].rect*document[n-1].derotation_matrix)
                       for n in selected}} if backend == 'vietocr' else {}
            return recognize_pdf(path, selected, data_dir=data_dir, scale=max(2.,scale) if backend == 'vietocr' else scale,
                                 timeout_seconds=timeout_seconds, progress=progress, include_layout=include_layout,
                                 hybrid_regions=hybrid_regions, **options)
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
            page = document[page_number - 1]
            regions = (hybrid_regions or {}).get(page_number)
            if regions:
                lines, audits, region_confidences, tables = [], [], [], []
                bounds = page.rect * page.derotation_matrix
                for region in regions:
                    if progress is not None:
                        progress(completed - 1, len(selected))
                    if time.perf_counter() - started > timeout_seconds:
                        raise OCRLimitExceeded('OCR time limit exceeded')
                    rect = fitz.Rect(region)
                    if rect.is_empty or not bounds.contains(rect):
                        raise ValueError('OCR image region outside page')
                    if rect.get_area() * scale ** 2 > 20_000_000:
                        raise OCRLimitExceeded('OCR page pixel limit exceeded')
                    pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=rect * page.rotation_matrix,
                                             alpha=False, colorspace=fitz.csRGB)
                    image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, pixmap.n)
                    text, confidence, layout = _recognize(engine, image)
                    def physical(box):
                        return list(fitz.Rect((box[0]+pixmap.x)/scale, (box[1]+pixmap.y)/scale,
                            (box[2]+pixmap.x)/scale, (box[3]+pixmap.y)/scale)*page.derotation_matrix)
                    numeric = _numeric_tables(engine, image, layout, physical, scale, [pixmap.x, pixmap.y])
                    if numeric:
                        layout = numeric['words']; tables.extend(numeric['tables'])
                        text = '\n'.join(row['text'] for row in layout)
                    if layout:
                        for row in layout:
                            x0, y0, x1, y1 = row['bbox']
                            box = fitz.Rect((x0 + pixmap.x) / scale, (y0 + pixmap.y) / scale,
                                            (x1 + pixmap.x) / scale, (y1 + pixmap.y) / scale) * page.derotation_matrix
                            lines.append({'text': row['text'], 'bbox': list(box)})
                        outcome = 'recognized'
                        region_confidences.append(confidence)
                    else:
                        detected, _ = engine(image, use_cls=False, use_rec=False)
                        outcome = 'unreadable' if detected else 'no_detected_text'
                    audits.append({'bbox': region, 'outcome': outcome})
                confidence = sum(region_confidences) / len(region_confidences) if region_confidences else 0
                pages.append({'page': page_number, 'text': '\n'.join(row['text'] for row in lines),
                              'lines': lines, 'image_audit': audits, 'confidence': confidence,
                              **({'ocr_tables': tables} if tables else {})})
                if confidence:
                    confidences.append(confidence)
                if progress is not None:
                    progress(completed, len(selected))
                continue
            pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
                pixmap.height, pixmap.width, pixmap.n
            )
            text, confidence, layout = _recognize(engine, image)
            def physical(box):
                return list(fitz.Rect([value/scale for value in box])*page.derotation_matrix)
            numeric = _numeric_tables(engine, image, layout, physical, scale, [0, 0])
            if numeric:
                layout = numeric['words']; text = '\n'.join(row['text'] for row in layout)
            result = {"page": page_number, "text": text, "confidence": confidence}
            if numeric:
                result['ocr_tables'] = numeric['tables']
            if include_layout:
                result['lines'] = [{'text': row['text'], 'bbox': list(fitz.Rect(
                    [value / scale for value in row['bbox']]) * page.derotation_matrix)} for row in layout]
            pages.append(result)
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
