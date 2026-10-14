"""Freeze source-reviewed relation queries before a prototype; gold stays here."""
from __future__ import annotations
import hashlib,json,re
from collections import Counter
from pathlib import Path
from datetime import datetime,timezone
from evaluation.common.artifact_store import ROOT,resolve_artifact
from evaluation.common.release_artifacts import source_identity
from campusai.rag.course_credits import headed_credit_rows,folded,course_code_key
from campusai.rag.multi_hop_evidence import table

OUT=ROOT/'evaluation/phase11'
RAW=ROOT/'.local_artifacts/experiment_runs/phase11-20261014'

def sha(p):return hashlib.sha256(resolve_artifact(p).read_bytes()).hexdigest()
def read(p):return json.loads(resolve_artifact(p).read_text(encoding='utf-8-sig'))
def write_once(p,d):
    text=json.dumps(d,ensure_ascii=False,indent=2)+'\n'
    if p.exists():assert p.read_text(encoding='utf-8')==text,str(p)
    else:p.write_text(text,encoding='utf-8')

def prepare():
    frozen=OUT/'protocol.json'
    if frozen.exists():
        p=read(frozen)
        for n,h in p['bindings'].items():assert sha(ROOT/n)==h,n
        return p
    assert source_identity(ROOT)['runtime_sha256']==read(OUT/'source-audit.json')['source_identity']['runtime_sha256']
    inventory=read(RAW/'source-inventory.json');sources=inventory['sources']
    items={k:read(ROOT/v['source_index']/'bm25.json')['items'] for k,v in sources.items()}
    def fact(label,code):
        found=[]
        for item in items[label]:
            t=table(item['content'])
            for key,credits,row in headed_credit_rows(item['content']) or []:
                if key==code:
                    found.append(dict(source=label,doc_id=sources[label]['doc_id'],code=code,credits=credits,
                        chunk_id=item['chunk_id'],page=item['page'],table_row=t['rows'].index(row),
                        headers=t['headers'],cells=row,cells_sha256=hashlib.sha256(json.dumps(row,ensure_ascii=False).encode()).hexdigest(),
                        code_column=next(i for i,h in enumerate(t['headers']) if folded(h) in {'ma hoc phan','ma so hoc phan','ma so','course code'}),
                        credit_column=next(i for i,h in enumerate(t['headers']) if folded(h) in {'so tin chi','credits'})))
        assert found,(label,code)
        assert len({json.dumps([x['headers'],x['cells']],ensure_ascii=False) for x in found})==1,(label,code,'ambiguous fact')
        return found[0]
    def edge(label,dependent,prerequisite):
        p=next(e for e in sources[label]['edge_occurrences'] if e['dependent']==dependent and e['prerequisite']==prerequisite)
        a,b=fact(label,dependent),fact(label,prerequisite)
        col=next(i for i,h in enumerate(a['headers']) if folded(h) in {'ma so hoc phan tien quyet','ma hoc phan tien quyet','hoc phan tien quyet','prerequisite','prerequisites','prerequisite code'})
        assert course_code_key(a['cells'][col])==prerequisite
        return dict(dependent=dependent,prerequisite=prerequisite,source=label,proof=a,endpoint_proof=b,prerequisite_column=col)
    rows=[];gold=[]
    def case(split,n,category,question,labels,*,answerable=True,edges=(),facts=(),basis=None,extra=None):
        request=dict(question=question,doc_ids=[sources[l]['doc_id'] for l in labels])
        request.update(extra or {})
        qid=f'p11-{split}-{n:02}'
        rows.append(dict(qid=qid,split=split,family='mechatronics-robotics' if split=='dev' else 'electronics',category=category,
            request=request,answerable=answerable,exposure='Previously exposed public corpus; new relation queries frozen before prototype; not fresh validation.'))
        gold.append(dict(qid=qid,answerable=answerable,required_edges=list(edges),required_facts=list(facts),negative_basis=basis,
            reviewer='Codex — Automated AI Review',officially_human_approved=False))
    A,B,C,D=[sources[k]['source_name'] for k in ['mech','robot','electronics','electronics_master']]
    # Keep a compatible historical direct query; all other facts remain source-owned.
    old=next(x for x in [json.loads(l) for l in (ROOT/'evaluation/phase10/benchmark.jsonl').read_text(encoding='utf-8').splitlines()] if x['qid']=='p10-dev-06')
    case('dev',1,'direct_inverse',old['request']['question'],['mech','robot'],edges=[edge('mech','INT2209','INT1006')],facts=[fact('mech','INT1006')])
    case('dev',2,'direct_inverse',f'Trong {A}, liệt kê đầy đủ các học phần có PHI1004 là tiên quyết trực tiếp; dẫn nguồn cho từng quan hệ.',
        ['mech'],edges=[edge('mech','PHI1005','PHI1004')])
    case('dev',3,'two_edge_path',f'Trong {A}, đi theo hai bước tiên quyết liên tiếp bắt đầu từ EMA2012. Nêu cả hai quan hệ và số tín chỉ của môn cuối chuỗi.',
        ['mech'],edges=[edge('mech','EMA2012','EMA2037E'),edge('mech','EMA2037E','EMA2036E')],facts=[fact('mech','EMA2036E')])
    case('dev',4,'two_edge_path',f'Trong {B}, đi theo chuỗi hai bước tiên quyết bắt đầu từ ELT3051. Nêu cả hai quan hệ và tên môn cuối chuỗi.',
        ['robot'],edges=[edge('robot','ELT3051','ELT2035'),edge('robot','ELT2035','MAT1042')],facts=[fact('robot','MAT1042')])
    case('dev',5,'identity_scope_time',f'Trong {A} và {B}, INT3401 trùng mã nên tự động được công nhận thay thế với cùng tiên quyết đúng không?',
        ['mech','robot'],answerable=False,basis='Same code across programs does not establish equivalence; mechatronics also has conflicting prerequisite occurrences. No merge or inference permitted.')
    case('dev',6,'identity_scope_time',f'Theo {A}, tiên quyết trực tiếp của EMA2012 có mã gì và bao nhiêu tín chỉ?',
        ['mech'],answerable=False,basis='Explicit source is outside authorized scope; intersection empty; no source traversal allowed.',extra=dict(authorized_doc_ids=[sources['robot']['doc_id']]))
    case('dev',7,'missing_ambiguous',f'Theo {A}, tiên quyết trực tiếp của MAT1041 có mã gì và bao nhiêu tín chỉ?',
        ['mech'],answerable=False,facts=[fact('mech','MAT1041')],basis='Blank prerequisite cell does not establish a direct edge.')
    case('dev',8,'missing_ambiguous',f'Theo {A}, xác định duy nhất một môn tiên quyết trực tiếp của EMA2050 và số tín chỉ môn đó.',
        ['mech'],answerable=False,facts=[fact('mech','EMA2050')],basis='Two identifiers MAT1093/MAT1042 in prerequisite cell; single-edge/AND/OR interpretation not supported.')
    case('acceptance',1,'direct_inverse',f'Theo {C}, học phần tiên quyết trực tiếp của ELT3103 có mã gì và bao nhiêu tín chỉ?',
        ['electronics'],edges=[edge('electronics','ELT3103','ELT2041')],facts=[fact('electronics','ELT2041')])
    case('acceptance',2,'direct_inverse',f'Trong {C}, liệt kê đầy đủ các học phần có ELT2030 là tiên quyết trực tiếp; dẫn nguồn cho từng quan hệ.',
        ['electronics'],edges=[edge('electronics','ELT2040','ELT2030')])
    case('acceptance',3,'two_edge_path',f'Trong {C}, đi theo hai bước tiên quyết liên tiếp bắt đầu từ ELT3189. Nêu cả hai quan hệ và số tín chỉ của môn cuối chuỗi.',
        ['electronics'],edges=[edge('electronics','ELT3189','ELT2036'),edge('electronics','ELT2036','EPN1096')],facts=[fact('electronics','EPN1096')])
    case('acceptance',4,'two_edge_path',f'Trong {C}, đi theo chuỗi hai bước tiên quyết bắt đầu từ ELT3077. Nêu cả hai quan hệ và tên môn cuối chuỗi.',
        ['electronics'],edges=[edge('electronics','ELT3077','ELT3051'),edge('electronics','ELT3051','ELT2035')],facts=[fact('electronics','ELT2035')])
    case('acceptance',5,'identity_scope_time',f'Theo {C}, tiên quyết trực tiếp của ELT3103 có mã gì và bao nhiêu tín chỉ?',
        ['electronics_master'],answerable=False,basis='Requested undergraduate source unavailable in explicitly selected masters source; cannot broaden scope.')
    case('acceptance',6,'identity_scope_time',f'Theo quy định hiện hành năm 2026, tiên quyết trực tiếp của ELT3103 trong {C} có mã gì và bao nhiêu tín chỉ?',
        ['electronics','electronics_master'],answerable=False,basis='Selected 2023/2022 curricula do not establish current legal applicability in 2026; filename/upload time not effective date.')
    case('acceptance',7,'missing_ambiguous',f'Theo {C}, tiên quyết trực tiếp của ELT2030 có mã gì và bao nhiêu tín chỉ?',
        ['electronics'],answerable=False,facts=[fact('electronics','ELT2030')],basis='Blank prerequisite cell does not establish a direct edge.')
    case('acceptance',8,'missing_ambiguous',f'Theo {C}, xác định duy nhất một môn tiên quyết trực tiếp của ELT3240 và số tín chỉ môn đó.',
        ['electronics'],answerable=False,facts=[fact('electronics','ELT3240')],basis='Two identifiers INT1008/ELT2041 in prerequisite cell; no unique single-edge inference.')
    assert len(rows)==16 and Counter(r['split'] for r in rows)=={'dev':8,'acceptance':8}
    assert Counter(r['category'] for r in rows)==dict(direct_inverse=4,two_edge_path=4,identity_scope_time=4,missing_ambiguous=4)
    assert all(sum(r['answerable'] for r in rows if r['split']==s)==4 for s in ['dev','acceptance'])
    for label,code,expected in [('mech','PHI1004',['PHI1005']),('electronics','ELT2030',['ELT2040'])]:
        actual=[e['dependent'] for e in sources[label]['edge_occurrences'] if e['prerequisite']==code]
        ambiguous=[x for x in sources[label]['unsupported_cells'] if code in re.sub(r'\s+','',x['cell'])]
        assert sorted(actual)==expected and not ambiguous
    bench=OUT/'benchmark.jsonl';assert not bench.exists()
    bench.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
    write_once(OUT/'source-rubric.json',dict(status='AUTOMATED_SOURCE_REVIEW_COMPLETE',reviewer='Codex — Automated AI Review',
        officially_human_approved=False,benchmark_sha256=sha(bench),cases=gold,
        source_review_notes=['10 original physical PDF pages visually inspected; render receipt retained.',
        'Mechatronics p4 continues headers from p3; masters physical9 is printed7; preserve original coordinates.',
        'Electronics spaced codes and source-inherited logical table columns retained without corpus edits.',
        'Inverse counts checked against all supported and unsupported source-index cells; exact-code PDF occurrence check recorded separately.']))
    pdfcheck={}
    import pymupdf
    for label,code in [('mech','PHI1004'),('electronics','ELT2030')]:
        doc=pymupdf.open(resolve_artifact(ROOT/sources[label]['pdf']));hits=[]
        pattern=re.compile(re.escape(code[:3])+r'\s*'+re.escape(code[3:]))
        for n,p in enumerate(doc,1):
            count=len(pattern.findall(p.get_text()))
            if count:hits.append(dict(page=n,occurrences=count))
        pdfcheck[label]=dict(code=code,pages=hits)
        assert hits==[dict(page=2 if label=='mech' else 9,occurrences=2)],hits
    write_once(RAW/'source-review.json',dict(status='CHOSEN_CASE_SOURCE_REVIEW_COMPLETE',reviewer='Codex — Automated AI Review',
        reviewed_at=datetime.now(timezone.utc).isoformat(),officially_human_approved=False,pdf_inverse_completeness=pdfcheck,
        bindings={str(p.relative_to(ROOT)):sha(p) for p in [RAW/'source-pages/render-receipt.json',OUT/'source-rubric.json']}))
    bindings=dict(inventory['bindings'])
    for p in [bench,OUT/'source-rubric.json',RAW/'source-review.json',RAW/'source-inventory.json']:
        bindings[p.relative_to(ROOT).as_posix()]=sha(p)
    p=dict(status='FROZEN_BEFORE_RELATION_INDEX_PROTOTYPE',baseline_identity=source_identity(ROOT),count=16,dev=8,acceptance=8,
        positive=8,negative=8,families_disjoint=True,exposure='Previously exposed corpus; not fresh validation.',provider_posts=0,
        benefit=dict(branch='quality',minimum_distinct_dev_failures_fixed=2,known_candidate_cases=['p11-dev-02','p11-dev-04'],
            note='Baseline full-service zero-generation false abstention must be observed; parser inventory alone is not enough.'),
        budget=dict(max_hops=2,max_source_groups=2,max_adjacency_lookups=2,max_nodes=40,max_edges=40,
            max_candidates=40,max_search_candidates=20,max_searches=2,max_encoder_queries=2,max_generation=1,context_chars=12000,output_tokens=1024),
        requirements=dict(positive_accuracy=1,negative_accuracy=1,edge_claim_citation_coordinate_schema_validity=1,
            false_edge=0,false_merge=0,scope_leak=0,unsupported=0,contradicted=0,false_abstention=0,minimum_offline_coverage=85),
        pilot_sources={k:{f:s[f] for f in ['doc_id','source_index','source_name','pdf','split']} for k,s in sources.items()},
        qualification='Quality regression plus local runtime observations, not API availability/latency/native-format qualification.',bindings=bindings)
    write_once(frozen,p)
    return p

if __name__=='__main__':
    p=prepare();print(json.dumps(dict(status=p['status'],cases=p['count'],benefit=p['benefit']['branch'],provider_posts=0)))
