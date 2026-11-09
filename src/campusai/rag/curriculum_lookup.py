"""Project unambiguous curriculum fields from the complete selected index.

This is a local source lookup, not model inference. The full indexed document
is inspected so an abbreviation cannot hide a second matching course in a
lower-ranked table. Unknown requests and incomplete proofs fall back to RAG.
"""
import json
import re
from decimal import Decimal

from .course_credits import folded, COURSE_CODE, course_code_key
from .multi_hop_evidence import table
from .semester_citations import _marker, _subtotal
from .semester_totals import _SEMESTER, _NUMBERS, requested_semesters, deterministic_semester_total


_NAMES = {'discipline', 'course name', 'subject', 'subject name', 'hoc phan', 'ten hoc phan'}
_PROVIDERS = {'resources', 'resource', 'provider', 'institution', 'don vi phu trach', 'don vi cung cap'}
_CATEGORIES = {'compulsory subjects', 'elective subjects', 'optional subjects'}
_CONTEXT = '\nContext topic (untrusted user input): '


def _clean(value):
    text = folded(value).strip(' .?!')
    text = re.sub(r'\b(?:(?:trong|theo|in|of)\s+)?(?:ban\s+)?'
        r'(?:chuong trinh(?: lien ket)?|curriculum|(?:the )?(?:selected |uploaded )?(?:programme|program|table)|'
        r'bang(?: (?:minh|em|toi) chon)?|tai lieu)\b'
        r'(?:\s+(?:nay|dang mo|da chon|da tai len))?', ' ', text)
    return ' '.join(text.split())


def _provider_request(question):
    numbers = []
    def slot(match):
        numbers.append(int(match[1]) if match[1].isdigit() else _NUMBERS[match[1]])
        return ' @ '
    text = _clean(_SEMESTER.sub(slot, folded(question)))
    text = re.sub(r' (?:vay|nhi|a)$', '', text)
    institution = r'[a-z][a-z0-9.-]{0,31}'
    patterns = (
        r'@ (?:thi )?(?:(?:cac )?(?:mon hoc|hoc phan) )?(?:do )?(?:truong nao|ben nao|don vi nao) (?:phu trach|day)',
        r'(?:toi |den )?@ (?:thi )?hoc (?:o |tai )?(?:ben|truong) (?:nao|dau)',
        r'(?:toi |den )?@ (?:thi )?hoc ben(?: '+institution+r')? hay ben '+institution,
        r'(?:cot )?don vi (?:cung cap|phu trach) (?:mon hoc|hoc phan) (?:o |cua |trong )?@ (?:ghi gi|la gi)',
        r'@ (?:courses )?taught by which institution',
        r'which (?:institution|provider) (?:teaches|provides) (?:the )?courses (?:in|for) @',
    )
    if len(numbers) == 1 and 1 <= numbers[0] <= 20 and any(re.fullmatch(p, text) for p in patterns):
        return numbers[0]


def _subtotal_question(question, tables):
    """Recognize a selected-programme frame without discarding its partner.

    A named partner must occur in the actual provider column of this source.
    Neither the name in the question nor a filename supplies a credit value.
    """
    text = folded(question).strip(' .?!')
    frame = re.fullmatch(r'(?:hoc )?chuong trinh(?: lien ket)?'
        r'(?: voi (?P<partner>[a-z0-9][a-z0-9 .-]{0,60}?))?'
        r'(?: theo (?:ban|bang|tai lieu) (?:dang mo|da chon|da tai len))?'
        r' thi (?P<request>.+)', text)
    if frame:
        partner = frame['partner']
        if partner:
            providers = set()
            for _item, data, _name in tables:
                column = _column(data['headers'], _PROVIDERS)
                if column is None:
                    return None
                providers.update(folded(row[column].strip()) for row in data['rows'] if row[column].strip())
            if partner not in providers:
                return None
        text = frame['request']
    return text if requested_semesters(text) is not None else None


def _course_request(text):
    text = _clean(text)
    quantity = r'(?:may|bao nhieu|bao nhiu|bn) (?:tin(?: chi)?|tc)'
    when = r'(?:hoc ky|ky|hk) (?:may|nao)'
    patterns = (
        r'@ (?:co )?' + quantity + r' (?:va )?' + when,
        r'@ ' + when + r' (?:va )?(?:co )?' + quantity,
        r'@ (?:credits and semester|semester and credits)(?: please)?',
        r'(?:phan danh gia cuoi ghi )?@ hoc luc nao va tinh ' + quantity,
    )
    return any(re.fullmatch(pattern, text) for pattern in patterns)


def _column(headers, names):
    matches = [i for i, value in enumerate(headers) if folded(value) in names]
    return matches[0] if len(matches) == 1 else None


