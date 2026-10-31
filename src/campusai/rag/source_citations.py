"""Resolve model-selected source IDs to original evidence, never model coordinates."""
import json
import re
import unicodedata
from decimal import Decimal
from .policies import sanitize_evidence_text
from .source_windows import verbatim_window
from ..retrieval.tokenizer_vi import normalized_tokens, source_body
from .course_credits import COURSE_CODE, course_code_key, folded

_TABLE_IDENTIFIER = re.compile(r'(?<![A-Za-z0-9])[A-Za-z]{1,6}\d{1,5}[A-Za-z]?(?![A-Za-z0-9])')


def _wrapped_line(previous, following):
    return (len(previous) >= 25 and len(following) >= 10 and following[0].islower()
            and previous.rstrip()[-1] not in '.;:?!'
            and not re.match(r'^[^:]{1,45}:', following))


def wrapped_prose(rows):
    """Some PDF extractors encode wrapped prose as a one-column table."""
    return (len(rows) > 1 and all(isinstance(r,list) and len(r)==1 and isinstance(r[0],str) for r in rows)
            and any(_wrapped_line(a[0],b[0]) for a,b in zip(rows,rows[1:])))


def relocate_literal_page_references(payload, results):
    """Resolve a wrong page ID only through unique literal same-PDF proof.

    Called only after the complete authorized source was checked. Original
    provider captures stay unchanged. Unknown IDs, repeated text, edited claims
    and cross-document matches retain the normal verification path.
    """
    claims, citations = payload.get('claims'), payload.get('citations')
    if not isinstance(claims, list) or not isinstance(citations, list) or payload.get('abstained'):
        return payload
    by_id = {r.chunk_id: r for r in results}
    compact = lambda text: ' '.join(unicodedata.normalize('NFC', text).casefold().split())
    remap = {}
    for citation in citations:
        if not isinstance(citation, dict) or set(citation) != {'chunk_id'}:
            continue
        identity = citation['chunk_id']
        original = by_id.get(identity)
        selected = [c['text'] for c in claims if identity in c.get('citation_ids', [])]
        if original is None or original.content_type != 'text' or not selected:
            continue
        if all(compact(text) in compact(original.content) for text in selected):
            continue
        candidates = [r for r in results if r.doc_id == original.doc_id and r.content_type == 'text'
                      and all(compact(text) in compact(r.content) for text in selected)]
        if len(candidates) == 1:
            remap[identity] = candidates[0].chunk_id
    if not remap:
        return payload
    return {**payload,
        'claims': [{**c, 'citation_ids': [remap.get(i, i) for i in c.get('citation_ids', [])]} for c in claims],
        'citations': [{**c, 'chunk_id': remap.get(c.get('chunk_id'), c.get('chunk_id'))}
                      if isinstance(c, dict) else c for c in citations]}


