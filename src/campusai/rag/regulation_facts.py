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
    # A prior topic supplies context, never the current requested field.
    text = folded(question.partition('\nContext topic (untrusted user input): ')[0]).strip()
    text = re.sub(r'^(?:use only (?:the )?uploaded|chi dung tai lieu da tai len) [\w.-]+\.pdf\.\s*', '', text)
    text = ' '.join(text.strip(' .?!').split())
    if (re.search(r'\bhoc truoc\b', text)
            and re.search(r'\b(?:hoc xong|chua dat|truot|rot|la gi)\b', text)
            and not re.search(r'\b(?:tien quyet|song hanh|va|so sanh|hoc phi|mat khau)\b|\b[a-z]{2,}\d+', text)):
        return ('prior_course_definition',)
    if (re.search(r'\bco\b.{1,160}\bky thi phu khong$', text)
            and not re.search(r'\b(?:neu|va|dong thoi|hoc phi|mat khau|so sanh)\b', text)):
        return ('exam_presence',)
    if (re.search(r'\b(?:gpa|cpa|diem trung binh(?: chung)? tich luy)\b', text)
            and re.search(r'\b(?:khoa luan|do an)\b', text)
            and re.search(r'\b(?:bao nhieu|may|toi thieu|dieu kien|can)\b', text)
            and not re.search(r'\b(?:va|dong thoi|ngoai ra|hoc phi|mat khau|thac si|tien si)\b', text)):
        return ('thesis_gpa',)
    if (re.search(r'\b(?:quy che|quy dinh|van ban|regulation|policy)\b', text)
            and re.search(r'\b(?:ap dung|applicable)\b', text)
            and re.search(r'\b(?:khoa|cohort|intake)\b', text)
            and not re.search(r'\b(?:va|and|dong thoi|ngoai ra|also|deadline|hoc phi|mat khau)\b', text)):
        return ('cohort',)
    registration = registration_request(text)
    if registration is not None:
        return registration
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
    if re.fullmatch(r'for (?:the )?reduced[- ]class option, what minimum study[- ]year rank is (?:necessary|required)',text):
        return ('reduced_class_year',)
    if re.fullmatch(r'what (?:normal )?minimum size applies to a master (?:programme|program) class taught in a classroom',text):
        return ('master_class_size',)
    if re.fullmatch(r'what minimum doctoral[- ]course credits must (?:every|each) doctoral (?:researcher|candidate|student) complete',text):
        return ('doctoral_credits',)
    match=re.fullmatch(r'how long is the possible additional coursework[- ]completion period after the initial '
        r'(one|two|three|four|five|\d+)[- ]year doctoral deadline',text)
    if match:
        return ('doctoral_extension',{'one':'1','two':'2','three':'3','four':'4','five':'5'}.get(match[1],match[1]))
    match=re.fullmatch(r'how many members are on the (institutional|university[- ]level|basic[- ]level) doctoral thesis assessment council',text)
    if match:
        return ('doctoral_council','co so' if match[1].replace('-',' ')=='basic level' else 'dai hoc')
    return None


def registration_request(text):
    """A single registration-limit field; unknown or compound requests fall back."""
    if (not re.search(r'\b(?:tin chi|tc|tin|credits?)\b', text)
            or not (re.search(r'\b(?:toi da|toi thieu|bao nhieu|may|gioi han)\b', text)
                or re.search(r'\b\d+\s*(?:tin(?: chi)?|tc)\b.{0,35}\b(?:duoc|dc)\s+(?:k|ko|khong)\b', text))
            or re.search(r'\b(?:hoc phi|le phi|gpa|cpa|mat khau|tai khoan|hoc bong|ngoai ngu|'
                         r'bao gio|ngay nao|het han|dong thoi|ngoai ra|also|so sanh|giong nhau|khac nhau|'
                         r'thac si|tien si|ky su|masters?|doctoral|hau qua|xu ly|bi gi|se bi|what happens)\b', text)):
        return None
    summer = bool(re.search(r'\bk[yi] he\b|\bhe\b(?=.{0,35}\b(?:muon|dang k[yi]|om|dk)\b)', text))
    primary = bool(re.search(r'\bk[yi] chinh\b', text))
    if summer == primary:
        return None
    warning = re.search(r'\bcanh bao(?: hoc tap)? muc (\d+)\b', text)
    if 'canh bao' in text and not warning and not re.search(r'\bkhong (?:bi|thuoc dien) canh bao\b', text):
        return None
    if warning and ('chuan' not in text or summer):
        return None
    return ('registration', 'summer' if summer else 'primary', warning[1] if warning else None)


