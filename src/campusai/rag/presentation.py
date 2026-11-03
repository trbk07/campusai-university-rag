"""Reject exact contradictions between visible output and supported claim records.

This is a bounded marker check, not a semantic entailment model. It preserves
cross-language prose while checking numbers, course IDs, units and directly
opposed wording. List labels and display citation numbers are not factual values.
"""
from collections import defaultdict
import json
from decimal import Decimal
from datetime import date
import re
import unicodedata

from .claims import CODE_RE, normalize_text
from .course_credits import COURSE_CODE, course_code_key

NUMBER = re.compile(r'(?<!\w)\d+(?:[.,]\d+)?')
UNIT = re.compile(r'(?<!\w)(\d+(?:[.,]\d+)?)\s*(%|percent\b|phan tram\b|credits?\b|tin chi\b|tc\b|vnd\b|usd\b|dollars?\b|dong\b)')
NEGATION = re.compile(r'\b(?:not|khong)\b')
COURSE_MARKER = re.compile(r'(?<!\w)' + COURSE_CODE + r'(?!\w)', re.I)
LOCATION_VALUE = r'[0-9]+(?:\.[0-9]+)*(?:\([a-z]\))?'
LOCATION = re.compile(r'\b(article|dieu|section|muc|chapter|chuong|page|trang)\s+('+LOCATION_VALUE+r')(?![\w(]|\.\d)')
VISIBLE_LOCATION = re.compile(r'\b(article|điều|dieu|section|mục|muc|chapter|chương|chuong|page|trang)\s+('+LOCATION_VALUE+r')(?![\w(]|\.\d)',re.I)
SEMESTER_LOCATION = re.compile(r'\b(?:semester|(?:học\s+)?k[ỳì]|(?:hoc\s+)?k[yi])\s*'
                               r'(?:(?:thứ|thu)\s*)?(\d{1,2})\b',re.I)
CALENDAR_DATE = re.compile(r'(?<!\w)(?:(\d{4})-(\d{1,2})-(\d{1,2})|(\d{1,2})/(\d{1,2})/(\d{4}))(?!\w)')
CLOCK_TIME = re.compile(r'(?<!\w)([0-9]{1,2})(?::|h)([0-9]{2})(?!\w)', re.I)
MONTHS = {name: index for index, name in enumerate(('january','february','march','april','may',
    'june','july','august','september','october','november','december'), 1)}
NAMED_DATE = re.compile(r'\b('+'|'.join(MONTHS)+r')\s+(\d{1,2}),?\s+(\d{4})\b|'
    r'\b(\d{1,2})\s+('+'|'.join(MONTHS)+r')\s+(\d{4})\b', re.I)
VIETNAMESE_DATE = re.compile(r'\b(?:ngày|ngay)\s+(\d{1,2})\s+'
    r'(?:tháng|thang)\s+(\d{1,2})\s+(?:năm|nam)\s+(\d{4})\b', re.I)


def calendar_presentation(text):
    """Canonicalize valid, explicit whole dates/times, retaining their identity."""
    markers = set()
    def dated(year, month, day, original):
        try: value = date(int(year), int(month), int(day)).isoformat()
        except ValueError:
            markers.add(('invalid_date', original.casefold()))
            return original
        markers.add(('date', value))
        return value
    def numeric(match):
        y,m,d,day,month,year=match.groups()
        return dated(y or year, m or month, d or day, match[0])
    def named(match):
        month,day,year,d,m,y=match.groups()
        return dated(year or y, MONTHS[(month or m).casefold()], day or d, match[0])
    def vietnamese(match):
        day,month,year=match.groups()
        return dated(year,month,day,match[0])
    def clock(match):
        hour,minute=map(int,match.groups())
        if hour > 23 or minute > 59:
            markers.add(('invalid_time', match[0].casefold()))
            return match[0]
        value=f'{hour:02d}:{minute:02d}'
        markers.add(('time',value))
        return value
    text=unicodedata.normalize('NFC',text)
    text=VIETNAMESE_DATE.sub(vietnamese,text)
    text=CALENDAR_DATE.sub(numeric,text)
    text=NAMED_DATE.sub(named,text)
    return CLOCK_TIME.sub(clock,text),markers


def location_key(kind, value):
    return ({'dieu':'article','muc':'section','chuong':'chapter','trang':'page'}.get(kind,kind),value)


