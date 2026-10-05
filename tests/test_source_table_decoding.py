import json

import pytest

from campusai.retrieval.source_scope import unsupported_source_reason
from campusai.retrieval.tokenizer_vi import source_body, normalize_retrieval_query
from evaluation.benchmarks.dev_evidence_extension import absence_proof
from evaluation.benchmarks.owner_generation import course_facts


def test_table_cells_with_json_line_breaks_are_actual_source_text():
    table = {'headers': ['Mã học phần', 'Học phần', 'Số tín chỉ'],
             'rows': [['ABC\n1234', 'Source\ncourse', '4']]}
    encoded = json.dumps(table, ensure_ascii=False)
    item = {'content': '[Document type: curriculum | Page: 1]\n\nTable headers\n\n'+encoded,
            'metadata': {'document_type': 'curriculum'}}
    body = source_body(item)
    assert 'ABC\n1234' in body and 'Source\ncourse' in body
    assert '\\n' not in body and 'Document type' not in body
    assert source_body(item, decode_tables=False).endswith(encoded)
    assert unsupported_source_reason('ABC1234 có bao nhiêu tín chỉ?', {'table':item}) is None
    assert unsupported_source_reason('DEF9876 có bao nhiêu tín chỉ?', {'table':item}) == 'course_code_not_in_selected_sources'


@pytest.mark.parametrize('content', ['{"headers": invalid', '{"headers": [42], "rows": [["a"]]}',
                                    '{"headers": ["a"], "rows": ["b"]}',
                                    '{"headers": ["a"], "rows": [[null]]}', '[ABC1234] literal source'])
def test_malformed_tables_and_literal_source_remain_unchanged(content):
    assert source_body({'content':content}) == content


@pytest.mark.parametrize('query', ['Tra cứu thông tin về nội dung tuyển sinh',
                                 'Information technology: thông tin và tin học',
                                 'Em muốn biết thông tin lịch học'])
def test_information_is_not_a_credit_request(query):
    assert 'tín chỉ credits' not in normalize_retrieval_query(query)


@pytest.mark.parametrize('query', ['mấy tin?', 'bao nhiêu tín?', '22 tín', '22tín',
                                 '5 tc', 'total credits', 'Số tín chỉ'])
def test_explicit_credit_and_count_shorthand_still_expand(query):
    assert 'tín chỉ credits' in normalize_retrieval_query(query)


def test_absence_proof_cannot_hide_policy_words_in_escaped_table_cells():
    table = {'headers':['Mã học phần','Học phần','Số tín chỉ'],
             'rows':[['ABC1234','Đại số','4'],['DEF1234','Vật lý','3']]}
    evidence = {('doc','table'):{'content':json.dumps(table,ensure_ascii=False), 'page':1,
                               'metadata':{'document_type':'curriculum'}}}
    facts=course_facts(evidence)
    evidence['doc','policy']={'content':json.dumps({'headers':['Lệ\nphí'], 'rows':[['100000']]},ensure_ascii=False),
                              'metadata':{'document_type':'curriculum'}}
    with pytest.raises(ValueError,match='source mention'):
        absence_proof(facts,'fee_waiver',evidence)


def test_candidates_keep_metadata_context_but_answer_lookup_requires_source_code(tmp_path):
    from campusai.retrieval.bm25_index import BM25Index
    from campusai.retrieval.hybrid import HybridRetriever
    rows = [{'doc_id':'catalog', 'chunk_id':'course', 'page':1,
             'content':'ABC1234 Source course 4 credits'},
            {'doc_id':'catalog', 'chunk_id':'context', 'page':2,
             'content':'Supporting curriculum information', 'heading_path':['ABC1234']}]
    BM25Index(rows).save(tmp_path/'catalog'/'bm25.json')
    retriever=HybridRetriever(tmp_path,query_cache_size=0)
    assert {r.chunk_id for r in retriever.generate_candidates('ABC1234 credits',['catalog'])} == {'course','context'}
    assert [r.chunk_id for r in retriever.search('ABC1234 credits',['catalog'],mode='auto')] == ['course']
    assert retriever.generate_candidates('DEF9876 credits',['catalog']) == []


def test_split_code_table_is_found_in_both_candidate_and_answer_paths(tmp_path):
    from campusai.retrieval.bm25_index import BM25Index
    from campusai.retrieval.hybrid import HybridRetriever
    table={'headers':['Mã học phần','Học phần','Số tín chỉ'],
           'rows':[['ABC\n1234','Source course','4']]}
    rows=[{'doc_id':'catalog','chunk_id':'table','page':1,
           'content':json.dumps(table,ensure_ascii=False)}]
    BM25Index(rows).save(tmp_path/'catalog'/'bm25.json')
    retriever=HybridRetriever(tmp_path,query_cache_size=0)
    assert [r.chunk_id for r in retriever.search('ABC1234 credits',['catalog'],mode='auto')] == ['table']
    assert [r.chunk_id for r in retriever.generate_candidates('ABC1234 credits',['catalog'])] == ['table']
