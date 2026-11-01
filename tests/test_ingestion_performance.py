"""Optimize work, not OCR resolution, coverage or the source/embedding contract."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from campusai.retrieval.dense_index import DenseIndex, HashEmbeddingProvider, IndexCorruptError
from campusai.ingestion.background.state import normalize_options
from campusai.ingestion.background import progressive


def records(count):
    return [{'chunk_id':f'p{n}', 'doc_id':'source', 'page':n, 'page_range':[n,n],
             'content':f'Source paragraph number {n}.', 'content_type':'text',
             'metadata':{'institution':'Fictional organization', 'source_name':'source.pdf'}}
            for n in range(1,count+1)]


def tracked_index():
    index=DenseIndex();calls=[]
    def encode(texts):
        calls.append(list(texts))
        return HashEmbeddingProvider().encode_documents(texts)
    index._encode=encode
    return index,calls


def test_incremental_vectors_match_full_build_and_encode_only_changed_inputs():
    previous=DenseIndex();previous.build(records(3),document_id='source')
    items=records(5);items[1]['content']='Corrected source paragraph.'
    current,calls=tracked_index();current.build(items,document_id='source',previous=previous)
    full=DenseIndex();full.build(items,document_id='source')
    assert current.vectors==full.vectors
    assert sum(map(len,calls))==3
    assert current.manifest['reused_vectors']==2
    assert current.search('Corrected source')==full.search('Corrected source')
    assert previous.items==records(3)


def test_progress_metadata_is_updated_without_reencoding_or_reusing_changed_semantics():
    previous=DenseIndex();previous.build(records(2),document_id='source')
    items=records(2)
    for item in items:item['metadata']['coverage_complete']=True
    current,calls=tracked_index();current.build(items,document_id='source',previous=previous)
    assert not calls and current.items==items and current.manifest['reused_vectors']==2
    items=deepcopy(items);items[0]['metadata']['institution']='A different organization'
    changed,calls=tracked_index();changed.build(items,document_id='source',previous=current)
    assert sum(map(len,calls))==1 and changed.manifest['reused_vectors']==1


@pytest.mark.parametrize('change', ['revision','document','corruption'])
def test_reuse_rejects_incompatible_or_corrupt_previous_vectors(change):
    previous=DenseIndex();previous.build(records(2),document_id='source')
    if change=='revision':previous.model_revision='another-revision'
    if change=='document':previous.manifest['document_id']='another-source'
    if change=='corruption':previous.vectors[0][0]=float('nan')
    current,calls=tracked_index();current.build(records(2),document_id='source',previous=previous)
    assert sum(map(len,calls))==2 and current.manifest['reused_vectors']==0


def test_corrupt_numeric_vectors_cannot_be_loaded_even_with_a_matching_checksum(tmp_path):
    index=DenseIndex();index.build(records(1),document_id='source')
    index.vectors[0][0]=float('nan');index.save(tmp_path/'dense.json')
    with pytest.raises(IndexCorruptError):DenseIndex.load(tmp_path/'dense.json')


def test_managed_snapshot_updates_coverage_without_reencoding_and_retains_old_index_on_failure(tmp_path, monkeypatch):
    import threading
    from campusai.schemas import Document,Chunk
    from campusai.ingestion.background.commit import build_indexes
    from campusai.retrieval.index_builder import build_document_indexes
    from campusai.retrieval.bm25_index import BM25Index
    ident='a'*64;job='b'*32;root=tmp_path/'index'
    document=Document(ident,'source.pdf',3,language='en',metadata={'coverage_complete':False},
                      chunks=[Chunk('one',ident,1,'The source policy is unchanged.')])
    manager=SimpleNamespace(_lock=threading.RLock(),_checkpoint=lambda _:None)
    options=normalize_options({'index_dir':root})
    calls=[];original=HashEmbeddingProvider.encode_documents
    def encode(self,texts):calls.append(len(texts));return original(self,texts)
    monkeypatch.setattr(HashEmbeddingProvider,'encode_documents',encode)
    build_indexes(manager,job,document,options,build_document_indexes)
    calls.clear();document.metadata['coverage_complete']=True
    build_indexes(manager,job,document,options,build_document_indexes)
    assert not calls
    assert DenseIndex.load(root/ident/'dense.json').items[0]['metadata']['coverage_complete'] is True
    assert BM25Index.load(root/ident/'bm25.json').items[0]['metadata']['coverage_complete'] is True
    before=(root/ident/'dense.json').read_bytes()
    document.chunks.append(Chunk('two',ident,2,'A new source paragraph.'))
    def fail_after_staging(*args,**kwargs):
        build_document_indexes(*args,**kwargs)
        raise ValueError('job_cancelled')
    with pytest.raises(ValueError,match='job_cancelled'):
        build_indexes(manager,job,document,options,fail_after_staging)
    assert (root/ident/'dense.json').read_bytes()==before
    assert not (root/'.jobs'/job).exists()


def run_progressive(monkeypatch, *, elapsed=1., stalled=False):
    remaining=list(range(1,21));batches=[];clock=[0.]
    monkeypatch.setattr(progressive.time,'monotonic',lambda:clock[0])
    def ingest(path, *, enable_ocr, **options):
        if enable_ocr:
            batches.append(options['ocr_max_pages']);clock[0]+=elapsed
            if not stalled:del remaining[:options['ocr_max_pages']]
        return SimpleNamespace(page_count=20,chunks=[],metadata={'unread_pages':list(remaining)})
    manager=SimpleNamespace(_jobs={'job':SimpleNamespace(source_path='source.pdf')},_checkpoint=lambda _:None)
    options=normalize_options({'enable_ocr':True,'ocr_max_pages':16,'ocr_timeout_seconds':120})
    document=progressive.ingest_progressively(manager,'job',options,lambda *a:None,ingest)
    return batches,document


def test_progressive_ocr_keeps_first_snapshot_small_then_amortizes_work(monkeypatch):
    batches,document=run_progressive(monkeypatch)
    assert batches==[4,8,16] and not document.metadata['unread_pages']


def test_slow_ocr_shrinks_batches_and_stalled_ocr_never_retries_automatically(monkeypatch):
    batches,document=run_progressive(monkeypatch,elapsed=80.)
    assert batches[0]==4 and batches[1]==1 and not document.metadata['unread_pages']
    batches,document=run_progressive(monkeypatch,stalled=True)
    assert batches==[4] and len(document.metadata['unread_pages'])==20


def parallel_setup(monkeypatch,worker):
    import threading
    from campusai.ingestion import tesseract_process as process
    monkeypatch.setattr(process,'_PAGE_WORKER_LIMIT',2)
    monkeypatch.setattr(process,'_PAGE_SLOTS',threading.BoundedSemaphore(2))
    monkeypatch.setattr(process,'_recognize_one',worker)
    return process


def page_result(numbers):
    from campusai.ingestion.ocr import OCRDocument
    return OCRDocument([{'page':n,'text':f'Physical page {n}','confidence':.95,
                        'lines':[{'text':f'Physical page {n}','bbox':[0,0,10,10]}]} for n in numbers],
                       'test-ocr',.95,.1,{'model_sha256':{'test':'pinned'}})


def test_parallel_ocr_keeps_physical_order_layout_and_caller_thread_progress(monkeypatch):
    import threading
    barrier=threading.Barrier(2);threads=set();progress=[]
    def worker(path,numbers,**options):
        threads.add(threading.get_ident());barrier.wait(timeout=2)
        options['progress'](len(numbers),len(numbers))
        return page_result(numbers)
    process=parallel_setup(monkeypatch,worker);selected=[8,3,7,1,6,2,5,4]
    main=threading.get_ident()
    result=process.recognize_pdf('source.pdf',selected,data_dir='models',scale=1.5,timeout_seconds=3,
        progress=lambda done,total:progress.append((threading.get_ident(),done,total)),include_layout=True)
    assert len(threads)==2 and all(ident==main for ident,_,_ in progress)
    assert [page['page'] for page in result.pages]==selected
    assert result.pages==page_result(selected).pages
    assert result.average_confidence==.95 and progress[-1][1:]==(8,8)


def test_parallel_ocr_timeout_keeps_completed_physical_pages(monkeypatch):
    from campusai.ingestion.ocr import OCRLimitExceeded
    def worker(path,numbers,**options):
        if 2 in numbers:raise OCRLimitExceeded('timeout',partial=page_result(numbers[:2]))
        return page_result(numbers)
    process=parallel_setup(monkeypatch,worker)
    with pytest.raises(OCRLimitExceeded) as caught:
        process.recognize_pdf('source.pdf',list(range(1,9)),data_dir='models',scale=1.5,
                              timeout_seconds=3,progress=None)
    assert [page['page'] for page in caught.value.partial.pages]==[1,2,3,4,5,7]


def test_parallel_ocr_cancellation_stops_both_workers_and_preserves_original_error(monkeypatch):
    import time
    processed=[]
    def worker(path,numbers,**options):
        for index,number in enumerate(numbers):
            options['progress'](index,len(numbers));time.sleep(.03);processed.append(number)
        return page_result(numbers)
    process=parallel_setup(monkeypatch,worker)
    def progress(done,total):
        if done:raise ValueError('job_cancelled')
    with pytest.raises(ValueError,match='job_cancelled'):
        process.recognize_pdf('source.pdf',list(range(1,9)),data_dir='models',scale=1.5,
                              timeout_seconds=3,progress=progress)
    assert len(processed)<8


def test_parallel_ocr_honors_global_worker_limit_across_documents(monkeypatch):
    import threading,time
    from concurrent.futures import ThreadPoolExecutor
    active=[0,0];lock=threading.Lock()
    def worker(path,numbers,**options):
        with lock:active[0]+=1;active[1]=max(active)
        try:
            time.sleep(.02)
            return page_result(numbers)
        finally:
            with lock:active[0]-=1
    process=parallel_setup(monkeypatch,worker)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(process.recognize_pdf,'source.pdf',list(range(1,9)),data_dir='models',
            scale=1.5,timeout_seconds=3,progress=None) for _ in range(2)]
        assert all(len(future.result().pages)==8 for future in futures)
    assert active[0]==0 and active[1]<=2


def test_large_ocr_batch_uses_four_bounded_workers_and_preserves_order(monkeypatch):
    import threading
    barrier=threading.Barrier(4);threads=set()
    def worker(path,numbers,**options):
        threads.add(threading.get_ident());barrier.wait(timeout=2)
        return page_result(numbers)
    process=parallel_setup(monkeypatch,worker)
    monkeypatch.setattr(process,'_PAGE_WORKER_LIMIT',4)
    monkeypatch.setattr(process,'_PAGE_SLOTS',threading.BoundedSemaphore(4))
    result=process.recognize_pdf('source.pdf',list(range(1,17)),data_dir='models',scale=1.5,
                                 timeout_seconds=3,progress=None)
    assert len(threads)==4 and result.pages==page_result(list(range(1,17))).pages
    assert result.model_identity['page_workers']==4


def print_image(height=8, *, columns=False, lines=8):
    from PIL import Image,ImageDraw
    image=Image.new('L',(400,400),255);draw=ImageDraw.Draw(image)
    ranges=[(30,170),(230,370)] if columns else [(30,370)]
    for index in range(lines):
        for left,right in ranges:
            for x in range(left,right,6):draw.rectangle((x,20+index*40,x+2,19+index*40+height),fill=0)
    return image


def test_ocr_extra_pixels_target_small_single_column_text_only():
    from campusai.ingestion.tesseract_worker import text_render_scale
    assert text_render_scale(print_image(),1.5)==3.
    assert text_render_scale(print_image(16),1.5)==1.5
    assert text_render_scale(print_image(columns=True),1.5)==1.5
    assert text_render_scale(print_image(lines=3),1.5)==1.5
    assert text_render_scale(print_image(),4.)==4.
    assert text_render_scale(print_image().point(lambda value:170 if value else 20),1.5)==1.5


def test_ocr_grayscale_rerender_keeps_clip_origin_and_original_page():
    import io
    import pymupdf as fitz
    from campusai.ingestion.tesseract_worker import render_page
    image=print_image();stream=io.BytesIO();image.save(stream,format='PNG')
    with fitz.open() as pdf:
        page=pdf.new_page(width=250,height=240)
        region=fitz.Rect(30,20,230,220)
        page.insert_image(region,stream=stream.getvalue())
        pix,rendered,scale=render_page(page,1.5,clip=region)
        assert scale>1.5 and rendered.mode=='L' and pix.n==1
        assert abs(pix.x/scale-region.x0)<1/scale and abs(pix.y/scale-region.y0)<1/scale
        assert list(page.rect)==[0,0,250,240]
        assert len(pdf)==1


def test_ocr_requested_pixel_limit_is_not_bypassed_by_adaptive_scaling():
    import pymupdf as fitz
    from campusai.ingestion.tesseract_worker import render_page
    with fitz.open() as pdf:
        page=pdf.new_page(width=4000,height=4000)
        with pytest.raises(ValueError,match='pixel limit'):render_page(page,1.5)


def test_ocr_coloured_regions_keep_the_original_rgb_pixels_and_resolution():
    import io
    import pymupdf as fitz
    from PIL import Image
    from campusai.ingestion.tesseract_worker import render_page
    image=Image.new('RGB',(200,200),(30,80,130));stream=io.BytesIO();image.save(stream,format='PNG')
    with fitz.open() as pdf:
        page=pdf.new_page(width=100,height=100);page.insert_image(page.rect,stream=stream.getvalue())
        pix,rendered,scale=render_page(page,1.5)
        original=page.get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False,colorspace=fitz.csRGB)
        assert rendered.mode=='RGB' and pix.n==3 and scale==1.5
        assert pix.samples==original.samples


def test_new_ocr_policy_reprocesses_legacy_checkpoints_then_reuses_current_results(tmp_path,monkeypatch):
    import json,hashlib
    from campusai.ingestion import pipeline
    from campusai.ingestion.ocr import OCRDocument
    from campusai.ingestion.tesseract_worker import RENDER_POLICY
    source=tmp_path/'source.pdf';source.write_bytes(b'controlled source identity for the mocked parser')
    store=tmp_path/'store';calls=[]
    monkeypatch.setattr(pipeline,'validate_pdf',lambda *a,**k:SimpleNamespace(pages=1,warnings=[]))
    monkeypatch.setattr(pipeline,'parse_pdf',lambda *a,**k:[{'page':1,'text':'','requires_ocr':True,'lines_meta':[]}])
    monkeypatch.setattr(pipeline,'extract_tables',lambda *a,**k:[])
    def recognize(*a,**k):
        calls.append(True)
        return OCRDocument([{'page':1,'text':f'Readable reference paragraph from recognition pass {len(calls)}.',
                             'confidence':.95}], 'tesseract-vie-eng',.95,.1,{'render_policy':RENDER_POLICY})
    monkeypatch.setattr(pipeline,'_bounded_ocr',recognize)
    options=dict(store_dir=store,enable_ocr=True,ocr_backend='tesseract',allow_partial=True)
    first=pipeline.ingest_document(source,**options)
    meta=store/first.doc_id/'meta.json';pages=meta.with_name('ocr-pages.json')
    saved=json.loads(meta.read_text(encoding='utf-8'));raw=json.loads(pages.read_text(encoding='utf-8'))
    saved['metadata']['ocr_resume_identity'].pop('render_policy')
    saved['metadata']['ocr']['model_identity'].pop('render_policy')
    raw['ocr']['model_identity'].pop('render_policy')
    encoded=json.dumps(raw).encode('utf-8');pages.write_bytes(encoded)
    saved['metadata']['ocr_pages_sha256']=hashlib.sha256(encoded).hexdigest()
    meta.write_text(json.dumps(saved),encoding='utf-8')
    native=pipeline.ingest_document(source,**{**options,'enable_ocr':False})
    assert not native.cached and native.metadata['unread_pages']==[1]
    assert len(calls)==1
    current=pipeline.ingest_document(source,**options)
    assert len(calls)==2 and not current.cached and 'pass 2' in current.chunks[0].content
    assert current.metadata['ocr']['model_identity']['render_policy']==RENDER_POLICY
    cached=pipeline.ingest_document(source,**options)
    assert cached.cached and len(calls)==2


@pytest.mark.parametrize('progressive',[False,True])
def test_upgraded_ocr_upload_has_a_new_identity_without_invalidating_the_old_journal(progressive):
    import json,hashlib
    from campusai.ingestion.background.state import job_identity,accepted_job_identities
    from campusai.ingestion.docling_parser import TEXT_COVERAGE_VERSION
    from campusai.ingestion.table_extractor import TABLE_EXTRACTOR_VERSION
    options=normalize_options({'enable_ocr':True,'ocr_backend':'tesseract','progressive_ocr':progressive})
    prior={key:value for key,value in options.items() if key!='progressive_ocr' or value}
    old=hashlib.sha256(json.dumps({'source_sha256':'c'*64,'options':prior,
        'text_coverage_version':TEXT_COVERAGE_VERSION,'table_extractor_version':TABLE_EXTRACTOR_VERSION},
        sort_keys=True,separators=(',',':')).encode()).hexdigest()
    assert old in accepted_job_identities('c'*64,options)
    assert job_identity('c'*64,options)!=old
    assert job_identity('c'*64,options)==job_identity('c'*64,dict(options))


@pytest.mark.parametrize('kind',['legacy','current','native','disabled'])
def test_ready_upload_only_bypasses_ingestion_when_its_ocr_policy_is_current(tmp_path,kind):
    import threading
    from campusai.web_documents import WebDocuments,WebError
    from campusai.ingestion.jobs import JobQueueFull
    from campusai.ingestion.tesseract_worker import RENDER_POLICY
    metadata={} if kind=='native' else {'ocr':{'backend':'tesseract','model_identity':
        {'render_policy':RENDER_POLICY} if kind=='current' else {}}}
    calls=[]
    def prepare(*a,**k):
        calls.append(True);raise JobQueueFull('test capacity gate before any file write')
    api=WebDocuments.__new__(WebDocuments)
    api.application=SimpleNamespace(ingestion_defaults={'enable_ocr':kind!='disabled','ocr_backend':'tesseract'},
        jobs=SimpleNamespace(prepare_upload=prepare),jobs_snapshot=lambda:{'jobs':[]})
    api.store=tmp_path;api.uploads=tmp_path/'uploads';api.max_mb=50
    api.lock=threading.RLock()
    api._registry=SimpleNamespace(get=lambda _:{'metadata':metadata})
    api.public_document=lambda _:{'ready':True}
    if kind=='legacy':
        with pytest.raises(WebError) as caught:api._upload(b'%PDF-test','source.pdf',{})
        assert caught.value.code=='ingestion_busy' and calls==[True]
        assert not api.uploads.exists()
    else:
        assert api._upload(b'%PDF-test','source.pdf',{})['duplicate'] is True
        assert not calls


@pytest.mark.parametrize('language',['en','vi'])
@pytest.mark.parametrize('size',[20,24,28])
def test_real_ocr_small_print_keeps_character_error_below_two_percent(language,size,monkeypatch):
    """Optional local integration: pinned OCR assets and a fixed Windows font.

    The reference creates only the source image; the recognizer receives pixels,
    never reference text. Nothing is written to the document library or Git.
    """
    import io,os,unicodedata
    from pathlib import Path
    data=Path(os.environ.get('CAMPUSAI_OCR_TEST_DATA_DIR','.cache/ocr/tessdata_fast'))
    font_path=Path('C:/Windows/Fonts/arial.ttf')
    if not (data/'vie.traineddata').exists() or not font_path.exists():
        pytest.skip('pinned local OCR assets and Windows Arial are required')
    monkeypatch.setenv('OMP_THREAD_LIMIT','1')
    tesserocr=pytest.importorskip('tesserocr')
    import pymupdf as fitz
    from PIL import Image,ImageDraw,ImageFont
    from campusai.ingestion.ocr_assets import validate_tesseract_assets
    from campusai.ingestion.tesseract_worker import render_page
    validate_tesseract_assets(data)
    lines=[(f'Record {n:02d}: minimum workload {110+n} credits; deadline 17 August 2025.' if language=='en' else
            f'Mục {n:02d}: người học cần đạt {110+n} tín chỉ; hạn nộp ngày 17 tháng 8 năm 2025.') for n in range(1,13)]
    image=Image.new('RGB',(2000,1600),'white');draw=ImageDraw.Draw(image)
    for index,line in enumerate(lines):
        draw.text((120,120+index*90),line,font=ImageFont.truetype(str(font_path),size),fill='black')
    stream=io.BytesIO();image.save(stream,format='PNG')
    with fitz.open() as pdf:
        page=pdf.new_page(width=500,height=400);page.insert_image(page.rect,stream=stream.getvalue())
        _,rendered,scale=render_page(page,1.5)
        mode=tesserocr.PSM.SINGLE_BLOCK if scale>1.5*1.05 else tesserocr.PSM.AUTO
        with tesserocr.PyTessBaseAPI(path=str(data),lang='vie+eng',psm=mode,oem=tesserocr.OEM.LSTM_ONLY) as api:
            api.SetImage(rendered);actual=api.GetUTF8Text()
    normalize=lambda text:' '.join(unicodedata.normalize('NFC',text).split())
    expected=normalize('\n'.join(lines));actual=normalize(actual)
    previous=list(range(len(expected)+1))
    for index,char in enumerate(actual,1):
        current=[index]
        for pos,reference in enumerate(expected,1):
            current.append(min(current[-1]+1,previous[pos]+1,previous[pos-1]+(char!=reference)))
        previous=current
    assert previous[-1]/len(expected)<=.02
