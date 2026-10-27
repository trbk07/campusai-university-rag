"""Conservative required-fact coverage from reviewed factual fields.

No model judge, runtime claim-support label or citation-hit proxy is used.
Unrecognized answer/gold forms count against the lower bound. Accuracy also
requires validating extra assertions; this module cannot certify that gate
or replace a hallucination audit.
"""
import re

from .natural_context import normal, field_check


def text(value):
    value = normal(str(value)).replace('–', '-').replace('—', '-')
    return re.sub(r'(?<=\d),(?=\d)', '.', value)


def has(value, *patterns):
    return all(re.search(pattern, value) for pattern in patterns)


def claim_check(claim, answer):
    """Return a named field verdict; None means not established, never PASS."""
    actual = text(answer)
    if re.search(r'\bkhông (?:phải|cần|yêu cầu|bắt buộc|bị|được)\b', actual):
        return 'negated_required_fact', False
    if claim.get('field') in {'course_name', 'credits'}:
        code = claim['course_code'].casefold()
        codes = {re.sub(r'\s+', '', m[0]) for m in re.finditer(r'\b[a-z]{2,}\s*\d{3,}[a-z]?\b', actual)}
        if codes != {code}:
            return claim['field'], False
        if claim['field'] == 'course_name':
            return 'course_name', text(claim['value']) in actual
        return 'credits', bool(re.search(r'\bcó '+re.escape(str(claim['value']))+r' tín chỉ\b', actual)) and 'không' not in actual
    gold = text(claim.get('text', ''))
    old = field_check(claim.get('text', ''), answer)
    if old is not None and old[1]:
        return old
    if 'đơn vị phụ trách/resources' in gold:
        semester = re.search(r'học kỳ (\d+)', gold); provider = re.search(r' là ([^.]+)\.', gold)
        return 'semester_provider', bool(semester and provider and has(actual,
            r'(?:học kỳ|kỳ|semester)(?: thứ)? '+semester[1]+r'\b', r'\b'+re.escape(provider[1])+r'\b') and 'không' not in actual)
    if 'hạn đăng ký trực tuyến diện tuyển thẳng' in gold:
        date = re.search(r'\b\d{2}/\d{2}/\d{4}\b', gold); clock = re.search(r'\b\d{1,2}h\d{2}\b', gold)
        return 'online_deadline', bool(date and clock and has(actual, r'(?:trực tuyến|online)',
            r'(?:đến|hạn[^.;]*là) '+re.escape(clock[0])+r' (?:ngày )?'+re.escape(date[0])) and 'không' not in actual)
    if gold.startswith('thời gian xét tuyển thẳng là từ ngày'):
        dates = re.findall(r'\b\d{2}/\d{2}/\d{4}\b', gold)
        return 'direct_admission_window', len(dates) == 2 and bool(re.search(
            r'xét tuyển thẳng[^.;]*từ ngày '+re.escape(dates[0])+r' đến (?:ngày )?'+re.escape(dates[1]), actual))
    if gold.startswith('ngày thông báo kết quả xét tuyển thẳng'):
        date = re.search(r'\b\d{2}/\d{2}/\d{4}\b', gold)
        return 'direct_admission_result_date', bool(date and re.search(r'thông báo kết quả[^.;]*'+re.escape(date[0]), actual))
    if 'tổng không quá' in gold:
        cap = re.search(r'tổng không quá (\d+(?:\.\d+)?) điểm', gold)
        return 'research_bonus_cap', bool(cap and has(actual, r'(?:điểm thưởng|điểm cộng|cộng điểm)',
            r'không quá '+re.escape(cap[1])+r' điểm\b'))
    if 'danh hiệu đóng góp công tác tập thể yêu cầu kết quả học tập' in gold:
        minimum = re.search(r'từ (\d+(?:\.\d+)?) trở lên', gold); grade = re.search(r'dưới ([a-f][+-]?)\b', gold)
        return 'award_academic_and_course_minimum', bool(minimum and grade and has(actual,
            r'học tập[^.;]*từ '+re.escape(minimum[1])+r' trở lên', r'không có học phần nào(?: có điểm)? dưới '+grade[1]+r'\b'))
    if gold.startswith('rèn luyện trong năm/toàn khóa đạt loại'):
        return 'award_conduct', bool(has(actual, r'rèn luyện[^.;]*loại xuất sắc'))
    if gold.startswith('giữ ít nhất một chức vụ'):
        return 'award_role_and_active_contribution', bool(has(actual,
            r'giữ ít nhất một chức vụ', r'ban cán sự lớp(?:/| hoặc )ban chấp hành đoàn-hội',
            r'và có đóng góp tích cực', r'công tác đoàn và phong trào sinh viên'))
    if gold.startswith('sinh viên phải tốt nghiệp đúng hoặc trước thời hạn'):
        return 'graduation_time', 'tốt nghiệp đúng hoặc trước thời hạn đào tạo chuẩn' in actual
    if gold.startswith('học tập và rèn luyện toàn khóa đạt từ loại'):
        return 'graduation_academic_and_conduct', bool(has(actual, r'học tập và rèn luyện toàn khóa', r'khá trở lên'))
    if gold.startswith('kết quả bảo vệ khóa luận/đồ án được hội đồng'):
        return 'defense_result', bool(has(actual, r'bảo vệ khóa luận/đồ án', r'hội đồng[^.;]*công nhận[^.;]*xuất sắc'))
    if gold.startswith('tập thể xuất sắc phải đạt các tiêu chuẩn tập thể tiên tiến'):
        return 'collective_prerequisite_award', bool(has(actual, r'tập thể xuất sắc', r'phải đạt các tiêu chuẩn[^.;]*tập thể tiên tiến'))
    if gold.startswith('có từ') and '% sinh viên trở lên' in gold:
        percent = re.search(r'có từ (\d+)%', gold)
        return 'collective_award_population', bool(percent and has(actual,
            r'có từ '+percent[1]+r'% sinh viên trở lên[^.;]*sinh viên giỏi', r'và có sinh viên[^.;]*sinh viên xuất sắc'))
    if 'thủ khoa ngành học xét điểm trung bình' in gold:
        return 'valedictorian_scope', bool(has(actual, r'điểm trung bình toàn khóa', r'cao nhất trong ngành học')) and 'toàn trường' not in actual
    if gold.startswith('sinh viên tốt nghiệp trước hạn được xem xét thủ khoa'):
        return 'early_graduation_award_time', bool(has(actual, r'tốt nghiệp trước hạn',
            r'xem xét vào thời điểm tốt nghiệp đúng hạn của ngành đào tạo'))
    if gold.startswith('danh hiệu sinh viên xuất sắc yêu cầu không có học phần nào dưới'):
        grade = re.search(r'dưới ([a-f][+-]?)', gold)
        return 'necessary_grade_condition', bool(grade and has(actual, r'sinh viên xuất sắc',
            r'dưới '+re.escape(grade[1]), r'không đáp ứng điều kiện', r'không có học phần nào có điểm dưới '+re.escape(grade[1])))
    if 'bị trừ' in gold and '% số điểm' in gold:
        penalty = re.search(r'bị trừ (\d+)% số điểm', gold)
        role = 'khiển trách' if gold.startswith('khiển trách') else 'cảnh cáo' if gold.startswith('cảnh cáo') else None
        return 'exam_penalty_fraction', bool(penalty and role and has(actual, re.escape(role),
            r'bị trừ '+penalty[1]+r'% số điểm đạt được của bài thi')) and not re.search(r'\b0\.5 điểm\b', actual)
    if gold.startswith('thông báo ghi thời gian đào tạo thạc sĩ là'):
        duration = re.search(r'là (\d+) năm', gold)
        return 'masters_duration', bool(duration and has(actual, r'thời gian đào tạo', r'thạc sĩ', r'là '+duration[1]+r' năm'))
    if gold.startswith('bài báo') and 'được thưởng' in gold:
        value = re.search(r'được thưởng (\d+(?:\.\d+)?) điểm', gold)
        journal = 'isi' if 'isi' in gold else 'scopus' if 'scopus' in gold else None
        return 'publication_bonus', bool(value and journal and has(actual, r'\b'+journal+r'\b', r'\b'+re.escape(value[1])+r' điểm'))
    if gold.startswith('địa chỉ phần mềm tuyển sinh sau đại học'):
        url = re.search(r'https?://[^; ]+', gold)
        urls = re.findall(r'https?://[^\s]+', actual)
        return 'historical_registration_url', bool(url and [u.rstrip('.') for u in urls] == [url[0].rstrip('.')])
    if gold.startswith('thí sinh xét tuyển thẳng vẫn phải nộp lệ phí'):
        value = re.search(r'lệ phí (\d[\d.]+) đồng', gold)
        return 'direct_admission_fee_required', bool(value and has(actual, r'xét tuyển thẳng',
            r'vẫn phải (?:trả|đóng|nộp)', re.escape(value[1])+r'\s*(?:đ|đồng)/thí sinh')) and not re.search(r'được miễn', actual)
    if gold.startswith('thông báo ghi học phí thạc sĩ năm học'):
        period = re.search(r'năm học (\d{4}-\d{4})', gold); value = re.search(r'là (\d[\d.]+) đồng', gold)
        return 'historical_tuition', bool(period and value and has(actual, re.escape(period[1]),
            re.escape(value[1])+r'\s*(?:đ|đồng)/năm học', r'10 tháng'))
    # Explicit semester/name and total relations are evaluated as pairs; all
    # occurrences are retained instead of a bag of otherwise-correct numbers.
    totals = re.findall(r'học kỳ (\d+) là (\d+) tín chỉ', gold)
    if totals:
        return 'semester_totals', all(re.search(r'học kỳ '+n+r' có '+value+r' tín chỉ\b', actual) for n, value in totals)
    if gold.startswith('tổng của hai học kỳ là'):
        equation = re.search(r'(\d+) \+ (\d+) = (\d+)', gold)
        return 'semester_sum', bool(equation and int(equation[1])+int(equation[2])==int(equation[3])
            and re.search(r'tổng[^.]*là '+equation[3]+r' tín chỉ\b', actual))
    if 'ghi tổng học kỳ' in gold:
        pair = re.search(r'tổng học kỳ (\d+) là (\d+) tín chỉ', gold)
        return 'semester_total', bool(pair and re.search(r'(?:học kỳ|semester) '+pair[1]+r'[^.;]* (?:có |số )?'+pair[2]+r' tín chỉ\b', actual))
    if gold.startswith('final state attestation'):
        semester = re.search(r'học kỳ (\d+)', gold); credits = re.search(r'có (\d+) tín chỉ', gold)
        if semester:
            return 'named_course_semester', bool(re.search(r'final state attestation[^.;]*(?:học kỳ|kỳ semester|semester) '+semester[1]+r'\b', actual))
        if credits:
            return 'named_course_credits', bool(re.search(r'final state attestation[^.;]*có '+credits[1]+r' tín chỉ\b', actual))
    if 'trí tuệ nhân tạo nâng cao' in gold or 'xử lý ngôn ngữ tự nhiên' in gold:
        entries = ('trí tuệ nhân tạo nâng cao', 'xử lý ngôn ngữ tự nhiên')
        # Derive the values from the reviewed clauses, not these subject names.
        fields = []
        for name in entries:
            value = re.search(re.escape(name)+r'[^.;]*?học kỳ (\d+)', gold)
            if value:
                found = re.search(re.escape(name)+r'(?:(?!trí tuệ nhân tạo nâng cao|xử lý ngôn ngữ tự nhiên)[^.;])*?(?:học kỳ|kỳ) (\d+)', actual)
                fields.append(bool(found and found[1] == value[1]))
        if fields:
            return 'named_course_semesters', all(fields)
    return old


def score_required_fields(rows, gold):
    checks = []
    for row in rows:
        public = row['public_response']; positive = gold['row_reviews'][row['id']]['answerable']
        fields = [claim_check(claim, public['answer']) for claim in gold['claims'][row['id']]]
        established = (not public['abstained'] and bool(fields) and all(f is not None and f[1] for f in fields)
                       if positive else public['abstained'] and not public['citations'])
        checks.append({'id': row['id'], 'positive': positive, 'established_correct': bool(established),
            'field_checks': [{'field': f[0], 'established': bool(f[1])} if f else
                             {'field': 'unrecognized', 'established': False} for f in fields]})
    correct = sum(c['established_correct'] for c in checks)
    return {'cases': len(rows), 'established_correct': correct, 'not_established': len(rows)-correct,
        'required_fact_coverage_lower_bound': correct/len(rows) if rows else None,
        'accuracy_certified': False, 'hallucination_certified': False,
        'method': 'Conservative required-field coverage against unchanged reviewed gold; every unrecognized, missing or mismatched field counts against the lower bound. Does not certify extra assertions, whole-answer accuracy or hallucination rate.',
        'checks': checks}
