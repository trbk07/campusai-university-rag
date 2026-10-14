"""Actual opt-in WSGI/service acceptance; rubric is used only after execution."""
from __future__ import annotations
import argparse,io,json,time
from datetime import date,datetime,timezone
from pathlib import Path
import psutil,torch

from campusai.api import CampusAIApplication
from campusai.web import make_wsgi_app
from campusai.rag.service import CampusAIQueryService
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.schemas import validate_release_response
from campusai.rag.relation_index import RelationIndex
from campusai.retrieval.hybrid import HybridRetriever
from campusai.retrieval.dense_index import DenseIndex
from campusai.request_timings import capture_request
from evaluation.common.release_artifacts import source_identity
from evaluation.phase10.run import CapturedOrRecordedModel
from evaluation.phase11.prepare import ROOT,OUT,RAW,prepare,sha
from evaluation.phase11.run import INDEX,build_index,append_path


def run(split):
    protocol=prepare();build_index(protocol);identity=source_identity(ROOT);torch.set_num_threads(8)
    rows=[json.loads(l) for l in (OUT/'benchmark.jsonl').read_text(encoding='utf-8').splitlines()]
    if split!='all':rows=[r for r in rows if r['split']==split]
    model=CapturedOrRecordedModel({});retriever=HybridRetriever(INDEX,dense_device='cuda')
    store=RelationIndex(INDEX)
    service=CampusAIQueryService(retriever,GroundedAnswerGenerator(model),default_mode='hybrid',
        temporal_clock=lambda:date(2026,10,14),relation_index=store)
    application=make_wsgi_app(CampusAIApplication(service))
    search=retriever.search;encode=DenseIndex.encode_query;searches=[];encodes=[]
    def observed_search(*args,**kwargs):
        start=time.perf_counter();result=search(*args,**kwargs)
        searches.append(dict(query=args[0],doc_ids=kwargs.get('doc_ids'),top_k=kwargs.get('top_k'),
            returned_candidates=len(result),elapsed_ms=(time.perf_counter()-start)*1000))
        return result
    def observed_encode(self,*args,**kwargs):
        encodes.append(dict(text=args[0],model=self.model_name,device=self.device))
        return encode(self,*args,**kwargs)
    retriever.search=observed_search;DenseIndex.encode_query=observed_encode
    observations=[];process=psutil.Process()
    try:
        for row in rows:
            qid=row['qid'];model.qid=qid;searches.clear();encodes.clear()
            payload=dict(row['request']);authorized=payload.pop('authorized_doc_ids',None)
            body=json.dumps(payload,ensure_ascii=False).encode('utf-8');statuses=[]
            env={'PATH_INFO':'/api/query','REQUEST_METHOD':'POST','CONTENT_LENGTH':str(len(body)),'wsgi.input':io.BytesIO(body)}
            if authorized is not None:env['campusai.authorized_doc_ids']=authorized
            with capture_request() as timings:
                response=json.loads(b''.join(application(env,lambda s,h:statuses.append(s))).decode('utf-8'))
            public=response.get('answer')
            transport_valid=(statuses==['200 OK'] and response.get('ok') is True and public is not None
                or statuses==['400 Error'] and response=={'ok':False,'error_code':'invalid_json'})
            assert transport_valid,(qid,statuses,response)
            observations.append(dict(qid=qid,request=row['request'],public=public,http_status=statuses[0],transport_response=response,
                transport_contract_valid=transport_valid,public_schema_valid=validate_release_response(public)[0] if public else None,
                timings=timings,searches=list(searches),encoder_queries=list(encodes),generation_boundary_calls=int(qid in model.captures),
                retrieved=[r.to_dict() for r in service.last_retrieval],relation_trace=service._request_local.relation_trace,
                temporal_trace=service._request_local.temporal_trace,multi_hop_trace=service._request_local.multi_hop_trace,
                process_memory=process.memory_info()._asdict()))
            print(json.dumps(dict(qid=qid,http_status=statuses[0],abstained=public['abstained'] if public else None,
                generation=int(qid in model.captures),searches=len(searches),encoder_calls=len(encodes))),flush=True)
    finally:
        DenseIndex.encode_query=encode;service.close()
    assert source_identity(ROOT)==identity,'source changed during actual execution'
    report=dict(status='ACTUAL_GRAPH_ON_OUTPUTS_PENDING_SOURCE_REVIEW',split=split,at=datetime.now(timezone.utc).isoformat(),
        source_identity=identity,observations=observations,captures=model.captures,provider_posts=0,
        profile=dict(torch_threads=8,dense_device='cuda',context_chars=12000,reranker=False,graph_enabled=True),
        bindings={p.relative_to(ROOT).as_posix():sha(p) for p in [OUT/'protocol.json',OUT/'benchmark.jsonl',store.path,store.manifest_path,Path(__file__)]})
    target=append_path(RAW/f'candidate-{split}.json');target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(path=str(target.relative_to(ROOT)),cases=len(observations),provider_posts=0)))
    return target


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--split',choices=['dev','acceptance','all'],default='dev')
    run(parser.parse_args().split)
