"""Apply an explicit necessary grade condition, never predict an award decision."""
import re
import unicodedata

from .course_credits import folded
from .footnotes import _fold_with_offsets
from ..retrieval.tokenizer_vi import source_body


def _request(question):
    text = folded(question).strip(' .?!')
    text = re.sub(r'\bsv\b','sinh vien',text)
    match = re.fullmatch(r'co (?:mot|1) (?:mon|hoc phan) duoi ([a-f][+-]?) '
                         r'la (?:bay|mat) danh hieu (sinh vien [\w ]+?)(?: a| ha)?',text)
    return (match[1],match[2]) if match else None


def lookup_award_condition(question, documents, *, doc_ids, language='vi', calibrator=None):
    if (not language.casefold().startswith('vi') or doc_ids is None or len(doc_ids)!=1
            or len(documents)!=1 or documents[0]['doc_id']!=doc_ids[0]):
        return None
    request = _request(question)
    if request is None:
        return None
    requested_grade, requested_title = request
    candidates = []
    for item in documents[0]['items']:
        if item.get('content_type')!='text':
            continue
        body = source_body(item,decode_tables=False)
        text,offsets = _fold_with_offsets(body)
        articles = list(re.finditer(r'(?m)^[ \t]*dieu\s+\d+\s*:',text))
        for index,heading in enumerate(articles):
            end = articles[index+1].start() if index+1<len(articles) else None
            block = text[heading.start():end]
            title = re.match(r'dieu\s+\d+\s*:\s*danh\s+hieu\s+["“](?P<name>[^"”]{1,140})["”]',block)
            if not title or folded(title['name'])!=requested_title:
                continue
            if not re.match(r'\s+duoc\s+trao\s+cho\b',block[title.end():]):
                return None
            # A chunk boundary cannot prove that an exception was not cut off.
            if end is None or re.search(r'\b(?:neu|gia su|vi du|ngoai tru|tru|hoac|hay|khong can|khong bat buoc|khong yeu cau|khong ap dung|mien dieu kien|dac cach)\b',block):
                return None
            sentence_end = re.search(r'\.(?=\s|$)',block)
            if not sentence_end:
                return None
            statement = block[:sentence_end.end()]
            grades = list(re.finditer(r'khong\s+co\s+hoc\s+phan\s+nao\s+(?:co\s+diem\s+)?duoi\s+([^\s.,;]+)',statement))
            if len(grades)!=1 or not re.fullmatch(r'[a-f][+-]?',grades[0][1]):
                return None
            start = heading.start(); stop = start+sentence_end.end()
            quote = body[offsets[start]:offsets[stop-1]+1]
            a,b = title.span('name'); label = body[offsets[start+a]:offsets[start+b-1]+1]
            candidates.append((item,quote,unicodedata.normalize('NFC',' '.join(label.split())),grades[0][1]))
    if (not candidates or len({(folded(quote),grade) for _item,quote,_title,grade in candidates})!=1
            or candidates[0][3]!=requested_grade):
        return None
    item,quote,label,grade = candidates[0]
    from .grounding import Citation, GroundedAnswer, validate_citation
    from .claims import Claim
    from .confidence import score_confidence
    from ..retrieval.hybrid import RetrievalResult
    result = RetrievalResult(item['chunk_id'],doc_ids[0],item['page'],item['content'],'text',1.,
                             'source_award_condition',item.get('metadata',{}))
    meta = result.metadata
    citation = Citation(result.chunk_id,result.doc_id,result.page,quote,
        ' > '.join(meta.get('heading_path',[])),meta.get('source_name',''),
        tuple(meta.get('page_range',[result.page,result.page])),meta.get('table_id',''),meta.get('source_hash',''))
    if not validate_citation(citation,result,require_quote=True).valid:
        return None
    # One below-threshold course violates this explicitly universal necessary
    # condition. This makes no claim about a real student's grade or revocation.
    fact = (f'Theo điều kiện trong tài liệu, một học phần dưới {grade.upper()} không đáp ứng điều kiện điểm để xét danh hiệu {label}: '
            f'quy định yêu cầu không có học phần nào có điểm dưới {grade.upper()}.')
    confidence = score_confidence(retrieval_support=1.,claim_entailment=1.,citation_completeness=1.,calibrator=calibrator)
    claim = Claim('necessary_grade',fact,'fact',1,(result.chunk_id,),'supported',1.,(result.chunk_id,),False)
    answer = GroundedAnswer(fact,(citation,),confidence.label,False,claims=(claim,),evidence_status='found',
        confidence_score=confidence.score,raw_confidence_score=confidence.raw_score,policy_version=confidence.policy_version)
    return answer,[result]