def location_proofs(citations, registry):
    """Actual cited page and explicit source headings, not arbitrary numbers."""
    from ..retrieval.tokenizer_vi import source_body
    proven=set()
    for citation in citations:
        proven.add(('page',str(citation.page)))
        record=registry.get(citation.chunk_id)
        if record is None:continue
        body=source_body({'content':record.content},decode_tables=False)
        for line in body.splitlines():
            match=LOCATION.match(folded(line))
            if match:proven.add(location_key(*match.groups()))
        if record.content_type=='table':
            try:
                quoted=json.loads(citation.quote)
                source=json.loads(body[body.index('{"headers"'):])
            except (ValueError,TypeError):
                continue
            selected=(quoted.get('rows',[]) if isinstance(quoted,dict) else
                      [quoted] if isinstance(quoted,list) and all(isinstance(c,str) for c in quoted) else quoted)
            if not isinstance(selected,list):continue
            # These quotes have already passed the citation/row validator.
            # Only selected literal markers or an explicit semester-column
            # cell prove a location; unrelated source rows cannot supply it.
            columns=[i for i,h in enumerate(source.get('headers',[])) if isinstance(h,str)
                     and ' '.join(folded(h).split()) in {'semester','term','hoc ky'}]
            for row in selected:
                if not isinstance(row,list) or any(not isinstance(c,str) for c in row):continue
                cells=[c.strip() for c in row if c.strip()]
                marker=SEMESTER_LOCATION.fullmatch(cells[0]) if len(cells)==1 else None
                if marker:proven.add(('semester',str(int(marker[1]))))
                if len(columns)==1 and len(row)>columns[0] and re.fullmatch(r'[0-9]{1,2}',row[columns[0]]):
                    proven.add(('semester',str(int(row[columns[0]]))))
            if isinstance(quoted,dict) and isinstance(quoted.get('scope'),str):
                marker=SEMESTER_LOCATION.fullmatch(quoted['scope'])
                if marker and any(line.strip()=='Table scope: '+quoted['scope'] for line in record.content.splitlines()):
                    proven.add(('semester',str(int(marker[1]))))
    return proven


def folded(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.casefold())
                   if not unicodedata.combining(c)).replace('đ', 'd')


def number(value):
    return Decimal(value.replace(',', '.'))


def prose(text):
    text = re.sub(r'^\s*\d+[.)]\s+', '', text, flags=re.M)
    return re.sub(r'\[\d+\]', '', text)


def quantities(text):
    result = defaultdict(set)
    for value, unit in UNIT.findall(folded(text)):
        unit = ('credits' if unit in {'credit', 'credits', 'tin chi', 'tc'} else
                'percent' if unit in {'%', 'percent', 'phan tram'} else
                'vnd' if unit in {'dong', 'vnd'} else 'usd')
        result[number(value)].add(unit)
    # A printed range shares its explicit trailing unit with both bounds.
    # Do not infer intermediate values or propagate another occurrence's unit.
    ranged=r'(?<!\w)(\d+(?:[.,]\d+)?)\s*(?:[-–—÷]|\bden\b|\bto\b)\s*'+UNIT.pattern
    for lower,upper,unit in re.findall(ranged,folded(text)):
        result[number(lower)].update(quantities(upper+' '+unit)[number(upper)])
    return result


def aggregate_period_conflict(answer, quotes):
    """An annual multi-term total cannot become one term's duration.

    Read the period and quantity from the actual citation, not the model's
    potentially truncated claim. This is a bounded veto, not division or a
    guessed per-term minimum. Unrecognized wording keeps ordinary validation.
    """
    term = r'(?:hoc\s+k[yi](?:\s+chinh)?|semester|term)'
    unit = r'(?:tuan|weeks?|ngay|days?|gio|hours?)'
    total = (r'(?:mot\s+nam\s+hoc|(?:an?\s+)?(?:academic|school)\s+year)'
             r'[^.!?;]{0,60}?\b(?:0?[2-9]|two|three|four)\s+' + term + r's?\b'
             r'[^.!?;]{0,60}?\b(?:tong\s+so|tong|total(?:ing)?)\b'
             r'[^.!?;]{0,40}?(?P<value>\d+(?:[.,]\d+)?)\s*(?P<unit>' + unit + r')\b')
    aliases = {'tuan': 'week', 'weeks': 'week', 'ngay': 'day', 'days': 'day',
               'gio': 'hour', 'hours': 'hour'}
    totals = set(); direct = set()
    for quote in quotes:
        normalized = ' '.join(folded(quote).split())
        for match in re.finditer(total, normalized):
            totals.add((number(match['value']), aliases.get(match['unit'], match['unit'])))
        for clause in re.split(r'[.!?;]\s+', normalized):
            if (re.search(r'\b(?:moi|mot|each|every|a|one)\s+'+term+r'\b',clause)
                    and not re.search(r'\b(?:tong|total|nam hoc|academic year|school year)\b',clause)):
                for match in re.finditer(r'(\d+(?:[.,]\d+)?)\s*('+unit+r')\b',clause):
                    direct.add((number(match[1]), aliases.get(match[2], match[2])))
    for clause in re.split(r'[.!?;]\s+|\n+', folded(answer)):
        if (not re.search(r'\b' + term + r'\b', clause)
                or re.search(r'\b(?:tong|total|nam\s+hoc|academic\s+year|school\s+year)\b', clause)
                or re.search(r'\b(?:0?[2-9]|two|three|four)\s+' + term, clause)):
            continue
        for match in re.finditer(r'(?P<value>\d+(?:[.,]\d+)?)\s*(?P<unit>' + unit + r')\b', clause):
            if (number(match['value']), aliases.get(match['unit'], match['unit'])) in totals-direct:
                return True
    return False


