"""Citation location alone cannot establish a claim's visible source proof."""
from copy import deepcopy
import json
import pytest

from evaluation.grounding.grounding_metrics import evaluate_grounding,is_grounded_answer


def composite_row():
    source = 'The programme lasts 4 years and requires 132 credits.'
    return {'answerable': True, 'abstained': False,
        'claims': [{'claim_id': 'combined', 'text': source, 'status': 'supported', 'citation_ids': ['c']}],
        'citations': [{'chunk_id': 'c', 'doc_id': 'doc', 'page': 3, 'quote': source}],
        'gold_claims': [{'claim_id': 'duration', 'text': 'The programme lasts 4 years.',
                        'evidence': [{'doc_id': 'doc', 'page': 3, 'quote': source}]},
                       {'claim_id': 'credits', 'text': 'The programme requires 132 credits.',
                        'evidence': [{'doc_id': 'doc', 'page': 3, 'quote': source}]}]}


def test_one_reviewed_composite_claim_can_prove_two_atomic_facts_without_changing_denominators():
    row = composite_row()
    metrics = evaluate_grounding([row], allow_reviewed_source_subspan=True)
    assert metrics['predicted_claim_count'] == metrics['matched_predicted_claim_count'] == 1
    assert metrics['gold_claim_count'] == metrics['matched_gold_claim_count'] == 2
    for field in ['grounded_claim_precision', 'grounded_claim_recall', 'citation_precision',
                  'citation_recall', 'citation_completeness']:
        assert metrics[field] == 1, (field, metrics)
    assert is_grounded_answer(row, allow_reviewed_source_subspan=True)


@pytest.mark.parametrize('mutation', ['wrong_value', 'wrong_page', 'missing_quote', 'extra_fact'])
def test_composite_coverage_cannot_hide_bad_values_sources_or_extra_claims(mutation):
    row = composite_row()
    if mutation == 'wrong_value': row['claims'][0]['text'] = row['claims'][0]['text'].replace('132', '133')
    if mutation == 'wrong_page': row['citations'][0]['page'] = 4
    if mutation == 'missing_quote': row['citations'][0]['quote'] = 'The programme lasts 4 years.'
    if mutation == 'extra_fact': row['claims'].append({'claim_id': 'extra', 'text': 'Tuition is free.', 'status': 'supported', 'citation_ids': ['c']})
    metrics = evaluate_grounding([row], allow_reviewed_source_subspan=True)
    assert not is_grounded_answer(row, allow_reviewed_source_subspan=True)
    assert metrics['citation_recall'] < 1 or metrics['unsupported_claim_leakage'] > 0


def test_repeated_model_claims_cannot_inflate_gold_recall_or_citation_recall():
    row = composite_row()
    row['claims'].append({**row['claims'][0], 'claim_id': 'repeat'})
    metrics = evaluate_grounding([row], allow_reviewed_source_subspan=True)
    assert metrics['matched_gold_claim_count'] == 2
    assert metrics['grounded_claim_recall'] == metrics['citation_recall'] == 1
    assert metrics['claim_citation_precision'] == .5


def test_identical_wording_in_an_uncited_second_source_does_not_gain_composite_credit():
    row = composite_row()
    row['gold_claims'] = [row['gold_claims'][0], deepcopy(row['gold_claims'][0])]
    row['gold_claims'][1]['claim_id'] = 'other-source'
    row['gold_claims'][1]['evidence'][0]['doc_id'] = 'other-doc'
    row['claims'][0]['text'] = 'The programme lasts 4 years.'
    metrics = evaluate_grounding([row], allow_reviewed_source_subspan=True)
    assert metrics['matched_gold_claim_count'] == 1
    assert metrics['grounded_claim_precision'] == metrics['citation_precision'] == 1
    assert metrics['grounded_claim_recall'] == .5


