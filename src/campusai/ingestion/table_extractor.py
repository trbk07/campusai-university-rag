"""Conservative extraction of simple text-rendered PDF tables."""

from __future__ import annotations

import re
from pathlib import Path

from ..schemas import Table

_COLUMN_SEPARATOR = re.compile(r"\s{2,}|\|")
_NUMBER = re.compile(r"[-+]?\(?\d[\d.,]*\)?%?")
_COURSE_CODE = re.compile(r"(?:(?:[A-Z]{2,5})\.)?[A-Z]{2,5}\s*\d{3,5}[A-Z]?",re.I)
_COURSE_SERIAL = re.compile(r"\d+(?:\.\d+)*")
TABLE_EXTRACTOR_VERSION = "table-v3-inherited-multipage-course-columns"


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


def _extract_pdfplumber(pdf_path: str | Path, doc_id: str) -> list[Table]:
    import pdfplumber

    tables: list[Table] = []
    course_headers = None
    course_columns = None
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            page_start=len(tables)
            active_course_section = False
            active_course_section_label = None
            raw_tables=page.extract_tables() or []
            for table_number, raw_table in enumerate(raw_tables, start=1):
                rows = [["" if cell is None else str(cell).strip() for cell in row] for row in raw_table]
                rows = [row for row in rows if any(row)]
                if len(rows) < 2:
                    # Some PDF table finders split a visually continuous table
                    # into one-row fragments. Reuse only a prior explicit
                    # course/credits header, and only after a semester marker
                    # has established the page's active table section.
                    if course_headers and course_columns and active_course_section:
                        inherited_rows = _course_rows(rows, course_columns)
                        if inherited_rows:
                            width = len(course_headers)
                            tables.append(Table(
                                table_id=f"{doc_id}_p{page_number}_t{table_number}",
                                doc_id=doc_id,
                                pages=[page_number],
                                headers=list(course_headers),
                                rows=inherited_rows,
                                schema={"columns": width, "row_count": len(inherited_rows),
                                        "parser": "pdfplumber-inherited-course-columns-v1",
                                        "pages": [page_number], "warnings": [],
                                        "raw_preserved": True,
                                        "section": active_course_section_label,
                                        "section_provenance": "explicit_pdf_marker"},
                            ))
                    continue
                width = max(map(len, rows))
                rows = [row + [""] * (width - len(row)) for row in rows]
                explicit_course_columns = _inherited_course_columns(rows[0])
                if explicit_course_columns:
                    course_headers = list(rows[0])
                    course_columns = explicit_course_columns
                tables.append(Table(
                    table_id=f"{doc_id}_p{page_number}_t{table_number}",
                    doc_id=doc_id,
                    pages=[page_number],
                    headers=rows[0],
                    rows=rows[1:],
                    schema={"columns": width, "row_count": len(rows) - 1,
                            "parser": "pdfplumber", "pages": [page_number],
                            "warnings": [], "raw_preserved": True},
                ))
                if course_headers and course_columns and not explicit_course_columns:
                    # A fragment with a real prior header can restore column
                    # meaning without treating its first data row as headers.
                    # Retain only rows in the explicitly marked semester.
                    inherited_rows = []
                    for row in rows:
                        row_text = " ".join(row).casefold()
                        semester = re.search(r"\bsemester\s*(\d+)\b", row_text)
                        if semester:
                            active_course_section = True
                            active_course_section_label = f"Semester {semester.group(1)}"
                            continue
                        if re.search(r"\bcredits?\s+per\s+semester\b", row_text):
                            continue
                        if not active_course_section:
                            continue
                        inherited_rows.extend(_course_rows([row], course_columns))
                    if inherited_rows:
                        tables[-1] = Table(
                            table_id=f"{doc_id}_p{page_number}_t{table_number}",
                            doc_id=doc_id,
                            pages=[page_number],
                            headers=list(course_headers),
                            rows=inherited_rows,
                            schema={"columns": len(course_headers), "row_count": len(inherited_rows),
                                    "parser": "pdfplumber-inherited-course-columns-v1",
                                    "pages": [page_number], "warnings": [],
                                    "raw_preserved": True,
                                    "section": active_course_section_label,
                                    "section_provenance": "explicit_pdf_marker"},
                        )
                    else:
                        tables.pop()
                        # Keep page-level raw text extraction as the fallback
                        # for fragments outside a verified course section.
            # Shaded header/row bands can look like a one-column ruled table
            # to pdfplumber and capture only the first row. Prefer a verified
            # complete aligned-column table; otherwise preserve old behavior.
            if not any(len(table.headers)>=2 for table in tables[page_start:]):
                aligned=_aligned_course_tables(page,doc_id,page_number)
                if aligned:tables[page_start:]=aligned
    return tables


def extract_tables(
    pages: list[dict], doc_id: str, pdf_path: str | Path | None = None
) -> list[Table]:
    """Extract candidate tables and merge adjacent repeated-header pages.

    The extractor preserves raw cell text. Ambiguous rows are retained with a
    warning in the schema instead of being silently rewritten.
    """
    if pdf_path is not None:
        parsed = _extract_pdfplumber(pdf_path, doc_id)
        if parsed:
            # Keep the heuristic parser as a page-level fallback. pdfplumber
            # can miss a tab-aligned or merged-cell table on one page while
            # finding another table elsewhere in the document.
            parsed_pages = {page for table in parsed for page in table.pages}
            fallback = _extract_heuristic_tables(pages, doc_id)
            parsed.extend(table for table in fallback if table.pages[0] not in parsed_pages)
            return parsed
    return _extract_heuristic_tables(pages, doc_id)


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
