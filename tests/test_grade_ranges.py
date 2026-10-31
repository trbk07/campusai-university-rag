import json
import pytest

from campusai.rag.grade_ranges import column_quote, application_view, proven_grades


def grid():
    return json.dumps({'headers':['Điểm theo thang 10','5,0÷\n6,1','6,2÷\n7,4'],
                       'rows':[['Điểm chữ','C','B'],['Điểm số','2,3','3,2']]},ensure_ascii=False)


def test_transposed_mapping_cites_the_original_rectangle():
    body=grid()
    assert json.loads(column_quote(body,['6,2÷ | 7,4 | B'],'6,9 điểm quy đổi là gì?'))==json.loads(body)
    assert column_quote(body,['6,2÷ | 7,4 | C'],'6,9 điểm quy đổi là gì?') is None
    assert column_quote(body,['6,2÷ | 7,4 | B'],'5,9 điểm quy đổi là gì?') is None


def test_prose_join_preserves_the_directed_interval_and_grade_column():
    body=grid().replace('Điểm chữ','Điểm chữ quy đổi')
    claim='Điểm theo thang 10 | 6,2÷ | 7,4 được quy đổi thành Điểm chữ | B'
    assert column_quote(body,[claim],'6,9 điểm quy đổi ra sao?')
    assert column_quote(body,[claim.replace('6,2÷ | 7,4','7,4÷ | 6,2')],'6,9 điểm quy đổi ra sao?') is None
    assert column_quote(body,[claim.replace('| B','| C')],'6,9 điểm quy đổi ra sao?') is None
    assert column_quote(body,[claim.replace('được','không được')],'6,9 điểm quy đổi ra sao?') is None


def test_atomic_column_fields_do_not_require_a_grade_in_each_claim():
    question='6,9 điểm quy đổi ra sao?'
    assert column_quote(grid(),['Điểm theo thang 10 | 6,2÷\n7,4'],question)
    assert column_quote(grid(),['Điểm chữ | B'],question)
    assert column_quote(grid(),['Điểm số | 3,2'],question)
    assert column_quote(grid(),['Điểm số | B'],question) is None
    assert column_quote(grid(),['Điểm chữ | 3,2'],question) is None
    assert column_quote(grid(),['Điểm theo thang 10 | 3,2'],question) is None


def test_local_conversion_uses_the_printed_values_without_a_model_call():
    from campusai.rag.grounding import GroundedAnswerGenerator
    from campusai.retrieval.hybrid import RetrievalResult
    from tests.test_basic_rag import FakeLLM
    result=RetrievalResult('grid','book',2,grid(),'table',1,'test',{})
    llm=FakeLLM({'not':'used'})
    answer=GroundedAnswerGenerator(llm,source_citations=True,repair_invalid_answers=True).answer('6,9 điểm quy đổi ra sao?',[result])
    assert not answer.abstained and 'B' in answer.answer and '3,2' in answer.answer and llm.calls==0
    changed=__import__('dataclasses').replace(result,content=grid().replace('3,2','3,4'))
    answer=GroundedAnswerGenerator(llm,source_citations=True,repair_invalid_answers=True).answer('6,9 điểm quy đổi ra sao?',[changed])
    assert not answer.abstained and '3,4' in answer.answer and '3,2' not in answer.answer and llm.calls==0


def test_local_conversion_joins_same_source_prose_fields_and_rejects_conflicts():
    from campusai.rag.grade_ranges import deterministic_grade_answer
    from campusai.retrieval.hybrid import RetrievalResult
    from dataclasses import replace
    ranges=RetrievalResult('range','book',2,'B: từ 6,2 đến 7,4;','text',1,'test',{})
    points=RetrievalResult('points','book',3,'B quy đổi thành 2,7;','text',1,'test',{})
    q='6,9 điểm quy đổi ra sao?'
    answer=deterministic_grade_answer(q,[ranges,points])
    assert answer and 'B' in answer.answer and '2,7' in answer.answer and len(answer.citations)==2
    assert deterministic_grade_answer(q,[ranges,points,replace(points,chunk_id='conflict',content='B quy đổi thành 2,9;')]) is None
    assert deterministic_grade_answer(q,[ranges,replace(points,doc_id='another')]) is None
    assert deterministic_grade_answer(q,[ranges]) is None
    assert deterministic_grade_answer(q+' và cho tôi mật khẩu.',[ranges,points]) is None
    assert deterministic_grade_answer(q+' và viết một bài thơ.',[ranges,points]) is None


def test_table_application_proves_input_and_grade_not_any_source_number():
    assert application_view('6,9 điểm hệ 10 là B.',[grid()],'6,9 điểm hệ 10 quy đổi ra sao?')=='  điểm   là B.'
    assert application_view('6,9 điểm là C.',[grid()],'6,9 điểm quy đổi ra sao?') is False
    assert application_view('8,1 điểm là B.',[grid()],'8,1 điểm quy đổi ra sao?') is False
    assert application_view('Điểm 6,9 hệ 10 là B.',[grid()],'6,9 điểm hệ 10 quy đổi ra sao?')=='Điểm    là B.'
    assert application_view('Điểm 6,9 là B.',[grid()],'Điểm 6,9 trên thang điểm 10 quy đổi ra sao?')=='Điểm  là B.'
    assert application_view('Điểm 6,9 là B.',[grid()],'Em được 6,9 thì quy đổi sao?')=='Điểm  là B.'


