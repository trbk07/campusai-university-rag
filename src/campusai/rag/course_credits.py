"""Prove simple course-credit assertions from explicitly headed source tables.

Bare text numbers, programme totals, hours and prerequisite columns do not
establish a course's credit value. Only directly cited tables are inspected.
"""
import json
import re
import unicodedata

COURSE_CODE = r'[a-z]{2,5}\s*\d{3,5}[a-z]?'


def course_code_key(code: str) -> str:
    """Canonicalize a parsed code, allowing spacing only before its digits."""
    return re.sub(r'\s+', '', code).upper()


def folded(text):
    value = unicodedata.normalize('NFD', text.casefold()).replace('đ', 'd')
    return ' '.join(''.join(c for c in value if not unicodedata.combining(c)).split())


def course_name_key(name: str) -> str:
    """Ignore presentation spacing/case, retaining accents and punctuation."""
    return ' '.join(unicodedata.normalize('NFC', name).casefold().split())


def headed_credit_rows(content: str, *, identity: str = 'code'):
    """Return explicit identity/credit cells, retaining invalid values as None."""
    start = content.find('{"headers"')
    if start < 0:
        return None
    try:
        table = json.loads(content[start:])
    except (ValueError, TypeError):
        return None
    if not isinstance(table, dict):
        return None
    headers, rows = table.get('headers'), table.get('rows')
    if (not isinstance(headers, list) or any(not isinstance(h, str) for h in headers)
            or not isinstance(rows, list)):
        return None
    names = [folded(header) for header in headers]
    identity_headers = ({'ma hoc phan', 'ma so hoc phan', 'ma so', 'course code'}
                        if identity == 'code' else {'discipline', 'course name', 'ten hoc phan', 'hoc phan'})
    code_cols = [i for i, name in enumerate(names) if name in identity_headers]
    credit_cols = [i for i, name in enumerate(names) if name in {'so tin chi', 'credits'}]
    if len(code_cols) != 1 or len(credit_cols) != 1 or code_cols[0] == credit_cols[0]:
        return None
    code_col, credit_col = code_cols[0], credit_cols[0]
    output = []
    for row in rows:
        if (not isinstance(row, list) or len(row) <= max(code_col, credit_col)
                or not isinstance(row[code_col], str) or not isinstance(row[credit_col], str)):
            continue
        code = (re.sub(r'\s+', '', row[code_col]).upper() if identity == 'code'
                else course_name_key(row[code_col]))
        if not code or (identity == 'code' and not re.fullmatch(r'[A-Z]{2,5}\d{3,5}[A-Z]?', code)):
            continue
        value = row[credit_col].strip()
        output.append((code, int(value) if value.isascii() and value.isdigit() and len(value) <= 6 else None, row))
    return output


def course_credit_support(claim_text: str, content: str) -> bool | None:
    """Return an exact headed-row verdict, or None when no such proof exists."""
    match = re.fullmatch(
        r'(?:mon|hoc phan|course)\s+(' + COURSE_CODE + r')\s+'
        r'(?:co|has|carries|is worth)\s+(\d+)\s+(?:tin chi|credits?)\s*[.!]?', folded(claim_text))
    identity = 'code'
    if match:
        key = course_code_key(match[1])
    else:
        # Parse names without stripping accents or punctuation. Never infer a
        # unit from nearby numbers: only an explicitly headed credit column.
        match = re.fullmatch(
            r'(?:môn|học phần|course)\s+(.+?)\s+'
            r'(?:có|has|carries|is worth)\s+([0-9]+)\s+(?:tín chỉ|credits?)\s*[.!]?',
            course_name_key(claim_text))
        if not match:
            return None
        identity = 'name'
        key = course_name_key(match[1])
    rows = headed_credit_rows(content, identity=identity)
    if rows is None:
        return None
    values = {value for code, value, _row in rows if code == key}
    if None in values:
        return None
    if len(values) != 1:
        return None
    return int(match[2]) == next(iter(values))
