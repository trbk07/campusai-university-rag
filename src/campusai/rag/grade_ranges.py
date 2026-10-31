"""Prove score-to-grade applications from literal ranges, never a grade scale list."""
import json
import re
import unicodedata
from decimal import Decimal

from .course_credits import folded

NUMBER = r'\d+(?:[.,]\d+)?'
INTERVAL = re.compile(r'('+NUMBER+r')\s*(?:÷|–|—|-|den|to)\s*('+NUMBER+r')')
GRADE = re.compile(r'[ABCDF][+-]?')
SCORE = re.compile(r'(?<![\w.,])('+NUMBER+r')\s+(?:diem|points?)\b|'
                   r'\b(?:score|diem)\s+(?:of\s+|la\s+)?('+NUMBER+r')(?![\w.,])')


def decimal(value):
    return Decimal(value.replace(',', '.'))


def score_input(question):
    text=folded(question)
    values = {decimal(m[1] or m[2]) for m in SCORE.finditer(text)
              if not re.search(r'\b(?:thang|scale)\s*$',text[:m.start()])
              and not re.match(r'\s+scale\b',text[m.end():])}
    if not values and re.search(r'\b(?:quy doi|convert|letter grade)\b',text):
        values={decimal(m[1]) for m in re.finditer(r'\b(?:duoc|dat|got|scored)\s+('+NUMBER+r')(?=\s*(?:thi\b|quy doi\b|[?!.]|$))',text)}
    return next(iter(values)) if len(values) == 1 else None


def table_proof(content, value):
    """Only a rectangular table with literal interval headers and grade cells."""
    try:
        table = json.loads(content[content.index('{"headers"'):])
        headers, rows = table['headers'], table['rows']
        if (not isinstance(headers, list) or not rows
                or any(not isinstance(h,str) for h in headers)
                or any(not isinstance(r,list) or len(r)!=len(headers)
                       or any(not isinstance(c,str) for c in r) for r in rows)):
            return None
    except (ValueError, TypeError, KeyError, AttributeError):
        return None
    candidates = []
    for i, header in enumerate(headers[1:], 1):
        interval = INTERVAL.fullmatch(folded(header).strip())
        if not interval or not decimal(interval[1]) <= value <= decimal(interval[2]):
            continue
        grades = {r[i].strip() for r in rows if GRADE.fullmatch(r[i].strip())}
        if len(grades) == 1:
            candidates.append((i, next(iter(grades))))
    if len(candidates) != 1:
        return None
    column, grade = candidates[0]
    return table, column, grade


def _column_claims(proof, texts):
    table, column, grade = proof
    literal = lambda s: ' '.join(unicodedata.normalize('NFC', s).split())
    cells = [table['headers'][0],table['headers'][column], *table['headers'][column].splitlines(),
             *(r[0] for r in table['rows']), *(r[column] for r in table['rows'])]
    allowed = {literal(c) for c in cells if c.strip()}
    fragments = [literal(c.strip()) for text in texts for c in text.split('|') if c.strip()]
    bounds=INTERVAL.fullmatch(folded(table['headers'][column]).strip())
    interval=lambda s:tuple(decimal(x) for x in m.groups()) if (m:=INTERVAL.fullmatch(folded(s).strip())) else None
    if len(fragments)==2:
        # Atomic claims may describe one field of the already proved column.
        # Never license a value under the label of a different row.
        fields=[(table['headers'][0],table['headers'][column]),*((r[0],r[column]) for r in table['rows'])]
        values={literal(v) for label,v in fields if literal(label).casefold()==fragments[0].casefold()}
        if values:
            return len(values)==1 and (fragments[1] in values or interval(fragments[1]) is not None
                and interval(fragments[1])==interval(next(iter(values))))
    if fragments and grade in fragments and all(c in allowed or interval(c)==tuple(decimal(x) for x in bounds.groups()) for c in fragments):
        return True
    # A prose claim may join those same fields. Require every number, grade
    # and content word to belong to this column; no unit/negation substitution.
    source=' '.join(cells)
    words=set(re.findall(r'\w+',folded(source)))|set('tu den tuong ung voi la va co the thanh'.split())
    numbers={decimal(n) for n in re.findall(NUMBER,source)}
    def prose_words(text):
        ranges=list(INTERVAL.finditer(folded(text).replace('|',' ')))
        if any(tuple(decimal(v) for v in m.groups())!=tuple(decimal(v) for v in bounds.groups()) for m in ranges):
            return False
        # Neutral connective, only with the same directed literal interval.
        allowed_words=words|({'duoc'} if ranges else set())
        return set(re.findall(r'\w+',folded(text)))<=allowed_words
    return bool(texts) and all(
        set(re.findall(r'(?<!\w)[ABCDF][+-]?(?![\w+\-])',t))=={grade}
        and prose_words(t)
        and {decimal(n) for n in re.findall(NUMBER,t)}<=numbers for t in texts)