def per_term_duration_guidance(language):
    return ('The retrieved passages give a combined duration for multiple terms, not a '
            'minimum duration for each term. Please provide the rule for individual terms '
            'or point to its section/page.' if language.startswith('en') else
            'Các đoạn đã truy hồi nêu tổng thời lượng nhiều học kỳ, chưa đủ căn cứ xác định '
            'thời lượng tối thiểu của từng kỳ. Bạn hãy chỉ rõ mục/trang quy định cho từng kỳ '
            'hoặc bổ sung nguồn phù hợp.')


def missing_per_term_duration(question, answer, quotes):
    """A verified annual total alone does not answer a per-term duration query."""
    term=r'(?:hoc\s+k[yi](?:\s+chinh)?|semester|term)'
    duration=r'(?:tuan|weeks?|ngay|days?|gio|hours?)'
    query=' '.join(folded(question).split())
    if (not re.search(r'\b'+term+r'\b',query)
            or not re.search(r'\b'+duration+r'\b',query)
            or not re.search(r'\b(?:bao nhieu|keo dai|how (?:many|long)|duration|length)\b',query)
            or re.search(r'\b(?:tong|total|nam hoc|academic year|school year)\b',query)
            or re.search(r'\b(?:0?[2-9]|two|three|four)\s+'+term,query)):
        return False
    units=[pattern for pattern in (r'(?:tuan|weeks?)',r'(?:ngay|days?)',r'(?:gio|hours?)')
           if re.search(r'\b'+pattern+r'\b',query)]
    if len(units)!=1:
        return False
    duration=units[0]
    # Use the existing total/individual distinction. Re-labelling a sentinel
    # individual statement exposes only totals actually printed in the quotes.
    totals=[]
    for quote in quotes:
        for match in re.finditer(r'(\d+(?:[.,]\d+)?)\s*('+duration+r')\b',folded(quote)):
            if aggregate_period_conflict('semester '+match[1]+' '+match[2], [quote]):
                totals.append(quote)
                break
    if not totals:
        return False
    # An explicit individual-period statement in either the visible answer
    # or a cited source stays on ordinary grounding. Do not infer equal terms.
    for text in [answer,*quotes]:
        for clause in re.split(r'[.!?;]\s+|\n+', ' '.join(folded(text).split())):
            if (re.search(r'\b'+term+r'\b',clause)
                    and re.search(r'\d+(?:[.,]\d+)?\s*'+duration+r'\b',clause)
                    and not re.search(r'\b(?:tong|total|nam hoc|academic year|school year)\b',clause)
                    and not re.search(r'\b(?:0?[2-9]|two|three|four)\s+'+term,clause)):
                return False
    return True


_SCOPE_CUES = re.compile(
    r"\b(?:admission|cohort|intake|academic year|school year|curriculum|programme|program|"
    r"issued|published|effective|version|regulations?|policy|quy che|quy dinh|ban hanh|nam hoc|khoa tuyen sinh|khoa|ap dung|"
    r"dieu chinh|cap nhat|so tay|handbook)\b",
    re.I,
)
_SCOPE_CUES_AFTER = re.compile(
    r"^\s*(?:curriculum|programme|program|academic year|school year|"
    r"regulations?|policy|(?:(?:undergraduate|graduate|postgraduate)\s+)?admissions?\s+(?:notice|plan|quota|intake|regulations?))\b",
    re.I,
)
_VERIFICATION_QUESTION = re.compile(
    r"\b(?:is that correct|is this correct|is that right|is this right|am i right|"
    r"co dung khong|dung khong|co chinh xac khong)\b",
    re.I,
)
_AFFIRMATIVE = re.compile(r"^\s*(?:yes|correct|that is correct|that's correct|đúng|chính xác)\b", re.I)
_NEGATIVE_CORRECTION = re.compile(r"\b(?:no|not correct|incorrect|không đúng|sai)\b", re.I)
_QUESTION_SCOPE_NUMBER = re.compile(
    r"\b(admission\s+cohort|cohort|semester|term|article|dieu|điều|section|muc|mục|mức|chapter|chuong|chương|page|trang)\s+("+LOCATION_VALUE+r")(?![\w(]|\.\d)",
    re.I,
)


