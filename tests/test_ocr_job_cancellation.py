"""Cancellation and progress must remain responsive between OCR pages."""
from io import BytesIO
import threading
import time

import fitz
from PIL import Image,ImageDraw

from campusai.ingestion.jobs import IngestionJobManager


def scanned_pdf(path):
    with fitz.open() as pdf:
        for number in range(3):
            image=Image.new('RGB',(600,600),'white')
            ImageDraw.Draw(image).text((40,40),f'Scanned source page {number+1}',fill='black')
            stream=BytesIO();image.save(stream,format='PNG')
            page=pdf.new_page(width=300,height=300)
            page.insert_image(page.rect,stream=stream.getvalue())
        pdf.save(path)


def terminal(manager,identifier):
    deadline=time.monotonic()+5
    while time.monotonic()<deadline:
        job=manager.get(identifier)
        if job['state'] in {'cancelled','failed','review_required','succeeded'}:return job
        time.sleep(.01)
    raise AssertionError('OCR job did not reach a terminal state')


def install_engine(monkeypatch,blocked_page):
    import rapidocr_onnxruntime
    entered=threading.Event();release=threading.Event();calls=[]
    class Engine:
        def __call__(self,image):
            calls.append(image.shape)
            if len(calls)==blocked_page:
                entered.set()
                assert release.wait(5),'Test must release the active OCR page'
            text=f'Academic regulation source page {len(calls)}. Students register course credits.'
            return [([[0,0],[10,0],[10,10],[0,10]],text,.99)],None
    monkeypatch.setattr(rapidocr_onnxruntime,'RapidOCR',lambda **kwargs:Engine())
    return entered,release,calls


def test_cancelling_active_ocr_does_not_recognize_remaining_pages(tmp_path,monkeypatch):
    source=tmp_path/'three-scan-pages.pdf';scanned_pdf(source)
    entered,release,calls=install_engine(monkeypatch,1)
    manager=IngestionJobManager(max_workers=1)
    try:
        identifier=manager.submit(source,store_dir=tmp_path/'store',enable_ocr=True)
        assert entered.wait(5)
        assert manager.cancel(identifier)
        release.set()
        job=terminal(manager,identifier)
        assert job['state']=='cancelled' and not job['ready']
        assert len(calls)==1,'Cancellation must be checked before processing the next physical page'
    finally:
        release.set();manager.shutdown()


def test_ocr_exposes_page_progress_and_never_moves_progress_backwards(tmp_path,monkeypatch):
    source=tmp_path/'three-scan-pages.pdf';scanned_pdf(source)
    entered,release,calls=install_engine(monkeypatch,2)
    manager=IngestionJobManager(max_workers=1)
    original=manager._update;values=[]
    def observe(identifier,**updates):
        if 'progress' in updates:values.append(updates['progress'])
        return original(identifier,**updates)
    manager._update=observe
    try:
        identifier=manager.submit(source,store_dir=tmp_path/'store',enable_ocr=True)
        assert entered.wait(5)
        active=manager.get(identifier)
        assert active['stage']=='ocr' and active['progress']>.45
        release.set()
        job=terminal(manager,identifier)
        assert job['state']=='succeeded' and len(calls)==3
        assert values==sorted(values),'Later metadata stages must not reset completed OCR progress'
    finally:
        release.set();manager.shutdown()
