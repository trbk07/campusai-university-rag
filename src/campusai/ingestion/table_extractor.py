"""Conservative extraction of simple text-rendered PDF tables."""

from __future__ import annotations

import re
import os
from pathlib import Path

from ..schemas import Table

_COLUMN_SEPARATOR = re.compile(r"\s{2,}|\|")
_NUMBER = re.compile(r"[-+]?\(?\d[\d.,]*\)?%?")
_COURSE_CODE = re.compile(r"(?:(?:[A-Z]{2,5})\.)?[A-Z]{2,5}\s*\d{3,5}[A-Z]?",re.I)
_COURSE_SERIAL = re.compile(r"\d+(?:\.\d+)*")
TABLE_EXTRACTOR_VERSION = "table-v6-leader-text-grid"


def _word_lines(words):
    """Keep physical baselines; never flatten separate source rows together."""
    lines=[]
    for word in sorted(words,key=lambda w:(w['top'],w['x0'])):
        if not lines or abs(word['top']-lines[-1][0]['top'])>2:
            lines.append([word])
        else:lines[-1].append(word)
    return [sorted(line,key=lambda w:w['x0']) for line in lines]


def _aligned_course_tables(page,doc_id,page_number):
    """Strict fallback for single-line, physically aligned course/credit rows.

    Explicit code and credit headers and at least three complete aligned rows
    are mandatory. Any continuation, missing cell or ambiguous row rejects the
    fallback. Preserve every column and actual bounding boxes, not guessed units
    from nearby numbers. Ruled tables keep their existing parser.
    """
    lines=_word_lines(page.extract_words());tables=[]
    for header_line in lines:
        groups=[]
        for word in header_line:
            if not groups or word['x0']-groups[-1][-1]['x1']>16:groups.append([word])
            else:groups[-1].append(word)
        headers=[' '.join(w['text'] for w in group) for group in groups]
        names=[h.casefold() for h in headers]
        codes=[i for i,n in enumerate(names) if n in {'course code','mã học phần','mã số học phần'}]
        credits=[i for i,n in enumerate(names) if n in {'credits','số tín chỉ','tín chỉ'}]
        if len(codes)!=1 or len(credits)!=1 or codes==credits or not 2<=len(groups)<=8:continue
        boundaries=[float('-inf')]+[(a[-1]['x1']+b[0]['x0'])/2 for a,b in zip(groups,groups[1:])]+[float('inf')]
        def cells(line):
            values=[[] for _ in headers]
            for word in line:
                center=(word['x0']+word['x1'])/2
                column=next(i for i in range(len(headers)) if boundaries[i]<=center<boundaries[i+1])
                values[column].append(word['text'])
            return [' '.join(value) for value in values]
        below=[line for line in lines if line[0]['top']>max(w['bottom'] for w in header_line)]
        candidates=[(line,cells(line)) for line in below if _COURSE_CODE.fullmatch(cells(line)[codes[0]])]
        if len(candidates)<3:continue
        first,last=candidates[0][0][0]['top'],candidates[-1][0][0]['top']
        body=[line for line in below if first<=line[0]['top']<=last]
        # Extra physical lines inside the body would make a multi-line cell or
        # column association ambiguous. Do not silently discard them.
        if len(body)!=len(candidates):continue
        rows=[row for _line,row in candidates]
        if any(not all(row) or not re.fullmatch(r'[0-9]{1,6}',row[credits[0]]) for row in rows):continue
        if first-max(w['bottom'] for w in header_line)>30:continue
        tables.append(Table(table_id=f'{doc_id}_p{page_number}_t{len(tables)+1}',doc_id=doc_id,
            pages=[page_number],headers=headers,rows=rows,
            schema={'columns':len(headers),'row_count':len(rows),'pages':[page_number],
                'parser':'pdfplumber-aligned-course-columns-v1','warnings':[], 'raw_preserved':True,
                'header_bboxes':[[min(w['x0'] for w in g),min(w['top'] for w in g),max(w['x1'] for w in g),max(w['bottom'] for w in g)] for g in groups],
                'row_bboxes':[[min(w['x0'] for w in line),min(w['top'] for w in line),max(w['x1'] for w in line),max(w['bottom'] for w in line)] for line,_row in candidates]}))
    return tables


