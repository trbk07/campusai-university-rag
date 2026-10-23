"""Immutable free-model HTTP qualification; ten actual provider POSTs maximum.

Keeps faults, never resumes/retries a run, never rotates credentials. Repeats
replay the exact original request context; negatives must abstain without LLM.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request
import urllib.request

from scripts.operations.local import configure_local
from scripts.operations.serve import build_application
from campusai.deployment.local_server import make_local_server
from campusai.web import make_wsgi_app


def free_boundary(model, evidence_dir):
    """Allow only screened models; paid-capable Gemini needs owner tier evidence."""
    if model in {'gemma-4-31b-it', 'gemma-4-26b-a4b-it'}:
        return {'basis': 'Official Google pricing: free-only Gemma API tier'}
    if model != 'gemini-3.5-flash-lite':
        raise ValueError('Model has not been screened for this free qualification')
    path = evidence_dir / 'owner-tier-attestation.json'
    proof = json.loads(path.read_text(encoding='utf-8'))
    if (proof.get('tier') != 'free' or proof.get('source') != 'owner_chat_reply'
            or proof.get('existing_campusai_project') is not True):
        raise ValueError('Existing CampusAI project must have owner-confirmed Free tier')
    return {'basis': 'Owner-confirmed Free tier; no independent Console verification',
            'evidence_sha256': sha(path)}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--profile',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--live',action='store_true')
    args=parser.parse_args()
    if not args.live:
        parser.error('Explicit --live required')
    manifest=json.loads(args.manifest.read_text(encoding='utf-8'))
    assert Path(manifest['profile']).resolve() == args.profile.resolve()
    cap=manifest['provider_call_cap']
    assert type(cap) is int and 1<=cap<=10 and len(manifest['cases'])==3*cap
    assert sum(case['kind']=='generated' for case in manifest['cases'])==cap
    if manifest.get('prior_attempts_report'):
        prior=json.loads(Path(manifest['prior_attempts_report']).read_text(encoding='utf-8'))
        assert prior['status']=='NOT_PASSED' and len(prior['calls'])+cap<=10
    public_proof=json.loads((args.manifest.parent/'public-source-check.json').read_text(encoding='utf-8'))
    assert public_proof['exact_public_source_match'] is True
    assert public_proof['url']=='https://algs4.cs.princeton.edu/lectures/keynote/13StacksAndQueues.pdf'
    assert manifest['doc_ids']==[public_proof['sha256']]
    args.output.mkdir(parents=True,exist_ok=False)
    os.environ['CAMPUSAI_LLM_CONFIG']=str(args.profile.resolve())
    os.environ['CAMPUSAI_RAG_CACHE_PATH']=str((args.output/'answer-cache.sqlite3').resolve())
    os.environ['CAMPUSAI_JOB_DB']=str((Path('.tmp')/'model-qualification-jobs.sqlite3').resolve())
    configure_local()
    app=build_application()
    client=app.query_service.answer_generator.llm
    boundary=free_boundary(client.model,args.manifest.parent)
    assert client.endpoint==f'https://generativelanguage.googleapis.com/v1beta/models/{client.model}:generateContent'
    original_urlopen=urllib.request.urlopen
    calls,results,traces=[],[],[]
    report={'model':client.model,'profile_sha256':sha(args.profile),'manifest_sha256':sha(args.manifest),
            'manifest':manifest,'status':'RUNNING','calls':calls,'results':results,'traces':traces,
            'scope':'Real provider and full local application over loopback; existing user PDF; no cloud/SLO claim',
            'auto_retry':False,'credential_rotation':False,'paid_fallback':False,
            'free_boundary':boundary,
            'sources_sha256':{str(path):sha(path) for path in [Path(__file__),Path('src/campusai/llm/client.py'),
                Path('src/campusai/llm/factory.py'),Path('src/campusai/llm/quota.py'),
                Path('src/campusai/rag/service.py'),Path('src/campusai/rag/grounding.py'),Path('src/campusai/rag/cache.py'),
                Path('src/campusai/rag/source_windows.py'),Path('src/campusai/retrieval/negative.py'),
                Path('scripts/operations/serve.py'),Path('src/campusai/web.py'),
                Path('src/campusai/api.py'),Path('src/campusai/web_documents.py'),
                Path('src/campusai/document_info.py'),Path('src/campusai/rag/context.py'),
                Path('src/campusai/rag/source_citations.py')]}}
    resource_stop=threading.Event()
    sampler=None
    try:
        import psutil
        process=psutil.Process()
        report['resources']={'scope':'Current application process after retrieval warm-up; sampled every 250 ms',
                             'physical_ram_bytes':psutil.virtual_memory().total,'rss_peak_bytes':0,
                             'available_ram_min_bytes':psutil.virtual_memory().available,
                             'cpu_percent_peak':0,'gpu_used_by_application':False}
        def sample():
            while not resource_stop.is_set():
                values=report['resources']
                values['rss_peak_bytes']=max(values['rss_peak_bytes'],process.memory_info().rss)
                values['available_ram_min_bytes']=min(values['available_ram_min_bytes'],psutil.virtual_memory().available)
                values['cpu_percent_peak']=max(values['cpu_percent_peak'],process.cpu_percent())
                resource_stop.wait(0.25)
        sampler=threading.Thread(target=sample,daemon=True)
        sampler.start()
    except ImportError:
        report['resources']={'status':'UNMEASURED: psutil unavailable'}
    def save():
        (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def transport(request,**kwargs):
        if request.full_url.startswith('https://generativelanguage.googleapis.com/') and request.get_method()=='POST':
            if len(calls)>=cap:
                raise RuntimeError('qualification provider call cap exhausted before send')
            body=json.loads(request.data)
            assert 'tools' not in body
            assert body['generationConfig']['maxOutputTokens']<=1536
            row={'attempt':len(calls)+1,'started_at_utc':time.time(),
                 'body_sha256':hashlib.sha256(request.data).hexdigest(),
                 'prompt_chars':sum(len(part.get('text','')) for content in body.get('contents',[]) for part in content.get('parts',[]))}
            calls.append(row)
            save()  # Reserve persistently before sending; a crash cannot resume.
            try:
                response=original_urlopen(request,**kwargs)
                data=response.read()
                response.close()
                payload=json.loads(data)
                response_path=args.output/f'provider-response-{len(calls):02d}.json'
                response_path.write_bytes(data)
                request_path=args.output/f'provider-request-{len(calls):02d}.json'
                request_path.write_bytes(request.data)  # No authentication headers; public-only workload.
                row.update(http_status=200,usage=payload.get('usageMetadata',{}),model_version=payload.get('modelVersion'))
                row.update(response_sha256=sha(response_path),request_sha256=sha(request_path))
                # Return exactly the received provider bytes to the real client.
                import io
                return io.BytesIO(data)
            except HTTPError as error:
                row['http_status']=error.code
                raise
            finally:
                save()
        return original_urlopen(request,**kwargs)
    urllib.request.urlopen=transport
    history=[]
    originals={}
    try:
        with make_local_server('127.0.0.1',0,make_wsgi_app(app,telemetry_hook=traces.append,max_concurrent_queries=1)) as server:
            thread=threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            base=f'http://127.0.0.1:{server.server_port}'
            try:
                for case in manifest['cases']:
                    if case['kind']=='cached':
                        payload=originals[case['repeat_of']]
                    else:
                        payload={'question':case['question'],'language':case['language'],'doc_ids':manifest['doc_ids'],
                                 'history':history[-8:] if case['kind']=='generated' else []}
                        if case['kind']=='generated':
                            originals[case['id']]=payload
                    started=time.perf_counter()
                    before=len(calls)
                    req=Request(base+'/api/query',data=json.dumps(payload,ensure_ascii=False).encode('utf-8'),
                                headers={'Content-Type':'application/json'})
                    try:
                        response=original_urlopen(req,timeout=43)
                    except HTTPError as error:
                        response=error
                    with response:
                        value=json.load(response)
                        status=response.code
                    answer=value.get('answer',{})
                    consumed=len(calls)-before
                    passed=bool(status==200 and value.get('ok') and not value.get('fallback'))
                    if case['kind']=='negative':
                        passed=passed and answer.get('abstained') is True and consumed==0
                    else:
                        passed=passed and answer.get('abstained') is False and bool(answer.get('citations'))
                        passed=passed and (consumed==1 if case['kind']=='generated' else value.get('cache_hit') is True and consumed==0)
                    row={'id':case['id'],'kind':case['kind'],'http_status':status,'passed':passed,
                         'latency_ms':(time.perf_counter()-started)*1000,'provider_attempts':consumed,
                         'request':payload,'response':value}
                    results.append(row)
                    save()
                    print(json.dumps({'case':case['id'],'kind':case['kind'],'passed':passed,'http':status,
                                      'reason':answer.get('abstention_reason',value.get('error_code')),
                                      'latency_ms':round(row['latency_ms']),'calls':len(calls)}),flush=True)
                    if not passed:
                        break
                    if case['kind']=='generated':
                        history.extend([{'role':'user','content':payload['question']},
                                        {'role':'assistant','content':answer['answer']}])
            finally:
                server.shutdown()
                thread.join(2)
    finally:
        urllib.request.urlopen=original_urlopen
        app.close()
        resource_stop.set()
        if sampler is not None:
            sampler.join(2)
        report['status']='PASS' if len(results)==len(manifest['cases']) and all(row['passed'] for row in results) and len(calls)==cap else 'NOT_PASSED'
        report['actual_provider_attempts']=len(calls)
        report['account_quota']='UNKNOWN: native successful calls do not identify the project ceiling'
        save()
    print(json.dumps({'status':report['status'],'http_requests':len(results),'provider_attempts':len(calls)}))
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__':
    raise SystemExit(main())
