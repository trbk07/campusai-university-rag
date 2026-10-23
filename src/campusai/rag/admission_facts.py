"""Read bounded admission facts from explicit source labels, without a model.

The question selects a field, never its value. Unknown wording or additional
obligations retain the normal grounding path. Values and verification statements
must be literal contiguous source spans from one selected document.
"""
from __future__ import annotations

import re
from datetime import date

from .course_credits import folded
from .footnotes import _fold_with_offsets
from .policies import sanitize_evidence_text
from .table_fields import admission_year_sources
from ..retrieval.tokenizer_vi import source_body


def admission_fact_request(question):
    text = folded(question).strip()
    text = re.sub(r'^(?:use only (?:the )?uploaded|chi dung tai lieu da tai len) [\w.-]+\.pdf\.\s*', '', text)
    text = ' '.join(text.strip(' .?!').split())
    coefficient = re.fullmatch(r'what coefficient applies to (mathematics|physics|chemistry|english) in the ([a-z]\d{2}) admission combination', text)
    if coefficient:
        subject = {'mathematics': 'toan', 'physics': 'ly', 'chemistry': 'hoa', 'english': 'anh'}[coefficient[1]]
        return f'coefficient:{coefficient[2]}:{subject}', ()
    bonus = re.fullmatch(r'what overall cap applies to bonus points on the (\d{1,3})-point admissions scale', text)
    if bonus:
        return 'bonus_cap:' + bonus[1], ()
    if re.fullmatch(r'for hsa (?:or|and) sat applicants, name both required online registration systems and the university-system registration window', text):
        return 'registration', ()
    patterns = (
        ('total_quota', r'(?:tong chi tieu tuyen sinh dai hoc(?: du kien)?(?: nam (?:19|20)\d{2})? la bao nhieu|what is the (?:total (?:proposed )?|proposed total )(?:undergraduate )?admission quota)'),
        ('entry_deadline', r'before which date does the notice plan to publish (?:(?:19|20)\d{2} )?admission entry thresholds'),
        ('entry_deadline', r'(?:nguong dau vao|nguong diem dau vao)(?: nam (?:19|20)\d{2})? (?:du kien )?duoc cong bo truoc ngay nao'),
        ('cutoff_deadline', r'before which date does the notice plan to publish the (?:(?:19|20)\d{2} )?final admission cutoff scores'),
        ('cutoff_deadline', r'diem trung tuyen(?: nam (?:19|20)\d{2})? (?:du kien )?duoc cong bo truoc ngay nao'),
        ('hsa_validity', r'(?:what test-age limit applies to hsa results|ket qua hsa co thoi han su dung bao lau(?: ke tu ngay thi)?)'),
        ('sat_validity', r'(?:what test-age limit applies to sat results|ket qua sat co thoi han su dung bao lau(?: ke tu ngay thi)?)'),
        ('english_validity', r'for how long from the test date can the specified english certificates be used for admissions conversion'),
        ('award_age', r'what maximum award age applies to the specified national or international prize route for direct admission'),
        ('points_scale', r'which common points scale is used to convert admission thresholds and cutoff scores between methods'),
    )
    for kind, pattern in patterns:
        if re.fullmatch(pattern, text):
            return kind, tuple(re.findall(r'\b(?:19|20)\d{2}\b', text))
    return None