def _scoped_years(text):
    """Return only years explicitly used as document/cohort scope labels."""
    normalized = folded(normalize_text(str(text or "")))
    years = set()
    for match in re.finditer(r"(?<![\w/.-])(?:19|20)\d{2}(?![\w/-])", normalized):
        if re.match(r"\.\d{1,2}[.-]\d{1,2}(?!\d)", normalized[match.end():]):
            continue
        prefix = normalized[max(0, match.start() - 64):match.start()]
        suffix = normalized[match.end():match.end() + 32]
        if _SCOPE_CUES.search(prefix) or _SCOPE_CUES_AFTER.search(suffix):
            years.add(int(match[0]))
    return years


def _scope_number_key(label, value):
    label = folded(normalize_text(label)).replace(" ", " ")
    if label == "admission cohort":
        label = "cohort"
    if label == "term":
        label = "semester"
    if label in {'article', 'dieu', 'section', 'muc', 'chapter', 'chuong', 'page', 'trang'}:
        label = location_key(label, value)[0]
    return label, re.sub(r'\d+', lambda match: str(int(match[0])), value.casefold())


def _question_scope_numbers(text):
    normalized = folded(normalize_text(str(text or "")))
    return {_scope_number_key(match[1], match[2]) for match in _QUESTION_SCOPE_NUMBER.finditer(normalized)}


def _affirmative_disagrees_with_review_value(question, answer, support):
    """Reject a confident yes when a reviewed credit value disproves the premise."""
    normalized_question = normalize_text(str(question or ""))
    normalized_answer = normalize_text(str(answer or ""))
    if (not _VERIFICATION_QUESTION.search(normalized_question)
            or not _AFFIRMATIVE.search(normalized_answer)
            or _NEGATIVE_CORRECTION.search(normalized_answer)):
        return False
    premise = quantities(normalized_question)
    reviewed = quantities(support)
    for value, units in premise.items():
        for unit in units:
            reviewed_values = {candidate for candidate, candidate_units in reviewed.items()
                               if unit in candidate_units}
            if reviewed_values and value not in reviewed_values:
                return True
    return False


def canonical_code_spacing(text, compact_anchors):
    """Normalize source-style codes without merging ordinary words and numbers."""
    def replace(match):
        value = match[0]
        key = course_code_key(value)
        prefix = re.split(r'\d', value, maxsplit=1)[0].strip()
        explicit = re.search(r'\b(?:course|code|mon|hoc phan)\s*$', folded(text[:match.start()]))
        if not re.search(r'\s', value) or prefix.isupper() or key.casefold() in compact_anchors or explicit:
            return key
        return value
    return COURSE_MARKER.sub(replace, text)


def code_markers(text):
    # Retain complete dotted namespaces as well as the existing broad compact IDs.
    return {code.casefold() for code in CODE_RE.findall(text)} | {
        course_code_key(m[0]).casefold() for m in COURSE_MARKER.finditer(text) if not re.search(r'\s', m[0])}


def omit_unverified_context(answer,claims,question):
    """Remove optional scope decorations, never an answer value or condition."""
    support='\n'.join(c.text for c in claims if c.status=='supported')
    scales=set(re.findall(r'\b(?:thang(?: diem)?|diem he|scale)\s+(\d+)\b',folded(support)))
    answer=re.sub(r'\(\s*(?:thang(?: điểm)?|hệ|scale)\s+(\d+)\s*\)',
        lambda m:m[0] if m[1] in scales else '',answer,flags=re.I)
    # A document number supplied as context is not the requested cohort/date.
    # If it is not source-proved, omit the repeated number rather than publish
    # it as a verified identifier. Identity/yes-no questions remain fail-closed.
    q=folded(str(question or ''))
    if (re.search(r'\b(?:quy doi|diem chu|letter grade)\b',q)
            and re.search(r'\b[ABCDF][+-]?\s+quy đổi\s+thành\s+\d',support)):
        # Omit only a trailing decoration after a proved grade mapping.
        # Converted values, units and explicitly requested scale labels stay.
        asked=set(re.findall(r'\b(?:thang(?: diem)?|diem he|scale)\s+(\d+)\b',q))
        answer=re.sub(r'(?:theo\s+)?thang(?:\s+điểm)?\s+(\d+)(?=\s*[.!?;]*$)',
            lambda m:m[0] if m[1] in scales|asked else '',answer,flags=re.I)
    identity_question=re.search(r'\b(?:so (?:may|nao)|ma (?:gi|nao)|what number|which identifier)\b|'
                                r'\b(?:khong|ko|correct|right)\s*[?!.]*$',q)
    if not identity_question:
        scope=re.compile(r'^(?P<label>(?:(?:Theo|According to)\s+)?(?:Quy chế|Quyết định|Tài liệu|Văn bản|Regulation|Decision|Document)\s+(?:số\s+)?)(?P<id>\d{2,6})(?=\s|[,;:])',re.I)
        m=scope.search(answer)
        if m and re.search(r'(?<!\w)'+re.escape(m['id'])+r'(?!\w)',q) and number(m['id']) not in {number(v) for v in NUMBER.findall(support)}:
            answer=answer[:m.start('id')]+answer[m.end('id'):]
    return re.sub(r'\s+([.!?,;])',r'\1',re.sub(r'[ \t]{2,}',' ',answer)).strip()


