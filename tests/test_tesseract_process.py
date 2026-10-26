"""Real subprocess fault boundaries, with synthetic protocol messages, not OCR accuracy."""
import json
import os
import subprocess
import time

import pytest

from campusai.ingestion.ocr import OCRLimitExceeded, OCRUnavailable
from campusai.ingestion.ocr_assets import TESSDATA_SHA256
from campusai.ingestion import tesseract_process as module


def worker(monkeypatch, body):
    original = subprocess.Popen
    processes = []
    monkeypatch.setattr(module, 'validate_tesseract_assets', lambda _: {'languages':'vie+eng'})
    ready = {'type':'ready','engine':'tesseract-vie-eng','model_sha256':TESSDATA_SHA256,
             'tesseract_version':'fault-fixture'}
    prefix = 'print('+repr(json.dumps(ready))+',flush=True);'
    script = 'import json,sys,time,os;json.load(sys.stdin);' + prefix + body
    def start(args, **kwargs):
        assert kwargs['env']['OMP_THREAD_LIMIT'] == '1'
        assert 'GEMINI_API_KEY' not in kwargs['env']
        assert 'PYTHONPATH' not in kwargs['env']
        process = original([args[0], '-I', '-u', '-c', script], **kwargs)
        processes.append(process)
        return process
    monkeypatch.setattr(module.subprocess, 'Popen', start)
    return processes


def recognize(tmp_path, **kwargs):
    return module.recognize_pdf(tmp_path/'input.pdf', [2], data_dir=tmp_path,
        scale=1.5, timeout_seconds=kwargs.pop('timeout_seconds', 5),
        progress=kwargs.pop('progress', None), **kwargs)


def test_worker_success_preserves_physical_page_and_parent_environment(tmp_path, monkeypatch):
    row={'type':'page','page':2,'text':'Verified source content','confidence':.97}
    body=';'.join('print('+repr(json.dumps(m))+',flush=True)' for m in
                  (row,{'type':'done'}))
    processes = worker(monkeypatch, body)
    monkeypatch.setenv('GEMINI_API_KEY','fixture-only-not-forwarded')
    before=dict(os.environ)
    output=recognize(tmp_path)
    assert output.pages==[{'page':2,'text':row['text'],'confidence':.97}]
    assert output.engine=='tesseract-vie-eng' and output.model_identity['languages']=='vie+eng'
    assert dict(os.environ)==before and processes[0].poll()==0


def test_deadline_terminates_a_worker_stuck_before_first_page(tmp_path, monkeypatch):
    processes = worker(monkeypatch, 'time.sleep(30)')
    started=time.monotonic()
    with pytest.raises(OCRLimitExceeded):
        recognize(tmp_path,timeout_seconds=.3)
    assert time.monotonic()-started < 3 and processes[0].poll() is not None


def test_cancel_terminates_a_worker_without_waiting_for_its_page(tmp_path, monkeypatch):
    processes = worker(monkeypatch, 'time.sleep(30)')
    started=time.monotonic()
    def cancel(completed,total):
        if time.monotonic()-started > .2:
            raise RuntimeError('job_cancelled')
    with pytest.raises(RuntimeError,match='job_cancelled'):
        recognize(tmp_path,progress=cancel)
    assert time.monotonic()-started < 3 and processes[0].poll() is not None


@pytest.mark.parametrize('body',[
    '',
    "print('not-json',flush=True)",
    "print(json.dumps({'type':'done'}),flush=True)",
    "print(json.dumps({'type':'page','page':7,'text':'wrong page','confidence':.99}),flush=True)",
    "print(json.dumps({'type':'page','page':2,'text':'invalid confidence','confidence':float('nan')}),flush=True)",
])
def test_incomplete_or_invalid_worker_output_fails_closed(tmp_path,monkeypatch,body):
    processes = worker(monkeypatch,body)
    with pytest.raises(OCRUnavailable):recognize(tmp_path)
    assert processes[0].poll() is not None


def test_timeout_after_recognition_does_not_return_a_partial_success(tmp_path,monkeypatch):
    body="print(json.dumps({'type':'page','page':2,'text':'partial text','confidence':.99}),flush=True);time.sleep(30)"
    processes=worker(monkeypatch,body)
    with pytest.raises(OCRLimitExceeded):recognize(tmp_path,timeout_seconds=.4)
    assert processes[0].poll() is not None


@pytest.mark.parametrize('lines', [None, [{'text': 'invalid', 'bbox': [1, 1, 0, 0]}],
    [{'text': 'invalid', 'bbox': [0, 0, float('nan'), 4]}]])
def test_invalid_hybrid_layout_fails_closed(tmp_path, monkeypatch, lines):
    row = {'type': 'page', 'page': 2, 'text': 'Text without reliable source geometry',
           'confidence': .99, 'lines': lines}
    processes = worker(monkeypatch, 'print('+repr(json.dumps(row))+',flush=True)')
    with pytest.raises(OCRUnavailable, match='layout'):
        recognize(tmp_path, include_layout=True)
    assert processes[0].poll() is not None


def test_hybrid_layout_cannot_silently_omit_recognized_body_text(tmp_path, monkeypatch):
    row = {'type': 'page', 'page': 2, 'text': 'Header\nImportant body evidence', 'confidence': .99,
           'lines': [{'text': 'Header', 'bbox': [0, 0, 20, 10]}]}
    processes = worker(monkeypatch, 'print('+repr(json.dumps(row))+',flush=True)')
    with pytest.raises(OCRUnavailable, match='mismatch'):
        recognize(tmp_path, include_layout=True)
    assert processes[0].poll() is not None


def test_deadline_also_covers_large_request_write_to_a_worker_that_never_reads(tmp_path, monkeypatch):
    import threading
    original = subprocess.Popen
    processes = []
    monkeypatch.setattr(module, 'validate_tesseract_assets', lambda _: {'languages': 'vie+eng'})
    def start(args, **kwargs):
        process = original([args[0], '-I', '-u', '-c', 'import time;time.sleep(30)'], **kwargs)
        processes.append(process)
        return process
    monkeypatch.setattr(module.subprocess, 'Popen', start)
    started = time.monotonic()
    with pytest.raises(OCRLimitExceeded):
        recognize(tmp_path, timeout_seconds=.3, include_layout=True,
                  hybrid_regions={2: [[0, 0, 100, 100]] * 6000})
    assert time.monotonic() - started < 3 and processes[0].poll() is not None
    assert not [thread for thread in threading.enumerate() if thread.name == 'local-ocr-input']