def _category(row):
    cells = [cell.strip() for cell in row if cell.strip()]
    return len(cells) == 1 and folded(cells[0]) in _CATEGORIES


def _tables(document):
    result = []
    for item in document['items']:
        if item.get('content_type') != 'table':
            continue
        value = table(item['content'])
        if not value or any(not isinstance(row, list) or len(row) != len(value['headers'])
                            or any(not isinstance(cell, str) for cell in row) for row in value['rows']):
            return None
        name = _column(value['headers'], _NAMES)
        if name is None:
            return None
        result.append((item, value, name))
    return result


def _provider(tables, semester):
    found = []
    for item, data, name in tables:
        column = _column(data['headers'], _PROVIDERS)
        if column is None:
            return None
        rows = data['rows']
        for start, row in enumerate(rows):
            marker = _marker(row)
            if not marker or marker[0] != semester:
                continue
            end = next((i for i in range(start + 1, len(rows)) if _marker(rows[i]) or _subtotal(rows[i])), None)
            if end is None:
                return None
            last = end if _subtotal(rows[end]) else end - 1
            courses = [r for r in rows[start + 1:last + 1] if not _category(r) and not _subtotal(r)]
            if not courses or any(not r[name].strip() or not r[column].strip()
                    or any(re.match(r'^(?:semester|hoc ky)(?:\s|\d|$)', folded(c)) for c in r)
                    for r in courses):
                return None
            providers = {r[column].strip() for r in courses}
            if len(providers) != 1:
                return None
            found.append((item, data, start, last, next(iter(providers))))
        # A continuation alone cannot prove coverage of the entire semester.
        scope = _marker([item.get('metadata', {}).get('table_scope') or ''])
        if scope and scope[0] == semester and not any(_marker(r) == scope for r in rows):
            return None
    if not found or len({json.dumps([p[1]['headers'], p[1]['rows'][p[2]:p[3]+1]]) for p in found}) != 1:
        return None
    item, data, start, end, provider = found[0]
    return item, {'scope': _marker(data['rows'][start])[1], 'headers':data['headers'],
                  'rows':data['rows'][start:end+1]}, provider


def _course(tables, question):
    inventory, mentions = [], []
    text = folded(question)
    for item, data, name in tables:
        credit = _column(data['headers'], {'credits', 'so tin chi'})
        if credit is None:
            return None
        active = None
        for row_index, row in enumerate(data['rows']):
            if marker := _marker(row):
                active = (marker[0], marker[1], row_index)
                continue
            if _subtotal(row):
                active = None
                continue
            if _category(row):
                continue
            if any(re.match(r'^(?:semester|hoc ky)(?:\s|\d|$)', folded(c)) for c in row):
                active = None
                continue
            label = ' '.join(row[name].split())
            if not label:
                active = None
                continue
            key = folded(label)
            inventory.append((key, item, data, row_index, active, row[credit].strip(), label))
            aliases = {key}
            words = label.split()
            if 3 <= len(words) <= 8 and all(re.fullmatch(r'[A-Z][A-Za-z]+', word) for word in words):
                aliases.add(''.join(word[0] for word in words).casefold())
            for alias in aliases:
                mentions.extend((key, m.start(), m.end()) for m in re.finditer(
                    r'(?<!\w)' + re.escape(alias) + r'(?!\w)', text))
    maximal = [(key,a,b) for key,a,b in mentions if not any(
        x <= a and b <= y and (x < a or b < y) for _,x,y in mentions)]
    if len({key for key,_,_ in maximal}) != 1 or len({(a,b) for _,a,b in maximal}) != 1:
        return None
    key, start, end = maximal[0]
    if not _course_request(text[:start] + '@' + text[end:]):
        return None
    records = [record for record in inventory if record[0] == key]
    if any(not p[4] or not re.fullmatch(r'[0-9]{1,3}(?:[.,][0-9]{1,2})?', p[5]) for p in records):
        return None
    if len({(p[4][0], Decimal(p[5].replace(',', '.'))) for p in records}) != 1:
        return None
    _, item, data, row_index, scope, credits, label = records[0]
    value = format(Decimal(credits.replace(',', '.')).normalize(), 'f')
    return item, {'scope':scope[1], 'headers':data['headers'],
                  'rows':data['rows'][scope[2]:row_index+1]}, label, scope[0], value


def _code_request(question):
    text = folded(question).strip(' .?!')
    patterns = (
        r'(?:mon|hoc phan) ('+COURSE_CODE+r')(?: trong chuong trinh)? la (?:mon|hoc phan) gi va co (?:bao nhieu|may|bn) tin chi(?: vay| nhi)?',
        r'what (?:is|are) the name and credits of course ('+COURSE_CODE+r')',
    )
    for pattern in patterns:
        if match := re.fullmatch(pattern,text,re.I):
            return course_code_key(match[1])