def _source_facts(content, kind):
    body = sanitize_evidence_text(source_body({'content': content}, decode_tables=False))
    text, offsets = _fold_with_offsets(body)
    if kind == 'registration':
        calendar = r'\d{1,2}/\d{1,2}/\d{4}'
        pattern = (r'(?P<statement>doi\s+voi\s+cac\s+phuong\s+thuc\s+xet\s+tuyen\s+gom:'
            r'[^:]{1,550}?dang\s+ky\s+xet\s+tuyen\s+dong\s+thoi\s+tren\s+hai\s+he\s+thong\s+sau:'
            r'\s*[•*-]?\s*he\s+thong\s+tuyen\s+sinh\s+truc\s+tuyen\s+cua\s+truong\s+[^;]{1,220}?'
            r'thoi\s+gian\s+tu\s+ngay\s+(?P<value>' + calendar + r')\s+den\s+'
            r'(?P<clock>\d{1,2}(?:h|:)\d{2})\s+ngay\s+(?P<end>' + calendar + r');'
            r'\s*[•*-]?\s*he\s+thong\s+tuyen\s+sinh\s+cua\s+bo\s+giao\s+duc\s+va\s+dao\s+tao,'
            r'[^.]{1,130}?ban\s+hanh\.)')
    elif kind.startswith('coefficient:'):
        _, code, subject = kind.split(':')
        pattern = (r'(?P<statement>(?:\d{1,3}\s+)?' + code + r':\s*(?:(?!\b[a-z]\d{2}\s*:)[^.;()]){1,100}?\('
                   + subject + r'\s+he\s+so\s+(?P<value>\d{1,2})\))')
    elif kind.startswith('bonus_cap:'):
        scale = kind.split(':')[1]
        pattern = (r'(?P<statement>tong\s+diem\s+cong[^.;]{1,300}?khong\s+vuot\s+qua\s+'
                   r'(?P<value>\d{1,2})%\s+muc\s+diem\s+toi\s+da\s+cua\s+thang\s+diem\s+xet\s*'
                   r'\(toi\s+da\s+\d{1,2}\s+diem\s+doi\s+voi\s+thang\s+diem\s+' + scale + r'\)\.?)')
    elif kind == 'total_quota':
        pattern = r'(?m)^[ \t]*(?P<statement>tong\s+chi\s+tieu\s*:\s*(?P<value>\d{1,6}))(?![\w.,])'
    elif kind in {'entry_deadline', 'cutoff_deadline'}:
        label = 'nguong dau vao' if kind == 'entry_deadline' else 'diem trung tuyen'
        label = r'\s+'.join(label.split())
        # Do not cross another sentence or an adjacent numbered section.
        pattern = (r'(?P<statement>(?:\d+(?:\.\d+)+\.?\s+' + label + r'\s*[-–]?\s*)?'
                   r'truong\s+[^.;\n]{1,60}?\s+(?:se\s+)?cong\s+bo\s+' + label
                   + r'[^.;]{0,380}?truoc\s+ngay\s+(?P<value>\d{1,2}/\d{1,2}/\d{4})\)?\.?)')
    elif kind in {'hsa_validity', 'sat_validity'}:
        code = 'hsa' if kind == 'hsa_validity' else 'sat'
        subject = r'thi\s+hsa' if code == 'hsa' else r'ky\s+thi\s+chuan\s+hoa\s+quoc\s+te\s+sat'
        pattern = (r'(?P<statement>(?:\d+(?:\.\d+)+\.?\s+)?xet\s+tuyen\s+theo\s+' + code
                   + r'\s*:\s*ap\s+dung\s+doi\s+voi\s+thi\s+sinh\s+co\s+ket\s+qua\s+'
                   + subject + r'\s+con\s+thoi\s+han\s+su\s+dung\s+trong\s+vong\s+'
                   + r'(?P<value>\d{1,2})\s+nam\s+ke\s+tu\s+ngay\s+du\s+thi)')
    elif kind == 'english_validity':
        pattern = (r'(?P<statement>thi\s+sinh\s+co\s+chung\s+chi\s+tieng\s+anh\s+quoc\s+te\s*'
                   r'\([^)]{1,100}\)\s+con\s+thoi\s+han\s+su\s+dung\s+'
                   r'(?P<value>\d{1,2})\s+nam\s+ke\s+tu\s+ngay\s+thi)')
    elif kind == 'award_age':
        pattern = (r'(?P<statement>thoi\s+gian\s+doat\s+giai\s+khong\s+qua\s+'
                   r'(?P<value>\d{1,2})\s+nam\s+tinh\s+toi\s+thoi\s+diem\s+xet\s+tuyen\s+thang)')
    elif kind == 'points_scale':
        pattern = (r'(?P<statement>truong\s+[^.;\n]{1,60}?\s+su\s+dung\s+thang\s+diem\s+'
                   r'(?P<value>\d{1,3}))\s+de\s+quy\s+doi\s+nguong\s+dau\s+vao\s+va\s+diem\s+trung\s+tuyen')
    else:
        return []
    facts = []
    for match in re.finditer(pattern, text, re.I):
        prefix = text[text.rfind('\n', 0, match.start())+1:match.start()]
        # An inline example, quotation, exception or conditional is not an
        # unconditional field declaration. Never drop its governing clause.
        if kind != 'award_age' and prefix.strip(' \t+-*•–'):
            continue
        statement_text = match['statement']
        controls = r'\b(?:chua|neu|gia su|vi du)\b' if kind.startswith('bonus_cap:') else r'\b(?:khong|chua|neu|gia su|vi du)\b'
        if kind != 'award_age' and re.search(controls, statement_text):
            continue
        if kind == 'award_age':
            context = text[max(0, match.start()-320):match.start()]
            if (not re.search(r'quoc\s+gia.{0,60}quoc\s+te', context)
                    or re.search(r'\b(?:neu|gia su|vi du)\b', context)):
                continue
        start, end = match.span('statement')
        if prefix.strip() in {'-', '*', '•', '', '', '–'}:
            start = text.rfind('\n', 0, match.start()) + 1 + len(prefix) - len(prefix.lstrip())
        value = match['value']
        if kind == 'registration':
            intro = statement_text.split('dang')[0]
            if not {'hsa', 'sat'} <= set(re.findall(r'\b[a-z]+\b', intro)):
                continue
            try:
                first, last = [date(*reversed(list(map(int, item.split('/'))))) for item in (value, match['end'])]
                hour, minute = map(int, re.split('[h:]', match['clock']))
                if first > last or hour > 23 or minute > 59:
                    continue
            except ValueError:
                continue
            value += '|' + f'{hour:02}:{minute:02}' + '|' + match['end']
        elif kind.endswith('_deadline'):
            day, month, year = map(int, value.split('/'))
            try:
                date(year, month, day)
            except ValueError:
                continue
        elif int(value) <= 0:
            continue
        if kind.startswith('bonus_cap:'):
            cap = re.search(r'toi\s+da\s+(\d{1,2})\s+diem\s+doi', match['statement'])
            value += ':' + cap[1]
        facts.append((body[offsets[start]:offsets[end-1]+1], value))
    return facts