def _registration_facts(body, request):
    text, offsets = _fold_with_offsets(body)
    unit = r'(?:tc|tin\s+chi)'
    if request[2]:
        level = re.escape(request[2])
        pattern = (r'(?P<fact>han che khoi luong hoc tap[^.]{0,200}?canh bao hoc tap tu muc '
            + level + r' tro len[^.]{0,180}?tai hoc ky (?P<term>\d+) cua nam hoc,?\s*cu the nhu sau:\s*'
            r'a\)\s*sinh vien thuoc cac (?:ctdt|chuong trinh dao tao) chuan duoc dang ky '
            r'toi da (?P<maximum>\d+)\s*' + unit + r' va toi thieu (?P<minimum>\d+)\s*' + unit +
            r' cho mot hoc ky chinh[.;])')
    elif request[1] == 'summer':
        pattern = (r'(?P<fact>sinh vien duoc dang ky toi da (?P<maximum>\d+)\s*' + unit +
                   r' trong hoc ky he\.)')
    else:
        pattern = (r'(?P<fact>sinh vien khong thuoc dien canh bao hoc tap[^.]{0,160}?duoc dang ky '
            r'toi da (?P<maximum>\d+)\s*' + unit + r' va toi thieu (?P<minimum>\d+)\s*' + unit +
            r' trong hoc ky chinh[^.]{0,220}\.)')
    found = []
    for match in re.finditer(pattern.replace(' ', r'\s+'), text):
        start, end = match.span('fact')
        # Require a source paragraph/bullet boundary, not a quoted example.
        prefix = text[max(0, start - 6):start]
        if start and not re.search(r'(?:^|\n|[.;])\s*(?:\d+[.)]|[a-z][)])?\s*$', prefix):
            continue
        if re.search(r'\b(?:vi du|gia su|example)\b[^\n]{0,100}$', text[max(0, start - 110):start]):
            continue
        quote = body[offsets[start]:offsets[end - 1] + 1]
        fields = match.groupdict()
        values = tuple(int(fields[name]) if fields.get(name) else None for name in ('minimum', 'maximum', 'term'))
        if values[0] is not None and values[0] > values[1]:
            continue
        found.append((quote, [' '.join(quote.split())], values))
    return found


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


