"""Indexing/query identity and singleton tests with an explicit fake encoder."""
from concurrent.futures import ThreadPoolExecutor
import json
from types import SimpleNamespace
import sys

import pytest

from campusai.deployment.runtime.models import pinned_retriever, ingestion_settings
from campusai.ingestion.jobs import IngestionJobManager
from campusai.retrieval import model_runtime
from campusai.retrieval.dense_index import DenseIndex, IndexVersionMismatchError, IndexNotFoundError
from campusai.retrieval.hybrid import HybridRetriever
from campusai.retrieval.index_builder import build_document_indexes
from campusai.schemas import Chunk, Document
from tests.deployment.test_cloud_configuration import prerequisites
from tests.test_web_documents import pdf_bytes


def runtime_fixture(tmp_path,monkeypatch):
    settings = prerequisites(tmp_path,monkeypatch)
    runtime, loaded = model_runtime.RetrievalModelRuntime(), []
    class Batch(list):
        def tolist(self): return list(self)
    class Encoder:
        def __init__(self,*args,**kwargs): loaded.append((args,kwargs))
        def encode(self,texts,**_kwargs): return Batch([[1.0,0.0,0.0] for _ in texts])
    monkeypatch.setitem(sys.modules,'sentence_transformers',SimpleNamespace(SentenceTransformer=Encoder))
    monkeypatch.setattr(model_runtime,'_RUNTIME',runtime)
    retriever = pinned_retriever(settings)
    return settings,runtime,retriever,loaded


def test_concurrent_queries_share_one_verified_offline_cpu_encoder(tmp_path,monkeypatch):
    settings,runtime,_retriever,loaded = runtime_fixture(tmp_path,monkeypatch)
    with ThreadPoolExecutor(max_workers=8) as workers:
        models = list(workers.map(lambda _i:runtime.get_encoder(settings.dense_model,'cpu',
                         revision=settings.dense_revision),range(20)))
    assert all(model is models[0] for model in models) and len(loaded)==1
    args,options = loaded[0]
    assert args == (str(settings.dense_snapshot),)
    assert options == {'device':'cpu','local_files_only':True,'trust_remote_code':False,
                       'model_kwargs':{'torch_dtype':'float32'}}
    assert runtime.loaded_models()[0]['revision'] == settings.dense_revision
    with pytest.raises(ValueError):
        runtime.get_encoder(settings.dense_model,'cuda',revision=settings.dense_revision)
    with pytest.raises(ValueError):
        runtime.get_encoder(settings.dense_model,'cpu',revision='a'*40)
    with pytest.raises(ValueError):
        runtime.register_encoder_snapshot(settings.dense_model,settings.dense_revision,
                                         settings.dense_snapshot,'a'*64)


def test_builder_persists_revision_and_query_uses_the_same_singleton(tmp_path,monkeypatch):
    settings,runtime,retriever,loaded = runtime_fixture(tmp_path,monkeypatch)
    for doc_id in ('document-a','document-b'):
        doc = Document(doc_id,doc_id+'.pdf',1,language='en',
                       chunks=[Chunk(doc_id+'-c1',doc_id,1,'Stack removes the most recently added item.')])
        build_document_indexes(doc,settings.indexes,dense_model=settings.dense_model,
                               model_revision=settings.dense_revision)
        dense = DenseIndex.load(settings.indexes/doc_id/'dense.json')
        assert dense.manifest['model_revision'] == settings.dense_revision
    results = retriever.search('Which item does a stack remove?',mode='hybrid_rrf')
    assert {r.doc_id for r in results} == {'document-a','document-b'}
    assert len(loaded) == 1 and len(runtime.loaded_models()) == 1


def test_ingestion_worker_forwards_the_pinned_revision_to_indexing(tmp_path,monkeypatch):
    settings,_runtime,retriever,loaded = runtime_fixture(tmp_path,monkeypatch)
    source = tmp_path/'Enrollment.pdf'
    source.write_bytes(pdf_bytes())
    manager = IngestionJobManager()
    try:
        job_id = manager.submit(source,**ingestion_settings(settings))
        manager._futures[job_id].result(timeout=5)
        job = manager.get(job_id)
        assert job['state'] == 'succeeded'
        doc_id = job['document_id']
        retriever.load_document(doc_id)
        assert retriever._indexes[doc_id][1].model_revision == settings.dense_revision
        assert len(loaded) == 1
    finally:
        manager.shutdown()


def test_legacy_or_missing_dense_index_is_rejected_without_rewriting_it(tmp_path,monkeypatch):
    settings,_runtime,retriever,_loaded = runtime_fixture(tmp_path,monkeypatch)
    doc = Document('legacy','legacy.pdf',1,language='en',
                   chunks=[Chunk('c1','legacy',1,'An original source statement.')])
    build_document_indexes(doc,settings.indexes,dense_model=settings.dense_model)
    path = settings.indexes/'legacy/dense.json'
    before = path.read_bytes()
    with pytest.raises(IndexVersionMismatchError): retriever.load_document('legacy')
    assert path.read_bytes() == before
    path.unlink()
    with pytest.raises(IndexNotFoundError): retriever.load_document('legacy')
    # Existing local/evaluation adapters retain their legacy BM25-only contract.
    HybridRetriever(settings.indexes).load_document('legacy')
    with pytest.raises(ValueError): HybridRetriever(settings.indexes,dense_model_revision='a'*40)