def _threshold_premise_view(answer, supported, question):
    """Prove a repeated credit premise against one literal strict lower bound.

    Output values remain claim-checked. Multiple bounds, different units,
    negative decisions and an input outside the source condition stay strict.
    """
    if len(supported)!=1:
        return answer
    rule=folded(supported[0])
    if len(NUMBER.findall(rule))!=1:
        return answer
    # A negative decision for an input above an explicit cap/deadline is a
    # literal numeric comparison. It cannot whitelist an output amount or a
    # premise in a different unit.
    families=[(r'(?:tin(?: chi)?|tc|credits?)',r'(?:tín(?: chỉ)?|tc|credits?)'),
              (r'(?:ngay|days?)',r'(?:ngày|days?)')]
    maximum=re.search(r'\b(?:toi da|at most|maximum(?: of)?|thoi han|within)\s+(\d+(?:[.,]\d+)?)',rule)
    if maximum:
        for query_unit,visible_unit in families:
            if not re.search(r'\b'+query_unit+r'\b',rule):
                continue
            values={number(m[1]) for m in re.finditer(r'(?<![\w.,])(\d+(?:[.,]\d+)?)\s*'+query_unit+r'\b',folded(str(question or '')))}
            if len(values)!=1 or next(iter(values))<=number(maximum[1]):
                continue
            value=next(iter(values))
            def negative_clause(match):
                clause=match[0]
                if re.search(r'\b(?:ma|nhung|but|however|instead)\b',folded(clause)):
                    return clause
                return re.sub(r'(?<![\w.,])(\d+(?:[.,]\d+)?)(?=\s*'+visible_unit+r'\b)',
                    lambda m:' ' if number(m[1])==value else m[0],clause,flags=re.I)
            return re.sub(r'\b(?:không\s+(?:thể|được|kịp|còn(?:\s+kịp)?)|cannot|may not|no)\b[^.!?;\n]{0,200}',
                          negative_clause,answer,flags=re.I)
    if re.match(r'^\s*(?:khong|no|not)\b',folded(answer)):
        return answer
    thresholds=list(re.finditer(r'\b(?:lon hon|greater than)\s+('+r'\d+(?:[.,]\d+)?'+r')(?!\w)',rule))
    if len(thresholds)!=1 or not re.search(r'\b(?:tc|tin chi|credits?)\b',rule):
        return answer
    outcome=re.split(r'\b(?:doi voi|when|if)\b',rule,maxsplit=1)
    if len(outcome)!=2 or not 3<=len(outcome[0].split())<=16 or outcome[0].strip() not in folded(answer):
        return answer
    unit=r'(?:tin(?: chi)?|tc|credits?)'
    values={number(m[1]) for m in re.finditer(r'(?<![\w.,])('+r'\d+(?:[.,]\d+)?'+r')\s*'+unit+r'\b',folded(str(question or '')))}
    if len(values)!=1 or next(iter(values))<=number(thresholds[0][1]):
        return answer
    value=next(iter(values))
    return re.sub(r'(?<![\w.,])(\d+(?:[.,]\d+)?)(?=\s*(?:tín(?: chỉ)?|tc|credits?)\b)',
        lambda m:' ' if number(m[1])==value else m[0],answer,flags=re.I)


