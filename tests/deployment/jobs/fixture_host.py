"""Isolated process-fault host; Hash embeddings/test provider only, never production."""
import argparse
import json
import os
from pathlib import Path
import threading
import uuid

from campusai.api import CampusAIApplication
from campusai.deployment.local_server import make_local_server
from campusai.ingestion import jobs
from campusai.ingestion import pipeline
from campusai.ingestion.background import journal
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.service import CampusAIQueryService
from campusai.retrieval.hybrid import HybridRetriever
from campusai.retrieval import index_builder
from campusai.web import make_wsgi_app
from tests.test_web_documents import LocalEvidenceLLM


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--hold',default='none')
    parser.add_argument('--instance',required=True)
    args=parser.parse_args()
    root=args.root.resolve()
    if not root.is_relative_to(Path.cwd().resolve()/'.tmp'):
        parser.error('Fault fixtures must stay inside workspace .tmp')
    root.mkdir(parents=True,exist_ok=True)
    (root/'index').mkdir(exist_ok=True)
    instance=args.instance
    def hold(stage):
        if args.hold != stage: return
        checkpoint={'stage':stage,'pid':os.getpid(),'instance':instance}
        with (root/'checkpoint.json').open('w',encoding='utf-8') as output:
            json.dump(checkpoint,output);output.flush();os.fsync(output.fileno())
        print(json.dumps(checkpoint),flush=True)
        while True: threading.Event().wait(1)

    manager=jobs.IngestionJobManager(journal_path=root/'operations/jobs.sqlite3')
    if args.hold=='upload_before_write':
        original=manager.prepare_upload
        def prepare(*a,**kw):
            result=original(*a,**kw);hold('upload_before_write');return result
        manager.prepare_upload=prepare
    if args.hold=='upload_partial':
        original_open=Path.open
        class PartialWriter:
            def __init__(self,handle):self.handle=handle
            def __enter__(self):return self
            def __exit__(self,*args):return self.handle.__exit__(*args)
            def write(self,data):
                self.handle.write(data[:len(data)//2]);self.handle.flush();os.fsync(self.handle.fileno())
                hold('upload_partial')
            def flush(self):return self.handle.flush()
            def fileno(self):return self.handle.fileno()
        def opening(path,*a,**kw):
            handle=original_open(path,*a,**kw)
            return PartialWriter(handle) if path.name.startswith('.uploading-') and a and a[0]=='xb' else handle
        Path.open=opening
    if args.hold=='upload_complete':
        from campusai import web_documents
        original=web_documents.validate_pdf
        def validate(*a,**kw):
            result=original(*a,**kw);hold('upload_complete');return result
        web_documents.validate_pdf=validate
    if args.hold=='upload_renamed':
        original=manager.activate
        def activate(*a,**kw):hold('upload_renamed');return original(*a,**kw)
        manager.activate=activate
    if args.hold=='parsing':
        original=pipeline.parse_pdf
        def parse(*a,**kw):
            result=original(*a,**kw);hold('parsing');return result
        pipeline.parse_pdf=parse
    if args.hold=='persisting':
        original=pipeline.atomic_text
        def atomic(path,*a,**kw):
            result=original(path,*a,**kw)
            if Path(path).name=='meta.json':hold('persisting')
            return result
        pipeline.atomic_text=atomic
    if args.hold in {'index_bm25','index_dense'}:
        kind=index_builder.BM25Index if args.hold=='index_bm25' else index_builder.DenseIndex
        original=kind.save
        def save(model,path,*a,**kw):
            result=original(model,path,*a,**kw)
            if '.jobs' in Path(path).parts:hold(args.hold)
            return result
        kind.save=save
    if args.hold=='index_published':
        original=index_builder._write_corpus_manifest
        def corpus(path,*a,**kw):
            if Path(path).resolve()==root/'index':hold('index_published')
            return original(path,*a,**kw)
        index_builder._write_corpus_manifest=corpus
    if args.hold=='success_persisted':
        original=journal.JobJournal.save
        def save(journal_self,job,options):
            result=original(journal_self,job,options)
            if job.state=='succeeded':hold('success_persisted')
            return result
        journal.JobJournal.save=save
    provider=LocalEvidenceLLM()
    service=CampusAIQueryService(HybridRetriever(root/'index'),GroundedAnswerGenerator(provider),default_mode='bm25')
    provider.evidence=lambda:service.last_retrieval[0]
    service.retriever.warm_up()
    app=CampusAIApplication(service,jobs=manager,ingestion_defaults={
        'store_dir':root/'store','index_dir':root/'index','dense_model':'fallback-hash-256'})
    try:
        with make_local_server('127.0.0.1',0,make_wsgi_app(app,max_concurrent_queries=1)) as server:
            (root/'server.json').write_text(json.dumps({'pid':os.getpid(),'parent_pid':os.getppid(),'port':server.server_port,
                'instance':instance,'provider':'deterministic test fixture; zero Gemini calls'}),encoding='utf-8')
            print('Fixture process ready',flush=True)
            server.serve_forever()
    finally:app.close()


if __name__=='__main__':main()
