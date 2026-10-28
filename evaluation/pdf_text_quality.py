"""Literal PDF text metrics; reference geometry is used only after inference.

These scores measure annotated text recognition. They do not attest reference
review, reading order, unannotated content, table structure or release readiness.
"""
from __future__ import annotations

import math
import unicodedata


def normalized_text(text: str) -> str:
    if not isinstance(text, str):
        raise ValueError('text must be a string')
    return ' '.join(unicodedata.normalize('NFC', text).split())


def character_distance(expected: str, actual: str) -> int:
    """Exact Levenshtein distance using bit vectors, with no optional dependency."""
    if not expected:
        return len(actual)
    positions: dict[str, int] = {}
    for index, character in enumerate(expected):
        positions[character] = positions.get(character, 0) | (1 << index)
    positive, negative = ~0, 0
    score, last = len(expected), 1 << (len(expected) - 1)
    for character in actual:
        equal = positions.get(character, 0)
        vertical = equal | negative
        horizontal = (((equal & positive) + positive) ^ positive) | equal
        add = negative | ~(horizontal | positive)
        remove = positive & horizontal
        score += bool(add & last) - bool(remove & last)
        add, remove = (add << 1) | 1, remove << 1
        positive = remove | ~(vertical | add)
        negative = add & vertical
    return score


def _box(value):
    if (not isinstance(value, (list, tuple)) or len(value) != 4
            or any(type(x) not in (int, float) or not math.isfinite(x) for x in value)
            or value[0] >= value[2] or value[1] >= value[3]):
        raise ValueError('invalid text rectangle')
    return tuple(value)


def _intersection(first, second):
    return (max(0, min(first[2], second[2]) - max(first[0], second[0]))
            * max(0, min(first[3], second[3]) - max(first[1], second[1])))


def score_text_regions(regions: list[dict], lines: list[dict]) -> dict:
    """Match source-only predicted lines to reference regions in the same units.

    Every nonempty reference remains in the denominator, including unmatched
    regions. A predicted line is assigned at most once. Ambiguous and out-of-
    region lines remain observable, rather than being copied to several regions.
    Serialization differences in formulas/HTML must be reported by the caller;
    this function deliberately does not rewrite either gold or predictions.
    """
    if not regions:
        raise ValueError('at least one literal reference region is required')
    identifiers, prepared = set(), []
    for region in regions:
        identifier = region['id']
        if not isinstance(identifier, str) or not identifier or identifier in identifiers:
            raise ValueError('reference IDs must be unique nonempty strings')
        identifiers.add(identifier)
        expected = normalized_text(region['text'])
        if not expected:
            raise ValueError('empty reference would conceal the denominator')
        prepared.append({'id': identifier, 'bbox': _box(region['bbox']),
                         'expected': expected, 'lines': []})
    unassigned = []
    for line in lines:
        box, text = _box(line['bbox']), normalized_text(line['text'])
        if not text:
            continue
        area = (box[2] - box[0]) * (box[3] - box[1])
        ranked = sorted(((_intersection(box, r['bbox']) / area, i)
                         for i, r in enumerate(prepared)), reverse=True)
        if (ranked[0][0] < .5 or len(ranked) > 1
                and ranked[0][0] - ranked[1][0] <= 1e-8):
            unassigned.append({'text': text, 'bbox': list(box)})
        else:
            prepared[ranked[0][1]]['lines'].append(text)
    rows = []
    for region in prepared:
        actual = normalized_text('\n'.join(region['lines']))
        expected = region['expected']
        edits = character_distance(expected, actual)
        rows.append({'id': region['id'], 'gold_characters': len(expected),
                     'prediction_characters': len(actual), 'edits': edits,
                     'character_accuracy': 1 - edits / len(expected),
                     'expected': expected, 'prediction': actual})
    characters = sum(row['gold_characters'] for row in rows)
    edits = sum(row['edits'] for row in rows)
    return {'gold_regions': len(rows), 'gold_characters': characters,
            'edits': edits, 'micro_character_accuracy': 1 - edits / characters,
            'rows': rows, 'unassigned_prediction_lines': unassigned,
            'scope': 'Annotated literal text recognition only;not release acceptance'}


def recognition_route(native_text: str, ocr_attempted: bool) -> str:
    """An OCR call for an illustration does not turn native body text into OCR."""
    if type(ocr_attempted) is not bool:
        raise ValueError('OCR route must be explicit')
    has_native = bool(normalized_text(native_text))
    return ('hybrid' if has_native else 'ocr') if ocr_attempted else 'native' if has_native else 'empty'
