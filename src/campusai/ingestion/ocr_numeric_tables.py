"""Closed numeric grids from pixels, with one independent cell recognition pass.

No text layer, source name, expected value or annotation enters this parser.
Every separator must be physically continuous; merged/open grids stay unread.
"""
import math
import re

NUMERIC_TABLE_POLICY = 'ruled-ocr-numeric-v1'
_SCALAR = re.compile(r'[+\-−]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\s*%?')


def _groups(values):
    groups = []
    for value in values:
        if groups and value - groups[-1][-1] <= 5:
            groups[-1].append(int(value))
        else:
            groups.append([int(value)])
    return [sum(group) / len(group) for group in groups]


def _numeric(value):
    if value.startswith('(') and value.endswith(')'):
        value = value[1:-1]
    return bool(_SCALAR.fullmatch(value))


def read_cell_jobs(gray, jobs, recognize_boxes):
    """Split real foreground lines, then batch recognition without redetection.

    Re-running a whole-page detector on dozens of tiny cells is slow and can
    lose a short header. Projection uses actual ink, preserving punctuation.
    """
    import cv2
    import numpy as np
    boxes, groups = [], []
    for job in jobs:
        a, b, c, d = [int(v) for v in job['bbox']]
        if not job['multiline']:
            source = job['word_bboxes']
            box = [max(a, min(v[0] for v in source)), max(b, min(v[1] for v in source)),
                   min(c, max(v[2] for v in source)), min(d, max(v[3] for v in source))]
            valid = box[0] < box[2] and box[1] < box[3]
            groups.append([len(boxes)] if valid else [])
            if valid:
                boxes.append(box)
            continue
        crop = gray[b:d, a:c]
        ink = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)[1]
        lines = []
        for y in np.flatnonzero((ink > 0).any(axis=1)):
            if lines and y-lines[-1][-1] <= 3:
                lines[-1].append(int(y))
            else:
                lines.append([int(y)])
        group = []
        if lines and len(lines) <= (4 if job['multiline'] else 1):
            for line in lines:
                top, bottom = line[0], line[-1]+1
                xs = np.flatnonzero((ink[top:bottom] > 0).any(axis=0))
                if not len(xs):
                    continue
                group.append(len(boxes))
                boxes.append([max(a, a+int(xs[0])-2), max(b, b+top-2),
                              min(c, a+int(xs[-1])+3), min(d, b+bottom+2)])
        groups.append(group)
    if len(boxes) > 512:
        return [('', 0.) for _ in jobs]
    output = recognize_boxes(boxes) if boxes else []
    if len(output) != len(boxes):
        raise ValueError('numeric OCR line count mismatch')
    return [(' '.join(output[i][0].strip() for i in group), min(float(output[i][1]) for i in group))
            if group and all(isinstance(output[i][0], str) and type(output[i][1]) in (int, float)
                             and math.isfinite(output[i][1]) and 0 <= output[i][1] <= 1 for i in group)
            else ('', 0.) for group in groups]


def validate_numeric_table(table):
    """Validate a publication-ready worker payload without trusting its label."""
    headers, rows = table['headers'], table['rows']
    identity = table.get('identity_column')
    scores = table.get('cell_recognition_confidences')
    if (type(identity) is not int or not 0 <= identity < len(headers)
            or not 3 <= len(headers) <= 16 or not 3 <= len(rows) <= 64
            or any(not row[identity] or _numeric(row[identity])
                   or any(not _numeric(value) for i, value in enumerate(row) if i != identity) for row in rows)
            or len({row[identity].casefold() for row in rows}) != len(rows)
            or table.get('recognition') != 'independent_physical_cell_pixels'
            or len({header.casefold() for header in headers}) != len(headers)
            or any(_numeric(header) and not re.fullmatch(r'(?:19|20)\d{2}', header) for header in headers)
            or not isinstance(scores, list) or len(scores) != (len(rows)+1)*len(headers)
            or any(type(score) not in (int, float) or not math.isfinite(score) or not .9 <= score <= 1
                   for score in scores)):
        raise ValueError('invalid numeric OCR cell proof')