def column_quote(content, texts, question):
    value = score_input(question)
    proof = table_proof(content, value) if value is not None else None
    if proof is None or not _column_claims(proof,texts):
        return None
    table=proof[0]
    # Keep the original rectangle, including its row/column labels. Projection
    # could silently detach a value from its interval; no cells are rewritten.
    quote = json.dumps(table, ensure_ascii=False)
    return quote if len(quote) <= 1200 else None


def flattened_grid(content):
    """Recover a rectangular printed grid only with three explicit row labels."""
    from .footnotes import _fold_with_offsets
    text=unicodedata.normalize('NFC',content);value,offsets=_fold_with_offsets(text)
    def original(start,end):
        return text[offsets[start]:offsets[end-1]+1]
    labels=[r'diem\s+hoc\s+phan\s+theo\s+thang\s+\d+',r'diem\s+chu\s+quy\s+doi',r'diem\s+so\s+quy\s+doi']
    found=[];start=0
    for label in labels:
        match=re.search(label,value[start:])
        if not match:return None
        found.append((start+match.start(),start+match.end()));start+=match.end()
    header=value[found[0][1]:found[1][0]]
    intervals=list(INTERVAL.finditer(header))
    if not intervals or INTERVAL.sub('',header).strip():return None
    grades=original(found[1][1],found[2][0]).split()
    if len(grades)!=len(intervals) or any(not GRADE.fullmatch(g) for g in grades):return None
    scalars=[];end=offsets[found[2][1]-1]+1
    for line in text[end:].splitlines(keepends=True):
        if not line.strip():end+=len(line);continue
        if not re.fullmatch(NUMBER,line.strip()):break
        scalars.append(line.strip());end+=len(line)
    if len(scalars)!=len(intervals):return None
    table={'headers':[original(*found[0]),*[original(found[0][1]+m.start(),found[0][1]+m.end()) for m in intervals]],
           'rows':[[original(*found[1]),*grades],[original(*found[2]),*scalars]]}
    return table,text[max(0,offsets[found[0][0]]-120):end].strip()


def flattened_quote(content,texts,question):
    value=score_input(question);grid=flattened_grid(content)
    if value is None or grid is None:return None
    table,quote=grid
    proof=table_proof(json.dumps(table,ensure_ascii=False),value)
    return quote if proof and _column_claims(proof,texts) and len(quote)<=1200 else None


def proven_grades(content, value):
    proof = table_proof(content, value)
    if proof is not None:
        return {proof[2]}
    grid=flattened_grid(content)
    if grid:
        proof=table_proof(json.dumps(grid[0],ensure_ascii=False),value)
        if proof:return {proof[2]}
    try:
        cells=json.loads(content)
    except (TypeError,ValueError):
        cells=None
    if isinstance(cells,list) and cells and all(isinstance(cell,str) for cell in cells):
        return set().union(*(proven_grades(cell,value) for cell in cells))
    found = set()
    from .footnotes import _fold_with_offsets
    for match in re.finditer(r'(?m)^\s*([ABCDF][+-]?)\s*:\s*(?:tu\s+)?('
                             +NUMBER+r')\s+den\s+('+NUMBER+r')\s*[;.]?\s*$', _fold_with_offsets(content)[0], re.I):
        # folded() lowers case; use the original grade spelling canonically.
        if decimal(match[2]) <= value <= decimal(match[3]):
            found.add(match[1].upper())
    return found


