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

_PAGE_WORKER_LIMIT=1  # Quiet default: one native OCR core across all documents.
_PAGE_SLOTS=threading.BoundedSemaphore(_PAGE_WORKER_LIMIT)


def worker_environment(environ):
    """Pass OS/native-library settings, never provider keys or app credentials."""
    allowed = {'PATH', 'PATHEXT', 'SYSTEMROOT', 'WINDIR', 'SYSTEMDRIVE', 'COMSPEC',
        'TEMP', 'TMP', 'TMPDIR', 'HOME', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA',
        'PROGRAMDATA', 'LANG', 'LC_ALL', 'LC_CTYPE', 'LD_LIBRARY_PATH', 'DYLD_LIBRARY_PATH',
        'CUDA_VISIBLE_DEVICES', 'NVIDIA_VISIBLE_DEVICES', 'CUDA_DEVICE_ORDER', 'CUDA_MODULE_LOADING'}
    result = {name: value for name, value in environ.items() if name.upper() in allowed}
    result.update(OMP_THREAD_LIMIT='1', OMP_NUM_THREADS='1')
    return result


def recognize_pdf(path, selected, *, data_dir, scale, timeout_seconds, progress,
                  include_layout=False, hybrid_regions=None, backend='tesseract', page_bounds=None):
    """Keep independent MuPDF/Tesseract processes behind a global CPU bound.

    No PDF handle or recognizer crosses threads/processes. The first small
    searchable batch and later work share one OCR core by default.
    Progress/cancellation remain on the caller thread and one shared deadline.
    """
    from .ocr import OCRDocument, OCRLimitExceeded, OCRUnavailable
    from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
    selected=list(selected);started=time.perf_counter()
    options=dict(data_dir=data_dir,scale=scale,include_layout=include_layout,
                 hybrid_regions=hybrid_regions,backend=backend,page_bounds=page_bounds)

    def run(numbers, callback):
        if backend!='tesseract':
            return _recognize_one(path,numbers,timeout_seconds=timeout_seconds,progress=callback,**options)
        while not _PAGE_SLOTS.acquire(timeout=.05):
            if callback:callback(0,len(numbers))
            if time.perf_counter()-started>=timeout_seconds:
                raise OCRLimitExceeded('OCR time limit exceeded while waiting for a local worker')
        try:
            remaining=timeout_seconds-(time.perf_counter()-started)
            if remaining<=0:raise OCRLimitExceeded('OCR time limit exceeded')
            return _recognize_one(path,numbers,timeout_seconds=remaining,progress=callback,**options)
        finally:
            _PAGE_SLOTS.release()

    workers=min(_PAGE_WORKER_LIMIT,max(2,math.ceil(len(selected)/4)))
    if backend!='tesseract' or len(selected)<4 or workers<2:
        return run(selected,progress)
    stopped=threading.Event();lock=threading.Lock();counts=[0]*workers
    def callback(index):
        def update(completed,total):
            if stopped.is_set():raise OCRLimitExceeded('OCR batch stopped')
            with lock:counts[index]=max(counts[index],completed)
        return update
    pool=ThreadPoolExecutor(max_workers=workers,thread_name_prefix='local-ocr-pages')
    futures=[pool.submit(run,selected[index::workers],callback(index)) for index in range(workers)]
    pending=set(futures);failure=None
    try:
        while pending:
            if progress:
                with lock:completed=sum(counts)
                progress(completed,len(selected))
            remaining=timeout_seconds-(time.perf_counter()-started)
            if remaining<=0:raise OCRLimitExceeded('OCR time limit exceeded')
            done,pending=wait(pending,timeout=min(.05,remaining),return_when=FIRST_COMPLETED)
            for future in done:future.result()
    except BaseException as error:
        failure=error
    finally:
        stopped.set()
        pool.shutdown(wait=True,cancel_futures=True)
    documents=[]
    for future in futures:
        if future.cancelled():continue
        try:
            documents.append(future.result())
        except OCRLimitExceeded as error:
            if error.partial:documents.append(error.partial)
        except BaseException:
            pass  # The original failure is re-raised after sibling cleanup.
    combined=None
    if documents:
        first=documents[0]
        if any(doc.engine!=first.engine or doc.model_identity!=first.model_identity for doc in documents):
            raise OCRUnavailable('local OCR workers disagree on model identity')
        pages={page['page']:page for doc in documents for page in doc.pages}
        ordered=[pages[number] for number in selected if number in pages]
        if ordered:
            identity={**(first.model_identity or {}),'page_workers':workers}
            combined=OCRDocument(ordered,first.engine,round(sum(page['confidence'] for page in ordered)/len(ordered),6),
                                 round(time.perf_counter()-started,6),identity)
    if failure is not None:
        if isinstance(failure,OCRLimitExceeded):failure.partial=combined
        raise failure
    if combined is None or len(combined.pages)!=len(selected):
        raise OCRUnavailable('local OCR workers returned incomplete pages')
    if progress:progress(len(selected),len(selected))
    return combined


def _recognize_one(path, selected, *, data_dir, scale, timeout_seconds, progress,
                  include_layout=False, hybrid_regions=None, backend='tesseract', page_bounds=None):
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
    environment = worker_environment(os.environ)
    worker = Path(__file__).with_name('vietocr_worker.py' if backend == 'vietocr' else 'tesseract_worker.py')
    process = subprocess.Popen([sys.executable, '-I', '-u', str(worker)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        env=environment, creationflags=(getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            | getattr(subprocess, 'BELOW_NORMAL_PRIORITY_CLASS', 0)))
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
    def limit(message):
        partial = OCRDocument(list(pages), engine,
            round(sum(p['confidence'] for p in pages)/len(pages),6),
            round(time.perf_counter()-started,6),identity) if ready and pages else None
        return OCRLimitExceeded(message,partial=partial)
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
                raise limit('OCR time limit exceeded')
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
                    if message.get('render_policy') != identity['render_policy']:
                        raise OCRUnavailable('local OCR rendering policy mismatch')
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
                if 'ocr_tables' in message:
                    from .ocr_tables import validate_tables
                    try:
                        if backend!='vietocr':raise ValueError('OCR tables require their pinned backend')
                        result['ocr_tables']=validate_tables(message['ocr_tables'],
                            (page_bounds or {}).get(message['page']))
                    except ValueError as error:
                        raise OCRUnavailable('invalid local OCR table result') from error
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
                raise limit('OCR page pixel limit exceeded')
            else:
                raise OCRUnavailable('local OCR worker failed')
        remaining = timeout_seconds - (time.perf_counter() - started)
        try:
            if process.wait(timeout=max(.001, remaining)) != 0:
                raise OCRUnavailable('local OCR worker failed')
        except subprocess.TimeoutExpired as error:
            raise limit('OCR time limit exceeded') from error
        if progress is not None:
            progress(len(pages), len(selected))
        return OCRDocument(pages, engine,
            round(sum(p['confidence'] for p in pages) / len(pages), 6),
            round(time.perf_counter() - started, 6), identity)
    except OCRLimitExceeded as error:
        if error.partial is None:error.partial=limit(str(error)).partial
        raise
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