def source_quote(result, claims, question=''):
    texts = [c['text'] for c in claims if isinstance(c, dict) and isinstance(c.get('text'), str)
             and result.chunk_id in c.get('citation_ids', [])]
    if not texts:
        return None
    body = sanitize_evidence_text(source_body({'content': result.content}, decode_tables=False))
    if result.content_type=='text':
        from .grade_ranges import flattened_quote
        converted=flattened_quote(body,texts,question)
        if converted is not None:
            return converted
    if result.content_type == 'table':
        start = body.find('{"headers"')
        try:
            table = json.loads(body[start:]) if start >= 0 else None
        except ValueError:
            table = None
        if not isinstance(table, dict) or not isinstance(table.get('rows'), list):
            return None
        rows = [row for row in table['rows'] if isinstance(row, list) and row
                and all(isinstance(cell, str) for cell in row)]
        if not rows:
            return None
        headers = table.get('headers', [])
        if not isinstance(headers, list) or any(not isinstance(header, str) for header in headers):
            return None
        from .grade_ranges import column_quote
        converted = column_quote(body, texts, question)
        if converted is not None:
            return converted
        from .year_cells import binding
        cells = [binding(text, body, question,
                         numeric_cells=result.metadata.get('numeric_cell_policy') == 'ruled-ocr-numeric-v1')
                 for text in texts]
        if any(cell is not None for cell in cells):
            if any(cell is None or not cell.supported for cell in cells):
                return None
            selected = sorted({cell.row for cell in cells})
            quote = json.dumps({'headers': headers, 'rows': [table['rows'][i] for i in selected]},
                               ensure_ascii=False)
            return quote if len(quote) <= 1200 else None
        from .semester_citations import scoped_quote
        scoped, quote = scoped_quote(result, table['rows'], headers, texts, question)
        if scoped:
            return quote
        identity_columns = [i for i, header in enumerate(headers) if isinstance(header, str)
                            and (folded(header) in {'course code', 'ma hoc phan', 'ma so hoc phan', 'ma so',
                                                   'ma xet tuyen', 'admission code', 'programme code',
                                                   'program code', 'discipline code'}
                                 or re.fullmatch(r'ma nganh\d*', folded(header)))]
        programme_columns = [i for i, header in enumerate(headers)
                             if folded(header) in {'chuong trinh', 'programme', 'program'}]
        degree = r'(?:cu nhan|ky su|thac si|tien si|bachelor|engineer|master|doctorate)'
        scopes = {}
        if len(programme_columns) == 1:
            column = programme_columns[0]
            start = None
            for i, row in enumerate(rows):
                cell = folded(row[column]) if column < len(row) else ''
                if cell:
                    start = i if re.fullmatch(degree, cell) else None
                if start is not None:
                    scopes[i] = (start, folded(rows[start][column]))
        def degree_request(text):
            value = folded(text)
            match = re.search(r'\b(?:chuong trinh|programme|program)\s+('+degree+r')\b', value)
            match = match or re.match(r'^('+degree+r')(?:\s*\||\s+t[oố]t nghiep|\s*$)', value)
            return match[1] if match else None
        requested_degree = degree_request(question)
        selected = set()
        for text in texts:
            terms = set(normalized_tokens(text))
            codes = {course_code_key(m[0]) for m in re.finditer(r'(?<!\w)' + COURSE_CODE + r'(?!\w)', text, re.I)}
            # Short programme identifiers such as CN2 and D01 are not course
            # codes. Resolve them through declared table identity columns so
            # lexical overlap with a neighbouring row cannot choose the quote.
            codes.update(m.group().upper() for m in _TABLE_IDENTIFIER.finditer(text))
            pools = []
            if len(headers) == 1 and all(len(row) == 1 for row in rows):
                # A one-column record may carry its identity before a colon.
                # A matching number in another named record is not evidence.
                labels = [(i, folded(row[0].split(':',1)[0])) for i,row in enumerate(rows)
                          if ':' in row[0] and 2 <= len(row[0].split(':',1)[0]) <= 80]
                requested = [(i,label) for i,label in labels
                             if re.search(r'(?<!\w)'+re.escape(label)+r'(?!\w)',folded(question))]
                if not requested:
                    requested = [(i,label) for i,label in labels
                                 if re.search(r'(?<!\w)'+re.escape(label)+r'(?!\w)',folded(text))]
                if requested:
                    pools.extend([[i] for i,_label in requested])
            for code in sorted(codes):
                matching = []
                for i, row in enumerate(rows):
                    columns = identity_columns if identity_columns else range(len(row))
                    cells = (row[column] for column in columns if column < len(row))
                    if any(code in {m.group().upper() for m in _TABLE_IDENTIFIER.finditer(cell)}
                           or course_code_key(cell.strip()) == code for cell in cells):
                        matching.append(i)
                if matching:
                    pools.append(matching)
            claim_degree = degree_request(text)
            if requested_degree and claim_degree and requested_degree != claim_degree:
                return None
            target_degree = requested_degree or claim_degree
            numbers = lambda value: {Decimal(n.replace(',', '.')) for n in
                re.findall(r'(?<!\w)\d+(?:[.,]\d+)?', value)}
            required_numbers = numbers(text)
            for pool in pools or [range(len(rows))]:
                eligible = [i for i in pool if not target_degree or not scopes
                            or (i in scopes and scopes[i][1] == target_degree)]
                if len(pools) <= 1:
                    eligible = [i for i in eligible if required_numbers <= numbers(' '.join(rows[i]))]
                if not eligible:
                    return None
                selected.add(max(eligible, key=lambda i: len(terms & set(normalized_tokens(' '.join(rows[i]))))))
        if len(headers) == 1 and wrapped_prose(rows):
            expanded = set(selected)
            for index in selected:
                left = right = index
                while left > 0 and index-left < 4 and _wrapped_line(rows[left-1][0],rows[left][0]):
                    left -= 1
                while right+1 < len(rows) and right-index < 4 and _wrapped_line(rows[right][0],rows[right+1][0]):
                    right += 1
                expanded.update(range(left,right+1))
            selected = expanded
        ordered = [row for i, row in enumerate(rows) if i in selected]
        # Bind a visible row to its physical semester scope when the PDF
        # provides one. Keep row boundaries in JSON; never paraphrase cells.
        scope = result.metadata.get('table_scope')
        selected_scopes = {scopes[i][0] for i in selected if i in scopes}
        if scopes and len(selected_scopes) == 1 and len(selected & scopes.keys()) == len(selected):
            start = next(iter(selected_scopes))
            # Empty programme cells inherit only the nearest original group.
            # Keep every intervening original row so the visible quotation
            # proves that scope; never replace an engineer row with a master
            # label or silently synthesize a filled-in source cell.
            scope = rows[start][programme_columns[0]]
            quote = json.dumps({'scope': scope, 'headers': headers,
                                'rows': rows[start:max(selected)+1]}, ensure_ascii=False)
        elif scope and result.metadata.get('table_scope_provenance') == 'explicit_pdf_marker':
            quote = json.dumps({'scope': str(scope), 'headers': headers, 'rows': ordered}, ensure_ascii=False)
        else:
            markers = []
            for index, row in enumerate(rows):
                text = ' '.join(cell for cell in row if cell.strip()).strip()
                match = re.fullmatch(r'(?i)semester\s+(\d+)', text)
                if match:
                    markers.append((index, text, match[1]))
            if markers:
                requested = re.search(r'(?i)\bsemester\s+(\d+)\b', question)
                target = min(selected)
                applicable = [item for item in markers if item[0] <= target]
                marker = next((item for item in reversed(applicable)
                               if not requested or item[2] == requested[1]), None)
                if marker and (not requested or marker[2] == requested[1]):
                    end = max(selected)
                    # A scope switch before the selected row means the exact
                    # section cannot be established from this table chunk.
                    if any(marker[0] < other[0] <= end and other[2] != marker[2]
                           for other in markers):
                        return None
                    quote = json.dumps({'scope': marker[1], 'headers': headers,
                                        'rows': rows[marker[0]:end + 1]}, ensure_ascii=False)
                else:
                    quote = json.dumps(ordered[0] if len(ordered) == 1 else ordered, ensure_ascii=False)
            else:
                quote = json.dumps(ordered[0] if len(ordered) == 1 else ordered, ensure_ascii=False)
        # Preserve every selected whole row or reject; never drop a claim's
        # evidence or stitch cells together to fit the public quote limit.
        return quote if len(quote) <= 1200 else None
    # An exact source-faithful claim identifies its own passage. A lexical
    # window can otherwise pick an earlier paragraph with common words and
    # hide the actual supporting condition from the public citation.
    compact=lambda value:' '.join(unicodedata.normalize('NFC',value).split())
    source=unicodedata.normalize('NFC',body)
    boundaries=list(re.finditer(r'[.!?](?:\s+|$)',source))
    question_ids = set(re.findall(r'\b[A-Z][A-Z0-9]{1,11}\b', question))
    def sentence_bounds(match):
        left=max((m.end() for m in boundaries if m.end()<=match.start()),default=0)
        right=next((m.end() for m in boundaries if m.end()>=match.end()),len(source))
        return left,right
    matches=[]
    for text in texts:
        candidates=list(re.finditer(r'\s+'.join(re.escape(part) for part in compact(text).split()),source,re.I))
        # Repeated clauses can describe different entities in the same chunk.
        # Prefer the occurrence whose own source sentence names the requested
        # identifier; a SAT question must not quote an identical HSA condition.
        def occurrence_rank(match):
            left,right=sentence_bounds(match)
            present=set(re.findall(r'\b[A-Z][A-Z0-9]{1,11}\b',source[left:right]))
            return len(question_ids & present),-match.start()
        matches.append(max(candidates,key=occurrence_rank) if candidates else None)
    if all(matches):
        start=min(m.start() for m in matches);end=max(m.end() for m in matches)
        left=max((m.end() for m in boundaries if m.end()<=start),default=0)
        right=next((m.end() for m in boundaries if m.end()>=end),len(source))
        # A period in a short article heading is a locator boundary, not a
        # separate supporting sentence. Keep that actual adjacent heading.
        headings = list(re.finditer(r'(?mi)^[ \t]*(?:(?:article|\u0111i\u1ec1u|dieu)\s+\d+[.:)]|'
                                    r'\d+(?:\.\d+)+\.?)[ \t]*(?:\n[ \t]*)?', source[:left]))
        if headings and not source[headings[-1].end():left].strip():
            if right - headings[-1].start() <= 1200:
                left = headings[-1].start()
        quote=source[left:right].strip()
        if len(quote)>1200:quote=source[start:end].strip()
        return quote if len(quote)<=1200 else None
    return verbatim_window(body, ' '.join(texts), 1200).strip() or None