def physical_tables(tables, transform, scale, origin):
    """Convert only documented pixel boxes; keep original grid edges explicit."""
    return [{**table, 'bbox': transform(table['bbox']),
             'row_bboxes': [transform(box) for box in table['row_bboxes']],
             'header_bboxes': [transform(box) for box in table['header_bboxes']],
             'geometry_coordinates': 'PDF points for boxes;render pixels for grid edges',
             'render_scale': scale, 'render_origin': list(origin)} for table in tables]


def assemble_numeric_tables(gray, words, recognize_cells, *, excluded_bboxes=()):
    """Return verified tables and source words, or the untouched original words.

    Recognition jobs carry physical cell interiors and a header/multiline flag.
    The callback must inspect those pixels, never a previous recognition label.
    Work is bounded across the page, not reset for every candidate.
    """
    import cv2
    import numpy as np
    if gray.ndim != 2 or gray.size > 20_000_000 or len(words) > 4096:
        raise ValueError('numeric OCR input bound')
    limit = min(8, max(0, 16-len(excluded_bboxes)))
    if not limit:
        return {'tables': [], 'words': words, 'recognition_jobs': 0}
    height, width = gray.shape
    ink = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                              cv2.THRESH_BINARY_INV, 35, 15)
    horizontal = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((1, max(25, width//40)), np.uint8))
    vertical = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((max(40, height//40), 1), np.uint8))
    combined = cv2.dilate(horizontal | vertical, np.ones((3, 3), np.uint8))
    _, _, components, _ = cv2.connectedComponentsWithStats(combined)
    candidates = [tuple(map(int, c)) for c in components[1:]
                  if c[2] >= 120 and c[3] >= 80 and c[4] >= 300]
    tables, replacements, jobs_used = [], [], 0
    for x, y, w, h, _ in candidates[:32]:
        vb = cv2.dilate(vertical[y:y+h, x:x+w], np.ones((1, 5), np.uint8))
        hb = cv2.dilate(horizontal[y:y+h, x:x+w], np.ones((5, 1), np.uint8))
        xs = [x+v for v in _groups(np.flatnonzero((vb > 0).sum(axis=0) > .8*h))]
        ys = [y+v for v in _groups(np.flatnonzero((hb > 0).sum(axis=1) > .85*w))]
        if not 4 <= len(xs) <= 17 or not 5 <= len(ys) <= 66:
            continue
        if min(xs)-x > 7 or x+w-max(xs) > 7 or min(ys)-y > 7 or y+h-max(ys) > 7:
            continue
        if any(b-a < 10 for a, b in zip(xs, xs[1:])) or any(b-a < 8 for a, b in zip(ys, ys[1:])):
            continue
        bbox = [xs[0], ys[0], xs[-1], ys[-1]]
        if any(min(bbox[2], b[2]) > max(bbox[0], b[0])
               and min(bbox[3], b[3]) > max(bbox[1], b[1]) for b in excluded_bboxes):
            continue
        # Validate every individual segment, not just the average line length.
        if any(np.count_nonzero(vertical[int(a)+2:int(b)-1, max(0, int(edge)-2):int(edge)+3].any(axis=1))
               < .9 * (int(b)-int(a)-3) for edge in xs for a, b in zip(ys, ys[1:])):
            continue
        if any(np.count_nonzero(horizontal[max(0, int(edge)-2):int(edge)+3, int(a)+2:int(b)-1].any(axis=0))
               < .9 * (int(b)-int(a)-3) for edge in ys for a, b in zip(xs, xs[1:])):
            continue
        cells = [[[] for _ in xs[1:]] for _ in ys[1:]]
        inside, ambiguous = [], False
        for word in words:
            a, b, c, d = word['bbox']
            if not (bbox[0] <= (a+c)/2 <= bbox[2] and bbox[1] <= (b+d)/2 <= bbox[3]):
                continue
            row = max(range(len(ys)-1), key=lambda i: max(0, min(d, ys[i+1])-max(b, ys[i])))
            col = max(range(len(xs)-1), key=lambda i: max(0, min(c, xs[i+1])-max(a, xs[i])))
            if (c <= a or d <= b or max(0, min(c, xs[col+1])-max(a, xs[col])) < .8*(c-a)
                    or max(0, min(d, ys[row+1])-max(b, ys[row])) < .8*(d-b)):
                ambiguous = True
                break
            cells[row][col].append(word)
            inside.append(word)
        # A real word in every body cell and at least one header word prevents
        # empty ruled forms, diagrams and extra blank rows from becoming data.
        if ambiguous or any(not cell for row in cells[1:] for cell in row) or any(not cell for cell in cells[0]):
            continue
        if any(max(word['bbox'][1] for word in cell) >= min(word['bbox'][3] for word in cell)
               for row in cells[1:] for cell in row):
            continue
        # Only attempt scalar grids: exactly one textual identity column.
        preliminary = [[' '.join(v['text'].strip() for v in cell).strip() for cell in row] for row in cells]
        identities = [i for i in range(len(xs)-1)
                      if all(not _numeric(row[i]) for row in preliminary[1:])]
        if len(identities) != 1 or any(not _numeric(row[i]) for row in preliminary[1:]
                                     for i in range(len(xs)-1) if i != identities[0]):
            continue
        count = (len(xs)-1)*(len(ys)-1)
        if jobs_used+count > 128:
            continue
        jobs = [{'bbox': [a+3, top+3, b-3, bottom-3], 'multiline': row == 0,
                 'word_bboxes': [v['bbox'] for v in cells[row][col]]}
                for row, (top, bottom) in enumerate(zip(ys, ys[1:]))
                for col, (a, b) in enumerate(zip(xs, xs[1:]))]
        if sum((j['bbox'][2]-j['bbox'][0])*(j['bbox'][3]-j['bbox'][1]) for j in jobs) > 4_000_000:
            continue
        jobs_used += count
        recognized = recognize_cells(jobs)
        if not isinstance(recognized, (list, tuple)) or len(recognized) != count:
            raise ValueError('numeric OCR cell count mismatch')
        values = []
        for text, confidence in recognized:
            if (not isinstance(text, str) or not text.strip() or len(text) > 4096
                    or type(confidence) not in (int, float) or not math.isfinite(confidence)
                    or not .9 <= confidence <= 1):
                break
            values.append(text.strip())
        if len(values) != count:
            continue
        rows = [values[i:i+len(xs)-1] for i in range(0, count, len(xs)-1)]
        identity = identities[0]
        if (any(_numeric(row[identity]) or any(not _numeric(v) for i, v in enumerate(row) if i != identity)
                for row in rows[1:]) or len({row[identity].casefold() for row in rows[1:]}) != len(rows)-1
                or len({header.casefold() for header in rows[0]}) != len(rows[0])
                or any(_numeric(header) and not re.fullmatch(r'(?:19|20)\d{2}', header) for header in rows[0])):
            continue
        table = {'headers': rows[0], 'rows': rows[1:], 'bbox': bbox,
                 'header_bboxes': [[a, ys[0], b, ys[1]] for a, b in zip(xs, xs[1:])],
                 'row_bboxes': [[xs[0], a, xs[-1], b] for a, b in zip(ys[1:], ys[2:])],
                 'column_edges': xs, 'row_edges': ys, 'identity_column': identity,
                 'cell_recognition_confidences': [float(c) for _, c in recognized],
                 'unresolved_cells': [], 'split_words': [], 'parser': NUMERIC_TABLE_POLICY,
                 'recognition': 'independent_physical_cell_pixels'}
        tables.append(table)
        replacements.append((inside, [{'text': value, 'bbox': job['bbox'], 'confidence': float(conf)}
                                     for value, job, (_, conf) in zip(values, jobs, recognized)]))
        if len(tables) == limit:
            break
    changed = list(words)
    for old, new in replacements:
        identities = {id(word) for word in old}
        changed = [word for word in changed if id(word) not in identities]
        changed.extend(new)
    return {'tables': tables, 'words': sorted(changed, key=lambda w: (w['bbox'][1], w['bbox'][0]))
            if tables else words, 'recognition_jobs': jobs_used}
