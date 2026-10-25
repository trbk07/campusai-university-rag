"""Reviewed source context must preserve exact values, roles and boundaries."""
import pytest

from evaluation.grounding.grounding_metrics import evaluate_grounding


def measured(fact, reviewed, claim, quote):
    row={'answerable':True,'abstained':False,
         'claims':[{'text':claim,'status':'supported','citation_ids':['c']}],
         'citations':[{'chunk_id':'c','doc_id':'document','page':2,'quote':quote}],
         'gold_claims':[{'text':fact,'evidence':[{'doc_id':'document','page':2,'quote':reviewed}]}]}
    return evaluate_grounding([row],allow_reviewed_source_subspan=True)


def test_layout_label_can_repeat_a_value_that_remains_inside_the_fact():
    source='Quy chế có hiệu lực từ học kỳ 1 năm học 2031-2032.'
    result=measured('Effective from semester 1 of academic year 2031-2032.',
                    '1. '+source,source,source)
    assert result['grounded_claim_precision']==result['citation_precision']==1
    wrong=source.replace('học kỳ 1','học kỳ 2')
    assert measured('Effective from semester 1 of academic year 2031-2032.',
                    '1. '+source,wrong,wrong)['grounded_claim_precision']==0


@pytest.mark.parametrize('day,month,expected',[(9,8,1),(8,9,0),(10,8,0)])
def test_spelled_calendar_date_is_not_a_months_or_years_duration(day,month,expected):
    source='Thay thế Quyết định số 7410 ngày 09 tháng 8 năm 2031.'
    actual=f'Thay thế Quyết định số 7410 ngày {day:02} tháng {month} năm 2031.'
    result=measured('Replaces Decision 7410 dated 09/8/2031.',source,actual,source)
    assert result['grounded_claim_precision']==expected


@pytest.mark.parametrize('claim,expected',[
    ('Mỗi tín chỉ yêu cầu tối thiểu 54 giờ thực tập tại cơ sở.',1),
    ('Mỗi tín chỉ yêu cầu tối thiểu 18 giờ thực tập tại cơ sở.',0),
    ('Mỗi tín chỉ yêu cầu tối đa 54 giờ thực tập tại cơ sở.',0),
    ('Mỗi tín chỉ yêu cầu tối thiểu 54 tín chỉ thực tập tại cơ sở.',0),
    ('Mỗi tín chỉ yêu cầu tối thiểu 54 giờ làm luận văn.',0),
])
def test_common_minimum_and_one_complete_list_item_need_literal_proof(claim,expected):
    source=('Mỗi tín chỉ yêu cầu tối thiểu 18 giờ giảng; '
            '54 giờ thực tập tại cơ sở; 72 giờ làm luận văn.')
    result=measured('54 giờ thực tập tại cơ sở','54 giờ thực tập tại cơ sở',claim,source)
    assert result['grounded_claim_precision']==expected


def test_a_complete_original_condition_after_reviewed_fact_is_source_context():
    reviewed='Nghiên cứu sinh còn tối thiểu 18 tháng'
    source=reviewed+' được chuyển cơ sở nếu có sự đồng ý của cả hai cơ sở.'
    fact='At least 18 months must remain.'
    assert measured(fact,reviewed,source,source)['grounded_claim_precision']==1
    assert measured(fact,reviewed,source,reviewed)['grounded_claim_precision']==0
    assert measured(fact,reviewed,source+' Invented extra fact.',source)['grounded_claim_precision']==0


def test_a_condition_before_the_fact_does_not_become_an_unconditional_fact():
    reviewed='Nghiên cứu sinh còn tối thiểu 18 tháng'
    source='Nếu được chấp thuận, '+reviewed+' được chuyển cơ sở.'
    assert measured('At least 18 months must remain.',reviewed,source,source)['grounded_claim_precision']==0


@pytest.mark.parametrize('fact,source,claim',[
    ('Minimum 12 credits, maximum 24 credits.',
     'Tối thiểu 12 tín chỉ, tối đa 24 tín chỉ. Tối thiểu 24 tín chỉ, tối đa 12 tín chỉ.',
     'Tối thiểu 24 tín chỉ, tối đa 12 tín chỉ.'),
    ('Final-year students are exempt from the minimum 12 credits.',
     'Sinh viên năm cuối được miễn mức tối thiểu 12 tín chỉ. Sinh viên đăng ký tối thiểu 12 tín chỉ.',
     'Sinh viên đăng ký tối thiểu 12 tín chỉ.'),
    ('A maximum of 24 credits per semester.',
     'Tối đa 24 tín chỉ trong một học kỳ. Tối đa 24 tín chỉ trong một năm học.',
     'Tối đa 24 tín chỉ trong một năm học.'),
    ('A grade from C or above is required.',
     'Yêu cầu từ điểm C trở lên. Yêu cầu từ điểm D trở lên.',
     'Yêu cầu từ điểm D trở lên.'),
])
def test_literal_but_different_rule_is_not_the_reviewed_fact(fact,source,claim):
    assert measured(fact,source,claim,source)['grounded_claim_precision']==0


