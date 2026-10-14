"""Offline real application observations; missing Chat is never answer PASS."""
from __future__ import annotations
import argparse,io,json,shutil,time,zipfile
from pathlib import Path
from datetime import date,datetime,timezone
import psutil,torch
from campusai.rag.service import CampusAIQueryService
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.schemas import validate_release_response
from campusai.retrieval.hybrid import HybridRetriever
from campusai.retrieval.dense_index import DenseIndex
from campusai.request_timings import capture_request
from campusai.api import CampusAIApplication
from campusai.web import make_wsgi_app
from evaluation.common.release_artifacts import source_identity
from evaluation.common.artifact_store import entries,resolve_artifact
from evaluation.phase10.run import CapturedOrRecordedModel
from evaluation.phase11.prepare import ROOT,RAW,OUT,prepare,read,sha

INDEX=RAW/'index'

def append_path(path):
    candidate=path;n=2;catalog=entries()
    while candidate.exists() or candidate.relative_to(ROOT).as_posix() in catalog:
        candidate=path.with_name(path.stem+f'-rerun-{n}'+path.suffix);n+=1
    return candidate

def build_index(protocol):
    for source in protocol['pilot_sources'].values():
        for name in ['bm25.json','dense.json']:
            original=ROOT/source['source_index']/name;target=INDEX/source['doc_id']/name
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():assert sha(target)==sha(original),'frozen source index drift'
            else:shutil.copyfile(resolve_artifact(original),target)

def snapshot_before():
    p=RAW/'runtime-before.zip'
    if p.exists() or p.relative_to(ROOT).as_posix() in entries():return
    files=set()
    for name in ['src','evaluation','scripts','tests']:files.update((ROOT/name).rglob('*.py'))
    files.update(p for p in (ROOT/'configs').rglob('*') if p.is_file() and p.name not in {'key.yaml','gemini.yaml'} and p.suffix in {'.json','.yaml','.yml','.toml'})
    files.update(ROOT/n for n in ['pyproject.toml','requirements.txt','requirements-dev.txt','uv.lock','poetry.lock'] if (ROOT/n).is_file())
    with zipfile.ZipFile(p,'x',zipfile.ZIP_DEFLATED) as z:
        for f in sorted(files):z.write(f,f.relative_to(ROOT).as_posix())

def run():
    protocol=prepare();identity=source_identity(ROOT)
    assert identity['runtime_sha256']==protocol['baseline_identity']['runtime_sha256'],'baseline production runtime changed'
    snapshot_before();build_index(protocol);torch.set_num_threads(8)
    rows=[json.loads(l) for l in (OUT/'benchmark.jsonl').read_text(encoding='utf-8').splitlines()]
    model=CapturedOrRecordedModel({});retriever=HybridRetriever(INDEX,dense_device='cuda')
    service=CampusAIQueryService(retriever,GroundedAnswerGenerator(model),default_mode='hybrid',temporal_clock=lambda:date(2026,10,14))
    application=make_wsgi_app(CampusAIApplication(service))
    search=retriever.search;encode=DenseIndex.encode_query;searches=[];encodes=[]
    def observed_search(*args,**kwargs):
        start=time.perf_counter();result=search(*args,**kwargs)
        searches.append(dict(query=args[0],doc_ids=kwargs.get('doc_ids'),returned_candidates=len(result),top_k=kwargs.get('top_k'),elapsed_ms=(time.perf_counter()-start)*1000))
        return result
    def observed_encode(self,*args,**kwargs):
        encodes.append(dict(text=args[0],model=self.model_name,device=self.device))
        return encode(self,*args,**kwargs)
    retriever.search=observed_search;DenseIndex.encode_query=observed_encode
    process=psutil.Process();observations=[];started=datetime.now(timezone.utc).isoformat()
    try:
        for row in rows:
            qid=row['qid'];model.qid=qid;searches.clear();encodes.clear()
            payload=dict(row['request']);authorized=payload.pop('authorized_doc_ids',None)
            body=json.dumps(payload,ensure_ascii=False).encode('utf-8');status=[]
            env={'PATH_INFO':'/api/query','REQUEST_METHOD':'POST','CONTENT_LENGTH':str(len(body)),'wsgi.input':io.BytesIO(body)}
            if authorized is not None:env['campusai.authorized_doc_ids']=authorized
            with capture_request() as timings:
                response=json.loads(b''.join(application(env,lambda s,h:status.append(s))).decode('utf-8'))
            captured=qid in model.captures
            public=response.get('answer')
            transport_valid=(status==['200 OK'] and response.get('ok') is True and public is not None
                or status==['400 Error'] and response=={'ok':False,'error_code':'invalid_json'})
            assert transport_valid,(qid,status,response)
            observations.append(dict(qid=qid,request=row['request'],public=public,http_status=status[0],transport_response=response,
                transport_contract_valid=transport_valid,public_schema_valid=validate_release_response(public)[0] if public else None,
                timings=timings,searches=list(searches),encoder_queries=list(encodes),
                generation_boundary_calls=int(captured),model_output_supplied=False,
                quality_status='UNMEASURED_MODEL_OUTPUT_ABSENT' if captured else 'ACTUAL_LOCAL_PUBLIC_OUTPUT_REQUIRES_SOURCE_REVIEW',
                multi_hop_trace=service._request_local.multi_hop_trace,temporal_trace=service._request_local.temporal_trace,
                retrieved=[r.to_dict() for r in service.last_retrieval],process_memory=process.memory_info()._asdict()))
            print(json.dumps(dict(qid=qid,http_status=status[0],abstained=public['abstained'] if public else None,generation=int(captured),searches=len(searches),encoder_calls=len(encodes))),flush=True)
    finally:
        DenseIndex.encode_query=encode;service.close()
    assert source_identity(ROOT)==identity,'source changed during baseline'
    result=dict(status='GRAPH_OFF_ACTUAL_APPLICATION_BASELINE_NOT_FULL_MODEL_QUALITY',started_at=started,source_identity=identity,
        protocol_sha256=sha(OUT/'protocol.json'),benchmark_sha256=sha(OUT/'benchmark.jsonl'),
        provider_posts=0,graph_enabled=False,profile=dict(torch_threads=8,dense_device='cuda',context_chars=12000,reranker=False),
        observations=observations,captures=model.captures,
        bindings={p.relative_to(ROOT).as_posix():sha(p) for p in [OUT/'protocol.json',OUT/'benchmark.jsonl',RAW/'runtime-before.zip',Path(__file__)]})
    target=append_path(RAW/'before.json');target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(path=str(target.relative_to(ROOT)),cases=len(rows),captures=len(model.captures),provider_posts=0)))
    return target

if __name__=='__main__':
    run()
