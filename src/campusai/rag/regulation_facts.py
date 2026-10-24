"""Bounded programme-table and assessment lookups from literal source fields.

Questions select fields, never values. Unsupported wording and extra requests
keep the ordinary model path. No benchmark annotations or document filenames
establish a fact, programme scope or numeric value.
"""
import json
import re

from .course_credits import folded
from .footnotes import _fold_with_offsets
from .policies import sanitize_evidence_text
from ..retrieval.tokenizer_vi import source_body


def regulation_request(question):
    text = folded(question).strip()
    text = re.sub(r'^(?:use only (?:the )?uploaded|chi dung tai lieu da tai len) [\w.-]+\.pdf\.\s*', '', text)
    text = ' '.join(text.strip(' .?!').split())
    match = re.fullmatch(r'(?P<field>thoi gian dao tao chuan|khoi luong hoc tap toi thieu) cua chuong trinh '
        r'(?P<degree>cu nhan|ky su|thac si|tien si) danh cho nguoi tot nghiep '
        r'(?P<prior>thpt|cu nhan|dai hoc|thac si)(?P<ordinary> thong thuong)?(?P<integrated> theo chuong trinh tich hop)?'
        r'(?: trong bang)? la bao (?:nhieu|lau)', text)
    if match:
        if match['integrated'] and (match['ordinary'] or match['prior'] != 'cu nhan'):
            return None
        return ('programme', 'duration' if match['field'].startswith('thoi') else 'credits',
                match['degree'], 'tot nghiep '+match['prior']+(match['integrated'] or ''))
    if re.fullmatch(r'for a high-school graduate entering a regular bachelor programme, '
                   r'what standard duration and minimum credits does the table prescribe', text):
        return ('programme', 'both', 'cu nhan', 'tot nghiep thpt')
    match = re.fullmatch(r'trong so diem cuoi ky cua hoc phan tu (hai|ba|\d+) tin chi tro len nam trong khoang nao', text)
    if match:
        return ('weight', {'hai':'2','ba':'3'}.get(match[1], match[1]))
    if re.fullmatch(r'duoc hoan thi cuoi ky dung ly do thi phai du thi hoan thien trong thoi han nao', text):
        return ('deferral',)
    return None


def programme_rows(content):
    try:
        table = json.loads(content[content.index('{"headers"'):])
        headers, rows = table['headers'], table['rows']
        names = [folded(h) for h in headers]
        columns = [names.index(label) for label in
                   ['chuong trinh', 'nguoi hoc', 'thoi gian', 'khoi luong toi thieu']]
    except (ValueError, TypeError, KeyError, AttributeError):
        return []
    if len(set(columns)) != 4 or len(names) != len(set(names)) or not isinstance(rows, list):
        return []
    found = []; start = None
    for i, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != len(headers) or any(not isinstance(c, str) for c in row):
            start = None
            continue
        degree = folded(row[columns[0]])
        if degree:
            start = i if degree in {'cu nhan','ky su','thac si','tien si'} else None
        if start is not None:
            scope = rows[start][columns[0]]
            found.append((folded(scope), folded(row[columns[1]]), row[columns[2]], row[columns[3]],
                {'scope':scope,'headers':headers,'rows':rows[start:i+1]}))
    return found


def _assessment_facts(content, request):
    body = sanitize_evidence_text(source_body({'content':content}, decode_tables=False))
    text, offsets = _fold_with_offsets(body)
    if request[0] == 'weight':
        decimal = r'\d+(?:[.,]\d+)?'
        pattern = (r'(?P<whole>mot\s+hoc\s+phan\s+tu\s+'+re.escape(request[1])+r'\s+tc\s+tro\s+len'
            r'[^.;]{1,180}?trong\s+do\s+(?P<fact>diem\s+cuoi\s+ky\s+co\s+trong\s+so\s+tu\s+'
            r'(?P<a>'+decimal+r')\s+den\s+(?P<b>'+decimal+r')))')
    else:
        pattern = (r'(?P<whole>nguoi\s+hoc\s+khong\s+the\s+du\s+thi\s+cuoi\s+ky\s+mot\s+hoc\s+phan'
            r'[^.;]{1,240}?thi\s+duoc\s+phep\s+hoan\s+thi\s+va\s+'
            r'(?P<fact>duoc\s+du\s+thi\s+cuoi\s+ky\s+hoc\s+phan\s+do\s+trong\s+thoi\s+han\s+'
            r'(?P<a>\d+)\s+hoc\s+ky\s+chinh\s+tiep\s+theo))')
    result = []
    for match in re.finditer(r'(?m)^[ \t]*(?:\d+[.)]\s*)?'+pattern, text):
        a = float(match['a'].replace(',','.'))
        b = float(match['b'].replace(',','.')) if request[0] == 'weight' else a
        def original(group):
            start, end = match.span(group)
            return body[offsets[start]:offsets[end-1]+1]
        if not (0 < a <= b <= (1 if request[0] == 'weight' else 100)):
            result.append((original('whole'), [], (a,b)))
            continue
        result.append((original('whole'), [original('fact')], (a,b)))
    return result