def _code_course(tables, code):
    records = []
    for item,data,name in tables:
        identity = _column(data['headers'],{'course code','ma hoc phan','ma so hoc phan'})
        credit = _column(data['headers'],{'credits','so tin chi'})
        if identity is None or credit is None:
            return None
        for row in data['rows']:
            cell = row[identity].strip()
            if code not in {course_code_key(m[0]) for m in re.finditer(COURSE_CODE,cell,re.I)}:
                continue
            value = row[credit].strip()
            if (course_code_key(cell)!=code or not row[name].strip()
                    or not re.fullmatch(r'[0-9]{1,3}(?:[.,][0-9]{1,2})?',value)):
                return None
            records.append((item,row,' '.join(row[name].split()),Decimal(value.replace(',','.'))))
    if not records or len({(folded(p[2]),p[3]) for p in records})!=1:
        return None
    item,row,label,value = records[0]
    return item,row,label,format(value.normalize(),'f')


def lookup_curriculum(question, documents, *, doc_ids, language='vi', calibrator=None):
    """Return an answer and exact indexed proof, only for one selected source."""
    if doc_ids is None or len(doc_ids) != 1 or len(documents) != 1 or documents[0]['doc_id'] != doc_ids[0]:
        return None
    question, _, topic = question.partition(_CONTEXT)
    if topic and re.search(r'\b(?:neu|if|unless|mien|waiver|transfer|chuyen nganh|so sanh|compare|versus)\b', folded(topic)):
        return None
    semester = _provider_request(question)
    code = _code_request(question)
    if code is None and semester is None and not (re.search(r'\b(?:tin|tc|credits)\b', folded(question))
                                and re.search(r'\b(?:ky|hk|semester|luc nao)\b', folded(question))):
        return None
    tables = _tables(documents[0])
    if not tables:
        return None
    subtotal_question = _subtotal_question(question, tables)
    if subtotal_question is not None:
        from ..retrieval.hybrid import RetrievalResult
        results = [RetrievalResult(item['chunk_id'], documents[0]['doc_id'], item['page'],
            item['content'], 'table', 1., 'source_table_lookup', item.get('metadata', {}))
            for item, _data, _name in tables]
        answer = deterministic_semester_total(subtotal_question, results, language, calibrator=calibrator)
        if answer is None:
            return None
        cited = {citation.chunk_id for citation in answer.citations}
        return answer, [result for result in results if result.chunk_id in cited]
    english = language.casefold().startswith('en')
    if code is not None:
        projection = _code_course(tables,code)
        if projection is None:
            return None
        item,quote,label,credits = projection
        facts = ([f'Course {code} is {label}.',f'Course {code} has {credits} credits.'] if english else
                 [f'Môn {code} là {label}.',f'Môn {code} có {credits} tín chỉ.'])
    elif semester is not None:
        projection = _provider(tables, semester)
        if projection is None:
            return None
        item, quote, provider = projection
        facts = [(f'All courses in semester {semester} are provided by {provider}.' if english else
                  f'Các học phần trong học kỳ {semester} do {provider} phụ trách.')]
    else:
        projection = _course(tables, question)
        if projection is None:
            return None
        item, quote, label, semester, credits = projection
        facts = ([f'{label} is in semester {semester}.', f'{label} has {credits} credits.'] if english else
                 [f'Học phần {label} nằm ở học kỳ {semester}.', f'Học phần {label} có {credits} tín chỉ.'])
    from .grounding import Citation, GroundedAnswer, validate_citation
    from .claims import Claim
    from .confidence import score_confidence
    from ..retrieval.hybrid import RetrievalResult
    result = RetrievalResult(item['chunk_id'], documents[0]['doc_id'], item['page'], item['content'],
                             'table', 1., 'source_table_lookup', item.get('metadata', {}))
    meta = result.metadata
    citation = Citation(result.chunk_id, result.doc_id, result.page, json.dumps(quote, ensure_ascii=False),
        ' > '.join(meta.get('heading_path', [])), meta.get('source_name', ''),
        tuple(meta.get('page_range', [result.page,result.page])), meta.get('table_id', ''), meta.get('source_hash', ''))
    if len(citation.quote) > 1200 or not validate_citation(citation,result,require_quote=True).valid:
        return None
    confidence = score_confidence(retrieval_support=1., claim_entailment=1., citation_completeness=1., calibrator=calibrator)
    claims = tuple(Claim(str(i), text, 'fact', 1, (result.chunk_id,), 'supported', 1.,
                         (result.chunk_id,), False) for i,text in enumerate(facts,1))
    answer = GroundedAnswer(' '.join(facts), (citation,), confidence.label, False, claims=claims,
        evidence_status='found', confidence_score=confidence.score, raw_confidence_score=confidence.raw_score,
        policy_version=confidence.policy_version)
    return answer, [result]
