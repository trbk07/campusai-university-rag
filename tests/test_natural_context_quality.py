"""Wrong values, roles, direction and omissions cannot pass context scoring."""
import pytest

from evaluation.grounding.natural_context import evaluate_context, field_check


@pytest.mark.parametrize('gold,answer', [
    ('Thời gian phỏng vấn trong thông báo là ngày 11/12/2031.', 'Không phải ngày phỏng vấn 11/12/2031.'),
    ('Ngoại ngữ đầu vào đạt từ Bậc 2 trở lên theo Khung năng lực ngoại ngữ 6 bậc Việt Nam, đáp ứng yêu cầu.',
     'Đầu ra Bậc 2 trở lên, đầu vào Bậc 4 trở lên theo Khung 6 bậc.'),
    ('Ngoại ngữ đầu vào đạt từ Bậc 2 trở lên theo Khung năng lực ngoại ngữ 6 bậc Việt Nam, đáp ứng yêu cầu.',
     'Đầu vào Bậc 4 trở lên, còn đầu ra Bậc 2 trở lên theo Khung 6 bậc.'),
    ('Ngoại ngữ đầu vào đạt từ Bậc 2 trở lên theo Khung năng lực ngoại ngữ 6 bậc Việt Nam, đáp ứng yêu cầu.',
     'Đầu vào Bậc 2, không cần đạt từ Bậc 2 trở lên theo Khung 6 bậc.'),
    ('Học phần tiên quyết của ABC123 trong bảng là DEF456.', 'Môn ABC123 là môn tiên quyết của môn DEF456.'),
    ('Học phần tiên quyết của ABC123 trong bảng là DEF456 và GHI789.', 'Môn DEF456 là môn tiên quyết của môn ABC123.'),
    ('Cơ học (ABC123) có 5 tín chỉ.', 'Môn ABC123 có 5 giờ học, còn DEF456 có 5 tín chỉ.'),
    ('Phải bổ sung trước thời điểm Nhà trường ra quyết định trúng tuyển; thông báo dự kiến thời điểm này vào tháng 12/2031.',
     'Được nợ minh chứng và bổ sung sau quyết định trúng tuyển tháng 12/2031.'),
])
def test_incomplete_or_wrong_semantics_fail(gold, answer):
    check = field_check(gold, answer)
    assert check is not None and not check[1]


def test_values_are_extracted_from_gold_instead_of_benchmark_constants():
    assert field_check('Cơ học (XYZ456) có 8 tín chỉ.', 'Môn XYZ456 có 8 tín chỉ.')[1]
    assert not field_check('Cơ học (XYZ456) có 8 tín chỉ.', 'Môn XYZ456 có 3 tín chỉ.')[1]


def test_unknown_gold_and_absent_history_cannot_be_certified():
    assert field_check('An unrecognized policy interpretation.', 'Same words.') is None
    prediction = {'id': 'example', 'request': {'history': []}, 'public_response': {'answer': 'Same words.', 'abstained': False}}
    with pytest.raises(ValueError, match='history'):
        evaluate_context(prediction, [{'text': 'Same words.'}])
    prediction['request']['history'] = [{'role': 'user', 'content': 'Earlier question'}]
    assert not evaluate_context(prediction, [{'text': 'Unknown fact.'}])['correct']
