"""Bounded natural single-course lookups from literal, headed source rows."""
import json
import re

from .course_credits import COURSE_CODE, course_code_key, folded, headed_credit_rows
from .multi_hop_evidence import find_premise, name_matches, prerequisite_codes, table


_CONTEXT = '\nContext topic (untrusted user input): '
_CREDIT = r'(?:may|bao nhieu|bn)\s+(?:tin(?: chi)?|tc)'
_TAIL = r'(?:\s+(?:vay|nhi|ban|a|the|ah|oi))*'


def _request(question):
    raw, _, topic = question.partition(_CONTEXT)
    text = folded(raw).strip(' .?!')
    if topic and re.search(r'\b(?:neu|if|unless|mien|waiver|transfer|chuyen nganh|so sanh|compare|comparison|versus)\b', folded(topic)):
        return None
    for pattern, fields in (
        (r'can hoc gi truoc va ' + _CREDIT + _TAIL, ('credits', 'prerequisites')),
        (r'(?:can )?hoc (?:gi truoc|truoc (?:nhung )?mon nao)' + _TAIL, ('prerequisites',)),
        (r'(?:(?:mon nay|hoc phan nay)\s+)?(?:co\s+)?' + _CREDIT + _TAIL, ('credits',)),
        (r'how many credits', ('credits',)),
    ):
        if topic and re.fullmatch(pattern, text):
            return fields, None, folded(topic)
    for pattern, fields in (
        (r'(?:(?:mon|hoc phan)\s+)?(.+?)\s+(?:co\s+)?' + _CREDIT + _TAIL, ('credits',)),
        (r'how many credits does (?:course )?(.+?) (?:have|carry)', ('credits',)),
        (r'what are (?:the )?prerequisites for (?:course )?(.+)', ('prerequisites',)),
        (r'what are (?:the )?prerequisites and credits for (?:course )?(.+)', ('credits', 'prerequisites')),
    ):
        match = re.fullmatch(pattern, text)
        if match:
            return fields, match[1].strip(' "\''), ''
    return None


def _target(results, name, topic):
    if name and re.fullmatch(COURSE_CODE, name, re.I):
        return course_code_key(name)
    matches = []
    for result in results:
        value = table(result.content)
        if not value:
            continue
        columns = [i for i, h in enumerate(value['headers']) if re.fullmatch(
            r'(?:hoc phan|ten hoc phan|course name|discipline)(?:\s*\(.*\))?', folded(h))]
        if len(columns) != 1:
            continue
        for code, _credits, row in headed_credit_rows(result.content) or []:
            if len(row) <= columns[0] or not isinstance(row[columns[0]], str):
                continue
            cell = row[columns[0]]
            if name:
                if name_matches(name, cell):
                    matches.append((code, 0, len(name)))
                continue
            lines = cell.splitlines()
            aliases = {' '.join(lines[:i]).rstrip().rstrip('*').rstrip()
                       for i in range(1, len(lines) + 1)}
            aliases.update(' '.join(lines[i:]) for i in range(len(lines)))
            for alias in aliases:
                if not alias or not name_matches(alias, cell):
                    continue
                for match in re.finditer(r'\b(?:mon|hoc phan|course|subject)\s+'
                                         + re.escape(folded(alias)) + r'(?=$|[\s.,;:!?])', topic):
                    matches.append((code, match.start(), match.end()))
    # A shorter name within the same explicitly named subject is not a second
    # course. Separate subject mentions and duplicate names remain ambiguous.
    maximal = [(code, start, end) for code, start, end in matches if not any(
        a <= start and end <= b and (a < start or end < b) for _, a, b in matches)]
    if not name and any(re.match(r'\s+(?:va|and|hay|or|voi|with)\b', topic[end:])
                        for _, _, end in maximal):
        return None
    codes = {code for code, _, _ in maximal}
    return next(iter(codes)) if len(codes) == 1 else None


_ROW_CODE = re.compile(r'(?m)^[ \t]*(?P<code>[A-Z]{2,5}\d{3,10})[ \t]*\([ \t]*(?P<credits>\d{1,2})[ \t]*\)[ \t]*(?P<inline>[^\n]*)$')
_GROUP_LINE = re.compile(r'^(?:chon|choose)\s*(?P<need>\d{1,2})\s*/\s*(?P<total>\d{1,2})\s*(?:tin\s*chi|credits?)\s*(?:sau|below)?\s*:\s*$')
_BRANCH_LINE = re.compile(r'^(?:neu|if)\s+(?P<neg>khong\s+)?(?:du\s+)?(?:dieu\s+kien|eligible)\b')
_QUESTION_BRANCH = re.compile(r'\b(?:neu|if)\s+(?P<neg>khong\s+)?(?:du\s+)?(?:dieu\s+kien|eligible)\b')