@pytest.mark.parametrize('mutation,expected', [('none',1), ('number',0), ('negation',0), ('extra',0), ('page',0)])
def test_literal_context_extension_preserves_the_reviewed_quantity_and_scope(mutation, expected):
    claim = 'tích lũy trước tối thiểu 03 học phần trong chương trình đại học'
    source = 'Thí sinh đủ điều kiện và '+claim+'.'
    row = {'answerable': True, 'abstained': False,
        'claims': [{'text': claim, 'status': 'supported', 'citation_ids': ['c']}],
        'citations': [{'chunk_id': 'c', 'doc_id': 'doc', 'page': 9, 'quote': source}],
        'gold_claims': [{'text': 'At least 3 prior courses are required.',
            'evidence': [{'doc_id': 'doc', 'page': 9, 'quote': 'và tích lũy trước tối thiểu 03 học phần'}]}]}
    if mutation == 'number': row['claims'][0]['text'] = claim.replace('03', '04')
    if mutation == 'negation': row['claims'][0]['text'] = 'không '+claim
    if mutation == 'extra': row['claims'][0]['text'] += '. Tuition is free.'
    if mutation == 'page': row['citations'][0]['page'] = 8
    metrics = evaluate_grounding([row], allow_reviewed_source_subspan=True)
    assert metrics['grounded_claim_precision'] == expected


@pytest.mark.parametrize('claim,expected', [
    ('Những học phần có điểm đánh giá từ điểm C trở lên.', 1),
    ('Những học phần có điểm đánh giá từ điểm D trở lên.', 0),
    ('Những học phần có điểm đánh giá điểm C.', 0),
])
def test_letter_grade_minimum_cannot_be_lost_or_replaced_in_reviewed_source_subspan(claim, expected):
    source = 'Quy định. Những học phần có điểm đánh giá từ điểm C trở lên.'
    row = {'answerable': True, 'abstained': False,
        'claims': [{'text': claim, 'status': 'supported', 'citation_ids': ['c']}],
        'citations': [{'chunk_id':'c','doc_id':'doc','page':2,'quote':source}],
        'gold_claims': [{'text':'A grade of at least C is required.',
            'evidence':[{'doc_id':'doc','page':2,'quote':source}]}]}
    assert evaluate_grounding([row], allow_reviewed_source_subspan=True)['grounded_claim_precision'] == expected


@pytest.mark.parametrize('label,actual,claim,gold,doc,page,expected',[
    ('5. ','Admissions contact phone: 02437547865 (business hours).',None,None,'source',1,1),
    ('5. ','Admissions contact phone: 02437547865 (business hours).',
        '5. Admissions contact phone: 02437547865 (business hours).',None,'source',1,1),
    ('5. ','Admissions contact phone: 02437547864 (business hours).',None,None,'source',1,0),
    ('5. ','Admissions contact phone: 02437547865 (business hours).',None,None,'other',1,0),
    ('5. ','Admissions contact phone: 02437547865 (business hours).',None,None,'source',2,0),
    ('2025. ','Admissions contact phone: 02437547865 (business hours).',None,None,'source',1,0),
    ('5. ','Admissions contact phone: 02437547865 (business hours).',None,
        'Item5 lists the telephone contact number02437547865.','source',1,0),
    ('5. ','Admissions contact phone: 02437547865 (business hours).',
        '9. Admissions contact phone: 02437547865 (business hours).',None,'source',1,0),
])
def test_source_list_label_is_cosmetic_only_when_not_a_required_fact(label,actual,claim,gold,doc,page,expected):
    source='Admissions contact phone: 02437547865 (business hours).'
    row={'answerable':True,'abstained':False,
        'claims':[{'text':claim or actual,'status':'supported','citation_ids':['c']}],
        'citations':[{'chunk_id':'c','doc_id':doc,'page':page,'quote':actual}],
        'gold_claims':[{'text':gold or 'The telephone contact number is02437547865.',
            'evidence':[{'doc_id':'source','page':1,'quote':label+source}]}]}
    metrics=evaluate_grounding([row])
    assert metrics['citation_precision']==metrics['grounded_claim_precision']==expected


def test_leading_quantity_and_decimal_are_not_discarded_as_layout():
    from evaluation.grounding.grounding_metrics import _citation_matches_evidence
    for prefix in ['5. years are required.','5.0 years are required.']:
        assert not _citation_matches_evidence({'doc_id':'doc','page':1,'quote':'years are required.'},
            {'doc_id':'doc','page':1,'quote':prefix},'The duration is3 years.')
    # No fact-aware opt-in: the ordinary source comparison remains strict.
    assert not _citation_matches_evidence({'doc_id':'doc','page':1,'quote':'Contact:123.'},
        {'doc_id':'doc','page':1,'quote':'5. Contact:123.'})


def test_same_row_label_and_programme_identifier_preserve_the_complete_identifier():
    from evaluation.grounding.grounding_metrics import _citation_matches_evidence
    evidence={'doc_id':'doc','page':1,'quote':'14. CN14 Information systems 7480104 240'}
    fact='Programme CN14 has national discipline code7480104.'
    assert _citation_matches_evidence({'doc_id':'doc','page':1,
        'quote':'CN14 Information systems 7480104 240'},evidence,fact)
    assert not _citation_matches_evidence({'doc_id':'doc','page':1,
        'quote':'CN15 Information systems 7480104 240'},evidence,fact)


