"""Recover bounded numeric grids whose body has no horizontal cell borders.

Only source geometry supplies columns, headers and rows. Incomplete numeric
vectors and ambiguous continuations reject the candidate rather than fill cells.
"""
from __future__ import annotations

import re

_NUMBER = re.compile(r"[-+]?\(?\d[\d.,]*\)?%?")


def _lines(words):
    lines = []
    for word in sorted(words, key=lambda w: (w['top'], w['x0'])):
        if not lines or abs(word['top'] - lines[-1][0]['top']) > 2:
            lines.append([word])
        else:
            lines[-1].append(word)
    return [sorted(line, key=lambda w: w['x0']) for line in lines]


def _box(words):
    return [min(w['x0'] for w in words), min(w['top'] for w in words),
            max(w['x1'] for w in words), max(w['bottom'] for w in words)]


def _unique(values):
    result = []
    for value in sorted(values):
        if not result or value - result[-1] > 1:
            result.append(value)
    return result


def _grid(words, vertical, left, right, top, header_end, bottom):
    dividers = [edge for edge in vertical if left + 3 < edge['x0'] < right - 3
                and min(edge['bottom'], header_end) - max(edge['top'], top) >= 5]
    edges = [left, *_unique(e['x0'] for e in dividers), right]
    if not 2 <= len(edges) - 1 <= 12:
        return None
    inside = [w for w in words if left <= (w['x0'] + w['x1']) / 2 <= right
              and top < (w['top'] + w['bottom']) / 2 < bottom]
    if not inside or len(inside) > 5000:
        return None
    if any(w['x0'] < left - 1 or w['x1'] > right + 1 for w in inside):
        return None
    header = [w for w in inside if (w['top'] + w['bottom']) / 2 < header_end]
    body = [w for w in inside if (w['top'] + w['bottom']) / 2 >= header_end]
    if not header or len(header) > 200 or not body:
        return None
    headers = [[] for _ in edges[:-1]]
    spans = []
    # A divider starting halfway through a header is not active above its
    # start. The actual spanning parent label applies to every child column.
    for line in _lines(header):
        y = sum((w['top'] + w['bottom']) / 2 for w in line) / len(line)
        active = [left, *_unique(e['x0'] for e in dividers
                  if e['top'] - 1 <= y <= e['bottom'] + 1), right]
        for x0, x1 in zip(active, active[1:]):
            part = [w for w in line if x0 <= (w['x0'] + w['x1']) / 2 < x1]
            if not part:
                continue
            text = ' '.join(w['text'] for w in part)
            columns = [i for i, (a, b) in enumerate(zip(edges, edges[1:]))
                       if x0 <= (a + b) / 2 < x1]
            for i in columns:
                headers[i].append(text)
            spans.append({'text': text, 'columns': columns, 'bbox': _box(part)})
    headers = [' '.join(parts) for parts in headers]
    if not all(headers[1:]):
        return None
    rows, row_boxes, cell_boxes, pending = [], [], [], []
    for line in _lines(body):
        cells = [[] for _ in headers]
        for word in line:
            center = (word['x0'] + word['x1']) / 2
            i = next(i for i, (a, b) in enumerate(zip(edges, edges[1:])) if a <= center <= b)
            if word['x0'] < edges[i] - 1 or word['x1'] > edges[i + 1] + 1:
                return None
            cells[i].append(word)
        values = [' '.join(w['text'] for w in cell) for cell in cells]
        if not any(values[1:]):
            # A wrapped label must fill the subject column. Short unvalued
            # headings, footnotes and prose are not silently assigned a value.
            if (not cells[0] or cells[0][-1]['x1'] - cells[0][0]['x0'] < .75 * (edges[1] - left)
                    or pending):
                return None
            pending = cells[0]
            continue
        if (not values[0] or not any(c.isalpha() for c in values[0])
                or not all(_NUMBER.fullmatch(v.replace(' ', '')) for v in values[1:])):
            return None
        if pending:
            # Require the source's hanging indent, not an inferred semantic
            # relationship between a previous label and the next numeric row.
            if cells[0][0]['x0'] - pending[0]['x0'] < 3:
                return None
            cells[0] = pending + cells[0]
            values[0] = ' '.join(w['text'] for w in cells[0])
            pending = []
        rows.append(values)
        row_boxes.append(_box([w for cell in cells for w in cell]))
        cell_boxes.append([_box(cell) for cell in cells])
    if pending or len(rows) < 3:
        return None
    return {'rows': [headers, *rows], 'edges': edges, 'bbox': [left, top, right, bottom],
            'proof': {'table_bbox': [left, top, right, bottom], 'header_spans': spans,
                      'row_bboxes': row_boxes, 'cell_bboxes': cell_boxes},
            'parser': 'pdfplumber-partial-numeric-grid-v1'}