def _marker_lines(body, pattern):
    """Match headings on normalized lines while retaining source offsets."""
    markers = []
    offset = 0
    for line in body.splitlines(keepends=True):
        match = pattern.match(folded(line.strip()))
        if match:
            markers.append((offset, offset + len(line), match))
        offset += len(line)
    return markers


def _source_course_rows(result):
    """Read explicit code/credit/name rows from one retrieved source span."""
    from ..retrieval.tokenizer_vi import source_body
    body=source_body({'content':result.content},decode_tables=False)
    found=[]
    matches=list(_ROW_CODE.finditer(body))
    for index,match in enumerate(matches):
        end=matches[index+1].start() if index+1<len(matches) else len(body)
        inline=' '.join(match.group('inline').split())
        tail=body[match.end():end]
        # Course names may wrap in scanned/diagram text. Stop at explicit
        # semester/group/branch labels and keep only a few literal lines.
        lines=[]
        for line in tail.splitlines():
            clean=' '.join(line.split()).strip(' |\t')
            folded_line=folded(clean)
            if not clean or re.fullmatch(r'\d{1,3}',clean):
                continue
            if (re.search(r'\b(?:hk|hoc ky|semester)\s*\d+\b',folded_line)
                    or _GROUP_LINE.fullmatch(folded_line) or _BRANCH_LINE.match(folded_line)
                    or re.search(r'\b(?:tong hoc ky|semester total|tong cong)\b',folded_line)):
                break
            lines.append(clean)
            if len(lines)>=4:
                break
        name=' '.join([inline,*lines]).strip()
        name=re.sub(r'\s+', ' ', name)
        if not name:
            continue
        quote=body[match.start():match.end()]
        if lines:
            # Quote exactly through the final source-name line, including any
            # line breaks so locator validation remains tied to the PDF text.
            name_end=match.end()
            for line in lines:
                pos=body.find(line,name_end,end)
                if pos<0:break
                name_end=pos+len(line)
            quote=body[match.start():name_end].strip()
        found.append({'result':result,'code':match.group('code').upper(),
            'credits':int(match.group('credits')),'name':name,'quote':quote,
            'start':match.start(),'end':end})
    return body,found


def _answer_source_course_facts(facts, language, calibrator, *, condition=None):
    """Build citation-validated answers from literal course rows."""
    from .grounding import Citation, GroundedAnswer, validate_citation
    from .claims import Claim
    from .confidence import score_confidence
    grouped={}
    for fact in facts:
        grouped.setdefault(fact['result'].chunk_id,[]).append(fact)
    citations=[];results=[]
    for chunk_id,items in grouped.items():
        result=items[0]['result']
        if any(item['result'].doc_id!=result.doc_id for item in items):
            return None
        if len(items)==1:
            quote=items[0]['quote']
        else:
            body,_=_source_course_rows(result)
            first=min(items,key=lambda item:item['start'])
            last=max(items,key=lambda item:item['start']+len(item['quote']))
            quote=body[first['start']:last['start']+len(last['quote'])].strip()
        if not quote or len(quote)>1200:
            return None
        citation=Citation(result.chunk_id,result.doc_id,result.page,quote,
            ' > '.join(result.metadata.get('heading_path',[])),result.metadata.get('source_name',''),
            tuple(result.metadata.get('page_range',[result.page,result.page])),
            result.metadata.get('table_id',''),result.metadata.get('source_hash',''))
        if not validate_citation(citation,result,require_quote=True).valid:
            return None
        citations.append(citation);results.append(result)
    sentences=[];claims=[]
    for index,fact in enumerate(facts,1):
        if language.casefold().startswith('en'):
            sentence=f"{fact['code']} is {fact['name']} ({fact['credits']} credits)."
        else:
            sentence=f"{fact['code']} là {fact['name']} ({fact['credits']} tín chỉ)."
        if condition:
            sentence=f'{condition} {sentence}'
        sentences.append(sentence)
        chunk_id=fact['result'].chunk_id
        claims.append(Claim(str(index),sentence,'numeric_fact',1,(chunk_id,),
                            'supported',1.0,(chunk_id,),False))
    answer=' '.join(sentences)
    confidence=score_confidence(retrieval_support=max(0.,min(1.,max(float(r.score) for r in results))),
        claim_entailment=1.,citation_completeness=1.,calibrator=calibrator)
    return GroundedAnswer(answer=answer,citations=tuple(citations),confidence=confidence.label,
        abstained=False,claims=tuple(claims),evidence_status='found',confidence_score=confidence.score,
        raw_confidence_score=confidence.raw_score,policy_version=confidence.policy_version)