@pytest.mark.parametrize('claim,expected', [
    ('La duracion es de 4 anos.', 1),
    ('La duracion es de 5 anos.', 0),
    ('No: La duracion es de 4 anos.', 0),
    ('La duracion es de 4 anos. Tuition is free.', 0),
])
def test_complete_reviewed_source_span_can_match_a_gold_in_another_language(claim, expected):
    source = 'La duracion es de 4 anos.'
    row = {'answerable': True, 'abstained': False,
           'claims': [{'text': claim, 'status': 'supported', 'citation_ids': ['c']}],
           'citations': [{'chunk_id': 'c', 'doc_id': 'doc', 'page': 1, 'quote': source}],
           'gold_claims': [{'text': 'The programme lasts 4 years.',
                            'evidence': [{'doc_id': 'doc', 'page': 1, 'quote': source}]}]}
    assert evaluate_grounding([row])['grounded_claim_precision'] == expected


def test_reviewed_literal_equivalence_still_requires_the_correct_visible_source():
    source = 'La duracion es de 4 anos.'
    row = {'answerable': True, 'abstained': False,
           'claims': [{'text': source, 'status': 'supported', 'citation_ids': ['c']}],
           'citations': [{'chunk_id': 'c', 'doc_id': 'other', 'page': 1, 'quote': source}],
           'gold_claims': [{'text': 'The programme lasts 4 years.',
                            'evidence': [{'doc_id': 'doc', 'page': 1, 'quote': source}]}]}
    assert evaluate_grounding([row])['grounded_claim_precision'] == 0


def test_cross_language_claim_can_be_a_literal_subspan_of_its_reviewed_gold_quote():
    reviewed = ('các khóa đào tạo thạc sĩ tuyển sinh từ năm 2022 có chuẩn đầu ra '
                'đạt từ Bậc 4 trở lên hoặc tương đương theo Khung năng lực ngoại ngữ 6 bậc dùng cho Việt Nam')
    claim = 'lưu ý ' + reviewed
    row = {'answerable': True, 'abstained': False,
           'claims': [{'text': claim, 'status': 'supported', 'citation_ids': ['c']}],
           'citations': [{'chunk_id': 'c', 'doc_id': 'doc', 'page': 1,
                          'quote': 'Chuẩn ngoại ngữ áp dụng (' + reviewed + ').'}],
           'gold_claims': [{'text': 'Masters cohorts admitted from 2022 require at least Level 4 or equivalent.',
                            'evidence': [{'doc_id': 'doc', 'page': 1, 'quote': reviewed}]}]}
    metrics = evaluate_grounding([row], allow_reviewed_source_subspan=True)
    assert metrics['grounded_claim_precision'] == metrics['grounded_claim_recall'] == 1
    assert metrics['citation_precision'] == metrics['citation_recall'] == 1


@pytest.mark.parametrize('claim,reviewed,gold,expected', [
    ('còn hiệu lực tính đến ngày đăng ký dự tuyển',
     'Một trong các chứng chỉ còn hiệu lực tính đến ngày đăng ký dự tuyển.',
     'A qualifying certificate must remain valid on the application date.', 1),
    ('còn hiệu lực tính đến ngày đăng ký dự tuyển và được gia hạn thêm một năm',
     'Một trong các chứng chỉ còn hiệu lực tính đến ngày đăng ký dự tuyển.',
     'A qualifying certificate must remain valid on the application date.', 0),
    ('bắt buộc có chứng chỉ', 'Chứng chỉ không bắt buộc có chứng chỉ.',
     'A certificate is mandatory.', 0),
])
def test_source_subspan_keeps_scope_and_polarity_and_rejects_added_facts(claim, reviewed, gold, expected):
    row = {'answerable': True, 'abstained': False,
           'claims': [{'text': claim, 'status': 'supported', 'citation_ids': ['c']}],
           'citations': [{'chunk_id': 'c', 'doc_id': 'doc', 'page': 2, 'quote': reviewed}],
           'gold_claims': [{'text': gold,
                            'evidence': [{'doc_id': 'doc', 'page': 2,
                                         'quote': 'còn hiệu lực tính đến ngày đăng ký dự tuyển'}]}]}
    assert evaluate_grounding([row], allow_reviewed_source_subspan=True)['grounded_claim_precision'] == expected


