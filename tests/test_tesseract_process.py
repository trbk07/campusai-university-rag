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