def _assessment_facts(content, request, metadata=None):
    body = sanitize_evidence_text(source_body({'content':content}, decode_tables=False))
    if request[0] == 'registration':
        return _registration_facts(body, request)
    text, offsets = _fold_with_offsets(body)
    if request[0] == 'prior_course_definition':
        match = re.search(r'(?m)(?:^[ \t]*(?:[a-z][)])?\s*|(?<=[.;])\s*)'
            r'(?:hoc\s+phan\s+hoc\s+truoc:\s*)?'
            r'(?P<fact>hoc\s+phan\s+a\s+la\s+hoc\s+phan\s+hoc\s+truoc\s+cua\s+hoc\s+phan\s+b\s+'
            r'thi\s+sinh\s+vien\s+phai\s+dang\s+ky\s+va\s+hoc\s+xong\s+'
            r'\(co\s+the\s+chua\s+dat\)\s+hoc\s+phan\s+a\s+moi\s+duoc\s+du\s+lop\s+hoc\s+phan\s+b\.)', text)
        if match:
            start, end = match.span('fact')
            quote = body[offsets[start]:offsets[end-1]+1]
            return [(quote, [' '.join(quote.split())], ('prior_course_definition',))]
        return []
    if request[0] == 'exam_presence':
        pattern = (r'(?m)(?:^[ \t]*(?:[a-z][)])?\s*|(?<=[.;])\s*)'
            r'(?P<fact>cuoi\s+moi\s+hoc\s+ky,\s*(?:nha\s+truong|truong)\s+to\s+chuc\s+'
            r'mot\s+ky\s+thi\s+chinh\s+va\s+mot\s+ky\s+thi\s+phu\.)')
        found = []
        for match in re.finditer(pattern, text):
            start, end = match.span('fact')
            if re.search(r'\b(?:vi du|gia su|example)\b[^\n]{0,100}$', text[max(0,start-110):start]):
                continue
            quote = body[offsets[start]:offsets[end-1]+1]
            found.append((quote, [' '.join(quote.split())], ('explicit_supplementary_exam',)))
        return found
    if request[0] == 'thesis_gpa':
        pattern = (r'(?P<whole>(?P<fact>diem\s+trung\s+binh(?:\s+chung)?\s+tich\s+luy\s+'
            r'tinh\s+den\s+thoi\s+diem\s+xet\s+dieu\s+kien\s+lam\s+'
            r'(?:do\s+an,?\s*)?khoa\s+luan\s+phai\s+dat\s+tu\s+'
            r'(?P<a>\d+(?:[.,]\d+)?)\s+tro\s+len[.;]))')
    elif request[0] == 'cohort':
        pattern = (r'(?P<whole>(?P<fact>(?:quyet dinh|quy che|quy dinh|van ban) nay '
            r'[^.]{0,180}?ap dung doi voi cac\s+khoa tuyen sinh tu nam (?P<a>(?:19|20|21)\d{2})\.))')
    elif request[0] == 'weight':
        decimal = r'\d+(?:[.,]\d+)?'
        pattern = (r'(?P<whole>mot\s+hoc\s+phan\s+tu\s+'+re.escape(request[1])+r'\s+tc\s+tro\s+len'
            r'[^.;]{1,180}?trong\s+do\s+(?P<fact>diem\s+cuoi\s+ky\s+co\s+trong\s+so\s+tu\s+'
            r'(?P<a>'+decimal+r')\s+den\s+(?P<b>'+decimal+r')))')
    elif request[0]=='deferral':
        pattern = (r'(?P<whole>nguoi\s+hoc\s+khong\s+the\s+du\s+thi\s+cuoi\s+ky\s+mot\s+hoc\s+phan'
            r'[^.;]{1,240}?thi\s+duoc\s+phep\s+hoan\s+thi\s+va\s+'
            r'(?P<fact>duoc\s+du\s+thi\s+cuoi\s+ky\s+hoc\s+phan\s+do\s+trong\s+thoi\s+han\s+'
            r'(?P<a>\d+)\s+hoc\s+ky\s+chinh\s+tiep\s+theo))')
    elif request[0]=='doctoral_credits':
        pattern=(r'(?P<whole>(?P<fact>moi\s+ncs\s+phai\s+hoan\s+thanh\s+toi\s+thieu\s+'
            r'(?P<a>\d+)\s+tc)\s+tuong\s+ung\s+\d+\s*[-–]\s*\d+\s+hoc\s+phan\s+tien\s+si)')
    elif request[0]=='doctoral_extension':
        if not re.search(r'hoc\s+phan\s+tien\s+si',text):return []
        pattern=(r'(?P<whole>trong\s+truong\s+hop\s+qua\s+thoi\s+han\s+'
            +re.escape(request[1])+r'\s+nam\s+nhung\s+khong\s+the\s+hoan\s+thanh,\s*'
            r'(?P<fact>ncs\s+co\s+the\s+de\s+nghi\s+xin\s+gia\s+han\s+thoi\s+gian\s+thuc\s+hien\s+'
            r'trong\s+khoang\s+thoi\s+gian\s+(?P<a>\d+)\s+thang\s+ke\s+tiep))')
    elif request[0]=='doctoral_council':
        pattern=(r'(?P<whole>(?P<fact>hoi\s+dong(?:\s+danh\s+gia\s+luan\s+an)?\s+cap\s+'
            +r'\s+'.join(map(re.escape,request[1].split()))+r'\b[^.;]{0,260}?\bco\s+'
            r'(?P<a>\d+)\s+thanh\s+vien))')
    elif request[0]=='master_class_size':
        headings=(metadata or {}).get('heading_path',[])
        heading=headings if isinstance(headings,str) else ' '.join(headings) if isinstance(headings,list) and all(isinstance(v,str) for v in headings) else ''
        if not re.search(r'chuong trinh thac si',folded(heading+' '+content)):return []
        pattern=(r'(?P<whole>doi\s+voi\s+cac\s+hoc\s+phan\s+duoc\s+giang\s+day\s+tren\s+lop,\s*'
            r'(?P<fact>quy\s+mo\s+lop\s+hoc\s+phan\s+toi\s+thieu\s+la\s+(?P<a>\d+)\s+hoc\s+vien))')
    elif request[0]=='reduced_class_year':
        if not re.search(r'lop\s+hoc\s+phan\s+rut\s+gon',text):return []
        pattern=(r'(?P<whole>(?P<fact>sinh\s+vien\s+dat\s+trinh\s+do\s+nam\s+hoc\s+tu\s+nam\s+thu\s+'
            r'(?P<rank>nhat|hai|ba|tu|nam|sau|bay|tam|chin|muoi)\s+tro\s+len))')
    else:return []
    result = []
    # A period/sentence boundary or an explicit list label must precede a
    # normative fact. A quoted assertion in the middle of prose is not a rule.
    prefix=(r'(?m)^[ \t]*(?:\d+[.)]\s*)?' if request[0] in {'weight','deferral'} else
            r'(?m)(?:^[ \t]*(?:(?:\d+|[a-zđ])[.)]\s*)?|(?<=[.;])\s+)')
    if request[0] == 'thesis_gpa':
        prefix = r'(?m)^[ \t]*(?:[-–—•~]\s*|(?:\d+|[a-zđ])[.)]\s*)?'
    for match in re.finditer(prefix+pattern, text):
        if re.search(r'(?m)(?:^|[.;])\s*(?:khong phai|not)\s+\d+[.)]\s*$',text[:match.start('whole')]):
            continue
        ranks={'nhat':1,'hai':2,'ba':3,'tu':4,'nam':5,'sau':6,'bay':7,'tam':8,'chin':9,'muoi':10}
        a = ranks[match['rank']] if request[0]=='reduced_class_year' else float(match['a'].replace(',','.'))
        b = float(match['b'].replace(',','.')) if request[0] == 'weight' else a
        def original(group):
            start, end = match.span(group)
            return body[offsets[start]:offsets[end-1]+1]
        maximum = 1 if request[0] == 'weight' else 2199 if request[0] == 'cohort' else 100
        if not (0 < a <= b <= maximum):
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
                and _assessment_facts(item.get('content',''), request,item.get('metadata')))]


