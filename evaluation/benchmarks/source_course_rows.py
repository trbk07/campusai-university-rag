"""Read source-proved curriculum rows by explicit column roles.

This extractor proposes facts only. It does not assign benchmark splits,
review approval, exposure eligibility or evidence sufficiency at serving.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata


def normalized_header(text: str) -> str:
    text = re.sub(r'\s+', ' ', text.replace('\u00a0', ' '))
    value = unicodedata.normalize('NFKD', text.casefold().replace('đ', 'd'))
    return ' '.join(value.encode('ascii', 'ignore').decode('ascii').split())


def _column(headers: list[str], role: str) -> int | None:
    accepted = {
        'code': {'ma so', 'ma hoc phan', 'ma so hoc phan', 'course code'},
        'name': {'hoc phan', 'ten hoc phan', 'course', 'course name', 'subject', 'discipline'},
        'credits': {'so tin chi', 'credits'},
        'prerequisites': {'ma hoc phan tien quyet', 'ma so hoc phan tien quyet', 'prerequisites'},
    }[role]
    positions = []
    for number, header in enumerate(headers):
        value = normalized_header(header)
        # Bilingual name instructions describe the column, not a second name.
        if role == 'name':
            value = re.sub(r'\s*\((?:ghi bang )?tieng viet va tieng anh\)\s*$', '', value)
        if value in accepted:
            positions.append(number)
    return positions[0] if len(positions) == 1 else None


def source_course_rows(evidence: dict[tuple[str, str], dict]) -> list[dict]:
    """Preserve source row/column hashes; never read a credit value from hours."""
    facts = []
    for (doc, chunk), item in sorted(evidence.items()):
        if item.get('content_type') != 'table':
            continue
        content = item.get('content', '')
        if not isinstance(content, str):
            continue
        start = content.find('{"headers"')
        if start < 0:
            continue
        try:
            table = json.loads(content[start:])
        except (ValueError, TypeError):
            continue
        headers, rows = table.get('headers'), table.get('rows')
        if (not isinstance(headers, list) or any(not isinstance(h, str) for h in headers)
                or not isinstance(rows, list)):
            continue
        columns = {role: _column(headers, role) for role in ('code','name','credits','prerequisites')}
        required = [columns[role] for role in ('code','name','credits')]
        if None in required or len(set(required)) != 3:
            continue
        for number, cells in enumerate(rows):
            if (not isinstance(cells, list) or len(cells) <= max(required)
                    or any(not isinstance(cell, str) for cell in cells)):
                continue
            code = re.sub(r'\s+', '', cells[columns['code']])
            name = ' '.join(cells[columns['name']].split())
            credit = cells[columns['credits']].strip()
            if (not re.fullmatch(r'(?:[A-Z]{2,5}\.)?[A-Z]{2,5}\d{3,5}[A-Z]?', code) or len(name) < 5
                    or not credit.isdigit() or not 0 < int(credit) < 30):
                continue
            prerequisite = columns['prerequisites']
            prerequisite_text = cells[prerequisite] if prerequisite is not None and prerequisite < len(cells) else ''
            compact = re.sub(r'\s+', '', prerequisite_text)
            prerequisites = None
            if compact and re.fullmatch(r'(?:[A-Z]{2,5}\.)?[A-Z]{2,5}\d{3,5}[A-Z]?(?:[,;](?:[A-Z]{2,5}\.)?[A-Z]{2,5}\d{3,5}[A-Z]?)*', compact):
                prerequisites = re.split(r'[,;]', compact)
            cells_bytes = json.dumps(cells, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
            facts.append({'doc_id':doc,'chunk_id':chunk,'page':item['page'],'table_row':number,
                          'code':code,'name':name,'name_lines':cells[columns['name']].splitlines(),
                          'credits':int(credit),'prerequisite_codes':prerequisites,
                          'prerequisite_text':prerequisite_text,'columns':columns,
                          'headers':headers,'source_content_sha256':hashlib.sha256(content.encode('utf-8')).hexdigest(),
                          'cells_sha256':hashlib.sha256(cells_bytes).hexdigest()})
    return facts