def regulation_candidates(question, records):
    request = regulation_request(question)
    if request is None:
        return None
    return [key for key, item in records.items()
            if (request[0] == 'programme' and item.get('content_type') == 'table'
                and any((d,p) == request[2:] for d,p,*_ in programme_rows(item.get('content',''))))
            or (request[0] != 'programme' and item.get('content_type') == 'text'
                and _assessment_facts(item.get('content',''), request))]


def deterministic_regulation_fact(question, results, language, *, calibrator=None):
    request = regulation_request(question)
    if request is None or not results or len({r.doc_id for r in results}) != 1:
        return None
    named = {n.casefold() for n in re.findall(r'[\w.-]+\.pdf\b', question, re.I)}
    if named and not named <= {str(r.metadata.get('source_name','')).casefold() for r in results}:
        return None
    from .grounding import Citation, GroundedAnswer, _abstention, validate_citation
    from .claims import Claim
    from .confidence import score_confidence
    matches = []
    for result in results:
        if request[0] != 'programme':
            if result.content_type == 'text':
                matches.extend((result, *fact) for fact in _assessment_facts(result.content, request))
            continue
        if result.content_type != 'table':
            continue
        for degree, prior, duration, credits, quoted in programme_rows(result.content):
            if (degree, prior) != request[2:]:
                continue
            year = re.fullmatch(r'(\d+(?:[.,]\d+)?)\s+năm', duration.strip(), re.I)
            credit = re.fullmatch(r'(\d+)\s+(?:tín\s+chỉ|tc)', credits.strip(), re.I)
            if not year or not credit or float(year[1].replace(',','.')) <= 0 or int(credit[1]) <= 0:
                return _abstention('unsupported_claim', language=language)
            dname = {'cu nhan':'cử nhân','ky su':'kỹ sư','thac si':'thạc sĩ','tien si':'tiến sĩ'}[degree]
            pname = {'tot nghiep thpt':'THPT','tot nghiep dai hoc':'đại học','tot nghiep thac si':'thạc sĩ',
                'tot nghiep cu nhan':'cử nhân','tot nghiep cu nhan theo chuong trinh tich hop':'cử nhân theo chương trình tích hợp'}[prior]
            claims = ([f'The standard duration is {year[1].replace(",", ".")} years.',
                       f'The minimum workload is {credit[1]} credits.'] if request[1] == 'both' else
                [f'Thời gian đào tạo chuẩn của chương trình {dname} dành cho người tốt nghiệp {pname} là {duration.strip()}.']
                    if request[1] == 'duration' else
                [f'Khối lượng học tập tối thiểu của chương trình {dname} dành cho người tốt nghiệp {pname} là {credits.strip()}.'])
            values = (float(year[1].replace(',','.')), int(credit[1]))
            if request[1] != 'both': values = (values[0 if request[1] == 'duration' else 1],)
            matches.append((result, json.dumps(quoted, ensure_ascii=False), claims, values))
    if not matches:
        return None
    if any(not match[2] for match in matches):
        return _abstention('unsupported_claim', language=language)
    if len({m[3] for m in matches}) != 1:
        return _abstention('conflicting_evidence', language=language)
    result, quote, texts, _ = min(matches, key=lambda m:(len(m[1]), -m[0].score))
    if len(quote) > 1200:
        return _abstention('context_budget_exceeded', language=language)
    citation = Citation(result.chunk_id, result.doc_id, result.page, quote,
        ' > '.join(result.metadata.get('heading_path', [])), result.metadata.get('source_name',''),
        tuple(result.metadata.get('page_range',[result.page,result.page])),
        result.metadata.get('table_id',''), result.metadata.get('source_hash',''))
    if not validate_citation(citation, result, require_quote=True).valid:
        return _abstention('invalid_citation', language=language)
    claims = tuple(Claim(f'regulation-{i}', text, 'fact', 1, (result.chunk_id,),
        'supported', 1., (result.chunk_id,), False) for i,text in enumerate(texts,1))
    confidence = score_confidence(retrieval_support=max(0.,min(1.,result.score)),
        claim_entailment=1.,citation_completeness=1.,calibrator=calibrator)
    return GroundedAnswer(' '.join(texts), (citation,), confidence.label, claims=claims,
        confidence_score=confidence.score, raw_confidence_score=confidence.raw_score,
        policy_version=confidence.policy_version)
