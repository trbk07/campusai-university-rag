"""Pinned assets, bounded inference and existing isolated OCR fault boundary."""
import hashlib
import json
import subprocess
import time

import pytest

from campusai.ingestion import ocr_assets, tesseract_process
from campusai.ingestion.background.state import normalize_options
from campusai.ingestion.ocr import OCRLimitExceeded, OCRUnavailable, ocr_pdf
from campusai.ingestion.vietocr_worker import reading_order


def test_assets_are_local_pinned_and_wrong_bytes_fail_closed(tmp_path,monkeypatch):
    expected={name:hashlib.sha256(name.encode()).hexdigest() for name in ocr_assets.VIETOCR_SHA256}
    monkeypatch.setattr(ocr_assets,'VIETOCR_SHA256',expected)
    monkeypatch.setattr(ocr_assets,'VIETOCR_BYTES',{name:len(name.encode()) for name in expected})
    monkeypatch.setattr(ocr_assets,'version',lambda name:'2.14.0+cu126' if name=='torch' else '1.4.4')
    for name in expected:(tmp_path/name).write_text(name)
    assert ocr_assets.validate_vietocr_assets(tmp_path)['model_sha256']==expected
    (tmp_path/'vgg_seq2seq.pth').write_text('wrong checkpoint')
    with pytest.raises(ValueError,match='checksum'):
        ocr_assets.validate_vietocr_assets(tmp_path)


@pytest.mark.parametrize('torch_version,rapid_version',[('2.1.0','1.4.4'),('3.0.0','1.4.4'),('2.14.0','1.4.5')])
def test_unqualified_package_versions_are_rejected(tmp_path,monkeypatch,torch_version,rapid_version):
    monkeypatch.setattr(ocr_assets,'version',lambda name:torch_version if name=='torch' else rapid_version)
    with pytest.raises(ValueError):ocr_assets.validate_vietocr_assets(tmp_path)


def line(text,x,y,width=30,height=10):
    return {'text':text,'bbox':[x,y,x+width,y+height]}


def test_two_prose_columns_are_read_column_by_column():
    left=[line('left '+str(i),10,20*i,width=80) for i in range(3)]
    right=[line('right '+str(i),140,20*i,width=80) for i in range(3)]
    assert reading_order([*right,*left])==left+right


def test_table_cells_keep_physical_rows_despite_different_font_heights():
    cells=[line('CODE1001',10,100,70,12),line('3',180,99,8,10),line('30',230,101,12,11),
           line('CODE1002',10,120,70,10),line('4',180,119,8,10),line('40',230,121,12,10)]
    assert [row['text'] for row in reading_order(list(reversed(cells)),ruled=True)]==[
        'CODE1001','3','30','CODE1002','4','40']


def test_numeric_unruled_table_is_not_split_into_prose_columns():
    cells=[line(str(i),10,y) for i,y in enumerate([0,20,40])]+[line(str(i),140,y) for i,y in enumerate([0,20,40])]
    assert [row['bbox'][0] for row in reading_order(cells)]==[10,140,10,140,10,140]


def protocol_worker(monkeypatch,body,*,bad_identity=False):
    original=subprocess.Popen;processes=[]
    monkeypatch.setattr(tesseract_process,'validate_vietocr_assets',lambda _: {'engine':'vietocr-vgg-seq2seq-v1'})
    ready={'type':'ready','engine':'vietocr-vgg-seq2seq-v1','model_sha256':ocr_assets.VIETOCR_SHA256,'device':'cpu'}
    if bad_identity:ready['model_sha256']={}
    script='import json,sys,time;json.load(sys.stdin);print('+repr(json.dumps(ready))+',flush=True);'+body
    def start(args,**kwargs):
        assert args[-1].endswith('vietocr_worker.py') and 'GEMINI_API_KEY' not in kwargs['env']
        process=original([args[0],'-I','-u','-c',script],**kwargs);processes.append(process);return process
    monkeypatch.setattr(tesseract_process.subprocess,'Popen',start)
    return processes


def test_backend_uses_same_page_protocol_and_preserves_parent_environment(tmp_path,monkeypatch):
    page={'type':'page','page':2,'text':'Recognized actual source','confidence':.98}
    body=';'.join('print('+repr(json.dumps(row))+',flush=True)' for row in [page,{'type':'done'}])
    processes=protocol_worker(monkeypatch,body)
    monkeypatch.setenv('GEMINI_API_KEY','fixture-not-forwarded')
    out=tesseract_process.recognize_pdf(tmp_path/'source.pdf',[2],backend='vietocr',data_dir=tmp_path,
        scale=2.,timeout_seconds=5,progress=None)
    assert out.engine=='vietocr-vgg-seq2seq-v1' and out.pages[0]['page']==2
    assert out.model_identity['device']=='cpu' and processes[0].poll()==0


