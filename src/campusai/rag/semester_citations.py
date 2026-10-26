"""Resolve scoped table quotations from literal source markers and headed cells."""
import json
import re
from decimal import Decimal

from .course_credits import folded, COURSE_CODE, course_code_key
from .multi_hop_evidence import name_matches
from .semester_totals import _SEMESTER, _NUMBERS
from ..retrieval.tokenizer_vi import normalized_tokens


def references(text):
    value = folded(text)
    return {int(m[1]) if m[1].isdigit() else _NUMBERS[m[1]]
            for m in _SEMESTER.finditer(value)
            if not re.search(r'\bcredits?\s*per\s*$',value[:m.start()])}


def _marker(row):
    cells = [c.strip() for c in row if c.strip()]
    match = re.fullmatch(r'(?:semester|hoc ky)\s*(\d+)', folded(cells[0])) if len(cells) == 1 else None
    return (int(match[1]), cells[0]) if match else None


def _subtotal(row):
    return any(re.fullmatch(r'credits?\s*per\s+semester|tong(?: so)? tin chi(?: hoc ky)?', folded(c)) for c in row)


def _named_rows(rows, headers, text):
    names = [i for i,h in enumerate(headers) if folded(h) in
             {'discipline','course name','subject','subject name','hoc phan','ten hoc phan',
              'course code','ma hoc phan','ma so hoc phan'}]
    if not names:
        return None
    found = []
    value = folded(text)
    for index,row in enumerate(rows):
        if _marker(row) or _subtotal(row):
            continue
        if sum(bool(c.strip()) for c in row)==1 and any(re.fullmatch(
                r'(?:compulsory|elective|optional) subjects',folded(c)) for c in row):
            continue
        for column in names:
            cell = row[column]
            lines = cell.splitlines()
            aliases = {' '.join(lines[:i]) for i in range(1,len(lines)+1)}
            aliases.update(' '.join(lines[i:]) for i in range(len(lines)))
            for alias in aliases:
                if not alias or not name_matches(alias,cell):
                    continue
                for match in re.finditer(r'(?<!\w)'+re.escape(folded(alias))+r'(?!\w)',value):
                    found.append((index,match.start(),match.end()))
    # A shorter literal course name inside a longer one is not a second
    # requested identity. Separate mentions and duplicate rows remain visible.
    maximal = [(i,a,b) for i,a,b in found if not any(x<=a and b<=y and (x<a or b<y) for _,x,y in found)]
    mentions = {(a,b) for _,a,b in maximal}
    return set.intersection(*({i for i,x,y in maximal if (x,y)==span} for span in mentions)) if mentions else None


