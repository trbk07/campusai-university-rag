"""One isolated local OCR process. Stdout is a bounded JSON-lines protocol."""
import hashlib
import json
import math
import os
from pathlib import Path
import sys


def emit(value):
    print(json.dumps(value, ensure_ascii=True, allow_nan=False), flush=True)


def main():
    # Set before importing native libraries, only in this child process.
    os.environ['OMP_THREAD_LIMIT'] = '1'
    os.environ['OMP_NUM_THREADS'] = '1'
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
        emit({'type': 'ready', 'engine': 'tesseract-vie-eng',
              'tesseract_version': tesserocr.tesseract_version().splitlines()[0],
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
                    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale),
                        clip=expected * page.rotation_matrix, alpha=False, colorspace=fitz.csRGB)
                    api.SetImage(Image.frombytes('RGB', (pix.width, pix.height), pix.samples))
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
                                rect = fitz.Rect((x0 + pix.x) / scale, (y0 + pix.y) / scale,
                                                (x1 + pix.x) / scale, (y1 + pix.y) / scale) * page.derotation_matrix
                                region_lines.append({'text': value.strip(), 'bbox': list(rect)})
                    detected = bool(text.strip() or api.GetComponentImages(tesserocr.RIL.TEXTLINE, True))
                    outcome = 'recognized' if region_lines else 'unreadable' if detected else 'no_detected_text'
                    audits.append({'bbox': region, 'outcome': outcome})
                    lines.extend(region_lines)
                    texts.extend(row['text'] for row in region_lines)
                    if region_lines: confidences.append(confidence)
                emit({'type': 'page', 'page': number, 'text': '\n'.join(texts), 'lines': lines,
                      'image_audit': audits,
                      'confidence': sum(confidences) / len(confidences) if confidences else 0})
                continue
            if page.rect.width * page.rect.height * scale ** 2 > 20_000_000:
                emit({'type': 'limit'}); return 2
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            api.SetImage(Image.frombytes('RGB', (pix.width, pix.height), pix.samples))
            text = api.GetUTF8Text()
            result = {'type': 'page', 'page': number, 'text': text,
                      'confidence': api.MeanTextConf() / 100}
            if request.get('include_layout'):
                lines = []
                iterator = api.GetIterator()
                if iterator is not None:
                    for line in tesserocr.iterate_level(iterator, tesserocr.RIL.TEXTLINE):
                        value = line.GetUTF8Text(tesserocr.RIL.TEXTLINE)
                        box = line.BoundingBox(tesserocr.RIL.TEXTLINE)
                        if value and value.strip() and box:
                            rect = fitz.Rect([coordinate / scale for coordinate in box]) * page.derotation_matrix
                            lines.append({'text': value.strip(), 'bbox': list(rect)})
                result['lines'] = lines
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