def deterministic_course_code_facts(question, results, language='vi', *, calibrator=None):
    """Resolve multiple explicitly named course codes from their literal source rows."""
    from ..retrieval.routing import detected_course_codes
    raw=question.partition(_CONTEXT)[0]
    codes=tuple(dict.fromkeys(code.upper() for code in detected_course_codes(raw)))
    if not codes or not results or len({r.doc_id for r in results})!=1:
        return None
    rows={code:[] for code in codes}
    for result in results:
        _body,found=_source_course_rows(result)
        for row in found:
            if row['code'] in rows:
                rows[row['code']].append(row)
    facts=[]
    for code in codes:
        values={(row['name'],row['credits']) for row in rows[code]}
        if len(values)!=1:
            return None
        name,credits=next(iter(values))
        candidates=[row for row in rows[code] if (row['name'],row['credits'])==(name,credits)]
        # Duplicate retrievals are harmless only when they quote the same
        # literal source row; prefer the highest-ranked verified occurrence.
        if len({row['result'].doc_id for row in candidates})!=1:
            return None
        row=max(candidates,key=lambda item:item['result'].score)
        facts.append({**row,'name':name,'credits':credits})
    return _answer_source_course_facts(facts,language,calibrator)


def deterministic_course_selection_group(question, results, language='vi', *, calibrator=None):
    """Answer course options only when a matching headed selection group is explicit."""
    raw=question.partition(_CONTEXT)[0]
    value=folded(raw)
    match=re.search(r'\b(?:nhom\s+)?(?:chon|choose)\s*(\d{1,2})\s*/\s*(\d{1,2})\b',value)
    if not match or not re.search(r'\b(?:m[o\u00f4]n|h[o\u1ecd]c ph[a\u1ea7]n|courses?|subjects?)\b',value):
        return None
    if not results or len({r.doc_id for r in results})!=1:
        return None
    topic=re.search(r'\b(?:thuoc phan|under|about|related to)\s+(.+)$',value)
    if not topic:
        return None
    requested_phrases=[part.strip(' .?!,:;') for part in re.split(r'[/,;]|\b(?:va|and|hoac|or)\b',topic.group(1))
                       if len(part.strip().split())>=2]
    if not requested_phrases:
        return None
    from ..retrieval.tokenizer_vi import requested_semesters
    semesters=requested_semesters(raw)
    groups=[]
    for result in results:
        body,rows=_source_course_rows(result)
        headings=_marker_lines(body,_GROUP_LINE)
        for i,heading in enumerate(headings):
            heading_start, heading_end, heading_match = heading
            if (int(heading_match.group('need'))!=int(match.group(1))
                    or int(heading_match.group('total'))!=int(match.group(2))):
                continue
            if semesters:
                explicit=list(re.finditer(r'\b(?:hk|hoc ky|semester)\s*(\d{1,2})\b',folded(body[:heading_start])))
                if not explicit or int(explicit[-1].group(1)) not in semesters:
                    continue
            end=headings[i+1][0] if i+1<len(headings) else len(body)
            total=re.search(r'(?im)^\s*(?:tong hoc ky|semester total)\b',body[heading_end:end])
            if total:
                end=heading_end+total.start()
            block_rows=[row for row in rows if heading_end<=row['start']<end]
            selected=[row for row in block_rows if any(phrase in folded(row['name']) for phrase in requested_phrases)]
            if selected:
                groups.append((result,heading_start,heading_end,body,end,selected))
    if len(groups)!=1:
        return None
    result,heading_start,heading_end,body,end,selected=groups[0]
    if len({(row['code'],row['credits'],row['name']) for row in selected})!=len(selected):
        return None
    if language.casefold().startswith('en'):
        sentence=f"The {match.group(1)}/{match.group(2)}-credit selection group includes " + ' or '.join(
            f"{r['code']} ({r['name']}, {r['credits']} credits)" for r in selected) + '.'
    else:
        sentence=f"Nhóm chọn {match.group(1)}/{match.group(2)} tín chỉ gồm các lựa chọn " + ' hoặc '.join(
            f"{r['code']} ({r['name']}, {r['credits']} tín chỉ)" for r in selected) + '.'
    from .grounding import Citation, GroundedAnswer, validate_citation
    from .confidence import score_confidence
    quote=body[heading_start:max(r['start']+len(r['quote']) for r in selected)].strip()
    citation=Citation(result.chunk_id,result.doc_id,result.page,quote,
        ' > '.join(result.metadata.get('heading_path',[])),result.metadata.get('source_name',''),
        tuple(result.metadata.get('page_range',[result.page,result.page])),
        result.metadata.get('table_id',''),result.metadata.get('source_hash',''))
    if not validate_citation(citation,result,require_quote=True).valid:
        return None
    confidence=score_confidence(retrieval_support=max(0.,min(1.,result.score)),claim_entailment=1.,
        citation_completeness=1.,calibrator=calibrator)
    from .claims import Claim
    claim=Claim('course-selection-group',quote,'numeric_fact',1,(result.chunk_id,),
        'supported',1.0,(result.chunk_id,),False)
    return GroundedAnswer(answer=sentence,citations=(citation,),confidence=confidence.label,
        abstained=False,claims=(claim,),evidence_status='found',confidence_score=confidence.score,
        raw_confidence_score=confidence.raw_score,policy_version=confidence.policy_version)


