"""Date fields require a proved notice/round and an unambiguous source label."""
from copy import deepcopy
import unicodedata

import pytest

from campusai.rag.grounding import GroundedAnswerGenerator, validate_citation
from campusai.rag.service import CampusAIQueryService
from campusai.retrieval.bm25_index import BM25Index
from campusai.retrieval.hybrid import HybridRetriever
from tests.test_curriculum_lookup import NoGeneration


def document():
    texts = [
        'THÔNG BÁO TUYỂN SINH ĐÀO TẠO THẠC SĨ ĐỢT 4 NĂM 2035\n1.',
        '6.2. Thời gian phỏng vấn: ngày 12/09/2035.',
        '2.14. Thời gian thu nhận hồ sơ\n'
        '- Thời gian đăng ký trực tuyến trên phần mềm tuyển sinh sau đại học của Trường:\n'
        'từ 8h00 ngày 01/07/2035 đến 16h30 ngày 20/08/2035.\n'
        '- Thời gian nộp hồ sơ đăng ký xét tuyển thẳng tại Phòng Đào tạo:\n'
        'từ 8h00 ngày 01/07/2035 đến 16h30 ngày 20/08/2035.\n'
        'Ghi chú: Đối với thí sinh đăng ký xét tuyển thẳng ngoài việc đăng ký trực tuyến còn phải nộp hồ sơ bản cứng.',
    ]
    return {'doc_id':'notice','items':[dict(chunk_id='part'+str(i),doc_id='notice',page=i+1,
        content=text,content_type='text',metadata={'source_name':'notice.pdf','source_hash':'notice',
        'page_range':[i+1,i+1]}) for i,text in enumerate(texts)]}


@pytest.mark.parametrize('question,value', [
    ('phong van thac sy dot 4 ngay nao', '12/09/2035'),
    ('han dang ky truc tuyen tuyen thang thac si dot 4 la ngay nao', '20/08/2035'),
    ('xtt ths đ4 chốt đk online bn h', '16h30'),
])
def test_selected_notice_dates_are_read_without_generation(tmp_path,question,value):
    doc=document()
    # Real PDF text commonly contains decomposed Vietnamese accents.
    for item in doc['items']:item['content']=unicodedata.normalize('NFD',item['content'])
    BM25Index(doc['items'],'vi').save(tmp_path/'notice'/'bm25.json')
    service=CampusAIQueryService(HybridRetriever(tmp_path),GroundedAnswerGenerator(NoGeneration()),default_mode='bm25')
    try:
        answer=service.ask(question,doc_ids=['notice'])
        assert not answer.abstained and value in answer.answer
        assert service.retriever.last_trace.route=='source_notice_field'
        assert all(validate_citation(c,service.last_retrieval[0],require_quote=True).valid for c in answer.citations)
    finally:service.close()


def project(question='phong van thac sy dot 4 ngay nao',doc=None,**kwargs):
    from campusai.rag.notice_dates import lookup_notice_date
    return lookup_notice_date(question,[doc or document()],doc_ids=['notice'],**kwargs)


@pytest.mark.parametrize('text',[
    'Thời gian phỏng vấn: ngày 99/09/2035.',
    'Thời gian phỏng vấn: chưa chốt.',
    'Thời gian phỏng vấn: ngày 13/09/2035.',
])
def test_a_second_invalid_unknown_or_conflicting_date_cannot_be_ignored(text):
    doc=document(); item=deepcopy(doc['items'][1]); item['chunk_id']='other'; item['content']=text
    doc['items'].append(item)
    assert project(doc=doc) is None


@pytest.mark.parametrize('question',[
    'phong van thac sy dot 3 ngay nao',
    'phong van thac sy dot 4 nam 2036 ngay nao',
    'phong van thac sy dot 4 ngay nao va hoc phi bao nhieu',
    'phong van thac sy dot 4 ngay nao neu em chuyen nganh',
    'phong van thac sy dot 4 va dot 5 ngay nao',
    'han dang ky truc tuyen tuyen thang thac si dot 4 la ngay nao va phi bao nhieu',
])
def test_wrong_scope_conditions_and_additional_facts_are_not_projected(question):
    assert project(question) is None


@pytest.mark.parametrize('title',[
    'Ví dụ: THÔNG BÁO TUYỂN SINH ĐÀO TẠO THẠC SĨ ĐỢT 4 NĂM 2035',
    'This filename mentions round4 but the source does not.',
    'THÔNG BÁO TUYỂN SINH ĐẠI HỌC ĐỢT 4 NĂM 2035',
])
def test_filename_or_metadata_cannot_establish_the_notice_role(title):
    doc=document(); doc['items'][0]['content']=title
    doc['items'][0]['metadata']['heading_path']=['THÔNG BÁO TUYỂN SINH ĐÀO TẠO THẠC SĨ ĐỢT 4 NĂM 2035']
    assert project(doc=doc) is None


@pytest.mark.parametrize('replacement',[
    ('16h30','25h00'),('20/08/2035','99/08/2035'),('20/08/2035','20/06/2035'),
])
def test_online_clock_date_and_chronology_are_validated(replacement):
    doc=document(); doc['items'][2]['content']=doc['items'][2]['content'].replace(*replacement)
    assert project('xtt ths đ4 chốt đk online bn h',doc) is None


def test_a_different_round_in_the_same_pdf_requires_disambiguation():
    doc=document(); item=deepcopy(doc['items'][0]); item['chunk_id']='other-title'
    item['content']=item['content'].replace('ĐỢT 4','ĐỢT 5'); doc['items'].append(item)
    assert project(doc=doc) is None


def test_conditional_source_fields_do_not_lose_their_qualifier():
    doc=document(); doc['items'][1]['content']='Nếu đủ hồ sơ, '+doc['items'][1]['content']
    assert project(doc=doc) is None


def test_only_the_selected_document_can_supply_title_and_value():
    from campusai.rag.notice_dates import lookup_notice_date
    doc=document()
    for ids,docs in [(None,[doc]),(['other'],[doc]),(['notice','other'],[doc]),(['notice'],[doc,doc])]:
        assert lookup_notice_date('phong van thac sy dot 4 ngay nao',docs,doc_ids=ids) is None


def test_old_refusal_is_bypassed_and_date_survives_sqlite_restart(tmp_path,monkeypatch):
    from campusai.rag import service as service_module, notice_dates
    from campusai.rag.cache import RAGAnswerCache, build_rag_cache_key
    from campusai.rag.grounding import _abstention
    doc=document(); BM25Index(doc['items'],'vi').save(tmp_path/'notice'/'bm25.json')
    path=str(tmp_path/'answers.sqlite3'); question='phong van thac sy dot 4 ngay nao'
    def application():
        return CampusAIQueryService(HybridRetriever(tmp_path),GroundedAnswerGenerator(NoGeneration()),
                                    default_mode='bm25',cache=RAGAnswerCache(path))
    with monkeypatch.context() as legacy:
        legacy.setattr(service_module,'build_rag_cache_key',
                       lambda **kw:build_rag_cache_key(**kw,grounding_policy_version='grounding-v34'))
        legacy.setattr(notice_dates,'lookup_notice_date',lambda *_a,**_kw:None)
        old=application(); legacy.setattr(old.answer_generator,'answer',lambda *_a,**_kw:_abstention('unsupported_claim'))
        try:assert old.ask(question,doc_ids=['notice']).abstained
        finally:old.close()
    for cached in (False,True):
        current=application()
        try:
            result=current.ask(question,doc_ids=['notice'])
            assert not result.abstained and '12/09/2035' in result.answer
            assert current.last_cache_hit is cached
        finally:current.close()
