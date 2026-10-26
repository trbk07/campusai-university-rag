"""Product/cache integration with synthetic evidence, never provider quality."""
import copy
from datetime import date
import json
import re

from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.service import CampusAIQueryService
from campusai.rag.schemas import validate_release_response
from campusai.retrieval.bm25_index import BM25Index
from campusai.retrieval.hybrid import HybridRetriever


class ContractLLM:
    model='synthetic-contract'
    def __init__(self): self.calls=0
    def generate_json(self,prompt,**kwargs):
        self.calls+=1
        ids=re.findall(r'chunk_id=([^\s\n]+)',prompt)
        cid=next(cid for cid in ids if cid.endswith('-fact'))
        return dict(answer='MATH101 is required.',confidence='high',abstained=False,
            citations=[dict(chunk_id=cid,page=1,quote='MATH101 is required.')],
            claims=[dict(claim_id='c1',text='MATH101 is required.',citation_ids=[cid])])


def write_doc(root,doc_id,version,start,end=None):
    block=dict(family_id='Campus/Program',version_label=version,effective_start=start,proofs={})
    fields=dict(family_id='Program: Campus/Program',version_label='Version: '+version,
                effective_start='Effective from: '+start)
    if end:
        fields['effective_end']='Effective until: '+end;block['effective_end']=end
    items=[]
    for name,text in fields.items():
        cid=doc_id+'-'+name
        items.append(dict(chunk_id=cid,doc_id=doc_id,page=1,content=text,content_type='text'))
        block['proofs'][name]=dict(chunk_id=cid,page=1,quote=text)
    items.append(dict(chunk_id=doc_id+'-fact',doc_id=doc_id,page=1,content='MATH101 is required.',content_type='text'))
    for item in items: item['metadata']=dict(source_hash=doc_id,source_name=doc_id,page_range=[1,1],temporal=copy.deepcopy(block))
    BM25Index(items,'en').save(root/doc_id/'bm25.json')


def test_product_current_clock_boundary_cache_and_public_schema(tmp_path):
    write_doc(tmp_path,'old','2020','2020-01-01','2025-09-01')
    write_doc(tmp_path,'new','2025','2025-09-01')
    now=[date(2025,8,31)]
    llm=ContractLLM()
    service=CampusAIQueryService(HybridRetriever(tmp_path),GroundedAnswerGenerator(llm),
        default_mode='bm25',temporal_clock=lambda:now[0])
    try:
        question='Currently, is MATH101 required?'
        one=service.ask(question,language='en');assert not one.abstained
        assert {c.doc_id for c in one.citations}=={'old'}
        assert validate_release_response(one.to_public_dict())[0]
        assert service.ask(question,language='en').cache_hit and llm.calls==1
        now[0]=date(2025,9,1)
        two=service.ask(question,language='en')
        assert not two.abstained and {c.doc_id for c in two.citations}=={'new'} and llm.calls==2
        # Changed metadata and proof must invalidate both answer and retrieval state.
        write_doc(tmp_path,'new','2025','2025-10-01')
        missing=service.ask(question,language='en')
        assert missing.abstained and llm.calls==2 and not service.last_cache_hit
        assert validate_release_response(missing.to_public_dict())[0]
    finally: service.close()


def test_temporal_scope_negative_precedes_model_and_retrieval(tmp_path):
    write_doc(tmp_path,'old','2020','2020-01-01')
    llm=ContractLLM();retriever=HybridRetriever(tmp_path)
    service=CampusAIQueryService(retriever,GroundedAnswerGenerator(llm),default_mode='bm25')
    try:
        answer=service.ask('Theo bản chương trình QH-2025, MATH101 là gì?',doc_ids=['old'],authorized_doc_ids=['old'])
        assert answer.abstained and not answer.to_public_dict()['citations']
        assert llm.calls==0 and not retriever._indexes
        assert service.retrieve('Theo bản chương trình QH-2025, MATH101 là gì?',doc_ids=['old'])==[]
    finally: service.close()


def test_selected_content_reference_uses_same_scope_for_ask_and_retrieve(tmp_path):
    write_doc(tmp_path, 'chosen', '2020', '2020-01-01')
    write_doc(tmp_path, 'other', '2025', '2025-01-01')
    llm = ContractLLM()
    service = CampusAIQueryService(HybridRetriever(tmp_path), GroundedAnswerGenerator(llm), default_mode='bm25')
    question = 'Trong bản chương trình này, MATH101 is required?'
    try:
        answer = service.ask(question, doc_ids=['chosen'], language='en')
        assert not answer.abstained and llm.calls == 1
        assert {c.doc_id for c in answer.citations} == {'chosen'}
        assert service._request_local.temporal_trace['intent'] == 'none'
        results = service.retrieve(question, doc_ids=['chosen'])
        assert results and {r.doc_id for r in results} == {'chosen'}
        assert not service.retrieve(question, doc_ids=['chosen', 'other'])
        assert service.ask(question).abstained and llm.calls == 1
        assert service.ask('Theo bản chương trình năm 2025, MATH101 là gì?',
                           doc_ids=['chosen']).abstained and llm.calls == 1
    finally:
        service.close()


