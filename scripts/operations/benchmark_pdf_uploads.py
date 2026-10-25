"""Offline loopback upload/OCR/index load measurement in a NEW isolated store."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import threading
import time
import sys
import traceback
from urllib.request import Request, urlopen

import psutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdfs', nargs='+', type=Path)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ocr', action='store_true')
    parser.add_argument('--dense-model', default='BAAI/bge-m3')
    parser.add_argument('--ocr-backend', choices=('rapidocr','tesseract'), default='rapidocr')
    parser.add_argument('--ocr-data-dir', type=Path)
    args = parser.parse_args()
    if not 1 <= len(args.pdfs) <= 5:
        parser.error('select one to five PDFs')
    if args.output.exists():
        parser.error('output already exists; preserve previous evidence')
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    from campusai.api import CampusAIApplication
    from campusai.deployment.local_server import make_local_server, LocalRequestHandler
    from campusai.ingestion.jobs import IngestionJobManager
    from campusai.rag.grounding import GroundedAnswerGenerator
    from campusai.rag.service import CampusAIQueryService
    from campusai.retrieval.dense_index import DenseIndex
    from campusai.retrieval.hybrid import HybridRetriever
    from campusai.web import make_wsgi_app

    proc, stop = psutil.Process(), threading.Event()
    initial_rss, samples, probes, thread_counts = proc.memory_info().rss, [], [], []
    tree_samples,tree_threads=[],[]
    def sample():
        while not stop.wait(.02):
            samples.append(proc.memory_info().rss)
            thread_counts.append(proc.num_threads())
            children=[]
            for child in proc.children(recursive=True):
                try:children.append((child.memory_info().rss,child.num_threads()))
                except (psutil.NoSuchProcess,psutil.AccessDenied):pass
            tree_samples.append(samples[-1]+sum(row[0] for row in children))
            tree_threads.append(thread_counts[-1]+sum(row[1] for row in children))
    sampler = threading.Thread(target=sample, daemon=True); sampler.start()
    print('Loading cached local embedding model; no answer provider configured', flush=True)
    warmed = time.perf_counter()
    DenseIndex(model_name=args.dense_model, device='cpu')._provider().encode_query('startup probe')
    warm_seconds = time.perf_counter()-warmed
    idle_rss = proc.memory_info().rss
    service = CampusAIQueryService(HybridRetriever(root/'index'), GroundedAnswerGenerator(None))
    app = CampusAIApplication(service, jobs=IngestionJobManager(max_workers=3,max_pending=8,
        journal_path=root/'jobs.sqlite3'), ingestion_defaults={'store_dir':root/'store',
        'index_dir':root/'index','dense_model':args.dense_model,'device':'cpu',
        'ocr_backend':args.ocr_backend,'ocr_data_dir':args.ocr_data_dir})
    failure_traces, stages = [], {}
    original_update = app.jobs._update
    def trace_update(job_id, **values):
        error = sys.exc_info()[1]
        if values.get('state') == 'failed' and error is not None:
            failure_traces.append({'job_id':job_id,'error':type(error).__name__,
                'frames':[{'file':Path(frame.filename).name,'function':frame.name,'line':frame.lineno}
                          for frame in traceback.extract_tb(error.__traceback__)]})
        return original_update(job_id, **values)
    app.jobs._update = trace_update
    class Quiet(LocalRequestHandler):
        def log_message(self,*args): pass
    server = make_local_server('127.0.0.1',0,make_wsgi_app(app,max_concurrent_queries=4))
    server.RequestHandlerClass = Quiet
    host = threading.Thread(target=server.serve_forever, daemon=True); host.start()
    base = f'http://127.0.0.1:{server.server_port}'
    def request(path, data=None, headers=None):
        with urlopen(Request(base+path,data=data,headers=headers or {}),timeout=60) as response:
            return json.load(response)
    failures=[]
    def upload(path):
        started=time.perf_counter()
        try:
            body=request('/api/documents/upload',path.read_bytes(),
                {'Content-Type':'application/pdf','X-Filename':path.name})
            return {'name':path.name,'seconds':time.perf_counter()-started,'job_id':body['job']['job_id']}
        except Exception as error:
            failures.append({'operation':'upload','name':path.name,'error':type(error).__name__})
            return None
    def monitor(job_ids):
        deadline=time.monotonic()+240
        while True:
            probe_started=time.perf_counter()
            try:
                listing=request('/api/documents')
                probes.append({'seconds':time.perf_counter()-probe_started,'ok':True})
            except Exception as error:
                probes.append({'seconds':time.perf_counter()-probe_started,'ok':False,'error':type(error).__name__})
                listing={'jobs':[]}
            jobs={job['job_id']:job for job in listing['jobs']}
            for job_id, job in jobs.items():
                history=stages.setdefault(job_id,[])
                state=(job['state'],job['stage'])
                if not history or state != (history[-1]['state'],history[-1]['stage']):
                    history.append({'state':state[0],'stage':state[1],
                                    'observed_seconds':time.perf_counter()-started})
            if all(j in jobs and jobs[j]['state'] not in {'staging','queued','running'} for j in job_ids):
                return [jobs[j] for j in job_ids]
            if time.monotonic()>deadline:
                failures.append({'operation':'monitor','error':'observation_deadline'})
                return [jobs.get(j,{'job_id':j,'state':'not_observed'}) for j in job_ids]
            time.sleep(.25)
    started=time.perf_counter()
    try:
        with ThreadPoolExecutor(max_workers=5) as pool: uploads=list(pool.map(upload,args.pdfs))
        accepted_seconds=time.perf_counter()-started
        initial_jobs=monitor([row['job_id'] for row in uploads if row])
        initial_seconds=time.perf_counter()-started
        print(json.dumps({'accepted_seconds':accepted_seconds,'initial_seconds':initial_seconds,
            'initial_states':[j['state'] for j in initial_jobs]}),flush=True)
        ocr_jobs=[]
        if args.ocr:
            for doc in request('/api/documents')['documents']:
                if not doc.get('ocr_available'): continue
                try:
                    result=request(f"/api/documents/{doc['doc_id']}/ocr",b'{}',{'Content-Type':'application/json'})
                    ocr_jobs.append(result['job']['job_id'])
                except Exception as error:
                    failures.append({'operation':'ocr_admission','error':type(error).__name__})
            monitor(ocr_jobs)
        elapsed=time.perf_counter()-started
        listing=request('/api/documents')
        records=[json.loads(p.read_text(encoding='utf-8')) for p in (root/'store').glob('*/meta.json')]
        latencies=sorted(p['seconds'] for p in probes)
        report={'scope':'offline loopback HTTP; real embedding/OCR; no answer provider',
            'dense_model':args.dense_model,'workers':3,'queue':8,'initial_rss_bytes':initial_rss,
            'ocr_backend':args.ocr_backend,
            'warm_seconds':warm_seconds,'warm_idle_rss_bytes':idle_rss,
            'peak_sampled_rss_bytes':max(samples+[initial_rss]),'accepted_seconds':accepted_seconds,
            'peak_sampled_process_tree_rss_bytes':max(tree_samples+[initial_rss]),
            'peak_sampled_process_tree_threads':max(tree_threads+[proc.num_threads()]),
            'peak_sampled_process_threads':max(thread_counts+[proc.num_threads()]),
            'initial_terminal_seconds':initial_seconds,'all_terminal_seconds':elapsed,
            'uploads':uploads,'documents':listing['documents'],'jobs':app.jobs.list(),
            'source_manifest':[{'name':p.name,'bytes':p.stat().st_size,
                'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in args.pdfs],
            'ingestion':[{'doc_id':r['doc_id'],'pages':r['page_count'],'chunks':len(r['chunks']),
                'tables':len(r['tables']),'ocr':r['metadata'].get('ocr')} for r in records],
            'library_probe_count':len(probes),'library_probe_errors':sum(not p['ok'] for p in probes),
            'library_probe_p95_seconds':latencies[min(len(latencies)-1,int(len(latencies)*.95))],
            'transport_failures':failures,'failure_traces':failure_traces,'observed_stages':stages,
            'ready_count':sum(doc['ready'] for doc in listing['documents']),
            'job_failure_count':sum(job['state']=='failed' for job in app.jobs.list())}
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open('x',encoding='utf-8') as stream: json.dump(report,stream,indent=2)
        print(json.dumps({k:report[k] for k in ('all_terminal_seconds','peak_sampled_rss_bytes',
            'library_probe_p95_seconds','ready_count','job_failure_count','transport_failures')}),flush=True)
    finally:
        server.shutdown(); server.server_close(); host.join(); app.close()
        stop.set(); sampler.join()


if __name__=='__main__': main()