@pytest.mark.parametrize('qualifier',[
    'including at least 12 credits', 'including only final-year students',
    'including not under academic warning', 'including PHI5001',
])
def test_parenthetical_scope_or_value_cannot_be_omitted(qualifier):
    from evaluation.grounding.grounding_metrics import _literal_source_versions
    source=f'Students ({qualifier}) may apply.'
    assert _literal_source_versions(source)==(source,)


def test_grade_threshold_requires_its_grade_not_a_neighboring_duration():
    source=('Kết quả học phần tiến sĩ có giá trị công nhận trong thời hạn 05 năm. '
            'Những học phần được công nhận phải đạt từ điểm C (hoặc quy đổi tương đương) trở lên.')
    gold='Recognised doctoral courses must have a grade of at least C or equivalent.'
    correct=source.split('. ',1)[1]
    assert measured(gold,source,correct,source)['grounded_claim_precision']==1
    assert measured(gold,source,source.split('. ',1)[0]+'.',source)['grounded_claim_precision']==0
    assert measured(gold,source,correct.replace('điểm C','điểm D'),source)['grounded_claim_precision']==0


def test_anaphoric_population_inheritance_requires_unambiguous_reviewed_context():
    source=('Học phần cử nhân có thời hạn 03 năm. Học phần tiến sĩ có thời hạn 05 năm. '
            'Những học phần này phải đạt từ điểm C trở lên.')
    assert measured('Doctoral courses require at least C.',source,
                    'Những học phần này phải đạt từ điểm C trở lên.',source)['grounded_claim_precision']==0


@pytest.mark.parametrize('fact,reviewed,source',[
    ('An undergraduate outside academic warning may register at most 24 credits in a main semester.',
     'Sinh viên không thuộc diện cảnh báo học tập được đăng ký tối đa 24 TC',
     'Sinh viên không thuộc diện cảnh báo học tập được đăng ký tối đa 24 TC và tối thiểu 12 TC trong học kỳ chính.'),
    ('The annual maximum is 45 credits.','nhưng không vượt quá 45 TC trong một năm học.',
     'Học viên được đăng ký tối đa 24 TC trong một học kỳ chính nhưng không vượt quá 45 TC trong một năm học.'),
])
def test_literal_additional_bounds_keep_each_reviewed_value_and_period(fact,reviewed,source):
    assert measured(fact,reviewed,source,source)['grounded_claim_precision']==1
    assert measured(fact,reviewed,source.replace('24 TC','45 TC').replace('45 TC trong một năm','24 TC trong một năm'),source)['grounded_claim_precision']==0


@pytest.mark.parametrize('fact,source,claim',[
    ('Minimum 12 credits, maximum 24 credits.',
     'Tối thiểu 12 tín chỉ, tối đa 24 tín chỉ. Tối thiểu 24 tín chỉ, tối đa 12 tín chỉ.',
     'Tối thiểu 24 tín chỉ, tối đa 12 tín chỉ.'),
    ('Final-year students are exempt from the minimum 12 credits.',
     'Sinh viên năm cuối được miễn mức tối thiểu 12 tín chỉ. Sinh viên đăng ký tối thiểu 12 tín chỉ.',
     'Sinh viên đăng ký tối thiểu 12 tín chỉ.'),
    ('A maximum of 24 credits per semester.',
     'Tối đa 24 tín chỉ trong một học kỳ. Tối đa 24 tín chỉ trong một năm học.',
     'Tối đa 24 tín chỉ trong một năm học.'),
    ('A grade from C or above is required.',
     'Yêu cầu từ điểm C trở lên. Yêu cầu từ điểm D trở lên.',
     'Yêu cầu từ điểm D trở lên.'),
])
def test_literal_but_different_rule_is_not_the_reviewed_fact(fact,source,claim):
    assert measured(fact,source,claim,source)['grounded_claim_precision']==0


@pytest.mark.parametrize('qualifier',[
    'including at least 12 credits', 'including only final-year students',
    'including not under academic warning', 'including PHI5001',
])
def test_parenthetical_scope_or_value_cannot_be_omitted(qualifier):
    from evaluation.grounding.grounding_metrics import _literal_source_versions
    source=f'Students ({qualifier}) may apply.'
    assert _literal_source_versions(source)==(source,)
