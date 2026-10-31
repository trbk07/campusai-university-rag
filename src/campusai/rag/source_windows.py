"""Select a contiguous source excerpt without generating or rewriting text."""
import re
from collections import Counter
import math
from ..retrieval.tokenizer_vi import normalized_tokens, normalize_retrieval_query
from .course_credits import folded

_STOP = set('a an the and or of to in on for is are was were be does do did what which how why when '
            'should would could called this that these those it its la cua va hay cho nhung gi nao '
            'the nao tai sao khi mot cac duoc dai truong hoc em toi minh ban bao nhieu may can'.split())


def verbatim_window(text: str, question: str, limit: int, *, registration: bool = False) -> str:
    if len(text) <= limit:
        return text
    # An explicitly requested article is a stronger source locator than common
    # words repeated in neighbouring articles. Keep the excerpt verbatim.
    requested = set(re.findall(r'\b(?:article|điều|dieu)\s+(\d+)\b', question,
                               flags=re.IGNORECASE))
    if len(requested) == 1:
        number = next(iter(requested))
        headings = list(re.finditer(
            r'(?mi)^[ \t]*(?:article|điều|dieu)\s+(\d+)\s*[:.)]', text))
        matching = [i for i, heading in enumerate(headings)
                    if heading.group(1) == number]
        if len(matching) == 1:
            index = matching[0]
            end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
            text = text[headings[index].start():end]
            if len(text) <= limit:
                return text
    # A named article also identifies the requested source clause. Generic
    # words in neighbouring articles must not win a window that ends at the
    # target title and drops its predicate on the next line. Keep every equally
    # specific match: duplicate titles may disagree, and comparisons need both
    # clauses. Explicit article numbers retain priority above.
    if not requested:
        headings = list(re.finditer(
            r'(?mi)^[ \t]*(?:article|điều|dieu)\s+\d+\s*[:.)]\s*([^\r\n]*)', text))
        # Retrieval tokens append accentless aliases; they are a bag, not an
        # ordered phrase. Literal title matching must preserve word order.
        ordered_tokens = lambda value: tuple(re.findall(r'[^\W_]+', folded(value)))
        query_tokens = ordered_tokens(question)
        labels = []
        for heading in headings:
            label = re.split(r'\b(?:is|are|shall|must|được|duoc|có|co)\b',
                             heading[1], maxsplit=1, flags=re.I)[0]
            # Match the complete title (or a complete quoted name in it).
            # A generic three-word fragment of a longer heading is not an
            # explicit locator and must not hide facts from another article.
            titles = [label, *re.findall(r'["“]([^"”]+)["”]', label)]
            labels.append({tokens for title in titles
                           if 3 <= len(tokens := ordered_tokens(title)) <= 32})
        sizes = {len(title) for group in labels for title in group}
        phrases = {tuple(query_tokens[i:i + size]) for size in sizes
                   for i in range(len(query_tokens) - size + 1)}
        matches = [group & phrases for group in labels]
        found = set().union(*matches) if matches else set()
        # A shared title prefix is not a second named object. E.g. the prefix
        # "student award" must not outrank a complete, explicitly named award.
        specific = {p for p in found if not any(len(q) > len(p) and any(
                    q[i:i + len(p)] == p for i in range(len(q) - len(p) + 1)) for q in found)}
        selected = [i for i, group in enumerate(matches) if group & specific]
        comparison = re.search(r'\b(?:compare|comparison|difference|versus|so sánh|so sanh)\b', question, re.I)
        if selected and (not comparison or len(selected) > 1):
            first, last = min(selected), max(selected)
            end = headings[last + 1].start() if last + 1 < len(headings) else len(text)
            section = text[headings[first].start():end]
            if len(section) <= limit:
                return section
            if len(selected) == 1:
                text = section
    terms = {t for t in normalized_tokens(normalize_retrieval_query(question)) if len(t) >= 2 and t not in _STOP}
    terms.update(m[0].lower() for m in re.finditer(r'(?<!\w)[ABCDF](?!\w)',question))
    lines = []
    offset = 0
    for line in text.splitlines(keepends=True):
        matches = terms & set(normalized_tokens(line))
        lines.append((offset + len(line) / 2, matches))
        offset += len(line)
    frequencies = Counter(term for _, matches in lines for term in matches)
    focus = max(lines, key=lambda row: sum(math.log1p(len(lines) / (frequencies[t] + 1))
                                           for t in row[1]))[0] if lines else 0
    numeric_focus=None
    if re.search(r'\b(?:bao nhieu|may|how many|how much|minimum|maximum|toi thieu|toi da)\b',folded(question)):
        raw_lines=text.splitlines(keepends=True)
        candidates=[]
        for i,line in enumerate(raw_lines):
            if len(line.strip())>=25 and re.search(r'\d',line):
                nearby=set().union(*(row[1] for row in lines[max(0,i-1):i+2]))
                candidates.append((len(nearby),sum(math.log1p(len(lines)/(frequencies[t]+1)) for t in nearby),lines[i][0]))
        if candidates:
            numeric_focus=max(candidates)[2]
    starts = {0, max(0, len(text) - limit)}
    starts.update(m.end() for m in re.finditer('\n', text) if m.end() < len(text))
    # Score coverage, not repetition: repeated generic words must not drown
    # a short source condition. No corpus IDs, synonyms or expected answers.
    def excerpt_at(start):
        end = min(len(text), start + limit)
        if end < len(text):
            boundary = text.rfind('\n', start, end)
            if boundary > start:
                end = boundary
        return text[start:end]
    required=None
    if registration:
        from .footnotes import _fold_with_offsets
        normalized,offsets=_fold_with_offsets(text)
        match=re.search(r'\b(?:toi da|toi thieu|khong vuot qua)\s+(?:bang\s+)?\d+(?:[.,/]\d+)?\s*(?:tc\b|tin chi\b|[,;])',normalized)
        if match:
            begin,end=offsets[match.start()],offsets[match.end()-1]+1
            bullets=list(re.finditer(r'(?m)^[ \t]*(?:\d+[.)]|[a-z][.)])\s*',text[:begin]))
            lead=bullets[-1].start() if bullets and end-bullets[-1].start()<=limit else begin
            required=(lead,end)
    def score(start):
        excerpt = excerpt_at(start)
        # A selected registration field must retain its first actual limit
        # and governing condition. Generic administrative prose cannot win
        # merely by repeating more of the question's vocabulary.
        complete=required is not None and start<=required[0] and start+len(excerpt)>=required[1]
        return (complete,len(terms & set(normalized_tokens(excerpt))),
                bool(numeric_focus is not None and start<=numeric_focus<=start+len(excerpt)),
                -abs(start + len(excerpt) / 2 - focus), -start)
    start = max(starts, key=score)
    return excerpt_at(start)