def _inherited_course_columns(headers):
    """Return the serial, subject, credit and source columns of a known schema."""
    names=[re.sub(r"\s+"," ",str(value or "").strip().casefold()) for value in headers]
    subject_labels={"discipline","subject","course","course name","subject name","module"}
    credit_labels={"credit","credits","credit point","credit points","tín chỉ","số tín chỉ"}
    source_labels={"resource","resources","source","institution","provider"}
    subjects=[i for i,name in enumerate(names) if name in subject_labels]
    credits=[i for i,name in enumerate(names) if name in credit_labels]
    sources=[i for i,name in enumerate(names) if name in source_labels]
    if len(subjects)!=1 or len(credits)!=1 or len(sources)!=1:
        return None
    remaining=[i for i in range(len(names)) if i not in {subjects[0],credits[0],sources[0]}]
    if len(remaining)!=1:
        return None
    return remaining[0],subjects[0],credits[0],sources[0]


def _course_rows(rows,columns):
    serial,subject,credit,source=columns
    valid=[]
    for raw in rows:
        row=["" if value is None else str(value).strip() for value in raw]
        row += [""] * max(0, max(columns)+1-len(row))
        if (serial < len(row) and _COURSE_SERIAL.fullmatch(row[serial])
                and subject < len(row) and row[subject]
                and credit < len(row) and re.fullmatch(r"\d+(?:\.\d+)?",row[credit])
                and source < len(row) and row[source]):
            valid.append(row)
    return valid


def _split_row(line: str) -> list[str]:
    cleaned = line.strip()
    if "|" in cleaned:
        # Empty pipe-delimited cells carry column positions. Dropping one
        # shifts later values (for example, a page number into prerequisites).
        if cleaned.startswith("|"):
            cleaned = cleaned[1:]
        if cleaned.endswith("|"):
            cleaned = cleaned[:-1]
        return [cell.strip() for cell in cleaned.split("|")]
    return [cell.strip() for cell in _COLUMN_SEPARATOR.split(cleaned) if cell.strip()]


def _is_candidate(line: str) -> bool:
    cells = _split_row(line)
    if len(cells) < 2:
        return False
    # Document navigation often uses the same visual spacing as a table
    # (for example, "PRINCIPLE 03" or "STEP 01").  It is a layout marker,
    # not a structured row, and accepting it creates false tables.
    if cells[0].casefold() in {"principle", "step"} and len(cells) == 2:
        return False
    numeric_cells = sum(bool(_NUMBER.fullmatch(cell.replace(" ", ""))) for cell in cells)
    return "|" in line or numeric_cells >= 1


def _visible_native_page(page, characters):
    """Keep character identities actually painted in the original PDF."""
    import fitz
    by_text = {}
    for char in characters:
        by_text.setdefault(char['text'], []).append(fitz.Rect(char['bbox']))
    def visible(item):
        if item.get('object_type') != 'char':
            return True
        rect = fitz.Rect(item['x0'], item['top'], item['x1'], item['bottom'])
        return any((rect & box).get_area() >= .5 * min(rect.get_area(), box.get_area())
                   and abs(rect.x0-box.x0) <= max(1., .3*box.width)
                   for box in by_text.get(item.get('text'), []) if rect.get_area() and box.get_area())
    return page.filter(visible).dedupe_chars(tolerance=1, extra_attrs=())