def institution_names_supported(answer, results):
    """An acronym does not license an invented expanded university name."""
    from ..retrieval.tokenizer_vi import source_body
    # The institution is source-derived document provenance. Its printed
    # heading may be on another page than the cited policy paragraph. Never
    # expand an acronym, or use a filename/programme as identity evidence.
    evidence=[]
    for result in results:
        evidence.append(source_body({'content':result.content}))
        institution=result.metadata.get('institution')
        if isinstance(institution,str):evidence.append(institution)
    allowed=' '.join(folded('\n'.join(evidence)).split())
    prefixes=list(re.finditer(r'\b(?:Trường\s+)?Đại\s+học\s+',answer,re.I))
    for i,match in enumerate(prefixes):
        end=prefixes[i+1].start() if i+1<len(prefixes) else len(answer)
        tail=re.split(r'[\n,.;:()]',answer[match.end():min(end,match.end()+120)],maxsplit=1)[0].strip()
        if not tail or not tail[0].isupper():continue
        name=re.split(r'\s+(?:có|được|không|theo|trong|sẽ|tại|là|với|đã|áp dụng|giới hạn|'
                      r'quy định|cho phép|yêu cầu|quy đổi|tổ chức|đăng ký|thực hiện|'
                      r'dành cho|cung cấp|học kỳ|học kì|sinh viên)\b',
                      tail,maxsplit=1,flags=re.I)[0]
        name=re.sub(r'\s+và\s*$','',name,flags=re.I).strip()
        if not re.search(r'(?<!\w)'+re.escape('dai hoc '+' '.join(folded(name).split()))+r'(?!\w)',allowed):return False
    return True


def source_ownership_conflicts(answer, claims, citations, results, question=''):
    """Veto simple scalar facts borrowed from a different cited source.

    Resolve labels from actual filenames and source-derived institution names,
    never a list of schools. Only forward, explicit subject/value assertions
    are checked. Joint calculations keep their existing multi-source proof.
    """
    from ..retrieval.institution_scope import _references
    by_id={citation.chunk_id:citation for citation in citations}
    texts={}
    for claim in claims:
        if claim.status!='supported':continue
        owners={by_id[i].doc_id for i in claim.citation_ids if i in by_id}
        if len(owners)>1:return False
        if owners:texts.setdefault(next(iter(owners)),[]).append(claim.text)
    documents={doc:{'doc_id':doc,'items':[]} for doc in texts}
    labels={}
    for result in results:
        if result.doc_id in documents:
            documents[result.doc_id]['items'].append({'page':result.page,'content':result.content,'metadata':result.metadata})
    for citation in citations:
        if citation.source_name:labels.setdefault(folded(citation.source_name),set()).add(citation.doc_id)
    allowed={doc:quantities('\n'.join(parts)) for doc,parts in texts.items()}
    view=_threshold_premise_view(answer,[c.text for c in claims if c.status=='supported'],question)
    for clause in re.split(r'[;!?\n]+|\.(?:\s+|$)',view):
        value=folded(clause);words=list(re.finditer(r'\w+',value));mentions=[]
        refs=_references(clause,list(documents.values()))
        for index,word in enumerate(words):
            candidates=[(word[0],word.start(),word.end())]
            if index+1<len(words):candidates.append((word[0]+words[index+1][0],word.start(),words[index+1].end()))
            for key,start,end in candidates:
                if len(owners:=refs.get(key,()))==1:mentions.append((start,end,next(iter(owners))))
        for label,owners in labels.items():
            if len(owners)==1:
                mentions.extend((m.start(),m.end(),next(iter(owners))) for m in re.finditer(re.escape(label),value))
        merged=[]
        for start,end,owner in sorted(set(mentions)):
            if merged and start<merged[-1][1] and owner!=merged[-1][2]:
                merged=[];break  # Ambiguous overlapping labels do not prove ownership.
            if (merged and owner==merged[-1][2]
                    and (start<=merged[-1][1] or re.fullmatch(r'[\s(),/-]*',value[merged[-1][1]:start]))):
                merged[-1]=(merged[-1][0],max(end,merged[-1][1]),owner)
            else:merged.append((start,end,owner))
        for index,(_start,end,owner) in enumerate(merged):
            segment=value[end:merged[index+1][0] if index+1<len(merged) else len(value)]
            first=UNIT.search(segment)
            if not first or not re.search(r'[:=]|\b(?:co|la|duoc|phi|gioi han|toi da|toi thieu|'
                                          r'ap dung|dang k[yi]|has|have|is|are|allows?)\b',segment[:first.start()]):
                continue
            if any(not units<=allowed.get(owner,{}).get(number,set()) for number,units in quantities(segment).items()):
                return True
    return False


MATERIAL_CONDITION = re.compile(r'\b(?:ngoai tru|tru (?:sinh vien|nguoi|truong hop|hoc k[yi]|nam|khi)|'
    r'khong ap dung|chi (?:ap dung|khi|duoc|danh)|som nhat|cham nhat|'
    r'ke tu|tinh tu|voi dieu kien|provided that|except|unless|only if|'
    r'this (?:rule |condition )?does not apply|does not apply|'
    r'no (?:earlier|later) than|at (?:the )?earliest)\b')