def deterministic_grade_answer(question, results, language='vi', *, calibrator=None):
    """Apply an unambiguous printed grade mapping; no model or fixed values.

    Restricted to score conversion, with one source and both typed fields.
    Mixed requests, overall averages, missing fields and conflicts fall back
    to the ordinary pipeline. The result passes normal citation/claim checks.
    """
    value=score_input(question);query=folded(question)
    if (value is None or len({r.doc_id for r in results})!=1
            or not re.search(r'\b(?:quy doi|diem chu|letter grade|convert|thang|diem he)\b|\b[a-f][+]?\s+hay\s+[a-f][+]?(?!\w)',query)
            or re.search(r'\b(?:gpa|cpa|trung binh|tich luy|weighted|average|tong diem|tot nghiep|graduation|hoc bong|scholarship|mat khau|password|tai khoan|account|hoc phi|tuition|dia chi|email|bi mat|secret|prompt|dong thoi)\b',query)):
        return None
    from .request_completeness import explicit_request_roles
    if explicit_request_roles(question):return None
    if re.search(r'\b(?:roi|ngoai ra|also|then|plus)\b|\b(?:va|and)\s+(?!(?:diem|thang|he|numeric|letter|grade)\b)',query):
        return None
    from ..retrieval.tokenizer_vi import source_body
    from .footnotes import _fold_with_offsets
    ranges=[];point_fields=[]
    for result in results:
        body=source_body({'content':result.content},decode_tables=False)
        proof=table_proof(body,value)
        if proof is None and (grid:=flattened_grid(body)):
            proof=table_proof(json.dumps(grid[0],ensure_ascii=False),value)
        if proof:
            table,col,grade=proof
            row=next(row for row in table['rows'] if row[col].strip()==grade)
            ranges.append((grade,result,' | '.join((table['headers'][0],table['headers'][col],row[0],grade))))
            for row in table['rows']:
                if re.search(r'\b(?:diem so|grade points?|numeric grade)\b',folded(row[0])) and re.fullmatch(NUMBER,row[col].strip()):
                    point_fields.append((grade,row[col].strip(),result,row[0]+' | '+row[col]))
        else:
            texts=[body]
            try:
                table=json.loads(body[body.index('{"headers"'):])
                texts.extend(cell for row in table['rows'] for cell in row if isinstance(cell,str))
            except (ValueError,TypeError,KeyError):pass
            for text in texts:
                for grade in proven_grades(text,value):ranges.append((grade,result,text))
        text=source_body({'content':result.content});normalized,offsets=_fold_with_offsets(text)
        pattern=r'(?m)^\s*([a-f][+-]?)\s+(?:quy\s+doi\s+thanh|maps?\s+to|converts?\s+to)\s+('+NUMBER+r')\s*[;.]?'
        for match in re.finditer(pattern,normalized,re.I):
            point_fields.append((match[1].upper(),match[2],result,text[offsets[match.start()]:offsets[match.end()-1]+1].strip()))
    grades={grade for grade,_,_ in ranges}
    if len(grades)!=1:return None
    grade=next(iter(grades));points=[field for field in point_fields if field[0]==grade]
    if len({decimal(field[1]) for field in points})!=1:return None
    _,range_result,range_claim=min(ranges,key=lambda item:len(item[2]))
    _,point,point_result,point_claim=min(points,key=lambda item:len(item[3]))
    letter_only=bool(re.search(r'\b(?:diem chu|letter grade)\b|\b[a-f][+]?\s+hay\s+[a-f][+]?(?!\w)',query)
                     and not re.search(r'\b(?:diem so|grade points?|numeric grade)\b|\b(?:va|and)\s+(?:thang|he)',query))
    texts=[(range_result,range_claim)] if letter_only else [(range_result,range_claim),(point_result,point_claim)]
    claims=[{'claim_id':f'grade{i}','text':text,'citation_ids':[result.chunk_id]}
            for i,(result,text) in enumerate(texts)]
    from .source_citations import source_quote
    from .grounding import Citation, validate_citation, _grounding_finalize
    citations=[]
    for result,_ in texts:
        if result.chunk_id in {citation.chunk_id for citation in citations}:continue
        quote=source_quote(result,claims,question)
        metadata=result.metadata
        citation=Citation(result.chunk_id,result.doc_id,result.page,quote or '',
            str(metadata.get('section_path','')),str(metadata.get('source_name','')),
            tuple(metadata.get('page_range') or (result.page,result.page)),str(metadata.get('table_id','')),
            str(metadata.get('source_hash','')))
        if not quote or not validate_citation(citation,result,require_quote=True).valid:return None
        citations.append(citation)
    answer=(f'Letter grade: {grade}.' if language.startswith('en') else f'Điểm chữ: {grade}.')
    if not letter_only:answer+=(f' Converted grade points: {point}.' if language.startswith('en') else f' Điểm số quy đổi: {point}.')
    checked=_grounding_finalize(answer,tuple(citations),{'confidence':'high','claims':claims},results,language,
        question=question,calibrator=calibrator)
    return checked if not checked.abstained else None