def test_reviewed_source_subspan_requires_gold_numeric_anchors_and_matching_coordinates():
    from evaluation.grounding.grounding_metrics import _pair_similarity
    gold = {'text': 'Cohorts admitted from 2022 require Level 4.',
            'evidence': [{'doc_id': 'doc', 'page': 1, 'chunk_id': 'c',
                          'quote': 'Theo thông báo, các khóa từ năm 2022 yêu cầu Bậc 4 hoặc tương đương.'}]}
    row = {'citations': [{'chunk_id': 'c', 'doc_id': 'doc', 'page': 1,
                          'quote': 'Theo thông báo, các khóa từ năm 2022 yêu cầu Bậc 4 hoặc tương đương.'}]}
    assert _pair_similarity({'text': 'yêu cầu Bậc 4', 'citation_ids': ['c']}, gold, row,
                            allow_reviewed_source_subspan=True) < .35
    predicted = {'text': 'các khóa từ năm 2022 yêu cầu Bậc 4', 'citation_ids': ['c']}
    assert _pair_similarity(predicted, gold, row, allow_reviewed_source_subspan=True) == 1
    assert _pair_similarity(predicted, gold, row) < .35  # Shared Phase 8/default metric remains unchanged.
    wrong = {'citations': [{'chunk_id': 'c', 'doc_id': 'other', 'page': 1,
                            'quote': 'Theo thông báo, các khóa từ năm 2022 yêu cầu Bậc 4 hoặc tương đương.'}]}
    assert _pair_similarity(predicted, gold, wrong, allow_reviewed_source_subspan=True) < .35


def test_scoped_table_row_can_cover_a_broader_reviewed_table_quote_only_in_phase5_mode():
    quote = json.dumps({'scope': 'Semester 4', 'headers': ['№', 'Discipline', 'Credits', 'Resources'],
        'rows': [['2', 'Strength of Materials', '3', 'VNU-UET']]}, ensure_ascii=False)
    row = {'answerable': True, 'abstained': False,
        'claims': [{'text': 'Strength of Materials has 3 credits.', 'status': 'supported',
                    'citation_ids': ['table-row']}],
        'citations': [{'chunk_id': 'table-row', 'doc_id': 'doc', 'page': 2, 'quote': quote}],
        'gold_claims': [{'text': 'In semester 4, Strength of Materials carries 3 credits.',
            'evidence': [{'doc_id': 'doc', 'page': 2,
                'quote': 'Semester 4 Compulsory Subjects 1 History of Vietnam Communist Party 2 Strength of Materials 3 VNU-UET'}]}]}
    strict = evaluate_grounding([row])
    assert strict['citation_precision'] == strict['grounded_claim_precision'] == 0
    phase5 = evaluate_grounding([row], allow_reviewed_source_subspan=True)
    assert phase5['citation_precision'] == phase5['grounded_claim_precision'] == 1
    wrong_scope = deepcopy(row)
    wrong_scope['citations'][0]['quote'] = json.dumps({'scope': 'Semester 6',
        'headers': ['№', 'Discipline', 'Credits', 'Resources'],
        'rows': [['2', 'Strength of Materials', '3', 'VNU-UET']]}, ensure_ascii=False)
    assert evaluate_grounding([wrong_scope], allow_reviewed_source_subspan=True)['citation_precision'] == 0
    wrong_row = deepcopy(row)
    wrong_row['citations'][0]['quote'] = json.dumps({'scope': 'Semester 4',
        'headers': ['№', 'Discipline', 'Credits', 'Resources'],
        'rows': [['1', 'History of Vietnam Communist Party', '2', 'VNU-UET']]}, ensure_ascii=False)
    assert evaluate_grounding([wrong_row], allow_reviewed_source_subspan=True)['citation_precision'] == 0


