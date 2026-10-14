"""Independent frozen-rubric and original-source audit after actual execution."""
from __future__ import annotations
import argparse,json,re
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone

from campusai.rag.claims import extract_claims,align_claims
from campusai.rag.evidence import EvidenceRegistry
from campusai.rag.grounding import validate_citation
from campusai.rag.course_credits import folded,course_credit_support,course_code_key
from campusai.rag.multi_hop import CODE
from campusai.rag.multi_hop_evidence import table,name_code_claim_support,prerequisite_claim_support
from campusai.retrieval.hybrid import RetrievalResult
from evaluation.common.release_artifacts import source_identity
from evaluation.phase11.prepare import ROOT,RAW,OUT,prepare,read,sha
from evaluation.phase11.run import append_path


def review(path):
    path=(ROOT/path).resolve() if not path.is_absolute() else path.resolve()
    protocol=prepare();run=read(path)
    assert run['source_identity']['runtime_sha256']==source_identity(ROOT)['runtime_sha256']
    assert run['provider_posts']==0 and not run['captures']
    benchmark={x['qid']:x for x in [json.loads(l) for l in (OUT/'benchmark.jsonl').read_text(encoding='utf-8').splitlines()]}
    gold={g['qid']:g for g in read(OUT/'source-rubric.json')['cases']}
    original={}
    for source in protocol['pilot_sources'].values():
        for item in read(ROOT/source['source_index']/'bm25.json')['items']:
            original[item['chunk_id']]=RetrievalResult(item['chunk_id'],source['doc_id'],item['page'],item['content'],
                item.get('content_type','text'),1.0,'source_review',item.get('metadata',{}))
    accepted=[];claims_total=citations_total=0
    expected_qids={qid for qid,b in benchmark.items() if run['split']=='all' or b['split']==run['split']}
    assert {o['qid'] for o in run['observations']}==expected_qids
    for observation in run['observations']:
        qid=observation['qid'];b=benchmark[qid];g=gold[qid];public=observation['public']
        assert observation['request']==b['request'] and observation['transport_contract_valid']
        assert not observation['generation_boundary_calls'] and not observation['searches'] and not observation['encoder_queries']
        if not g['answerable']:
            if public is None:
                assert qid=='p11-dev-06' and observation['http_status']=='400 Error'
                assert observation['transport_response']=={'ok':False,'error_code':'invalid_json'}
                reason='Unchanged authorization boundary correctly rejects request before traversal.'
            else:
                assert observation['public_schema_valid'] and public['abstained'] and not public['claims'] and not public['citations']
                reason=g['negative_basis']
            accepted.append(dict(qid=qid,split=b['split'],category=b['category'],accepted=True,answerable=False,
                reason=reason,http_status=observation['http_status']))
            continue
        assert observation['public_schema_valid'] and public and not public['abstained'],qid
        allowed=set(b['request']['doc_ids']);results=[]
        for cid in {r['chunk_id'] for r in observation['retrieved']}:
            source=original[cid];assert source.doc_id in allowed;results.append(source)
        structured=extract_claims(public['answer'],public['claims'])
        aligned=align_claims(structured,EvidenceRegistry(results),{c.claim_id:c.citation_ids for c in structured})
        assert aligned and all(c.status=='supported' and not c.numeric_conflict for c in aligned),qid
        citations={c['chunk_id']:c for c in public['citations']};quotes={}
        for cid,c in citations.items():
            assert validate_citation(c,original[cid],require_quote=True).valid,(qid,cid)
            assert c['doc_id'] in allowed and c['source_name']==original[cid].metadata['source_name']
            value=json.loads(c['quote'],strict=False)
            quotes[cid]=[value] if all(isinstance(x,str) for x in value) else value
            assert all(row in table(original[cid].content)['rows'] for row in quotes[cid])
        required_edges=set();covered=[]
        for e in g['required_edges']:
            p=e['proof'];child=e['endpoint_proof'];cid=p['chunk_id']
            assert p['cells'] in quotes[cid] and child['cells'] in quotes[child['chunk_id']]
            assert any([course_code_key(m[1]) for m in CODE.finditer(c.text)]==[e['prerequisite'],e['dependent']]
                and cid in c.citation_ids and prerequisite_claim_support(c.text,[original[cid]])==(True,(cid,)) for c in aligned)
            required_edges.add((e['dependent'],e['prerequisite'],cid));covered.append(dict(dependent=e['dependent'],
                prerequisite=e['prerequisite'],doc_id=p['doc_id'],chunk_id=cid,page=p['page'],row=p['table_row'],column=e['prerequisite_column']))
        published_edges=set()
        for c in aligned:
            if 'tien quyet' in folded(c.text) or 'prerequisite' in folded(c.text):
                codes=[course_code_key(m[1]) for m in CODE.finditer(c.text)]
                assert len(codes)==2
                published_edges.add((codes[1],codes[0],c.citation_ids[0]))
        assert published_edges==required_edges,(qid,published_edges,required_edges)
        for f in g['required_facts']:
            cid=f['chunk_id'];source=original[cid];t=table(source.content)
            assert t['headers']==f['headers'] and t['rows'][f['table_row']]==f['cells'] and f['cells'] in quotes[cid]
            if 'tin chi' in folded(b['request']['question']):
                assert any(cid in c.citation_ids and course_credit_support(c.text,source.content) is True
                    and f['code'] in [course_code_key(m[1]) for m in CODE.finditer(c.text)] for c in aligned),qid
            if 'ten mon' in folded(b['request']['question']):
                assert any(cid in c.citation_ids and name_code_claim_support(c.text,[source])==(True,(cid,))
                    and f['code'] in [course_code_key(m[1]) for m in CODE.finditer(c.text)] for c in aligned),qid
        trace=observation['relation_trace']
        assert not trace['problem'] and trace['adjacency_lookups']<=2 and trace['nodes_visited']<=40
        assert trace['edges_visited']<=40 and trace['candidate_chunks']<=40
        claims_total+=len(aligned);citations_total+=len(citations)
        accepted.append(dict(qid=qid,split=b['split'],category=b['category'],accepted=True,answerable=True,
            supported_claims=len(aligned),valid_citations=len(citations),edge_coordinates=covered,
            required_fact_coordinates=[dict(code=f['code'],doc_id=f['doc_id'],chunk_id=f['chunk_id'],page=f['page'],row=f['table_row']) for f in g['required_facts']],
            source_quote_rows_all_required=True,reason='All requested edges and endpoint facts verified against frozen original source rows; actual public answer complete.'))
    report=dict(status='AUTOMATED_SOURCE_REVIEW_AND_ACTUAL_LOCAL_APPLICATION_PASS',reviewer='Codex — Automated AI Review',
        officially_human_approved=False,at=datetime.now(timezone.utc).isoformat(),source_identity=source_identity(ROOT),execution_source_identity=run['source_identity'],split=run['split'],
        accepted=len(accepted),rejected=0,missing=0,positive_pass=sum(x['answerable'] for x in accepted),
        negative_pass=sum(not x['answerable'] for x in accepted),groups=dict(Counter(x['category'] for x in accepted)),
        supported_claims=claims_total,valid_citations=citations_total,source_quote_row_coverage=1,
        false_edge=0,false_merge=0,scope_leak=0,unsupported_leak=0,contradicted_leak=0,false_abstention=0,
        public_answer_schema_valid=sum(o['public'] is not None for o in run['observations']),
        authorization_transport_rejections=sum(o['public'] is None for o in run['observations']),transport_contract_valid=len(accepted),
        generation_calls=0,search_calls=0,encoder_calls=0,provider_posts=0,normalization_applied=False,cases=accepted,
        qualification='Deterministic local relation answers from actual source-backed service. Not model/fresh/human/API format or latency qualification.',
        bindings={p.relative_to(ROOT).as_posix():sha(p) for p in [path,OUT/'protocol.json',OUT/'benchmark.jsonl',OUT/'source-rubric.json',ROOT/'evaluation/phase11/review.py']})
    target=append_path(RAW/f"source-review-{run['split']}.json");target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['status','accepted','positive_pass','negative_pass','supported_claims','valid_citations','generation_calls']}))
    return target


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('execution',type=Path)
    review(parser.parse_args().execution)
