"""Conservative field checks for the reviewed natural multi-turn gold.

This is an offline evaluator, not runtime NLU or an LLM judge. Unknown gold
forms remain unscored. A citation hit alone never makes an answer correct.
"""
import re
import unicodedata


def normal(text):
    return ' '.join(unicodedata.normalize('NFC', text).casefold().split())


def _has(text, *patterns):
    return all(re.search(pattern, text) is not None for pattern in patterns)


def field_check(gold, answer):
    """Return (field, correct), or None when no bounded contract applies."""
    gold, answer = normal(gold), normal(answer)
    if 'thời gian phỏng vấn' in gold:
        dates = re.findall(r'\b\d{2}/\d{2}/\d{4}\b', gold)
        return 'interview_date', (len(dates) == 1 and _has(answer, r'phỏng vấn', re.escape(dates[0]))
            and set(re.findall(r'\b\d{2}/\d{2}/\d{4}\b', answer)) == set(dates)
            and not re.search(r'không|chưa', answer))
    if 'lệ phí dự tuyển' in gold:
        amount = re.search(r'(\d[\d.]+) đồng/thí sinh', gold)
        return 'fee_per_candidate', bool(amount and _has(answer, r'lệ phí', re.escape(amount[1])+r'\s*(?:đ|đồng)/thí sinh')
            and not re.search(r'không|miễn', answer))
    if gold.startswith('có thể chuyển khoản lệ phí'):
        return 'payment_choices', _has(answer, r'chuyển khoản', r'tài khoản', r'trường đại học công nghệ',
            r'hoặc', r'(?:tiền mặt.*trực tiếp|trực tiếp.*tiền mặt)') and not re.search(r'không|chỉ được', answer)
    if 'ngoại ngữ đầu vào' in gold:
        value = re.search(r'bậc (\d+) trở lên', gold)
        return 'entry_language_minimum', bool(value and _has(answer,
            r'đầu vào(?:(?!đầu ra)[^.;])*bậc '+value[1]+r' trở lên', r'(?:khung[^.;]*6 bậc|6 bậc[^.;]*khung)')
            and not re.search(r'không (?:cần|yêu cầu|bắt buộc)', answer))
    if 'chuẩn ngoại ngữ đầu ra' in gold:
        value = re.search(r'bậc (\d+) trở lên', gold); year = re.search(r'từ năm (\d{4})', gold)
        return 'exit_language_minimum_and_cohort', bool(value and year and _has(answer,
            r'từ năm '+year[1], r'đầu ra(?:(?!đầu vào)[^.;])*bậc '+value[1]+r' trở lên', r'tương đương', r'6 bậc')
            and not re.search(r'không (?:cần|yêu cầu|bắt buộc)', answer))
    if gold == 'thí sinh có thể được nợ minh chứng năng lực ngoại ngữ.':
        return 'deferred_language_evidence', _has(answer, r'có thể được nợ minh chứng', r'năng lực ngoại ngữ') and 'không' not in answer
    if gold.startswith('phải bổ sung trước thời điểm nhà trường ra quyết định trúng tuyển;'):
        month = re.search(r'tháng (\d{1,2}/\d{4})', gold)
        return 'supplement_deadline', bool(month and _has(answer,
            r'bổ sung trước thời điểm nhà trường ra quyết định trúng tuyển', r'dự kiến', re.escape(month[1]))
            and not re.search(r'bổ sung sau|không cần', answer))
    if gold.startswith('danh hiệu sinh viên giỏi yêu cầu kết quả rèn luyện'):
        return 'named_award_conduct', _has(answer, r'sinh viên giỏi', r'rèn luyện[^.;]*tốt trở lên') and 'không' not in answer
    if gold.startswith('sinh viên xuất sắc được tặng giấy khen'):
        return 'named_award_rewards', _has(answer, r'sinh viên xuất sắc', r'giấy khen', r'hiệu trưởng', r'tiền thưởng',
            r'(?:đhqghn|đại học quốc gia hà nội)', r'(?:trường đại học công nghệ)') and 'không được' not in answer
    if 'phần thưởng cho diện thành tích tuyển sinh' in gold:
        return 'tuition_reward_year', _has(answer, r'tuyển sinh', r'thưởng', r'học phí của năm học đầu tiên') and 'không' not in answer
    if 'chuẩn kỹ năng tiếng anh' in gold:
        fraction = re.search(r'\b\d/\d\b', gold)
        return 'english_exit_framework', bool(fraction and _has(answer, r'tiếng anh', re.escape(fraction[0]), r'khung năng lực ngoại ngữ việt nam')
            and not re.search(r'không|chưa', answer))
    credit = re.fullmatch(r'.*?\(([a-z]+\d+[a-z]*)\) có (\d+) tín chỉ\.', gold)
    if credit:
        code, value = credit.groups()
        return 'course_credits', bool(re.search(r'\b'+code+r' có '+value+r' tín chỉ\b', answer)) and 'không' not in answer
    if 'tiên quyết' in gold:
        codes = re.findall(r'\b[a-z]{2,}\d{3,}[a-z]?\b', gold)
        if len(codes) < 2:
            return None
        target, bridges = codes[0], codes[1:]
        # Each source code stays attached to its directed prerequisite role.
        pairs = re.findall(r'\b(?:môn )?([a-z]+\d+[a-z]*) là môn tiên quyết của môn ([a-z]+\d+[a-z]*)', answer)
        return 'directed_prerequisites', set(pairs) == {(code, target) for code in bridges} and 'không' not in answer
    if 'đơn vị phụ trách/resources' in gold:
        semester = re.search(r'học kỳ (\d+)', gold); provider = re.search(r' là ([^.]+)\.', gold)
        return 'semester_provider', bool(semester and provider and _has(answer,
            r'học kỳ '+semester[1]+r'\b', r'\bdo '+re.escape(provider[1])+r' phụ trách\b') and 'không' not in answer)
    return None


def evaluate_context(prediction, gold_claims):
    if not prediction['request'].get('history'):
        raise ValueError('Context metric requires a genuine history-bearing input')
    public = prediction['public_response']
    checks = [field_check(claim.get('text', ''), public['answer']) for claim in gold_claims]
    return {'id': prediction['id'], 'required_fields': len(gold_claims),
        'scored_fields': sum(check is not None for check in checks),
        'fields': [{'field': check[0], 'correct': bool(check[1])} if check else
                   {'field': 'unknown', 'correct': None} for check in checks],
        'correct': bool(gold_claims) and not public['abstained'] and
                   all(check is not None and check[1] for check in checks)}