def restore_claim_conditions(claims, citations):
    """Keep a literal cited clause's immediate qualifier before re-verifying it.

    A provider can truncate both its summary and its diagnostic claim. Extend
    only an exact claim substring followed directly by a condition in the
    already validated quote, never another sentence or an uncited paragraph.
    The caller must align and validate the resulting claims normally.
    """
    from dataclasses import replace
    by_id={citation.chunk_id:citation for citation in citations}
    restored=[]
    for claim in claims:
        refs=[by_id[ident] for ident in claim.citation_ids if ident in by_id]
        candidates=set()
        core=' '.join(claim.text.split()).rstrip(' .;')
        if len(core.split())>=5 and refs and len({ref.doc_id for ref in refs})==1:
            for ref in refs:
                quote=' '.join(ref.quote.split())
                for match in re.finditer(r'(?<!\w)'+re.escape(core)+r'(?!\w)',quote,re.I):
                    tail=quote[match.end():]
                    condition=MATERIAL_CONDITION.match(folded(tail.lstrip(' ,(:')))
                    if not condition:
                        separator=re.match(r'^\.\s+',tail)
                        if separator:
                            from .source_citations import attached_exception_end
                            begin=match.end()+separator.end()
                            end=attached_exception_end(quote,begin,core)
                            if end>begin:candidates.add(quote[match.start():end].strip())
                        continue
                    # Sentence stops exclude decimal punctuation. A directly
                    # attached parenthesis or comma condition stays in place.
                    boundary=re.search(r'[;!?]|\.(?:\s+|$)',tail)
                    end=match.end()+(boundary.end() if boundary else len(tail))
                    full=quote[match.start():end].strip()
                    if len(full)<=1200:
                        candidates.add(full)
        restored.append(replace(claim,text=next(iter(candidates))) if len(candidates)==1 else claim)
    return restored


def complete_material_conditions(answer, claims, citations, language='vi'):
    """Expose an already-proved condition dropped from an otherwise valid summary.

    Never add a new claim or borrow facts from an uncited paragraph. Numeric
    grids and unrelated diagnostic claims do not match a prose action anchor.
    Source labels keep a multi-document note attached to its actual evidence.
    """
    stop=set(('a an the of to for and or in is are be with as '
              'la va cua cho cac nhung mot duoc theo trong tai co da thi quy che nay dinh').split())
    exclusion=re.compile(r'\b(?:khong ap dung|ngoai tru|(?:this (?:rule |condition )?)?does not apply|except)\b')
    def words(text):
        text=folded(text)
        text=exclusion.sub('__exception__',text)
        # Legal cross-references are not the action being summarized. The
        # separate numeric coverage check still protects condition quantities.
        text=re.sub(r'\b(?:khoan|dieu|muc|chuong|clause|article|section)\s+\d+(?:[.]\d+)*\b',' ',text)
        text=NUMBER.sub(lambda m:format(number(m[0]),'f').rstrip('0').rstrip('.')
            if '.' in format(number(m[0]),'f') else str(number(m[0])),text)
        return set(re.findall(r'\w+',text))-stop
    clauses=re.split(r'[!?;\n]+|\.(?:\s+|$)',answer)
    by_id={citation.chunk_id:citation for citation in citations}
    additions=[];seen=set()
    for claim in claims:
        if claim.status!='supported' or not claim.citation_ids:
            continue
        refs=[by_id[ident] for ident in claim.citation_ids if ident in by_id]
        if not refs or len({ref.doc_id for ref in refs})!=1:
            continue
        text=claim.text;normalized=folded(text)
        for match in MATERIAL_CONDITION.finditer(normalized):
            anchor=words(normalized[:match.start()])
            if len(anchor)<4:
                continue
            matching=[]
            for index,part in enumerate(clauses):
                if len(anchor & words(part))/len(anchor)<.7:continue
                matching.append(part)
                if index+1<len(clauses) and exclusion.match(folded(clauses[index+1]).lstrip()):
                    matching.append(part+' '+clauses[index+1])
            if not matching:
                continue
            condition=words(normalized[match.start():])
            def covers(part):
                available=words(part)
                numbers={number(v) for v in NUMBER.findall(normalized[match.start():])}
                return (numbers <= {number(v) for v in NUMBER.findall(part)}
                    and all(neg not in condition or neg in available for neg in ('khong','not','__exception__'))
                    and len(condition & available)/max(1,len(condition))>=.8)
            if not any(covers(part) for part in matching):
                key=(refs[0].doc_id,' '.join(normalized.split()))
                if key not in seen:
                    label=' '.join(refs[0].source_name.split())
                    prefix=('Condition in '+label if language.startswith('en') else 'Điều kiện trong '+label) if label else (
                        'Source condition' if language.startswith('en') else 'Điều kiện theo nguồn')
                    additions.append(prefix+': '+' '.join(text.split()))
                    seen.add(key)
                break
    return answer+('\n\n'+'\n'.join(additions) if additions else '')