def partial_numeric_records(page):
    """Find closed, partially ruled numeric tables without reading annotations."""
    groups = []
    for edge in getattr(page, 'horizontal_edges', []):
        if edge['x1'] - edge['x0'] < 80:
            continue
        group = next((g for g in groups if abs(g[0]['x0'] - edge['x0']) <= 1
                      and abs(g[0]['x1'] - edge['x1']) <= 1), None)
        if group is None:
            groups.append([edge])
        else:
            group.append(edge)
    groups = [g for g in groups if 3 <= len(g) <= 32]
    if not groups or len(groups) > 32:
        return []
    vertical = getattr(page, 'vertical_edges', [])
    if not vertical:
        return []
    attempts = sum(1 for group in groups
        for position, (top, header_end) in enumerate(zip(
            _unique(e['top'] for e in group), _unique(e['top'] for e in group)[1:]))
        if 8 <= header_end - top <= 60
        for bottom in _unique(e['top'] for e in group)[position + 2:]
        if 15 <= bottom - header_end <= 600)
    if attempts > 64:
        return []
    words = page.extract_words()
    if len(words) > 5000:
        return []
    candidates = []
    for group in groups:
        left, right = group[0]['x0'], group[0]['x1']
        levels = _unique(e['top'] for e in group)
        for position, (top, header_end) in enumerate(zip(levels, levels[1:])):
            if not 8 <= header_end - top <= 60:
                continue
            valid = []
            for bottom in levels[position + 2:]:
                if not 15 <= bottom - header_end <= 600:
                    continue
                record = _grid(words, vertical, left, right, top, header_end, bottom)
                if record:
                    following = next((value for value in levels if value > bottom + 1), None)
                    tail = [w for w in words if left <= (w['x0'] + w['x1']) / 2 <= right
                            and bottom < (w['top'] + w['bottom']) / 2 < (following or bottom)]
                    if tail:
                        line = _lines(tail)[0]
                        cells = [[] for _ in record['edges'][:-1]]
                        compatible = True
                        for word in line:
                            center = (word['x0'] + word['x1']) / 2
                            i = next(i for i, (a, b) in enumerate(zip(record['edges'], record['edges'][1:]))
                                     if a <= center <= b)
                            compatible &= word['x0'] >= record['edges'][i] - 1 and word['x1'] <= record['edges'][i+1] + 1
                            cells[i].append(word)
                        base = min(boxes[0][0] for boxes in record['proof']['cell_bboxes'])
                        aligned = cells[0] and abs(cells[0][0]['x0'] - base) <= 1.5
                        numeric = any(cells[1:]) and all(not cell or
                            _NUMBER.fullmatch(''.join(w['text'] for w in cell)) for cell in cells[1:])
                        if compatible and (aligned or numeric):
                            # A subtotal cannot hide a later incomplete row.
                            # Only accept a later closing boundary if its whole
                            # body also passes the grid checks above.
                            continue
                    valid.append(record)
            if valid:
                # Subtotal separators are not the end of a larger valid grid.
                candidates.append(max(valid, key=lambda r: r['bbox'][3]))
    return candidates