def test_retrieve_as_of_does_not_require_query_year_in_fact_chunk(tmp_path):
    write_doc(tmp_path,'old','2020','2020-01-01')
    service=CampusAIQueryService(HybridRetriever(tmp_path),GroundedAnswerGenerator(ContractLLM()),default_mode='bm25')
    try:
        result=service.retrieve('As of 01/01/2024, is MATH101 required?',doc_ids=['old'])
        assert result and {r.doc_id for r in result}=={'old'}
        assert service.ask('As of 01/01/2024, is MATH101 required?',doc_ids=['old'],top_k=0).abstained
    finally: service.close()


def test_program_filter_precedes_temporal_selection(tmp_path):
    for doc_id,program in [('a','Program A'),('b','Program B')]:
        write_doc(tmp_path,doc_id,'2025','2025-01-01')
        p=tmp_path/doc_id/'bm25.json';d=json.loads(p.read_text())
        for item in d['items']:item['metadata']['program']=program
        p.write_text(json.dumps(d),encoding='utf-8')
    service=CampusAIQueryService(HybridRetriever(tmp_path),GroundedAnswerGenerator(ContractLLM()),default_mode='bm25')
    try:
        answer=service.ask('Theo bản chương trình năm 2025, MATH101 là gì?',filters={'program':'Program A'})
        assert not answer.abstained and {c.doc_id for c in answer.citations}=={'a'}
    finally: service.close()


def test_restart_preserves_native_metadata_provenance(tmp_path):
    from campusai.ingestion.metadata_detector import detect_metadata
    text='Institution: Campus\nProgram: Engineering\nVersion: 2025\nEffective date: 01/09/2025\nMATH101 is required.'
    metadata=detect_metadata(text)
    metadata.update(source_hash='native',source_name='native',page_range=[1,1])
    BM25Index([dict(chunk_id='native-fact',doc_id='native',page=1,content=text,content_type='text',metadata=metadata)]).save(tmp_path/'native'/'bm25.json')
    for _ in range(2):
        service=CampusAIQueryService(HybridRetriever(tmp_path),GroundedAnswerGenerator(ContractLLM()),default_mode='bm25')
        try:
            answer=service.ask('Theo bản chương trình năm 2025, MATH101 là gì?',doc_ids=['native'])
            assert service._request_local.temporal_trace['eligible_doc_ids']==['native']
            assert not answer.abstained
        finally: service.close()


def test_compare_keeps_short_fact_blocks_and_source_verified_version(tmp_path):
    """Split HTML facts must survive a long subject's high ranking."""
    from campusai.retrieval.hybrid import RetrievalResult
    for doc, version in [('old', '2023'), ('new', 'QH-2025')]:
        write_doc(tmp_path, doc, version, '2020-01-01')
    class RankedCandidates(HybridRetriever):
        calls = 0
        def search(self, *args, **kwargs):
            self.calls += 1
            result = []
            for doc in ['old', 'new']:
                for i, content in enumerate(['Program name repeated', 'Program introduction',
                                              'Graduation title: Bachelor']):
                    result.append(RetrievalResult(doc + '-candidate-' + str(i), doc, 1,
                        content, 'text', 1.0, 'synthetic', {'source_hash': doc}))
            return result
    class Answer:
        calls = 0
        def generate_json(self, prompt, **kwargs):
            self.calls += 1
            for doc in ['old', 'new']:
                assert 'chunk_id=' + doc + '-candidate-2\n' in prompt
            return dict(answer='The 2023 graduation title is Bachelor; QH-2025 is Bachelor.',
                abstained=False, confidence='high',
                citations=[dict(chunk_id=d+'-candidate-2', page=1, quote='Graduation title: Bachelor')
                           for d in ['old', 'new']],
                claims=[dict(claim_id=d, text='The '+v+' graduation title is Bachelor.',
                             citation_ids=[d+'-candidate-2']) for d,v in [('old','2023'),('new','QH-2025')]])
    retriever = RankedCandidates(tmp_path)
    llm = Answer()
    service = CampusAIQueryService(retriever, GroundedAnswerGenerator(llm), default_mode='bm25')
    try:
        answer = service.ask('Compare graduation title of Program between version 2023 and QH-2025.', top_k=4)
        assert not answer.abstained
        assert {c.doc_id for c in answer.citations} == {'old', 'new'}
        assert retriever.calls == llm.calls == 1
        # The same source version cannot support a fabricated future year.
        from campusai.rag.claims import Claim, align_claims
        from campusai.rag.evidence import EvidenceRegistry
        bad = align_claims([Claim('bad', 'The QH-2099 graduation title is Bachelor.',
                                  citation_ids=('new-candidate-2',))],
                           EvidenceRegistry(service.last_retrieval), {})
        assert bad[0].status != 'supported'
    finally:
        service.close()
