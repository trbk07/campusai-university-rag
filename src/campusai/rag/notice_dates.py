"""Read a narrow date/window field from a proved selected admission notice.

Values come exclusively from labelled source spans. A round/year in the
question must agree with the document's literal title, never its filename or
inferred metadata. Ambiguous notices, conditions and extra intents fall back.
"""
from datetime import datetime
import re
import unicodedata

from .course_credits import folded
from .footnotes import _fold_with_offsets
from ..retrieval.tokenizer_vi import source_body


_TITLE = re.compile(r'thong bao tuyen sinh(?: dao tao)? thac s[iy] dot (\d{1,2}) nam ((?:19|20|21)\d{2})')
_DATE = r'\d{1,2}/\d{1,2}/\d{4}'
_CLOCK = r'\d{1,2}(?:h|:)\d{2}'
_CONTEXT = '\nContext topic (untrusted user input): '


def _request(question):
    if _CONTEXT in question:
        return None
    text = folded(question).strip(' .?!')
    for pattern, value in [(r'\b(?:ths|thac sy)\b','thac si'), (r'\bxtt\b','xet tuyen thang'),
                           (r'\bdk\b','dang ky'), (r'\bonline\b','truc tuyen')]:
        text = re.sub(pattern,value,text)
    text = re.sub(r'\bd(\d{1,2})\b',r'dot \1',text)
    rounds, years = [], []
    def select(match, values):
        values.append(int(match[1]))
        return '@' if values is rounds else '&'
    text = re.sub(r'\bdot\s+(\d{1,2})\b',lambda m:select(m,rounds),text)
    text = re.sub(r'\bnam\s+((?:19|20|21)\d{2})\b',lambda m:select(m,years),text)
    if len(rounds)>1 or len(years)>1:
        return None
    scope = r'(?: @)?(?: &)?'
    interview = r'(?:phong van|pv) thac si'+scope+r' (?:la )?ngay (?:nao|bn)'
    online = (r'han dang ky truc tuyen (?:xet )?tuyen thang thac si'+scope+r' (?:la )?ngay (?:nao|bn)',
              r'(?:xet )?tuyen thang thac si'+scope+r' chot dang ky truc tuyen bn h')
    kind = ('interview' if re.fullmatch(interview,text) else
            'direct_online' if any(re.fullmatch(p,text) for p in online) else None)
    return (kind,rounds[0] if rounds else None,years[0] if years else None) if kind else None


def _notice_scope(items):
    scopes = set()
    for item in items:
        if item.get('page')!=1 or item.get('content_type')!='text':
            continue
        lines = source_body(item,decode_tables=False).strip().splitlines()
        # Only an actual opening title, optionally wrapped across three lines.
        # An example/quotation elsewhere or a metadata heading is not a title.
        for count in range(1,min(3,len(lines))+1):
            match = _TITLE.fullmatch(folded(' '.join(lines[:count])))
            if match:
                scopes.add(tuple(map(int,match.groups())))
                break
    return next(iter(scopes)) if len(scopes)==1 else None


def _stamp(day, clock='00h00'):
    return datetime.strptime(day+' '+clock.replace('h',':'),'%d/%m/%Y %H:%M')


def _facts(item, kind):
    if item.get('content_type')!='text':
        return []
    body = source_body(item,decode_tables=False)
    text, offsets = _fold_with_offsets(body)
    label = (r'\bthoi\s+gian\s+phong\s+van\b' if kind=='interview' else
             r'\bthoi\s+gian\s+dang\s+ky\s+truc\s+tuyen\b')
    label_count = len(list(re.finditer(label,text)))
    if not label_count:
        return []
    if kind!='interview' and (not re.search(r'\bxet\s+tuyen\s+thang\b',text)
                              or re.search(r'\b(?:phong\s+van|du\s+thi)\b',text)):
        return []
    invalid = [(None,item,'')]
    if re.search(r'\b(?:neu|gia su|vi du|du kien|ngoai tru|tru truong hop)\b',text):
        return invalid
    if kind=='interview':
        pattern = (r'\s*(?:\d+(?:\.\d+)*\.?\s+)?'
                   r'(?P<fact>thoi\s+gian\s+phong\s+van\s*:\s*ngay\s+(?P<day>'+_DATE+r')\.?)\s*')
        matches = [match] if (match:=re.fullmatch(pattern,text)) else []
    else:
        pattern = (r'(?m)^[ \t]*[-•]?[ \t]*(?P<fact>thoi\s+gian\s+dang\s+ky\s+truc\s+tuyen[^:\n]{0,180}:\s*'
                   r'tu\s+(?P<begin_clock>'+_CLOCK+r')\s+ngay\s+(?P<begin>'+_DATE+r')\s+'
                   r'den\s+(?P<end_clock>'+_CLOCK+r')\s+ngay\s+(?P<end>'+_DATE+r')\.?)\s*(?=\n|$)')
        matches = list(re.finditer(pattern,text))
    if len(matches)!=label_count:
        return invalid
    found = []
    for match in matches:
        try:
            if kind=='interview':
                value = (_stamp(match['day']),)
            else:
                value = (_stamp(match['begin'],match['begin_clock']),_stamp(match['end'],match['end_clock']))
                if value[0]>value[1]:
                    return invalid
        except ValueError:
            return invalid
        start,end = match.span('fact')
        quote = body[offsets[start]:offsets[end-1]+1]
        found.append((value,item,quote))
    return found


def lookup_notice_date(question, documents, *, doc_ids, language='vi', calibrator=None):
    if (not language.casefold().startswith('vi') or doc_ids is None or len(doc_ids)!=1
            or len(documents)!=1 or documents[0]['doc_id']!=doc_ids[0]):
        return None
    request = _request(question)
    if request is None:
        return None
    kind, number, year = request
    scope = _notice_scope(documents[0]['items'])
    if scope is None or (number is not None and number!=scope[0]) or (year is not None and year!=scope[1]):
        return None
    candidates = [fact for item in documents[0]['items'] for fact in _facts(item,kind)]
    if any(value is None for value,_item,_quote in candidates) or len({value for value,_item,_quote in candidates})!=1:
        return None
    _value,item,quote = candidates[0]
    from .grounding import Citation, _grounding_finalize, validate_citation
    from ..retrieval.hybrid import RetrievalResult
    result = RetrievalResult(item['chunk_id'],doc_ids[0],item['page'],item['content'],'text',1.,
                             'source_notice_field',item.get('metadata',{}))
    meta = result.metadata
    citation = Citation(result.chunk_id,result.doc_id,result.page,quote,
        ' > '.join(meta.get('heading_path',[])),meta.get('source_name',''),
        tuple(meta.get('page_range',[result.page,result.page])),meta.get('table_id',''),meta.get('source_hash',''))
    if not validate_citation(citation,result,require_quote=True).valid:
        return None
    # Preserve the complete labelled source field, including both bounds of a
    # registration window. A source locator need not become an extra answer fact.
    answer_text = unicodedata.normalize('NFC',' '.join(quote.split()))
    payload = {'claims':[{'claim_id':'field','text':answer_text,'citation_ids':[result.chunk_id]}]}
    answer = _grounding_finalize(answer_text,(citation,),payload,[result],language,
                                 question=question,calibrator=calibrator)
    return (answer,[result]) if not answer.abstained else None