def application_view(answer, quotes, question, *, doc_ids=None):
    """Validate the applied grade and mask only the proved input for presentation.

    None means this is not a recognized score/letter conversion. False means
    the application lacks a literal in-range proof. Thresholds stay unchanged.
    """
    value = score_input(question)
    if value is None or not re.search(r'\b(?:quy doi|diem chu|letter grade|convert)\b|'
                                     r'\b[ABCDF][+]?(?!\w)(?:\s+hay\s+[ABCDF][+]?(?!\w))', folded(question), re.I):
        return None
    visible_grades = set(re.findall(r'(?<!\w)[ABCDF][+-]?(?![\w+\-])', answer))
    if not visible_grades:
        return None
    grouped = {}
    for doc,quote in zip(doc_ids or ['source']*len(quotes),quotes):
        grouped.setdefault(doc,set()).update(proven_grades(quote,value))
    if any(not grades for grades in grouped.values()):
        return False
    proved = set().union(*grouped.values()) if grouped else set()
    if not proved or not visible_grades <= proved:
        return False
    # Numeric input is premise, not an output quantity. Mask only a score span
    # whose value was just proved inside the cited interval.
    pattern = re.compile(r'(?<![\w.,])('+NUMBER+r')(?=\s+(?:điểm|points?)\b)', re.I)
    view = pattern.sub(lambda m:' ' if decimal(m[1])==value else m[0], answer)
    view = re.sub(r'\b((?:điểm|score)\s+(?:of\s+|là\s+)?)('+NUMBER+r')(?![\w.,])',
                  lambda m:m[1] if decimal(m[2])==value else m[0],view,flags=re.I)
    # A transposed table can explicitly identify the source scale in its header.
    scales = set()
    for quote in quotes:
        proof = table_proof(quote, value)
        if proof is None and (grid:=flattened_grid(quote)):
            proof=table_proof(json.dumps(grid[0],ensure_ascii=False),value)
        if proof:
            scales.update(re.findall(r'\bthang\s+(\d+)\b',folded(proof[0]['headers'][0])))
    return re.sub(r'\b(?:hệ|thang(?: điểm)?)\s+(\d+)\b',
                  lambda m:' ' if m[1] in scales else m[0], view, flags=re.I)


def retrieval_evidence(question,documents):
    """Recover the original interval and linked grade-point field per source.

    This selects source chunks, not answers. No question IDs, gold, filenames
    or fixed scale values participate in selection.
    """
    value=score_input(question)
    if value is None or not re.search(r'\b(?:quy doi|diem chu|letter grade|convert)\b|\b[a-f][+]?\s+hay\s+[a-f][+]?(?!\w)',folded(question)):
        return []
    from ..retrieval.tokenizer_vi import source_body
    from ..retrieval.hybrid import RetrievalResult
    from .footnotes import _fold_with_offsets
    found=[]
    for doc in documents:
        candidates=[]
        for item in doc['items']:
            body=source_body(item,decode_tables=False)
            texts=[body]
            if item.get('content_type')=='table':
                try:
                    table=json.loads(body[body.index('{"headers"'):])
                    texts.extend(cell for row in table['rows'] for cell in row if isinstance(cell,str))
                except (ValueError,TypeError,KeyError):pass
            grades=set().union(*(proven_grades(text,value) for text in texts))
            if grades:candidates.append((item,grades))
        grades=set().union(*(g for _,g in candidates)) if candidates else set()
        if len(grades)!=1:continue
        grade=next(iter(grades))
        # Prefer a rectangular original grid over a long flattened duplicate.
        selected=[min(candidates,key=lambda pair:(pair[0].get('content_type')!='table',len(pair[0]['content'])))[0]]
        pattern=re.compile(r'(?m)^\s*'+re.escape(grade)+r'(?![\w+\-])\s+(?:quy\s+doi\s+thanh|converts?\s+to|maps?\s+to|is\s+equivalent\s+to)\s+'+NUMBER,re.I)
        mapped=[item for item in doc['items'] if pattern.search(_fold_with_offsets(source_body(item))[0])]
        if mapped:selected.append(min(mapped,key=lambda item:len(item['content'])))
        for item in selected:
            if item['chunk_id'] not in {r.chunk_id for r in found}:
                found.append(RetrievalResult(item['chunk_id'],doc['doc_id'],item['page'],item['content'],
                    item.get('content_type','text'),1.0,'source_grade_field',item.get('metadata',{})))
    return found