def admission_fact_candidates(question, records):
    request = admission_fact_request(question)
    if request is None:
        return None
    kind, years = request
    matching = [key for key, item in records.items() if item.get('content_type') == 'text'
                and _source_facts(item.get('content', ''), kind)]
    if not matching:
        return None
    if years:
        titles = admission_year_sources(records.values(), years)
        if not titles:
            return None
        matching.extend(key for key, item in records.items() if item in titles)
    return list(dict.fromkeys(matching))


def deterministic_admission_fact(question, results, language, *, calibrator=None):
    request = admission_fact_request(question)
    if request is None or len({r.doc_id for r in results}) != 1:
        return None
    kind, years = request
    named = {name.casefold() for name in re.findall(r'[\w.-]+\.pdf\b', question, re.I)}
    if named and not named <= {str(r.metadata.get('source_name', '')).casefold() for r in results}:
        return None
    titles = admission_year_sources(({'page': r.page, 'content': r.content,
        'content_type': r.content_type} for r in results), years) if years else []
    if years and not titles:
        return None
    if kind == 'total_quota' and re.search(r'\b(?:undergraduate|dai hoc)\b', folded(question)):
        if not any(r.content_type == 'text' and re.search(r'\b(?:bac dai hoc|undergraduate)\b',
                   folded(source_body({'content': r.content}, decode_tables=False))) for r in results):
            return None
    matches = [(r, statement, value) for r in results if r.content_type == 'text'
               for statement, value in _source_facts(r.content, kind)]
    from .grounding import Citation, GroundedAnswer, _abstention, validate_citation
    if not matches:
        opposite = {'entry_deadline': 'cutoff_deadline', 'cutoff_deadline': 'entry_deadline',
                    'hsa_validity': 'sat_validity', 'sat_validity': 'hsa_validity'}.get(kind)
        if opposite and any(_source_facts(r.content, opposite) for r in results if r.content_type == 'text'):
            return _abstention('unsupported_claim', language=language)
        return None
    def value_key(value):
        if kind == 'registration':
            first, clock, last = value.split('|')
            return tuple(date(*reversed(list(map(int, d.split('/'))))) for d in (first, last)) + (clock,)
        if kind.endswith('_deadline'):
            day, month, year = map(int, value.split('/'))
            return date(year, month, day)
        return tuple(map(int, value.split(':')))
    if len({value_key(value) for _, _, value in matches}) != 1:
        return _abstention('conflicting_evidence', language=language)
    # Prefer a complete statement on one physical page, with the original
    # section heading; a clipped multi-page chunk must not replace it.
    result, statement, value = min(matches, key=lambda item: (
        item[0].metadata.get('page_range', [item[0].page, item[0].page])[1]
        - item[0].metadata.get('page_range', [item[0].page, item[0].page])[0],
        -bool(re.match(r'\d+(?:\.\d+)+', item[1])), -bool(re.match(r'\d+\s+', item[1])), -item[0].score))
    if len(statement) > 1200:
        return _abstention('context_budget_exceeded', language=language)
    citation = Citation(result.chunk_id, result.doc_id, result.page, statement,
        ' > '.join(result.metadata.get('heading_path', [])), result.metadata.get('source_name', ''),
        tuple(result.metadata.get('page_range', [result.page, result.page])),
        result.metadata.get('table_id', ''), result.metadata.get('source_hash', ''))
    if not validate_citation(citation, result, require_quote=True).valid:
        return _abstention('invalid_citation', language=language)
    from .claims import Claim
    from .confidence import score_confidence
    english = language.casefold().startswith('en')
    labels = {
        'total_quota': (f'The total admission quota is {value}.', f'Tổng chỉ tiêu tuyển sinh là {value}.'),
        'entry_deadline': (f'Entry thresholds are planned to be published before {value}.', f'Ngưỡng đầu vào dự kiến được công bố trước ngày {value}.'),
        'cutoff_deadline': (f'Final cutoff scores are planned to be published before {value}.', f'Điểm trúng tuyển dự kiến được công bố trước ngày {value}.'),
        'hsa_validity': (f'HSA results must be within {value} years of the test date.', f'Kết quả HSA có thời hạn sử dụng trong vòng {value} năm kể từ ngày dự thi.'),
        'sat_validity': (f'SAT results must be within {value} years of the test date.', f'Kết quả SAT có thời hạn sử dụng trong vòng {value} năm kể từ ngày dự thi.'),
        'english_validity': (f'The English certificates must be within {value} years of the test date.', f'Chứng chỉ tiếng Anh có thời hạn sử dụng {value} năm kể từ ngày thi.'),
        'award_age': (f'The award must be no more than {value} years old at direct-admission consideration.', f'Thời gian đoạt giải không quá {value} năm tính tới thời điểm xét tuyển thẳng.'),
        'points_scale': (f'The university uses a {value}-point scale.', f'Trường sử dụng thang điểm {value}.'),
    }
    claim_text = statement
    if kind == 'registration':
        first, clock, last = value.split('|')
        claim_text = ('HSA and SAT applicants must register simultaneously on the university '
                      'and Ministry of Education and Training systems.')
        window = f'The university system accepts registration from {first} until {clock} on {last}.'
        labels[kind] = (claim_text + ' ' + window,
            f'Thí sinh HSA và SAT phải đăng ký đồng thời trên hệ thống tuyển sinh của Trường và Bộ GD&ĐT. '
            f'Hệ thống của Trường nhận đăng ký từ {first} đến {clock} ngày {last}.')
    elif kind.startswith('coefficient:'):
        _, code, subject = kind.split(':')
        en_subject = {'toan': 'Mathematics', 'ly': 'Physics', 'hoa': 'Chemistry', 'anh': 'English'}[subject]
        vi_subject = {'toan': 'Toán', 'ly': 'Lý', 'hoa': 'Hóa', 'anh': 'Anh'}[subject]
        claim_text = f'{en_subject} has coefficient {value} in {code.upper()}.'
        labels[kind] = (claim_text, f'Môn {vi_subject} có hệ số {value} trong tổ hợp {code.upper()}.')
    elif kind.startswith('bonus_cap:'):
        percent, cap = value.split(':')
        scale = kind.split(':')[1]
        labels[kind] = (f'Total bonus points cannot exceed {percent}% of the scale maximum, or {cap} points on a {scale}-point scale.',
                        f'Tổng điểm cộng không vượt quá {percent}% mức điểm tối đa, tối đa {cap} điểm đối với thang điểm {scale}.')
    claim = Claim('admission-fact', claim_text, 'fact', 1, (result.chunk_id,),
        'supported', 1.0, (result.chunk_id,), False)
    claims = (claim,)
    if kind == 'registration':
        claims += (Claim('registration-window', window, 'fact', 1, (result.chunk_id,),
            'supported', 1.0, (result.chunk_id,), False),)
    confidence = score_confidence(retrieval_support=max(0.0, min(1.0, result.score)),
        claim_entailment=1.0, citation_completeness=1.0, calibrator=calibrator)
    return GroundedAnswer(answer=labels[kind][0 if english else 1], citations=(citation,),
        confidence=confidence.label, abstained=False, claims=claims, evidence_status='found',
        confidence_score=confidence.score, raw_confidence_score=confidence.raw_score,
        policy_version=confidence.policy_version)
