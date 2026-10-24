import json
from dataclasses import replace

import pytest

from campusai.rag.grounding import GroundedAnswerGenerator, validate_citation
from campusai.rag.regulation_facts import deterministic_regulation_fact, regulation_candidates
from tests.test_basic_rag import evidence


def programme(duration='6 năm', credits='162 tín chỉ'):
    return replace(evidence(content=json.dumps({'headers':['Chương trình','Người học','Thời gian','Khối lượng\ntối thiểu'],
        'rows':[['Cử nhân','Tốt nghiệp THPT',duration,credits],
                ['Thạc sĩ','Tốt nghiệp cử nhân','2 năm','65 tín chỉ'],
                ['','Tốt nghiệp cử nhân theo chương trình tích hợp','1,5 năm','49 tín chỉ'],
                ['Tiến sĩ','Tốt nghiệp thạc sĩ','3 năm','108 tín chỉ'],
                ['','Tốt nghiệp đại học','5 năm','153 tín chỉ']]},ensure_ascii=False)), content_type='table')


class NoModel:
    def generate_json(self,*args,**kwargs):
        raise AssertionError('An exact headed source field does not need a model')


def test_programme_duration_and_credits_are_separate_atomic_source_projections():
    item = programme()
    question = 'For a high-school graduate entering a regular bachelor programme, what standard duration and minimum credits does the table prescribe?'
    answer = GroundedAnswerGenerator(NoModel()).answer(question,[item],'en')
    assert not answer.abstained and len(answer.claims) == 2
    assert '6 years' in answer.claims[0].text and '162 credits' in answer.claims[1].text
    assert validate_citation(answer.citations[0],item,require_quote=True).valid
    different = deterministic_regulation_fact(question,[programme('7 năm','170 tín chỉ')],'en')
    assert '7 years' in different.answer and '170 credits' in different.answer


@pytest.mark.parametrize('degree,prior,field,value', [
    ('thạc sĩ','cử nhân theo chương trình tích hợp','Khối lượng học tập tối thiểu','49'),
    ('tiến sĩ','đại học','Thời gian đào tạo chuẩn','5'),
    ('tiến sĩ','đại học','Khối lượng học tập tối thiểu','153'),
    ('thạc sĩ','cử nhân thông thường','Khối lượng học tập tối thiểu','65'),
])
def test_merged_programme_rows_keep_degree_and_entry_qualification(degree,prior,field,value):
    question = f'{field} của chương trình {degree} dành cho người tốt nghiệp {prior} trong bảng là bao nhiêu?'
    item = programme();answer = deterministic_regulation_fact(question,[item],'vi')
    assert answer is not None and not answer.abstained and value in answer.answer
    assert json.loads(answer.citations[0].quote)['scope'] == degree.capitalize()
    assert validate_citation(answer.citations[0],item,require_quote=True).valid


def test_programme_conflicting_fields_missing_headers_and_extra_requests_are_not_guessed():
    item = programme();question = 'Thời gian đào tạo chuẩn của chương trình cử nhân dành cho người tốt nghiệp THPT trong bảng là bao lâu?'
    other = replace(programme('7 năm'),chunk_id='conflict')
    assert deterministic_regulation_fact(question,[item,other],'vi').reason == 'conflicting_evidence'
    bad = replace(item,content=item.content.replace('Khối lượng\\ntối thiểu','Giờ học'))
    assert deterministic_regulation_fact(question,[bad],'vi') is None
    assert deterministic_regulation_fact(question+' Và mật khẩu của tôi là gì?',[item],'vi') is None
    assert regulation_candidates(question,{'a':item.to_dict(),'b':other.to_dict()}) == ['a','b']


@pytest.mark.parametrize('lower,upper',[('0,4','0,7'),('0.3','0.6')])
def test_assessment_range_comes_from_its_own_course_threshold(lower,upper):
    text = f'1. Một học phần từ 3 TC trở lên được đánh giá từ hai điểm thành phần, trong đó điểm cuối kỳ có trọng số từ {lower} đến {upper} theo đề cương.'
    item = evidence(content=text)
    question = 'Trọng số điểm cuối kỳ của học phần từ ba tín chỉ trở lên nằm trong khoảng nào?'
    answer = GroundedAnswerGenerator(NoModel()).answer(question,[item],'vi')
    assert not answer.abstained and lower in answer.answer and upper in answer.answer
    assert answer.claims[0].text in text and answer.citations[0].quote in text
    assert deterministic_regulation_fact(question.replace('ba','hai'),[item],'vi') is None
    assert deterministic_regulation_fact(question,[replace(item,content='Không phải '+text)],'vi') is None


def test_approved_deferral_window_is_not_the_appeal_or_midterm_deadline():
    text = ('3. Người học không thể dự thi cuối kỳ một học phần (đã học và đã đóng học phí) do bị ốm '
        'thì được phép hoãn thi và được dự thi cuối kỳ học phần đó trong thời hạn 3 học kỳ chính tiếp theo để hoàn thiện điểm.\n'
        '4. Phúc tra trong thời hạn 9 ngày.')
    item = evidence(content=text)
    question = 'Được hoãn thi cuối kỳ đúng lý do thì phải dự thi hoàn thiện trong thời hạn nào?'
    answer = GroundedAnswerGenerator(NoModel()).answer(question,[item],'vi')
    assert not answer.abstained and '3 học kỳ' in answer.answer and '9 ngày' not in answer.answer
    assert answer.claims[0].text in text and answer.citations[0].quote in text


def test_an_invalid_weight_range_cannot_be_silently_pruned_from_conflicting_source_statements():
    question = 'Trọng số điểm cuối kỳ của học phần từ hai tín chỉ trở lên nằm trong khoảng nào?'
    text = 'Một học phần từ 2 TC trở lên được đánh giá từ hai điểm thành phần, trong đó điểm cuối kỳ có trọng số từ 0,4 đến 0,7.'
    first = evidence(content=text)
    invalid = replace(first,chunk_id='invalid',content=text.replace('0,7','1,4'))
    answer = deterministic_regulation_fact(question,[first,invalid],'vi')
    assert answer.abstained and answer.reason == 'unsupported_claim'