def _page_packet(page, doc_id, page_number):
    physical_tables = page.find_tables() or []
    records = []
    for number, physical in enumerate(physical_tables, 1):
        rows = [["" if cell is None else str(cell).strip() for cell in row]
                for row in physical.extract()]
        rows = [row for row in rows if any(row)]
        if not rows:
            continue
        width = max(map(len, rows))
        records.append({'number':number, 'rows':[row+[""]*(width-len(row)) for row in rows],
                        'edges':sorted({float(cell[i]) for cell in physical.cells for i in (0, 2)}),
                        'bbox': [min(c[0] for c in physical.cells), min(c[1] for c in physical.cells),
                                 max(c[2] for c in physical.cells), max(c[3] for c in physical.cells)]})
    def collapsed(record):
        return any(row[1:] and all(len(cell.splitlines()) > 1 and
            all(_NUMBER.fullmatch(value.strip()) for value in cell.splitlines())
            for cell in row[1:]) for row in record['rows'][1:])
    if not records or any(collapsed(record) for record in records):
        from .partial_numeric_tables import partial_numeric_records
        for candidate in partial_numeric_records(page):
            a = candidate['bbox']
            overlap = [record for record in records if
                min(a[2], record['bbox'][2]) > max(a[0], record['bbox'][0]) and
                min(a[3], record['bbox'][3]) > max(a[1], record['bbox'][1])]
            if overlap:
                if len(overlap) != 1:
                    continue
                old = overlap[0]; b = old['bbox']
                if (not collapsed(old) or not (a[0]-1 <= b[0] and a[1]-1 <= b[1]
                        and a[2]+1 >= b[2] and a[3]+1 >= b[3])
                        or len(candidate['rows'][0]) < len(old['rows'][0])
                        or len(candidate['rows']) <= len(old['rows'])):
                    continue
                candidate['number'] = old['number']
                records[records.index(old)] = candidate
            else:
                candidate['number'] = max([len(physical_tables), *[r['number'] for r in records]]) + 1
                records.append(candidate)
    if not records:
        from .leader_text_tables import leader_text_records
        for candidate in leader_text_records(page):
            candidate['number'] = len(records) + 1
            records.append(candidate)
    # Such a table always survives the ordered semantic assembly below, so the
    # aligned fallback cannot replace it. Otherwise compute that fallback now,
    # using the same already decoded page, independent of adjacent-page state.
    aligned = ([] if any(len(r['rows']) >= 2 and len(r['rows'][0]) >= 2 for r in records)
               else _aligned_course_tables(page, doc_id, page_number))
    return {'page':page_number, 'physical_tables':bool(physical_tables),
            'records':records, 'aligned':aligned}


def _read_page_batch(pdf_path, doc_id, page_numbers, visibility):
    import pdfplumber
    packets = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for number in page_numbers:
            page = pdf.pages[number-1]
            if visibility and number in visibility:
                page = _visible_native_page(page, visibility[number])
            packets.append(_page_packet(page, doc_id, number))
            page.close()
    return packets


