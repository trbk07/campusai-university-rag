"""Resolve model-selected source IDs to original evidence, never model coordinates."""
import json
import re
import unicodedata
from .policies import sanitize_evidence_text
from .source_windows import verbatim_window
from ..retrieval.tokenizer_vi import normalized_tokens, source_body
from .course_credits import COURSE_CODE, course_code_key, folded


def source_quote(result, claims, question=''):
    texts = [c['text'] for c in claims if isinstance(c, dict) and isinstance(c.get('text'), str)
             and result.chunk_id in c.get('citation_ids', [])]
    if not texts:
        return None
    body = sanitize_evidence_text(source_body({'content': result.content}, decode_tables=False))
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
        identity_columns = [i for i, header in enumerate(headers) if isinstance(header, str)
                            and folded(header) in {'course code', 'ma hoc phan', 'ma so hoc phan', 'ma so'}]
        selected = set()
        for text in texts:
            terms = set(normalized_tokens(text))
            codes = {course_code_key(m[0]) for m in re.finditer(r'(?<!\w)' + COURSE_CODE + r'(?!\w)', text, re.I)}
            pools = []
            for code in sorted(codes):
                matching = [i for i, row in enumerate(rows) if any(
                    course_code_key(row[column]) == code for column in
                    (identity_columns if identity_columns else range(len(row))) if column < len(row))]
                if matching:
                    pools.append(matching)
            for pool in pools or [range(len(rows))]:
                selected.add(max(pool, key=lambda i: len(terms & set(normalized_tokens(' '.join(rows[i]))))))
        ordered = [row for i, row in enumerate(rows) if i in selected]
        # Bind a visible row to its physical semester scope when the PDF
        # provides one. Keep row boundaries in JSON; never paraphrase cells.
        scope = result.metadata.get('table_scope')
        if scope and result.metadata.get('table_scope_provenance') == 'explicit_pdf_marker':
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
    matches=[re.search(r'\s+'.join(re.escape(part) for part in compact(text).split()),source,re.I)
             for text in texts]
    if all(matches):
        start=min(m.start() for m in matches);end=max(m.end() for m in matches)
        boundaries=list(re.finditer(r'[.!?](?:\s+|$)',source))
        left=max((m.end() for m in boundaries if m.end()<=start),default=0)
        right=next((m.end() for m in boundaries if m.end()>=end),len(source))
        # A period in a short article heading is a locator boundary, not a
        # separate supporting sentence. Keep that actual adjacent heading.
        headings = list(re.finditer(r'(?mi)^[ \t]*(?:article|\u0111i\u1ec1u|dieu)\s+\d+[.:)]\s*', source[:left]))
        if headings and not source[headings[-1].end():left].strip():
            if right - headings[-1].start() <= 1200:
                left = headings[-1].start()
        quote=source[left:right].strip()
        if len(quote)>1200:quote=source[start:end].strip()
        return quote if len(quote)<=1200 else None
    return verbatim_window(body, ' '.join(texts), 1200).strip() or None