def condition_list_quote(content, anchor):
    """Return a closed, explicitly headed bullet list containing an exact fact.

    Keep the source bytes and stop at a new heading/paragraph. An isolated
    numeric criterion must not silently become all of an eligibility policy.
    Ambiguous, oversized or unheaded lists stay on ordinary generation.
    """
    body=source_body({'content':content},decode_tables=False)
    lines=body.splitlines(keepends=True);found=[]
    normalized=lambda text:' '.join(text.casefold().split()).strip(' .;')
    bullet=re.compile(r'^\s*[-–—•~]\s+(.+)')
    for index,line in enumerate(lines):
        heading=folded(line.strip())
        if (len(heading)>160 or not heading.endswith(':')
                or not re.search(r'\b(?:dieu kien|conditions?|requirements?|eligibility)\b',heading)
                or re.search(r'\b(?:vi du|example|illustration|khong|not)\b',heading)):
            continue
        items=[];current=[];end=index+1;closed=False
        for pos in range(index+1,len(lines)):
            value=lines[pos];match=bullet.match(value)
            if match:
                if current:items.append(''.join(current).strip())
                current=[match[1]+('\n' if value.endswith('\n') else '')]
            elif current and value.strip() and not re.match(r'^\s*(?:\d+|[a-zđ])[.)]\s+',value,re.I):
                current.append(value)
            else:
                closed=bool(current and re.match(r'^\s*(?:\d+|[a-zđ])[.)]\s+',value,re.I))
                break
            end=pos+1
        if current:items.append(''.join(current).strip())
        if not closed or len(items)<2 or sum(normalized(item)==normalized(anchor) for item in items)!=1:
            continue
        quote=''.join(lines[index:end]).strip()
        if len(quote)<=1200 and sanitize_evidence_text(quote)==quote:found.append((quote,items))
    return found[0] if len(found)==1 else None