def test_locale_grouped_thousands_are_equivalent_without_changing_decimal_or_single_separator_values():
    source = 'học phí đào tạo bậc thạc sĩ năm học 2022-2023 là 30.000.000 đồng (10 tháng)'
    claim = 'học phí đào tạo bậc thạc sĩ năm học 2022-2023 là 30.000.000 đồng (10 tháng)'
    row = {'answerable': True, 'abstained': False,
        'claims': [{'text': claim, 'status': 'supported', 'citation_ids': ['c']}],
        'citations': [{'chunk_id': 'c', 'doc_id': 'doc', 'page': 5, 'quote': source}],
        'gold_claims': [{'text': 'Masters tuition for 2022–2023 is 30,000,000 VND for 10 months.',
            'evidence': [{'doc_id': 'doc', 'page': 5, 'quote': source}]}]}
    assert evaluate_grounding([row], allow_reviewed_source_subspan=True)['grounded_claim_precision'] == 1
    from evaluation.grounding.grounding_metrics import _text_similarity
    assert _text_similarity('The amount is 1,500 VND.', 'The amount is 1.500 VND.') == 0
    from evaluation.grounding.grounding_metrics import _program_code_anchors
    assert _program_code_anchors('VND 30,000,000') == frozenset()


def test_reviewed_source_subspan_cannot_match_a_different_programme_with_the_same_value():
    from evaluation.grounding.grounding_metrics import _pair_similarity
    reviewed = 'CN1 admission quota 420; CN2 admission quota 420.'
    gold = {'text': 'CN2 has an admission quota of 420.',
            'evidence': [{'doc_id': 'doc', 'page': 4, 'quote': reviewed}]}
    row = {'citations': [{'chunk_id': 'c', 'doc_id': 'doc', 'page': 4, 'quote': reviewed}]}
    wrong = {'text': 'CN1 admission quota 420', 'citation_ids': ['c']}
    right = {'text': 'CN2 admission quota 420', 'citation_ids': ['c']}
    assert _pair_similarity(wrong, gold, row, allow_reviewed_source_subspan=True) < .35
    assert _pair_similarity(right, gold, row, allow_reviewed_source_subspan=True) >= .35


ROWS=[['1','PHI 5001','Triết học\nPhilosophy','3','1'],
      ['2','ENG\n5001','Tiếng Anh\nGeneral English','4','1']]


def shared(quote):
    return {'answerable':True,'abstained':False,'confidence_score':1.0,
        'claims':[{'claim_id':'phi','text':'Course PHI5001 has 3 credits.','status':'supported','citation_ids':['table']},
                  {'claim_id':'eng','text':'Course ENG5001 has 4 credits.','status':'supported','citation_ids':['table']}],
        'citations':[{'chunk_id':'table','doc_id':'source','page':1,'quote':quote}],
        'gold_claims':[{'claim_id':'phi','text':'Course PHI5001 has 3 credits.',
            'evidence':[{'doc_id':'source','page':1,'quote':'PHI 5001 Triết học Philosophy 3 1'}]},
            {'claim_id':'eng','text':'Course ENG5001 has 4 credits.',
            'evidence':[{'doc_id':'source','page':1,'quote':'ENG 5001 Tiếng Anh General English 4 1'}]}]}


@pytest.mark.parametrize('claim,quote,expected',[
    ('Article 8: The threshold is 70 percent.','Article 8: The threshold is 70 percent.',1),
    ('Article 8: The threshold is 70 percent.','Article 9: The threshold is 70 percent.',0),
    ('Article 8: The threshold is 8 percent.','Article 8: The threshold is 70 percent.',0)])
def test_cited_source_location_is_not_a_factual_quantity(claim,quote,expected):
    row={'answerable':True,'abstained':False,'claims':[{'text':claim,'status':'supported','citation_ids':['a']}],
        'citations':[{'chunk_id':'a','doc_id':'source','page':3,'quote':quote}],
        'gold_claims':[{'text':'The threshold is 70 percent.','evidence':[{'doc_id':'source','page':3,'quote':'The threshold is 70 percent.'}]}]}
    result=evaluate_grounding([row])
    assert result['citation_precision']==result['grounded_claim_precision']==expected


def test_reviewed_explicit_article_identity_still_has_to_match():
    row={'answerable':True,'abstained':False,'claims':[{'text':'Article 9: The threshold is 70 percent.','status':'supported','citation_ids':['a']}],
        'citations':[{'chunk_id':'a','doc_id':'source','page':3,'quote':'Article 9: The threshold is 70 percent.'}],
        'gold_claims':[{'text':'Article 8: The threshold is 70 percent.','evidence':[{'doc_id':'source','page':3,'quote':'The threshold is 70 percent.'}]}]}
    assert evaluate_grounding([row])['grounded_claim_precision']==0


@pytest.mark.parametrize('prefix,extra,expected',[
    ('The published catalogue describes registration, study and student assessment. ','',1),
    ('It is false that ','',0),
    ('The published catalogue describes registration, study and student assessment. ',' Invented extra fact.',0)])