def deterministic_conditional_course_lookup(question, results, language='vi', *, calibrator=None):
    """Resolve a course branch only from an explicit source condition marker."""
    raw=question.partition(_CONTEXT)[0];value=folded(raw)
    if not re.search(r'\b(?:hoc phan|mon|course)\b',value) or not re.search(r'\b(?:bao nhieu|may|how many)\b.*\b(?:tin chi|tin|tc|credits?)\b',value):
        return None
    qbranch=_QUESTION_BRANCH.search(folded(raw))
    if not qbranch or not results or len({r.doc_id for r in results})!=1:
        return None
    wants_negative=bool(qbranch.group('neg'))
    candidates=[]
    for result in results:
        body,rows=_source_course_rows(result)
        markers=_marker_lines(body,_BRANCH_LINE)
        for marker_index,marker in enumerate(markers):
            marker_start,marker_end,marker_match=marker
            if bool(marker_match.group('neg'))!=wants_negative:
                continue
            previous_marker=markers[marker_index-1][1] if marker_index else 0
            next_marker=markers[marker_index+1][0] if marker_index+1<len(markers) else len(body)
            following=[row for row in rows if marker_end<=row['start']<next_marker]
            attached=[row for row in rows if row['start']<marker_start<row['end']]
            preceding=[row for row in rows if previous_marker<=row['start']<marker_start]
            if wants_negative:
                selected=following or preceding
            else:
                selected=attached or following
            for row in selected:
                if wants_negative and not following:
                    quote_start=previous_marker
                    quote_end=marker_end
                else:
                    quote_start=min(marker_start,row['start'])
                    quote_end=max(marker_end,row['start']+len(row['quote']))
                candidates.append({**row,'start':quote_start,
                    'quote':body[quote_start:quote_end].strip()})
    unique={(r['result'].doc_id,r['code'],r['credits'],r['name']):r for r in candidates}
    facts=list(unique.values())
    if not facts:
        return None
    # A conditional branch resolving to several different rows is safe only
    # when the user asks for plural courses; otherwise keep model/clarification.
    if len(facts)>1 and not re.search(r'\b(?:which courses|what courses|which course|what course|mon nao|hoc phan nao|nhung mon|nhung hoc phan)\b',value):
        return None
    condition=('If not eligible,' if wants_negative else 'If eligible,') if language.casefold().startswith('en') else (
        'Nếu không đủ điều kiện,' if wants_negative else 'Nếu đủ điều kiện,')
    return _answer_source_course_facts(facts,language,calibrator,condition=condition)


def deterministic_course_lookup(question, results, language='vi', *, calibrator=None):
    request = _request(question)
    docs = {r.doc_id for r in results}
    if request is None or len(docs) != 1:
        return None
    fields, name, topic = request
    code = _target(results, name, topic)
    if not code:
        return None
    premise = find_premise(results, next(iter(docs)), code=code,
                           require_credits='credits' in fields)
    if premise is None:
        return None
    bridges = prerequisite_codes(premise) if 'prerequisites' in fields else ()
    if 'prerequisites' in fields and not bridges:
        return None
    english = language.casefold().startswith('en')
    facts = []
    if 'credits' in fields:
        facts.append(f'Course {code} has {premise.credits} credits.' if english else
                     f'Môn {code} có {premise.credits} tín chỉ.')
    facts.extend(f'Course {bridge} is a prerequisite of course {code}.' if english else
                 f'Môn {bridge} là môn tiên quyết của môn {code}.' for bridge in bridges)
    from .grounding import Citation, _grounding_finalize, validate_citation
    result = premise.result
    citation = Citation(result.chunk_id, result.doc_id, result.page,
        json.dumps(list(premise.row), ensure_ascii=False),
        ' > '.join(result.metadata.get('heading_path', [])), result.metadata.get('source_name', ''),
        tuple(result.metadata.get('page_range', [result.page, result.page])),
        result.metadata.get('table_id', ''), result.metadata.get('source_hash', ''))
    if len(citation.quote) > 1200 or not validate_citation(citation, result, require_quote=True).valid:
        return None
    claims = [{'claim_id': str(i), 'text': fact, 'citation_ids': [result.chunk_id]}
              for i, fact in enumerate(facts, 1)]
    answer = _grounding_finalize(' '.join(facts), (citation,), {'claims': claims},
                                [result], language, question=question, calibrator=calibrator)
    return answer if not answer.abstained else None