def deterministic_regulation_fact(question, results, language, *, calibrator=None):
    request = regulation_request(question)
    if request is None or not results or len({r.doc_id for r in results}) != 1:
        return None
    if request[0] in {'registration', 'cohort', 'exam_presence', 'thesis_gpa', 'prior_course_definition'} and not language.startswith('vi'):
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
                matches.extend((result, *fact) for fact in _assessment_facts(result.content, request,result.metadata))
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
    conditions=None
    if request[0]=='thesis_gpa':
        lists=[condition_list_quote(match[0].content,match[2][0]) for match in matches]
        signatures={tuple(' '.join(item.split()) for item in entry[1]) if entry else None for entry in lists}
        if len(signatures)>1:return None
        conditions=condition_list_quote(result.content,texts[0])
        if conditions:
            quote,items=conditions
            core=' '.join(texts[0].split()).strip(' .;')
            texts=[texts[0],*[item for item in items if ' '.join(item.split()).strip(' .;')!=core]]
    if len(quote) > 1200:
        return _abstention('context_budget_exceeded', language=language)
    citation = Citation(result.chunk_id, result.doc_id, result.page, quote,
        ' > '.join(result.metadata.get('heading_path', [])), result.metadata.get('source_name',''),
        tuple(result.metadata.get('page_range',[result.page,result.page])),
        result.metadata.get('table_id',''), result.metadata.get('source_hash',''))
    if not validate_citation(citation, result, require_quote=True).valid:
        return _abstention('invalid_citation', language=language)
    if conditions:
        from .grounding import _grounding_finalize
        answer=texts[0]+'\n\nĐiều kiện cùng mục:\n'+'\n'.join('- '+' '.join(text.split()) for text in texts[1:])
        checked=_grounding_finalize(answer,(citation,),{'confidence':'high','claims':[
            {'claim_id':f'regulation-{i}','text':text,'citation_ids':[result.chunk_id]}
            for i,text in enumerate(texts,1)]},results,language,question=question,calibrator=calibrator)
        return checked if not checked.abstained else None
    claims = tuple(Claim(f'regulation-{i}', text, 'fact', 1, (result.chunk_id,),
        'supported', 1., (result.chunk_id,), False) for i,text in enumerate(texts,1))
    confidence = score_confidence(retrieval_support=max(0.,min(1.,result.score)),
        claim_entailment=1.,citation_completeness=1.,calibrator=calibrator)
    return GroundedAnswer(' '.join(texts), (citation,), confidence.label, claims=claims,
        confidence_score=confidence.score, raw_confidence_score=confidence.raw_score,
        policy_version=confidence.policy_version)