@pytest.mark.parametrize('fault',['timeout','cancel','identity'])
def test_vietnamese_worker_is_killed_on_failure_or_cancellation(tmp_path,monkeypatch,fault):
    processes=protocol_worker(monkeypatch,'time.sleep(30)',bad_identity=fault=='identity')
    started=time.monotonic()
    def progress(*_):
        if fault=='cancel' and time.monotonic()-started>.2:raise RuntimeError('job_cancelled')
    expected=OCRUnavailable if fault=='identity' else OCRLimitExceeded if fault=='timeout' else RuntimeError
    with pytest.raises(expected):
        tesseract_process.recognize_pdf(tmp_path/'source.pdf',[1],backend='vietocr',data_dir=tmp_path,
            scale=2.,timeout_seconds=.4,progress=progress)
    assert processes[0].poll() is not None and time.monotonic()-started<3


def test_backend_is_explicit_and_has_a_distinct_job_identity():
    from campusai.ingestion.background.state import job_identity
    old=normalize_options({});new=normalize_options({'ocr_backend':'vietocr','ocr_data_dir':'.cache/ocr/vietocr'})
    assert old['ocr_backend']=='rapidocr' and job_identity('a'*64,old)!=job_identity('a'*64,new)


def test_native_pdf_does_not_load_ocr_models_or_invalidate_its_cache(tmp_path,monkeypatch):
    import pymupdf
    from campusai.ingestion import pipeline
    source=tmp_path/'native.pdf'
    with pymupdf.open() as pdf:
        page=pdf.new_page();page.insert_text((40,80),'Actual native source content for extraction.')
        pdf.save(source)
    monkeypatch.setattr(pipeline,'ocr_pdf',lambda *a,**kw:pytest.fail('native page must not load OCR'))
    first=pipeline.ingest_document(source,store_dir=tmp_path/'store',enable_ocr=True,
        ocr_backend='vietocr',ocr_data_dir=tmp_path/'missing-models')
    second=pipeline.ingest_document(source,store_dir=tmp_path/'store',enable_ocr=True,
        ocr_backend='vietocr',ocr_data_dir=tmp_path/'missing-models')
    assert first.status=='succeeded' and second.cached and first.chunks==second.chunks
    assert first.metadata['parser_version']=='pymupdf-text-v1' and not first.metadata.get('ocr')


def test_checkpoint_loader_uses_restricted_torch_loading(monkeypatch):
    torch=pytest.importorskip('torch')
    from campusai.ingestion import vietocr_recognizer as module
    class Model:
        def load_state_dict(self,value,strict): assert value=={'fixture':1} and strict
        def to(self,device): assert device=='cpu';return self
        def eval(self):return self
    calls=[]
    def load(path,**kwargs):calls.append((path,kwargs));return {'fixture':1}
    monkeypatch.setattr(module,'Model',Model);monkeypatch.setattr(torch,'load',load)
    module.Recognizer('fixture.pth',device='cpu')
    assert calls==[('fixture.pth',{'map_location':'cpu','weights_only':True})]


def test_no_eos_or_special_tokens_cannot_become_valid_ocr_text():
    torch=pytest.importorskip('torch')
    from PIL import Image
    from campusai.ingestion.vietocr_recognizer import Recognizer
    class Decoder:
        def __init__(self,token):self.token=token;self.count=0
        def __call__(self,value,hidden,encoded):
            logits=torch.zeros((len(value),233))
            logits[:,2 if self.token==0 and self.count else self.token]=10
            self.count+=1
            return logits,hidden
    from types import SimpleNamespace
    for token in [0,4]:
        recognizer=Recognizer.__new__(Recognizer);recognizer.device='cpu'
        recognizer.model=SimpleNamespace(cnn=SimpleNamespace(model=lambda value:value),
            transformer=SimpleNamespace(encoder=lambda value:(value,None),decoder=Decoder(token)))
        assert recognizer.predict([Image.new('RGB',(20,20))])==[('',0.)]
    with pytest.raises(ValueError):recognizer.predict([],batch_size=0)
