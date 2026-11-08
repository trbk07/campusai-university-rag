"""Literal table-heading proofs shared by ingestion and answer validation."""
import unicodedata

CODE_HEADERS = {'ma hoc phan','ma so hoc phan','ma so','ma hp','mahp','ma mon','course code','subject code'}
NAME_HEADERS = {'discipline','course name','ten hoc phan','hoc phan'}


def _folded(text):
    text=unicodedata.normalize('NFD',text.casefold()).replace('đ','d')
    return ' '.join(''.join(c for c in text if not unicodedata.combining(c)).split())


def credit_columns(headers):
    """Prefer explicit total-credit labels over BB/TC elective flags."""
    names=[_folded(h) for h in headers]
    columns=[i for i,h in enumerate(names) if h in
             {'so tin chi','credits','tong so tc','tong so tin chi','so tc','credit count'}]
    if not columns and 'bb' not in names:
        columns=[i for i,h in enumerate(names) if h in {'tc','tin chi'}]
    return columns


def embedded_credit_header(table, *, before_row=None):
    """Find an unambiguous printed column header beneath a merged title.

    Every embedded identity header must agree, including column positions.
    Nothing is filled in: callers retain/cite the actual original header row.
    """
    headers,rows=table.get('headers'),table.get('rows')
    if (not isinstance(headers,list) or not isinstance(rows,list) or not headers
            or any(not isinstance(h,str) for h in headers)):
        return None
    identities=CODE_HEADERS|NAME_HEADERS
    if any(_folded(h) in identities for h in headers):
        return None
    candidates=[]
    for index,row in enumerate(rows):
        if not isinstance(row,list) or len(row)!=len(headers) or any(not isinstance(c,str) for c in row):
            return None
        names=[_folded(c) for c in row]
        if not any(name in identities for name in names):continue
        codes=[i for i,name in enumerate(names) if name in CODE_HEADERS]
        subjects=[i for i,name in enumerate(names) if name in NAME_HEADERS]
        credits=credit_columns(row)
        if (len(credits)!=1 or len(codes)>1 or len(subjects)>1
                or not (codes or subjects) or credits[0] in codes+subjects):
            return None
        candidates.append((index,names))
    if not candidates or any(names!=candidates[0][1] for _,names in candidates):
        return None
    eligible=[index for index,_ in candidates if before_row is None or index<before_row]
    return (eligible[0] if before_row is None else eligible[-1]) if eligible else None