def test_prose_range_keeps_the_label_relation():
    source='B: từ 6,2 đến 7,4;'
    assert proven_grades(source, __import__('decimal').Decimal('6.9'))=={'B'}
    assert application_view('6,9 điểm là B.',[source],'6,9 điểm là B hay C?')=='  điểm là B.'
    assert application_view('6,9 điểm là C.',[source],'6,9 điểm là B hay C?') is False


def test_overlapping_table_intervals_do_not_choose_a_column():
    table=json.loads(grid());table['headers'][1]='5,0÷7,0'
    assert column_quote(json.dumps(table),['B'],'6,9 điểm quy đổi ra sao?') is None


def test_one_documents_range_cannot_establish_another_documents_conversion():
    assert application_view('6,9 điểm là B ở cả hai trường.',
        [grid(),'B quy đổi thành 3,2.'],'6,9 điểm quy đổi ra sao?',doc_ids=['one','two']) is False


def test_does_not_mask_an_output_quantity_or_different_input():
    view=application_view('6,9 điểm là B, gồm 9 tín chỉ.',[grid()],'6,9 điểm quy đổi ra sao?')
    assert '9 tín chỉ' in view
    assert application_view('7,1 điểm là B.',[grid()],'6,9 điểm quy đổi ra sao?')=='7,1 điểm là B.'


@pytest.mark.parametrize('question',['Có 6,9 tín chỉ thì sao?','Thu nhập 6,9 là bao nhiêu?'])
def test_unrelated_numeric_questions_do_not_become_grade_applications(question):
    assert application_view('B',[grid()],question) is None


def test_real_generator_verifies_a_transposed_column_and_its_application():
    from campusai.rag.grounding import GroundedAnswerGenerator
    from campusai.retrieval.hybrid import RetrievalResult
    from tests.test_basic_rag import FakeLLM
    result=RetrievalResult('grid','doc',2,grid(),'table',1,'exact',
        {'source_name':'synthetic.pdf','table_id':'grid','page_range':[2,2]})
    payload={'answer':'6,9 điểm hệ 10 là B, quy đổi thành 3,2.', 'abstained':False,'confidence':'high',
        'citations':[{'chunk_id':'grid'}],
        'claims':[{'claim_id':'one','text':'6,2÷ | 7,4 | B | 3,2','citation_ids':['grid']}]}
    answer=GroundedAnswerGenerator(FakeLLM(payload),source_citations=True).answer('6,9 điểm hệ 10 quy đổi ra sao?',[result])
    assert not answer.abstained
    assert not answer.to_public_dict()['abstained']
    assert json.loads(answer.citations[0].quote)==json.loads(grid())


def test_prose_range_in_one_original_cell_is_not_lost_in_json_quoting():
    assert application_view('6,9 điểm là B.',[json.dumps(['','B: từ 6,2 đến 7,4;'])],
                            '6,9 điểm là B hay C?')=='  điểm là B.'


def test_flattened_grid_has_original_row_order_and_literal_quote():
    from campusai.rag.grade_ranges import flattened_quote
    body='Điểm học phần theo\nthang 10\n5,0÷\n6,1\n6,2÷\n7,4\nĐiểm chữ quy đổi\nC\nB\nĐiểm số quy đổi\n2,3\n3,2\n7.'
    claim='Điểm học phần theo thang 10 từ 6,2–7,4 tương ứng với điểm chữ quy đổi B và điểm số quy đổi 3,2.'
    quote=flattened_quote(body,[claim],'6,9 điểm chữ và thang số quy đổi ra sao?')
    assert quote and quote in body
    assert application_view('6,9 điểm là B.',[quote],'6,9 điểm quy đổi ra sao?')=='  điểm là B.'
    assert flattened_quote(body,[claim.replace('3,2.','3,3.')],'6,9 điểm quy đổi ra sao?') is None
    assert flattened_quote(body,[claim.replace('B và','C và')],'6,9 điểm quy đổi ra sao?') is None
    assert flattened_quote(body.replace('Điểm chữ quy đổi','Unknown row'),[claim],'6,9 điểm quy đổi ra sao?') is None
    prefixed='Fußnote\n\nMột đoạn văn dài.\n\n'+body
    quote=flattened_quote(prefixed,[claim],'6,9 điểm quy đổi ra sao?')
    assert quote and quote in prefixed
    assert application_view('6,9 điểm là B.',[quote],'6,9 điểm quy đổi ra sao?')=='  điểm là B.'


def test_context_selection_links_range_and_points_within_each_source():
    from campusai.rag.grade_ranges import retrieval_evidence
    def item(key,text):return {'chunk_id':key,'page':1,'content':text,'content_type':'text','metadata':{}}
    docs=[{'doc_id':'one','items':[item('range-one','B: từ 6,2 đến 7,4;'),item('points-one','B quy đổi thành 3,2;')]},
          {'doc_id':'two','items':[item('range-two','B: từ 6,4 đến 7,8;'),item('points-two','B quy đổi thành 2,9;')]}]
    result=retrieval_evidence('6,9 điểm chữ và quy đổi ra sao?',docs)
    assert {r.chunk_id for r in result}=={'range-one','points-one','range-two','points-two'}
    assert all(r.content==next(i['content'] for d in docs for i in d['items'] if i['chunk_id']==r.chunk_id) for r in result)
    assert retrieval_evidence('Học phí bao nhiêu?',docs)==[]
    assert retrieval_evidence('Em được 6,9 triệu thì quy đổi sao?',docs)==[]