def presentation_conflicts(answer, claims, *, locations=(), question=None, source_scope_codes=()):
    """Only supported claims supply allowable visible markers, not random source numbers."""
    supported = [claim.text for claim in claims if claim.status == 'supported']
    if not supported:
        return True
    visible = prose(answer)
    from .numeric_inference import gpa_application_view, percentage_application_view
    for proof in (gpa_application_view, percentage_application_view):
        applied=proof(visible,supported,question)
        if applied is False:return True
        if isinstance(applied,str):visible=applied
    visible = _threshold_premise_view(visible,supported,question)
    # A requested scale label is context, not an extra output quantity. Mask
    # that label only; the same digit used as the converted value still needs
    # ordinary claim support. This does not authorize changing the scale.
    if re.search(r'\b(?:diem|score|grade|quy doi)\b',folded(str(question or ''))):
        scales=set(re.findall(r'\b(?:thang(?: diem)?|diem he|scale)\s+(\d+)\b',folded(str(question or ''))))
        visible=re.sub(r'\b(?:thang(?: điểm)?|thang(?: diem)?|hệ|he|scale)\s+(\d+)\b',
            lambda m:' ' if m[1] in scales else m[0],visible,flags=re.I)
    shared_scope_numbers = _question_scope_numbers(question) & _question_scope_numbers(visible)
    # Remove only a proved location label. Its number must never become an
    # allowable factual quantity elsewhere in the sentence (e.g.9 credits).
    def mask_location(match):
        key = location_key(folded(match[1]),match[2])
        return ' ' if key in locations or key in shared_scope_numbers else match[0]
    if locations:
        visible=VISIBLE_LOCATION.sub(mask_location,visible)
        visible=SEMESTER_LOCATION.sub(lambda m:' ' if ('semester',str(int(m[1]))) in locations else m[0],visible)
    visible = _QUESTION_SCOPE_NUMBER.sub(
        lambda match: ' ' if _scope_number_key(match[1], match[2]) in shared_scope_numbers else match[0],
        visible,
    )
    visible, visible_calendar = calendar_presentation(visible)
    canonical_supported = [calendar_presentation(text) for text in supported]
    if visible_calendar - set().union(*(markers for _, markers in canonical_supported)):
        return True
    supported = [text for text, _ in canonical_supported]
    if locations:
        supported = [SEMESTER_LOCATION.sub(lambda m:' ' if ('semester',str(int(m[1]))) in locations else m[0],text)
                     for text in supported]
    support = '\n'.join(supported)
    # A scoped cohort/document year may be repeated in the prose answer while
    # the verification claim correctly omits it. Allow only the same year,
    # only when both question and answer label it as scope, and never a date.
    allowed_scope_years = _scoped_years(question) & _scoped_years(visible)
    if _affirmative_disagrees_with_review_value(question, visible, support):
        return True
    anchors = code_markers(visible) | code_markers(support)
    visible = canonical_code_spacing(visible, anchors)
    supported = [canonical_code_spacing(text, anchors) for text in supported]
    support = '\n'.join(supported)
    # An identifier repeated as question scope is permitted only when the
    # physically validated cited passage also names it. It cannot authorize a
    # different ID or an arbitrary number elsewhere in the answer.
    scope_codes = code_markers(str(question or '')) & set(source_scope_codes)
    if code_markers(visible) - code_markers(support) - scope_codes:
        return True
    visible_numbers = {number(v) for v in NUMBER.findall(visible)}
    supported_numbers = {number(v) for v in NUMBER.findall(support)}
    ungrounded_numbers = visible_numbers - supported_numbers - {number(str(year)) for year in allowed_scope_years}
    if ungrounded_numbers:
        return True
    known_units = quantities(support)
    for value, units in quantities(visible).items():
        if known_units.get(value) and not units <= known_units[value]:
            return True
    # Opposite negation of the same explicit clause is a contradiction. Do not
    # guess polarity across unrelated clauses or infer it from vocabulary alone.
    for clause in re.split(r'[.!?。！？]\s*|\n+', visible):
        normalized = normalize_text(folded(clause)).strip(' .!?')
        if not normalized:
            continue
        base = ' '.join(NEGATION.sub('', normalized).split())
        for claim in supported:
            original = normalize_text(folded(claim)).strip(' .!?')
            if base == ' '.join(NEGATION.sub('', original).split()) and bool(NEGATION.search(normalized)) != bool(NEGATION.search(original)):
                return True
    return False
