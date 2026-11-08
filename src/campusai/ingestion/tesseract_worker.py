"""One isolated local OCR process. Stdout is a bounded JSON-lines protocol."""
import hashlib
import json
import math
import os
from pathlib import Path
import sys

RENDER_POLICY = 'gray-small-print-symbol-v4'


def paper_like(image):
    """Do not mistake photographic texture for fine print on a light page."""
    import numpy as np
    pixels = np.asarray(image)
    return pixels.ndim == 2 and (pixels >= 225).mean() >= .85 and (pixels < 160).mean() <= .18


def text_render_scale(image, scale, *, max_scale=3.):
    """Spend extra pixels only on several consistently small printed lines.

    Projection is a rendering hint, never text proof or an accuracy score.
    Short decorations, isolated rules and photographs keep the ordinary path.
    """
    import numpy as np
    if scale >= max_scale: return scale
    gray = np.asarray(image)
    if gray.ndim != 2 or min(gray.shape) < 40 or not paper_like(image): return scale
    active = (gray < 160).sum(axis=1) >= max(8, gray.shape[1] * .01)
    edges = np.flatnonzero(np.diff(np.r_[False, active, False]))
    heights = edges[1::2] - edges[::2]
    heights = heights[(heights >= 5) & (heights <= 40)]
    if len(heights) < 6: return scale
    median = float(np.median(heights))
    if median > 10: return scale
    # A large persistent gutter identifies separate columns. Do not change
    # their segmentation into a single block merely because the text is small.
    ink = gray < 160
    rows = active & (ink.mean(axis=1) < .6)
    columns = ink[rows].sum(axis=0) >= max(2, rows.sum() * .01)
    occupied = np.flatnonzero(columns)
    if not len(occupied): return scale
    interior = columns[occupied[0]:occupied[-1] + 1]
    edges = np.flatnonzero(np.diff(np.r_[True, interior, True]))
    if any(edges[1::2] - edges[::2] >= max(4, len(interior) * .025)): return scale
    return min(max_scale, scale * 16 / median)


def render_page(page, scale, *, clip=None):
    """Render displayed content, preserving overlays, masks and physical origin."""
    import pymupdf as fitz
    from PIL import Image
    area = (clip or page.rect).get_area()
    if area * scale ** 2 > 20_000_000: raise ValueError('OCR pixel limit')
    options = dict(alpha=False, colorspace=fitz.csGRAY)
    if clip is not None: options['clip'] = clip
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), **options)
    image = Image.frombytes('L', (pix.width, pix.height), pix.samples)
    if not paper_like(image):
        options['colorspace'] = fitz.csRGB
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), **options)
        return pix, Image.frombytes('RGB', (pix.width, pix.height), pix.samples), scale
    selected = min(text_render_scale(image, scale), math.sqrt(20_000_000 / area))
    if selected > scale * 1.05:
        scale = selected
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), **options)
        image = Image.frombytes('L', (pix.width, pix.height), pix.samples)
    return pix, image, scale


def emit(value):
    print(json.dumps(value, ensure_ascii=True, allow_nan=False), flush=True)


