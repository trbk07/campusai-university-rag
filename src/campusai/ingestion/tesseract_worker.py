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
    request = json.loads(sys.stdin.readline(65536))
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
            if page.rect.width * page.rect.height * scale ** 2 > 20_000_000:
                emit({'type': 'limit'}); return 2
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            api.SetImage(Image.frombytes('RGB', (pix.width, pix.height), pix.samples))
            text = api.GetUTF8Text()
            emit({'type': 'page', 'page': number, 'text': text,
                  'confidence': api.MeanTextConf() / 100})
        emit({'type': 'done'})
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        # Never print source text, environment credentials or local paths.
        emit({'type': 'error'})
        raise SystemExit(1)
