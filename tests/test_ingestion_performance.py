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
