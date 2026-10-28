"""Run OCR with a hard deadline/cancellation boundary outside the app process."""
import json
import math
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

from .ocr_assets import TESSDATA_SHA256, VIETOCR_SHA256, validate_tesseract_assets, validate_vietocr_assets


def recognize_pdf(path, selected, *, data_dir, scale, timeout_seconds, progress,
                  include_layout=False, hybrid_regions=None, backend='tesseract'):
    from .ocr import OCRDocument, OCRLimitExceeded, OCRUnavailable
    started = time.perf_counter()
    if backend not in {'tesseract','vietocr'}:
        raise ValueError('unsupported isolated OCR backend')
    expected = VIETOCR_SHA256 if backend == 'vietocr' else TESSDATA_SHA256
    engine = 'vietocr-vgg-seq2seq-v1' if backend == 'vietocr' else 'tesseract-vie-eng'
    try:
        identity = (validate_vietocr_assets if backend == 'vietocr' else validate_tesseract_assets)(data_dir)
    except ValueError as error:
        raise OCRUnavailable(str(error)) from error
    environment = {k: v for k, v in os.environ.items()
                   if k not in {'PYTHONPATH', 'PYTHONHOME', 'GEMINI_API_KEY', 'OPENAI_API_KEY', 'GROQ_API_KEY'}}
    environment.update(OMP_THREAD_LIMIT='1', OMP_NUM_THREADS='1')
    worker = Path(__file__).with_name('vietocr_worker.py' if backend == 'vietocr' else 'tesseract_worker.py')
    process = subprocess.Popen([sys.executable, '-I', '-u', str(worker)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        env=environment, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    messages = queue.Queue(maxsize=2)
    stopped = threading.Event()

    def read():
        try:
            while not stopped.is_set():
                line = process.stdout.readline(4 * 1024 * 1024 + 1)
                value = None if not line else json.loads(line) if len(line) <= 4 * 1024 * 1024 else {'type': 'error'}
                while not stopped.is_set():
                    try:
                        messages.put(value, timeout=.1); break
                    except queue.Full:
                        pass
                if value is None or value.get('type') == 'error':
                    return
        except (OSError, ValueError, AttributeError):
            while not stopped.is_set():
                try:
                    messages.put({'type': 'error'}, timeout=.1); return
                except queue.Full:
                    pass

    reader = threading.Thread(target=read, daemon=True, name='local-ocr-output')
    writer = None
    pages, ready, finished = [], False, False
    try:
        payload = {'path': str(Path(path).resolve()), 'data_dir': str(Path(data_dir).resolve()),
                   'page_numbers': selected, 'scale': scale, 'model_sha256': expected,
                   'include_layout': include_layout, 'hybrid_regions': hybrid_regions or {}}
        encoded = json.dumps(payload, allow_nan=False).encode('utf-8') + b'\n'
        if len(encoded) > 2 * 1024 * 1024:
            raise OCRLimitExceeded('OCR request size limit exceeded')
        def send():
            try:
                process.stdin.write(encoded)
                process.stdin.close()
            except (OSError, ValueError):
                while not stopped.is_set():
                    try:
                        messages.put({'type': 'error'}, timeout=.1); return
                    except queue.Full:
                        pass
        writer = threading.Thread(target=send, daemon=True, name='local-ocr-input')
        reader.start()
        writer.start()
        while not finished:
            remaining = timeout_seconds - (time.perf_counter() - started)
            if remaining <= 0:
                raise OCRLimitExceeded('OCR time limit exceeded')
            if progress is not None:
                progress(len(pages), len(selected))
            try:
                message = messages.get(timeout=min(.1, remaining))
            except queue.Empty:
                continue
            if not isinstance(message, dict):
                raise OCRUnavailable('local OCR worker ended before completion')
            kind = message.get('type')
            if kind == 'ready' and not ready and not pages:
                if message.get('model_sha256') != expected or message.get('engine') != engine:
                    raise OCRUnavailable('local OCR identity mismatch')
                if backend == 'tesseract':
                    identity['tesseract_version'] = message.get('tesseract_version')
                else:
                    identity.update(device=message.get('device'),render_scale=scale)
                ready = True
            elif kind == 'page' and ready and len(pages) < len(selected):
                text, confidence = message.get('text'), message.get('confidence')
                if (message.get('page') != selected[len(pages)] or not isinstance(text, str)
                        or isinstance(confidence, bool) or not isinstance(confidence, (int, float))
                        or not math.isfinite(confidence) or not 0 <= confidence <= 1):
                    raise OCRUnavailable('invalid local OCR page result')
                result = {'page': message['page'], 'text': text, 'confidence': confidence}
                if include_layout:
                    lines = message.get('lines')
                    if (not isinstance(lines, list) or len(lines) > 100000 or any(
                            not isinstance(row, dict) or not isinstance(row.get('text'), str)
                            or not isinstance(row.get('bbox'), list) or len(row['bbox']) != 4
                            or any(isinstance(v, bool) or not isinstance(v, (int, float))
                                   or not math.isfinite(v) for v in row['bbox'])
                            or row['bbox'][0] >= row['bbox'][2] or row['bbox'][1] >= row['bbox'][3]
                            for row in lines)):
                        raise OCRUnavailable('invalid local OCR layout')
                    if lines and ' '.join(text.split()) != ' '.join(
                            ' '.join(row['text'] for row in lines).split()):
                        raise OCRUnavailable('local OCR text/layout mismatch')
                    result['lines'] = lines
                    if 'image_audit' in message:
                        audit = message['image_audit']
                        if (not (hybrid_regions or {}).get(message['page'])
                                or not isinstance(audit, list) or len(audit) > 100000 or any(not isinstance(row, dict)
                                or row.get('outcome') not in {'recognized', 'no_detected_text', 'unreadable'}
                                or not isinstance(row.get('bbox'), list) or len(row['bbox']) != 4
                                or any(isinstance(v, bool) or not isinstance(v, (int, float))
                                       or not math.isfinite(v) for v in row['bbox']) for row in audit)):
                            raise OCRUnavailable('invalid local image OCR audit')
                        result['image_audit'] = audit
                pages.append(result)
            elif kind == 'done' and ready and len(pages) == len(selected):
                finished = True
            elif kind == 'limit':
                raise OCRLimitExceeded('OCR page pixel limit exceeded')
            else:
                raise OCRUnavailable('local OCR worker failed')
        remaining = timeout_seconds - (time.perf_counter() - started)
        try:
            if process.wait(timeout=max(.001, remaining)) != 0:
                raise OCRUnavailable('local OCR worker failed')
        except subprocess.TimeoutExpired as error:
            raise OCRLimitExceeded('OCR time limit exceeded') from error
        if progress is not None:
            progress(len(pages), len(selected))
        return OCRDocument(pages, engine,
            round(sum(p['confidence'] for p in pages) / len(pages), 6),
            round(time.perf_counter() - started, 6), identity)
    finally:
        stopped.set()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=3)
        if reader.ident is not None:
            reader.join(timeout=3)
        if writer is not None and writer.ident is not None:
            writer.join(timeout=3)
        process.stdout.close()
        if not process.stdin.closed:
            process.stdin.close()
