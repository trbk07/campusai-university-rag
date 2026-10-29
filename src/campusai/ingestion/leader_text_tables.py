"""Recover closed two-column text grids with aligned source dot leaders.

No header vocabulary, annotation or expected value is used. Full outer rules,
a continuous internal divider and repeated aligned leader runs are required.
"""
from __future__ import annotations

import re

from .partial_numeric_tables import _box, _lines, _unique

_LEADER = re.compile(r'[.\u00b7\u2026]{3,}')


def _divider(vertical, left, right, top, bottom):
    groups = []
    for edge in vertical:
        if not left + 30 < edge['x0'] < right - 30:
            continue
        if edge['bottom'] <= top or edge['top'] >= bottom:
            continue
        group = next((g for g in groups if abs(g[0]['x0'] - edge['x0']) <= 1), None)
        if group is None:
            groups.append([edge])
        else:
            group.append(edge)
    if len(groups) != 1:
        return None
    edges = sorted(groups[0], key=lambda e: e['top'])
    if abs(edges[0]['top'] - top) > 1 or abs(max(e['bottom'] for e in edges) - bottom) > 1:
        return None
    reached = top
    for edge in edges:
        if edge['top'] > reached + 1:
            return None
        reached = max(reached, edge['bottom'])
    return edges[0]['x0'] if reached >= bottom - 1 else None


def _grid(words, left, right, top, header_end, bottom, divider):
    inside = [w for w in words if left <= (w['x0'] + w['x1']) / 2 <= right
              and top < (w['top'] + w['bottom']) / 2 < bottom]
    if not inside:
        return None
    edges = [left, divider, right]
    header = [[], []]
    body = []
    for word in inside:
        column = int((word['x0'] + word['x1']) / 2 >= divider)
        if word['x0'] < edges[column] - 1 or word['x1'] > edges[column + 1] + 1:
            return None
        if (word['top'] + word['bottom']) / 2 < header_end:
            header[column].append(word)
        else:
            body.append(word)
    if not all(header) or not body:
        return None
    for i, cell in enumerate(header):
        box = _box(cell); width = edges[i + 1] - edges[i]
        if box[2] - box[0] > .75 * width or abs((box[0] + box[2]) / 2 - (edges[i] + edges[i + 1]) / 2) > max(5, .04 * width):
            return None
    columns = [[w for w in body if int((w['x0'] + w['x1']) / 2 >= divider) == i] for i in (0, 1)]
    if not all(columns):
        return None
    margins = [min(w['x0'] for w in cell) for cell in columns]
    lines = _lines(body)
    rows = []
    first_left_end = wrapped = previous_y = None
    for line in lines:
        cells = [[w for w in line if int((w['x0'] + w['x1']) / 2 >= divider) == i] for i in (0, 1)]
        y = min(w['top'] for w in line)
        anchor = cells[0] and abs(cells[0][0]['x0'] - margins[0]) <= 1.5
        if anchor:
            if not cells[1] or abs(cells[1][0]['x0'] - margins[1]) > 1.5:
                return None
            if not any(c.isalpha() for w in cells[0] for c in w['text']):
                return None
            rows.append(cells)
            first_left_end = cells[0][-1]['x1']
            wrapped = False
        else:
            # Only a source hanging wrap may extend the primary label.
            # Right-only indented lines continue their own cell. A flush-left
            # right paragraph needs a source-wrapped primary label, not an
            # invented identity for an unvalued row or a global footnote.
            if (not rows or y - previous_y > 2 * max(w['bottom'] - w['top'] for w in line)
                    or len(rows[-1][0]) + len(rows[-1][1]) + len(line) > 500):
                return None
            if cells[0]:
                if (cells[0][0]['x0'] - margins[0] < 3
                        or first_left_end - margins[0] < .75 * (divider - left)
                        or any(_LEADER.fullmatch(w['text']) for w in cells[0])
                        or cells[1] and cells[1][0]['x0'] - margins[1] < 3):
                    return None
                wrapped = True
            if cells[1] and cells[1][0]['x0'] - margins[1] < 3 and not wrapped:
                return None
            for i in (0, 1):
                rows[-1][i].extend(cells[i])
        previous_y = y
        if len(rows) > 256:
            return None
    leaders = [w for row in rows for w in row[0] if _LEADER.fullmatch(w['text'])]
    if (len(rows) < 3 or len(leaders) < 3
            or max(w['x1'] for w in leaders) - min(w['x1'] for w in leaders) > 1.5
            or not 1 <= divider - max(w['x1'] for w in leaders) <= 12):
        return None
    text = lambda cell: ' '.join(w['text'] for line in _lines(cell) for w in line)
    return {'rows': [[text(cell) for cell in header], *[[text(cell) for cell in row] for row in rows]],
            'edges': edges, 'bbox': [left, top, right, bottom],
            'parser': 'pdfplumber-leader-text-grid-v1',
            'proof': {'table_bbox': [left, top, right, bottom],
                      'header_bboxes': [_box(cell) for cell in header],
                      'row_bboxes': [_box(row[0] + row[1]) for row in rows],
                      'cell_bboxes': [[_box(cell) for cell in row] for row in rows],
                      'leader_bboxes': [_box([word]) for word in leaders],
                      'row_grouping': 'aligned_primary_column_with_hanging_wraps_v1'}}


def leader_text_records(page):
    """Read source-only grids; reject incomplete borders/cells or ambiguity."""
    horizontal = getattr(page, 'horizontal_edges', [])
    if len(horizontal) > 1024:
        return []
    groups = []
    for edge in horizontal:
        if edge['x1'] - edge['x0'] < 100:
            continue
        group = next((g for g in groups if abs(g[0]['x0'] - edge['x0']) <= 1
                      and abs(g[0]['x1'] - edge['x1']) <= 1), None)
        if group is None:
            groups.append([edge])
        else:
            group.append(edge)
    if not groups or len(groups) > 32:
        return []
    vertical = getattr(page, 'vertical_edges', [])
    if not vertical or len(vertical) > 1024:
        return []
    plans = []
    for group in groups:
        levels = _unique(e['top'] for e in group)
        if len(levels) > 32:
            return []
        for i, (top, header_end) in enumerate(zip(levels, levels[1:])):
            if 8 <= header_end - top <= 40:
                plans.extend((group[0]['x0'], group[0]['x1'], top, header_end, bottom)
                             for bottom in levels[i + 2:] if 15 <= bottom - header_end <= 600)
    if not plans or len(plans) > 64:
        return []
    words = page.extract_words()
    if len(words) > 5000:
        return []
    records = []
    for left, right, top, header_end, bottom in plans:
        divider = _divider(vertical, left, right, top, bottom)
        if divider is not None:
            record = _grid(words, left, right, top, header_end, bottom, divider)
            if record:
                records.append(record)
    return records