def scoped_quote(result, rows, headers, texts, question):
    requested = references(question)
    asserted = set().union(*(references(t) for t in texts))
    if not requested and not asserted:
        return False,None
    if any(not isinstance(r,list) or len(r)!=len(headers) or any(not isinstance(c,str) for c in r)
           for r in rows):
        return True,None
    semester_columns = [i for i,h in enumerate(headers) if folded(h) in {'hoc ky','semester','term'}]
    if len(semester_columns)>1:
        return True,None
    locations = {}
    scope = result.metadata.get('table_scope','')
    inherited = (_marker([scope]) if isinstance(scope,str) and
                 result.metadata.get('table_scope_provenance')=='explicit_pdf_marker' else None)
    active = (inherited[0],-1,inherited[1]) if inherited else None
    for i,row in enumerate(rows):
        if semester_columns:
            value = row[semester_columns[0]].strip()
            locations[i] = (int(value),-2,'column') if re.fullmatch(r'[0-9]{1,2}',value) else None
            continue
        marker = _marker(row)
        if marker:
            active = (marker[0],i,marker[1])
        elif any(re.match(r'^(?:semester|hoc ky)(?:\s|\d|$)',folded(c)) for c in row):
            active = None
        locations[i] = active
        if _subtotal(row):
            active = None
    selected = set()
    for text in texts:
        explicit = references(text)
        if len(explicit)>1 or (explicit and requested and not explicit<=requested):
            return True,None
        targets = explicit or (requested if len(requested)==1 else asserted)
        if len(targets)!=1:
            return True,None
        target = next(iter(targets))
        eligible = [i for i in range(len(rows)) if locations[i] and locations[i][0]==target]
        named = _named_rows(rows,headers,text)
        if named is None:
            named = _named_rows(rows,headers,question)
        if named is not None:
            eligible = [i for i in eligible if i in named]
        claimed_codes = {course_code_key(m[0]) for m in re.finditer(COURSE_CODE,text,re.I)}
        if semester_columns and named is None and not claimed_codes:
            return True,None
        if claimed_codes:
            columns = [i for i,h in enumerate(headers) if folded(h) in {'course code','ma hoc phan','ma so hoc phan'}]
            eligible = [i for i in eligible if claimed_codes<={course_code_key(rows[i][c]) for c in columns}]
        units = {Decimal(n.replace(',','.')) for n in re.findall(
            r'(?<!\w)(\d+(?:[.,]\d+)?)\s*(?:credits?\b|tin chi\b)',folded(text))}
        if units:
            columns = [i for i,h in enumerate(headers) if folded(h) in {'credits','so tin chi'}]
            if len(columns)!=1 or len(units)!=1:
                return True,None
            if named is None and not claimed_codes:
                total_text = _SEMESTER.sub('@',folded(text)).strip(' .?!')
                if not re.fullmatch(r'@ (?:has|co) [0-9]+(?:[.,][0-9]+)? (?:credits?|tin chi)',total_text):
                    return True,None
                eligible = [i for i in eligible if _subtotal(rows[i])]
            cells = [rows[i][columns[0]].strip() for i in eligible]
            if not cells or any(not re.fullmatch(r'[0-9]+(?:[.,][0-9]+)?',cell) for cell in cells):
                return True,None
            if {Decimal(cell.replace(',','.')) for cell in cells}!=units:
                return True,None
        # Remove only the locator span, never its numeric value from a set:
        # "Semester5 Alpha5" still has an independently asserted value5.
        value = folded(text)
        remainder = _SEMESTER.sub(lambda m:m[0] if re.search(
            r'\bcredits?\s*per\s*$',value[:m.start()]) else '',value)
        numbers = lambda s: {Decimal(n.replace(',','.')) for n in re.findall(r'(?<!\w)\d+(?:[.,]\d+)?',s)}
        required = numbers(remainder)
        eligible = [i for i in eligible if required<=numbers(' '.join(rows[i]))]
        if not eligible:
            return True,None
        terms = set(normalized_tokens(text))
        selected.add(max(eligible,key=lambda i:len(terms & set(normalized_tokens(' '.join(rows[i]))))))
    provider_question = (_named_rows(rows,headers,question) is None and re.search(
        r'\b(?:institution|provider|resources|taught|teaches|truong nao|ben nao|hoc ben|don vi)\b',folded(question)))
    selected_scopes = {locations[i][0] for i in selected}
    if provider_question and len(selected_scopes)==1:
        columns = [i for i,h in enumerate(headers) if folded(h) in {'resources','resource','provider','institution'}]
        if len(columns)!=1:
            return True,None
        start = min(locations[i][1] for i in selected)
        end = None
        for i in range(max(0,start+1),len(rows)):
            if _marker(rows[i]):
                end = i-1
                break
            if _subtotal(rows[i]):
                end = i
                break
        # A partial table fragment cannot prove a statement about every
        # course in an entire semester. No arbitrary row may hide a provider.
        if end is None or start<0:
            return True,None
        providers = {row[columns[0]].strip() for row in rows[start:end+1] if row[columns[0]].strip()}
        claim_text = folded(' '.join(texts))
        if not providers or any(not re.search(r'(?<!\w)'+re.escape(folded(p))+r'(?!\w)',claim_text) for p in providers):
            return True,None
        selected.update(range(start,end+1))
    starts = [locations[i][1] for i in selected if locations[i]]
    first,last = min(starts),max(selected)
    if semester_columns:
        quoted = rows[next(iter(selected))] if len(selected)==1 else [rows[i] for i in sorted(selected)]
    elif first<0:
        quoted = {'scope':inherited[1],'headers':headers,'rows':[rows[i] for i in sorted(selected)]}
    elif len(selected_scopes)==1:
        quoted = {'scope':locations[min(selected)][2],'headers':headers,'rows':rows[first:last+1]}
    else:
        # Comparisons retain all intervening original rows/markers; never
        # label a multi-semester quote as if it belonged to the first one.
        quoted = rows[first:last+1]
    quote = json.dumps(quoted,ensure_ascii=False)
    return True,quote if len(quote)<=1200 else None