def main():
    # Set before importing native libraries, only in this child process.
    os.environ['OMP_THREAD_LIMIT'] = '1'
    os.environ['OMP_NUM_THREADS'] = '1'
    from contextlib import redirect_stdout
    # Package/native imports can print notices; stdout is exclusively JSON RPC.
    with redirect_stdout(sys.stderr):
        from campusai.ingestion.ocr_symbols import RasterLabelVerifier, has_ambiguous_label
    import pymupdf as fitz
    from PIL import Image
    import tesserocr
    raw_request = sys.stdin.readline(2 * 1024 * 1024 + 1)
    if len(raw_request) > 2 * 1024 * 1024:
        raise ValueError('OCR request size limit exceeded')
    request = json.loads(raw_request)
    directory = Path(request['data_dir'])
    models = request['model_sha256']
    if set(models) != {'vie', 'eng'}:
        raise ValueError('invalid OCR languages')
    for language, expected in models.items():
        if hashlib.sha256((directory / (language + '.traineddata')).read_bytes()).hexdigest() != expected:
            raise ValueError('OCR asset changed')
    scale = request['scale']
    if not isinstance(scale, (int, float)) or not math.isfinite(scale) or not 0 < scale <= 4:
        raise ValueError('invalid OCR scale')
    with fitz.open(request['path']) as pdf, tesserocr.PyTessBaseAPI(
            path=str(directory), lang='vie+eng', oem=tesserocr.OEM.LSTM_ONLY,
            psm=tesserocr.PSM.AUTO) as api:
        label_verifier=RasterLabelVerifier()
        emit({'type': 'ready', 'engine': 'tesseract-vie-eng',
              'tesseract_version': tesserocr.tesseract_version().splitlines()[0],
              'render_policy': RENDER_POLICY,
              'model_sha256': models})
        for number in request['page_numbers']:
            if type(number) is not int or not 1 <= number <= len(pdf):
                raise ValueError('invalid OCR physical page')
            page = pdf[number - 1]
            regions = request.get('hybrid_regions', {}).get(str(number))
            if regions:
                # Inspect each displayed raster region independently. Rendering
                # retains masks, clipping and overlays, unlike raw image bytes.
                # Native text in a background region is deduplicated by geometry.
                lines, audits, texts, confidences = [], [], [], []
                bounds = page.rect * page.derotation_matrix
                for region in regions:
                    expected = fitz.Rect(region)
                    if expected.is_empty or not bounds.contains(expected):
                        raise ValueError('image region outside page')
                    if expected.get_area() * scale ** 2 > 20_000_000:
                        emit({'type': 'limit'}); return 2
                    pix, image, render_scale = render_page(page, scale, clip=expected * page.rotation_matrix)
                    api.SetPageSegMode(tesserocr.PSM.SINGLE_BLOCK if render_scale > scale * 1.05 else tesserocr.PSM.AUTO)
                    api.SetImage(image)
                    text = api.GetUTF8Text()
                    confidence = api.MeanTextConf() / 100
                    iterator = api.GetIterator()
                    region_lines = []
                    if text.strip() and iterator is not None:
                        for line in tesserocr.iterate_level(iterator, tesserocr.RIL.TEXTLINE):
                            value = line.GetUTF8Text(tesserocr.RIL.TEXTLINE)
                            box = line.BoundingBox(tesserocr.RIL.TEXTLINE)
                            if value and value.strip() and box:
                                x0, y0, x1, y1 = box
                                rect = fitz.Rect((x0 + pix.x) / render_scale, (y0 + pix.y) / render_scale,
                                                (x1 + pix.x) / render_scale, (y1 + pix.y) / render_scale) * page.derotation_matrix
                                region_lines.append({'text': value.strip(), 'bbox': list(rect)})
                    detected = bool(text.strip() or api.GetComponentImages(tesserocr.RIL.TEXTLINE, True))
                    outcome = 'recognized' if region_lines else 'unreadable' if detected else 'no_detected_text'
                    audits.append({'bbox': region, 'outcome': outcome})
                    lines.extend(region_lines)
                    texts.extend(row['text'] for row in region_lines)
                    if region_lines: confidences.append(confidence)
                text,lines,symbol_review=label_verifier.refine(page,'\n'.join(texts),lines)
                emit({'type': 'page', 'page': number, 'text': text, 'lines': lines,
                      'image_audit': audits,
                      **({'symbol_review':symbol_review} if symbol_review else {}),
                      'confidence': sum(confidences) / len(confidences) if confidences else 0})
                continue
            if page.rect.width * page.rect.height * scale ** 2 > 20_000_000:
                emit({'type': 'limit'}); return 2
            pix, image, render_scale = render_page(page, scale)
            api.SetPageSegMode(tesserocr.PSM.SINGLE_BLOCK if render_scale > scale * 1.05 else tesserocr.PSM.AUTO)
            api.SetImage(image)
            text = api.GetUTF8Text()
            result = {'type': 'page', 'page': number, 'text': text,
                      'confidence': api.MeanTextConf() / 100}
            if request.get('include_layout') or has_ambiguous_label(text):
                lines = []
                iterator = api.GetIterator()
                if iterator is not None:
                    for line in tesserocr.iterate_level(iterator, tesserocr.RIL.TEXTLINE):
                        value = line.GetUTF8Text(tesserocr.RIL.TEXTLINE)
                        box = line.BoundingBox(tesserocr.RIL.TEXTLINE)
                        if value and value.strip() and box:
                            rect = fitz.Rect([coordinate / render_scale for coordinate in box]) * page.derotation_matrix
                            lines.append({'text': value.strip(), 'bbox': list(rect)})
                text,lines,symbol_review=label_verifier.refine(page,text,lines)
                result['text']=text
                if symbol_review:result['symbol_review']=symbol_review
                if request.get('include_layout'):result['lines'] = lines
            emit(result)
        emit({'type': 'done'})
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        # Never print source text, environment credentials or local paths.
        emit({'type': 'error'})
        raise SystemExit(1)