def _table_page_packets(pdf_path, doc_id, visibility):
    """Parallelize only physical decoding; semantics stay ordered in the parent.

    Four workers per document, at most twelve with the app's three ingestion
    jobs. Each reads the original PDF, never shares an interpreter/file handle.
    Small PDFs and environments unable to spawn keep the sequential path.
    """
    import fitz
    import multiprocessing
    from concurrent.futures import ProcessPoolExecutor
    from concurrent.futures.process import BrokenProcessPool
    with fitz.open(pdf_path) as pdf:
        count = len(pdf)
    workers = min(4, os.cpu_count() or 1, max(1, count//24))
    if workers > 1:
        try:
            size = (count+workers-1)//workers
            batches = [list(range(start, min(count+1, start+size))) for start in range(1,count+1,size)]
            with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context('spawn')) as pool:
                futures = [pool.submit(_read_page_batch, str(pdf_path), doc_id, batch, visibility)
                           for batch in batches]
                # Finish all batches before emitting evidence. Failure must not
                # mix a partial parallel result with its sequential fallback.
                packets = [packet for future in futures for packet in future.result()]
            return packets
        except (OSError, BrokenProcessPool):
            pass
    return _read_page_batch(pdf_path, doc_id, range(1,count+1), visibility)


def _extract_pdfplumber(pdf_path: str | Path, doc_id: str, *, visibility=None) -> list[Table]:

    tables: list[Table] = []
    course_headers = course_columns = header_source = header_edges = None
    def marker(row):
        cells = [c for c in row if c.strip()]
        match = re.fullmatch(r'semester\s*(\d+)', ' '.join(cells), re.I) if len(cells) == 1 else None
        return f'Semester {match[1]}' if match else None
    def subtotal(row):
        return any(re.fullmatch(r'credits?\s*per\s+semester', c, re.I) for c in row)
    def known_row(row):
        label = re.fullmatch(r'(?:compulsory|elective|optional) subjects',
                             ' '.join(c for c in row if c.strip()), re.I)
        return marker(row) or subtotal(row) or label or _course_rows([row], course_columns)
    def compatible(edges):
        if not header_edges or len(edges) != len(header_edges):
            return False
        # A whole fragment may shift horizontally. Its column widths must
        # still match the actual explicit header's physical grid.
        return all(abs((b-a)-(d-c)) <= 1.0 for a,b,c,d in
                   zip(edges, edges[1:], header_edges, header_edges[1:]))
    for packet in _table_page_packets(pdf_path, doc_id, visibility):
        page_number = packet['page']
        if visibility is not None and page_number in visibility:
            course_headers = course_columns = header_source = header_edges = None
        page_start=len(tables)
        active_course_section_label = None
        for record in packet['records']:
            table_number, rows, edges = record['number'], record['rows'], record['edges']
            width = len(rows[0])
            explicit_course_columns = _inherited_course_columns(rows[0])
            identity = f"{doc_id}_p{page_number}_t{table_number}"
            if explicit_course_columns:
                course_headers = list(rows[0])
                course_columns = explicit_course_columns
                header_edges = edges if len(edges) == width + 1 else None
                header_source = {"page": page_number, "table_id": identity,
                                 "column_edges": edges, "headers": list(course_headers)}
                active_course_section_label = None
                headers, body, parser = rows[0], rows[1:], 'pdfplumber'
            else:
                inherited = (course_headers and course_columns and width == len(course_headers)
                    and compatible(edges) and all(known_row(row) for row in rows))
                if inherited:
                    # The first source row is data, not a replacement
                    # header. Keep every marker, subtotal and spillover row.
                    headers, body, parser = list(course_headers), rows, 'pdfplumber-inherited-course-columns-v2'
                else:
                    course_headers = course_columns = header_source = header_edges = None
                    active_course_section_label = None
                    if len(rows) < 2:
                        continue
                    headers, body, parser = rows[0], rows[1:], record.get('parser', 'pdfplumber')
            scopes = []
            course_scopes = set()
            if course_columns:
                for row in body:
                    label = marker(row)
                    if label:
                        active_course_section_label = label
                    scopes.append(active_course_section_label)
                    if _course_rows([row], course_columns):
                        course_scopes.add(active_course_section_label)
                    if subtotal(row):
                        active_course_section_label = None
                # Multiple scopes and unknown leading course rows cannot
                # acquire the last marker as one table-wide section.
            schema = {"columns": len(headers), "row_count": len(body),
                      "parser": parser, "pages": [page_number],
                      "warnings": [], "raw_preserved": True, "column_edges": edges}
            schema.update(record.get('proof', {}))
            if header_source:
                schema['header_source'] = dict(header_source)
                schema['row_scopes'] = scopes
            if len(course_scopes) == 1 and None not in course_scopes:
                schema.update(section=next(iter(course_scopes)), section_provenance='explicit_pdf_marker')
            tables.append(Table(
                table_id=identity,
                doc_id=doc_id,
                pages=[page_number],
                headers=headers,
                rows=body,
                schema=schema,
            ))
        if not packet['physical_tables']:
            course_headers = course_columns = header_source = header_edges = None
        # Shaded header/row bands can look like a one-column ruled table
        # to pdfplumber and capture only the first row. Prefer a verified
        # complete aligned-column table; otherwise preserve old behavior.
        if not any(len(table.headers)>=2 for table in tables[page_start:]):
            aligned=packet['aligned']
            if aligned:tables[page_start:]=aligned
    return tables


def extract_tables(
    pages: list[dict], doc_id: str, pdf_path: str | Path | None = None
) -> list[Table]:
    """Extract candidate tables and merge adjacent repeated-header pages.

    The extractor preserves raw cell text. Ambiguous rows are retained with a
    warning in the schema instead of being silently rewritten.
    """
    optical=[]
    for page in pages:
        if page.get('ocr_tables'):
            from .ocr_tables import validate_tables
            for i,raw in enumerate(validate_tables(page['ocr_tables']),1):
                schema={key:value for key,value in raw.items() if key not in {'headers','rows','unresolved_cells','split_words'}}
                schema.update(columns=len(raw['headers']),row_count=len(raw['rows']),pages=[int(page['page'])],
                    raw_preserved=True,warnings=[],header_source={'kind':'rendered_ocr_grid','page':int(page['page'])})
                optical.append(Table(table_id=f"{doc_id}_p{page['page']}_ocr_t{i}",doc_id=doc_id,
                    pages=[int(page['page'])],headers=raw['headers'],rows=raw['rows'],schema=schema))
    fallback_pages=[page for page in pages
                    if not page.get('ocr_tables') and not page.get('untrusted_native_mapping')]
    if pdf_path is not None:
        visibility = {page['page']:page['visible_characters'] for page in pages
                      if page.get('ignored_invisible_spans') or page.get('untrusted_native_mapping')}
        parsed = (_extract_pdfplumber(pdf_path, doc_id, visibility=visibility) if visibility
                  else _extract_pdfplumber(pdf_path, doc_id))
        if parsed:
            # Keep the heuristic parser as a page-level fallback. pdfplumber
            # can miss a tab-aligned or merged-cell table on one page while
            # finding another table elsewhere in the document.
            parsed_pages = {page for table in parsed for page in table.pages}
            fallback = _extract_heuristic_tables(fallback_pages, doc_id)
            parsed.extend(table for table in fallback if table.pages[0] not in parsed_pages)
            return parsed + optical
    return _extract_heuristic_tables(fallback_pages, doc_id) + optical


def _extract_heuristic_tables(pages: list[dict], doc_id: str) -> list[Table]:
    """Extract tables from already-flattened page text as a fallback."""
    tables: list[Table] = []
    for page in pages:
        page_number = int(page["page"])
        lines = [line.strip() for line in str(page.get("text", "")).splitlines() if line.strip()]
        candidates = [line for line in lines if _is_candidate(line)]
        if len(candidates) < 2:
            continue

        rows = [_split_row(line) for line in candidates]
        width = max(len(row) for row in rows)
        warnings: list[str] = []
        if any(len(row) != width for row in rows):
            warnings.append("inconsistent_column_count")
        rows = [row + [""] * (width - len(row)) for row in rows]
        headers, body = rows[0], rows[1:]

        previous = tables[-1] if tables else None
        if previous and previous.headers == headers and previous.pages[-1] == page_number - 1:
            previous.rows.extend(body)
            previous.pages.append(page_number)
            previous.schema["pages"] = previous.pages
            previous.schema["row_count"] = len(previous.rows)
            previous.schema["warnings"] = sorted(set(previous.schema.get("warnings", []) + warnings))
            continue

        table_id = f"{doc_id}_p{page_number}_t1"
        tables.append(
            Table(
                table_id=table_id,
                doc_id=doc_id,
                pages=[page_number],
                headers=headers,
                rows=body,
                schema={
                    "columns": width,
                    "row_count": len(body),
                    "parser": "heuristic",
                    "pages": [page_number],
                    "warnings": warnings,
                    "raw_preserved": True,
                },
            )
        )
    return tables