def test_longer_contextual_quote_needs_complete_literal_source_proof(prefix,extra,expected):
    fact='The threshold is 70 percent.'
    source=prefix+fact
    row={'answerable':True,'abstained':False,'claims':[{'text':source+extra,'status':'supported','citation_ids':['a']}],
        'citations':[{'chunk_id':'a','doc_id':'source','page':3,'quote':source}],
        'gold_claims':[{'text':fact,'evidence':[{'doc_id':'source','page':3,'quote':fact}]}]}
    assert evaluate_grounding([row])['grounded_claim_precision']==expected


def test_shared_chunk_with_only_one_course_row_is_incomplete_and_not_calibration_success():
    row=shared(json.dumps(ROWS[0],ensure_ascii=False));m=evaluate_grounding([row])
    assert m['grounded_claim_precision']==m['grounded_claim_recall']==.5
    assert m['claim_citation_precision']==m['claim_citation_recall']==.5
    assert m['citation_completeness']==.5
    assert m['citation_precision']==0
    assert not is_grounded_answer(row)


@pytest.mark.parametrize('quote',[json.dumps(ROWS,ensure_ascii=False),
    'PHI 5001 Triết học Philosophy 3 1\nENG 5001 Tiếng Anh General English 4 1'])
def test_complete_original_rows_support_both_links(quote):
    row=shared(quote);m=evaluate_grounding([row])
    assert m['grounded_claim_precision']==m['citation_precision']==m['citation_completeness']==1
    assert m['claim_citation_recall']==1 and is_grounded_answer(row)


@pytest.mark.parametrize('quote',[None,'','PHI 5001','3','ENG5001 General English 3 1',
    json.dumps([['PHI 5001','Triết học'],['Philosophy','3','1']]),
    '{"headers": broken','[]'])
def test_missing_wrong_or_cross_row_fragment_is_not_reviewed_evidence(quote):
    row=shared(quote);m=evaluate_grounding([row])
    assert m['citation_precision']==m['claim_citation_recall']==0
    assert not is_grounded_answer(row)


def test_same_chunk_identifier_cannot_override_conflicting_document_or_page():
    row=shared(json.dumps(ROWS,ensure_ascii=False))
    for gold in row['gold_claims']:gold['evidence'][0]['chunk_id']='table'
    for field,value in [('doc_id','other-source'),('page',9)]:
        wrong=deepcopy(row);wrong['citations'][0][field]=value
        m=evaluate_grounding([wrong]);assert m['citation_precision']==m['claim_citation_recall']==0
        assert not is_grounded_answer(wrong)


def test_unmapped_public_citation_is_not_precision_credit():
    row=shared(json.dumps(ROWS,ensure_ascii=False))
    for claim in row['claims']:claim['citation_ids']=[]
    assert evaluate_grounding([row])['citation_precision']==0


def test_all_required_source_links_are_needed_for_grounding_and_completeness():
    row={'answerable':True,'abstained':False,'confidence_score':1,
        'claims':[{'claim_id':'x','text':'The duration is 4 years.','status':'supported','citation_ids':['a']}],
        'citations':[{'chunk_id':'a','doc_id':'one','page':1,'quote':'The duration is 4 years.'}],
        'gold_claims':[{'claim_id':'x','text':'The duration is 4 years.','evidence':[
            {'doc_id':'one','page':1,'quote':'The duration is 4 years.'},
            {'doc_id':'two','page':2,'quote':'The duration is 4 years.'}]}]}
    m=evaluate_grounding([row])
    assert m['citation_recall']==.5
    assert m['citation_completeness']==m['grounded_claim_precision']==0
    assert not is_grounded_answer(row)


@pytest.mark.parametrize('actual',["Course RBE201 has 3 credits.","Course UET.RBE201A has 3 credits.",
    "Course UET.RBE201 has 4 credits.","Course UET.RBE201 has 3 hours."])
def test_visible_quote_preserves_namespace_suffix_value_and_unit(actual):
    row={'answerable':True,'abstained':False,
        'claims':[{'text':'Course UET.RBE201 has 3 credits.','status':'supported','citation_ids':['c']}],
        'citations':[{'chunk_id':'c','doc_id':'one','page':1,'quote':actual}],
        'gold_claims':[{'text':'Course UET.RBE201 has 3 credits.','evidence':[
            {'doc_id':'one','page':1,'quote':'Course UET.RBE201 has 3 credits.'}]}]}
    assert evaluate_grounding([row])['citation_precision']==0