def registration_evidence(question, documents):
    """Keep literal registration limits in view, independent of rank noise.

    This selects source chunks, never values or answers. The default ordering
    retains the earliest applicable rule; explicitly requested qualifications
    take priority. Normal citation and claim verification remain mandatory.
    """
    from .course_credits import folded
    from ..retrieval.tokenizer_vi import source_body
    from ..retrieval.hybrid import RetrievalResult
    query=folded(question)
    if (not re.search(r'\b(?:tc|tin chi|credits?|(?:may|bao nhieu|so)\s+tin)\b',query)
            or not re.search(r'\b(?:(?:hoc|moi|tung) k[yi]|k[yi] (?:chinh|he|phu)|semester|term|dang k[yi]|registration)\b',query)
            or not re.search(r'\b(?:toi da|toi thieu|gioi han|limit|dang k[yi]|registration)\b',query)):
        return []
    qualifiers=(('thac si','cao hoc','master','postgraduate'),('tien si','doctoral','phd'),
                ('ky su','engineering'),('canh bao','warning'))
    requested=[terms for terms in qualifiers if any(term in query for term in terms)]
    result=[]
    for doc in documents:
        candidates=[]
        for item in doc.get('items',[]):
            body=folded(source_body(item));section=folded(str((item.get('metadata') or {}).get('section_path','')))
            anchor=bool(re.search(r'\b(?:so (?:luong tc|tin chi).{0,25}dang k[yi]|dang k[yi] hoc tap|khoi luong hoc tap)\b',body))
            literal_limits=bool(re.search(r'\b(?:toi da|toi thieu|khong vuot qua)\s+(?:bang\s+)?\d+(?:[.,/]\d+)?\s*(?:tc\b|tin chi\b|[,;])',body))
            if not anchor or not literal_limits or not re.search(r'\b(?:tc|tin chi)\b',body):continue
            title=bool(re.search(r'\b(?:dang k[yi] hoc tap|khoi luong hoc tap)\b',section or body[:140]))
            qualification=sum(any(term in section for term in terms) for terms in requested)
            if requested and qualification<len(requested):continue
            score=(qualification,title,-int(item.get('page',1)))
            candidates.append((score,item))
        if candidates:
            _,item=max(candidates,key=lambda pair:pair[0])
            result.append(RetrievalResult(item['chunk_id'],doc['doc_id'],item['page'],item['content'],
                item.get('content_type','text'),1.0,'source_registration_fields',item.get('metadata',{})))
    return result
