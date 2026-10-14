"""Freeze a small source-reviewed multi-document/two-hop protocol offline.

Gold lives only in the separate rubric; runtime requests never contain it.
Existing source bytes/indexes are read, never changed or downloaded.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from campusai.rag.course_credits import headed_credit_rows, course_code_key
from evaluation.common.artifact_store import ROOT, resolve_artifact
from evaluation.common.release_artifacts import source_identity

OUT = ROOT / 'evaluation/phase10'
RAW = ROOT / '.local_artifacts/experiment_runs/phase10-20261014'
CURATED = ROOT / '.tmp/phase7-curated-source-20261005-v2/index'
SOURCES = {
    'mech': ('c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850',
             ROOT / '.tmp/hybrid-index', 'data/corpus/university/uet_mechatronics_curriculum_2023.pdf'),
    'robot': ('d39c59d1f20bd87275cbe8758d179ac90cd1e2045ef07f7270830bb167540e09',
              CURATED, 'data/corpus/phase7_source_expansion/20261004b/uet_robotics_curriculum_2020.pdf'),
    'electronics': ('1d782088cffaa263149ede526bc0ddfd82693ce42f76986c82cb64a43bfe6cbf',
                    CURATED, 'data/corpus/phase7_source_expansion/20261004b/uet_electronics_masters_curriculum_2022.pdf'),
    'communications': ('e7e5444554d2e0aff3f306e6b65f4ecc739ee3d92b9bcc6e0e45f0351306a52e',
                       CURATED, 'data/corpus/phase7_source_expansion/20261004b/uet_telecommunications_masters_curriculum_2022.pdf'),
}


def sha(path):
    return hashlib.sha256(resolve_artifact(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(resolve_artifact(path).read_text(encoding='utf-8-sig'))


def write_once(path, data):
    text = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    if path.exists():
        assert path.read_text(encoding='utf-8') == text, f'frozen input differs: {path}'
    else:
        path.write_text(text, encoding='utf-8')


def prepare():
    frozen = OUT / 'protocol.json'
    if frozen.exists():
        protocol = read(frozen)
        for name, digest in protocol['bindings'].items():
            assert sha(ROOT / name) == digest, name
        print(json.dumps({'status':'FROZEN_INPUTS_VERIFIED', 'cases':24, 'provider_posts':0}))
        return
    assert source_identity(ROOT)['runtime_sha256'] == read(OUT/'source-audit.json')['source_identity']['runtime_sha256'], 'freeze before runtime edits'
    records, bindings = {}, {}
    for label, (doc_id, index, pdf) in SOURCES.items():
        assert sha(ROOT/pdf) == doc_id
        items = read(index/doc_id/'bm25.json')['items']
        records[label] = dict(doc_id=doc_id, source_name=items[0]['metadata']['source_name'],
                              pdf=pdf, original_items=items, source_index=str((index/doc_id).relative_to(ROOT)))
        for path in [ROOT/pdf, index/doc_id/'bm25.json', index/doc_id/'dense.json']:
            bindings[path.relative_to(ROOT).as_posix()] = sha(path)
    write_once(RAW/'source-records.json', dict(sources=records))

    def fact(label, code):
        found = []
        for item in records[label]['original_items']:
            for key, value, row in headed_credit_rows(item['content']) or []:
                if key == course_code_key(code):
                    start = item['content'].index('{"headers"')
                    table = json.loads(item['content'][start:])
                    found.append(dict(source=label, doc_id=records[label]['doc_id'],
                        chunk_id=item['chunk_id'], page=item['page'], table_row=table['rows'].index(row),
                        code=key, credits=value, cells=row,
                        cells_sha256=hashlib.sha256(json.dumps(row,ensure_ascii=False).encode()).hexdigest(),
                        headers=table['headers']))
        assert found and len({x['credits'] for x in found}) == 1, (label,code)
        return found[0]

    rows, rubric = [], []
    def case(split, number, category, question, *, sources, facts=(), edge=None,
             answerable=True, negative_basis=None, operation=None, result=None, request_extra=None):
        qid=f'p10-{split}-{number:02}'
        request=dict(question=question,doc_ids=[records[s]['doc_id'] for s in sources])
        request.update(request_extra or {})
        rows.append(dict(qid=qid,split=split,family='undergraduate-engineering' if split=='dev' else 'masters-electronics',
            category=category,request=request,answerable=answerable,
            exposure='Previously reviewed source corpus; new Phase10 questions frozen before runtime edits. Not fresh validation.'))
        rubric.append(dict(qid=qid,answerable=answerable,required_facts=list(facts),required_edge=edge,
                           operation=operation,expected_result=result,negative_basis=negative_basis))

    A,B=records['mech']['source_name'],records['robot']['source_name']
    C,D=records['electronics']['source_name'],records['communications']['source_name']
    for n,code in [(1,'MAT1041'),(2,'EPN1095')]:
        case('dev',n,'compare',f'Trong {A} và {B}, số tín chỉ của {code} là bao nhiêu? So sánh và nêu riêng từng tài liệu.',
             sources=['mech','robot'],facts=[fact('mech',code),fact('robot',code)])
    case('dev',3,'arithmetic',f'Lấy tín chỉ EMA2012 từ {A} và tín chỉ MAT1093 từ {B}. Tổng hai giá trị này là bao nhiêu?',
         sources=['mech','robot'],facts=[fact('mech','EMA2012'),fact('robot','MAT1093')],operation='sum',result=8)
    case('dev',4,'arithmetic',f'Lấy tín chỉ POL1001 trong {A} trừ tín chỉ MAT1041 trong {B}. Chênh lệch có dấu là bao nhiêu?',
         sources=['mech','robot'],facts=[fact('mech','POL1001'),fact('robot','MAT1041')],operation='difference',result=-2)
    for n,target,key in [(5,'EMA2012','EMA2037E'),(6,'INT2209','INT1006')]:
        parent,lookup=fact('mech',target),fact('mech',key)
        assert course_code_key(parent['cells'][-1]) == key
        case('dev',n,'two_hop',f'Theo {A}, học phần tiên quyết của {target} có mã gì và có bao nhiêu tín chỉ trong cùng tài liệu?',
             sources=['mech','robot'],facts=[lookup],edge=dict(kind='prerequisite',target_code=target,bridge_code=key,proof=parent))
    case('dev',7,'false_join',f'Chỉ từ {A} và {B}, hãy xác nhận MAT1041 của hai chương trình tự động được công nhận thay thế cho nhau.',
         sources=['mech','robot'],answerable=False,negative_basis='Equal course code/credits do not prove automatic cross-program credit recognition; neither selected source supplies that mapping.')
    case('dev',8,'false_join',f'Theo {A}, hãy chứng minh MAT1093 là học phần tiên quyết trực tiếp của EMA2012.',
         sources=['mech','robot'],answerable=False,negative_basis='EMA2012 prerequisite cell states EMA2037E, not the requested direct edge MAT1093; endpoints and indirect chains cannot certify the requested direct relation.')
    assert fact('mech','FLF2102')['cells'][-1]=='FLF1105'
    assert not any(k=='FLF1105' for item in records['mech']['original_items'] for k,v,row in headed_credit_rows(item['content']) or [])
    case('dev',9,'missing_hop',f'Theo {A}, môn tiên quyết của FLF2102 có bao nhiêu tín chỉ?',
         sources=['mech','robot'],answerable=False,negative_basis='FLF2102 names FLF1105, but the selected mechatronics source has no headed credit row for FLF1105; do not substitute FLF2101 or a different program.')
    case('dev',10,'missing_hop',f'Lấy tín chỉ EMA2012 từ {A} và tín chỉ MAT1093 từ {B}. Tổng hai giá trị là bao nhiêu?',
         sources=['mech'],answerable=False,negative_basis='Requested robotics operand source is outside selected scope; same code in mechatronics cannot fill that role.',request_extra=dict(authorized_doc_ids=[records['mech']['doc_id']]))
    case('dev',11,'scope_time_context',f'Hiện tại MAT1041 trong {A} và {B} có phải cùng một học phần đang áp dụng và được thay thế cho nhau không?',
         sources=['mech','robot'],answerable=False,negative_basis='No complete effective timeline or cross-program recognition proof; version/filename/signing year cannot establish current applicability or equivalence.')
    case('dev',12,'scope_time_context','Môn đó có bao nhiêu tín chỉ?',sources=['mech','robot'],answerable=False,
         negative_basis='Only assistant history supplies a subject; no user anchor exists. Assistant output is not trusted source/context authority.',
         request_extra=dict(history=[dict(role='assistant',content='Môn đang nói tới là MAT1041 trong tài liệu Robot.')]))

    for n,code in [(1,'INT7016'),(2,'ELT7200')]:
        case('acceptance',n,'compare',f'Trong {C} và {D}, số tín chỉ của {code} là bao nhiêu? So sánh và nêu riêng từng tài liệu.',
             sources=['electronics','communications'],facts=[fact('electronics',code),fact('communications',code)])
    case('acceptance',3,'arithmetic',f'Lấy tín chỉ ELT7200 từ {C} và tín chỉ ELT7010 từ {D}. Tổng hai giá trị này là bao nhiêu?',
         sources=['electronics','communications'],facts=[fact('electronics','ELT7200'),fact('communications','ELT7010')],operation='sum',result=18)
    case('acceptance',4,'arithmetic',f'Lấy tín chỉ INT7016 trong {C} trừ tín chỉ ELT7200 trong {D}. Chênh lệch có dấu là bao nhiêu?',
         sources=['electronics','communications'],facts=[fact('electronics','INT7016'),fact('communications','ELT7200')],operation='difference',result=-12)
    for n,source,target,name,code in [(5,'electronics','communications','Công nghệ chuỗi khối','INT7016'),
                                     (6,'communications','electronics','Luận văn','ELT7200')]:
        parent,lookup=fact(source,code),fact(target,code)
        case('acceptance',n,'two_hop',f'Tìm mã môn {name} trong {records[source]["source_name"]}; môn mang mã đó trong {records[target]["source_name"]} có bao nhiêu tín chỉ?',
             sources=['electronics','communications'],facts=[lookup],edge=dict(kind='name_to_code_lookup',name=name,bridge_code=code,proof=parent,
                interpretation='Explicit requested identifier lookup in another named source; does not assert program equivalence or transferability.'))
    case('acceptance',7,'false_join',f'Chỉ từ {C} và {D}, hãy xác nhận ELT7200 của hai chuyên ngành tự động được công nhận thay thế cho nhau.',
         sources=['electronics','communications'],answerable=False,negative_basis='Same thesis code/credits do not prove cross-specialization recognition or an automatic substitution rule.')
    case('acceptance',8,'false_join',f'Theo {C}, hãy chứng minh INT7016 là học phần tiên quyết trực tiếp của ELT7006.',
         sources=['electronics','communications'],answerable=False,negative_basis='Both independent course rows exist but prerequisite cells are blank; blank is unknown, not an edge or a proof of no prerequisites.')
    assert not any(k=='ELT7006' for item in records['communications']['original_items'] for k,v,row in headed_credit_rows(item['content']) or [])
    case('acceptance',9,'missing_hop',f'Tìm mã môn Điện tử y sinh và các thiết bị điện tử y sinh trong {C}; môn mang mã đó trong {D} có bao nhiêu tín chỉ?',
         sources=['electronics','communications'],answerable=False,negative_basis='Source electronics identifies ELT7006; communications has no headed row for that code. Source-A credits cannot replace the requested source-B lookup.')
    case('acceptance',10,'missing_hop',f'Lấy tín chỉ ELT7200 từ {C} và tín chỉ ELT7010 từ {D}. Tổng hai giá trị là bao nhiêu?',
         sources=['electronics'],answerable=False,negative_basis='Requested communications operand is not in selected/authorized scope; do not borrow an identically coded electronics row.',request_extra=dict(authorized_doc_ids=[records['electronics']['doc_id']]))
    case('acceptance',11,'scope_time_context',f'Hiện tại INT7016 trong {C} và {D} có phải cùng một học phần đang áp dụng và được thay thế cho nhau không?',
         sources=['electronics','communications'],answerable=False,negative_basis='Intake 2022/signing date alone do not establish current effectivity or automatic cross-specialization equivalence.')
    case('acceptance',12,'scope_time_context','Môn đó có bao nhiêu tín chỉ?',sources=['electronics','communications'],answerable=False,
         negative_basis='Assistant-only topic history is not user authority or source proof; ask for the subject.',
         request_extra=dict(history=[dict(role='assistant',content='Môn đang nói tới là ELT7200 trong tài liệu Viễn thông.')]))
    assert len(rows)==len(rubric)==24 and len({x['qid'] for x in rows})==24
    for split in ['dev','acceptance']:
        group=[x for x in rows if x['split']==split]
        assert len(group)==12 and sum(x['answerable'] for x in group)==6
        assert Counter(x['category'] for x in group)==dict.fromkeys(['compare','arithmetic','two_hop','false_join','missing_hop','scope_time_context'],2)
    dev_docs={doc for row in rows if row['split']=='dev' for doc in row['request']['doc_ids']}
    acc_docs={doc for row in rows if row['split']=='acceptance' for doc in row['request']['doc_ids']}
    assert not dev_docs & acc_docs
    bench=OUT/'benchmark.jsonl'
    assert not bench.exists(), 'benchmark already exists without a protocol; inspect, never overwrite'
    bench.write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows),encoding='utf-8')
    write_once(OUT/'source-rubric.json',dict(status='SOURCE_REVIEWED_BEFORE_RUNTIME_CHANGE',reviewer='Codex — Automated AI Review',
        officially_human_approved=False,benchmark_sha256=sha(bench),cases=rubric,
        source_notes=['Mechatronics p4 continues the table headed on p3; physical row locations preserved.',
                      'Masters physical PDF p9 is printed p7; citations use physical p9.',
                      'Dev two-hop cases use real prerequisite relations across pages of one source; acceptance two-hop cases are explicit name-to-code-to-other-source lookups, not equivalence assertions.',
                      'Sources/code/value equality never supplies credit-recognition or prerequisite relationships.']))
    for path in [bench,OUT/'source-rubric.json',RAW/'source-records.json',RAW/'source-pages/render-receipt.json']:
        bindings[path.relative_to(ROOT).as_posix()]=sha(path)
    write_once(frozen,dict(status='FROZEN_BEFORE_PHASE10_RUNTIME_CHANGE',baseline_identity=source_identity(ROOT),
        count=24,dev=12,acceptance=12,positive=12,negative=12,families_disjoint=True,provider_posts=0,
        requirements=dict(resolution_and_required_hop_accuracy=1,semantic_answer_accuracy=1,negative_accuracy=1,
            false_join=0,scope_leak=0,unsupported_claim=0,contradicted_claim=0,false_abstention=0,public_schema_validity=1,
            source_coordinate_validity=1,minimum_coverage_percent=85),
        budget=dict(max_searches=2,max_candidates_per_search=20,max_total_candidates=40,max_generation_calls=1,
                    context='Unchanged configured char/token/output caps; no new model load for planning.'),
        qualification='Small exposed quality regression; not fresh validation, human approval, or live API qualification.',bindings=bindings))
    print(json.dumps(dict(status='PROTOCOL_FROZEN',cases=24,dev=12,acceptance=12,provider_posts=0)))


if __name__=='__main__':
    prepare()
