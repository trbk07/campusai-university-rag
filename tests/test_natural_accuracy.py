"""Required-fact coverage cannot be promoted to unproved answer accuracy."""
import pytest

from evaluation.grounding.natural_accuracy import claim_check, score_required_fields


@pytest.mark.parametrize('gold,good,bad', [
    ({'text': 'Bài báo đăng ở tạp chí ISI được thưởng 0,7 điểm trong xét tuyển thẳng theo thông báo.'},
     'Bài báo ISI được thưởng 0.7 điểm.', 'Bài báo ISI không được thưởng 0.7 điểm.'),
    ({'text': 'Khiển trách trong thi học phần bị trừ 35% số điểm đạt được của bài thi đó.'},
     'Khiển trách bị trừ 35% số điểm đạt được của bài thi.', 'Khiển trách không bị trừ 35% số điểm đạt được của bài thi.'),
    ({'field': 'credits', 'course_code': 'XYZ456', 'value': 7},
     'Môn XYZ456 có 7 tín chỉ.', 'Môn XYZ456 có 7 giờ học và môn ABC123 có 7 tín chỉ.'),
    ({'field': 'course_name', 'course_code': 'XYZ456', 'value': 'Cơ học'},
     'Môn XYZ456 là Cơ học.', 'Môn XYZ456 không phải Cơ học.'),
    ({'text': 'Trí tuệ nhân tạo nâng cao (ABC111) được bố trí ở học kỳ 7.'},
     'Trí tuệ nhân tạo nâng cao học ở kỳ 7.', 'Trí tuệ nhân tạo nâng cao học ở kỳ 2.'),
    ({'text': 'Bảng ghi học kỳ 3 là 12 tín chỉ và học kỳ 4 là 18 tín chỉ.'},
     'Học kỳ 3 có 12 tín chỉ. Học kỳ 4 có 18 tín chỉ.', 'Học kỳ 3 có 18 tín chỉ. Học kỳ 4 có 12 tín chỉ.'),
    ({'text': 'Hạn đăng ký trực tuyến diện tuyển thẳng trong thông báo là 15h30 ngày 21/08/2032.'},
     'Thời gian đăng ký trực tuyến từ 8h00 ngày 01/08/2032 đến 15h30 ngày 21/08/2032.',
     'Thời gian đăng ký trực tuyến từ 15h30 ngày 21/08/2032 đến 17h00 ngày 22/08/2032.'),
])
def test_values_units_direction_and_polarity_remain_bound(gold, good, bad):
    assert claim_check(gold, good)[1]
    assert not claim_check(gold, bad)[1]


def test_missing_required_contribution_cannot_be_hidden_by_a_correct_role():
    claim = {'text': 'Giữ ít nhất một chức vụ trong Ban cán sự lớp hoặc Ban chấp hành Đoàn-Hội các cấp, '
                    'đồng thời có đóng góp tích cực cho công tác Đoàn/phong trào sinh viên; không bắt buộc chỉ là cán bộ lớp.'}
    good = 'Giữ ít nhất một chức vụ trong Ban cán sự lớp/Ban chấp hành Đoàn-Hội các cấp và có đóng góp tích cực cho công tác Đoàn và phong trào sinh viên.'
    assert claim_check(claim, good)[1]
    assert not claim_check(claim, good.split(' và có đóng góp')[0]+'.')[1]


def test_unknown_gold_is_unscored_and_required_coverage_is_not_accuracy():
    rows = [{'id': 'known', 'public_response': {'answer': 'Môn XYZ456 có 7 tín chỉ.', 'abstained': False, 'citations': [{}]}},
            {'id': 'unknown', 'public_response': {'answer': 'A plausible statement.', 'abstained': False, 'citations': [{}]}}]
    gold = {'row_reviews': {'known': {'answerable': True}, 'unknown': {'answerable': True}},
            'claims': {'known': [{'field': 'credits', 'course_code': 'XYZ456', 'value': 7}],
                       'unknown': [{'text': 'Unknown policy interpretation.'}]}}
    score = score_required_fields(rows, gold)
    assert score['required_fact_coverage_lower_bound'] == .5
    assert not score['accuracy_certified'] and not score['hallucination_certified']
    assert score['checks'][1]['field_checks'][0]['field'] == 'unrecognized'
