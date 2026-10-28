"""Catch optimistic denominators and geometry contamination in PDF scoring."""
import random

import pytest

from evaluation.pdf_text_quality import (
    character_distance, normalized_text, recognition_route, score_text_regions,
)


def _slow_distance(first, second):
    previous = list(range(len(second) + 1))
    for i, left in enumerate(first, 1):
        row = [i]
        for j, right in enumerate(second, 1):
            row.append(min(previous[j] + 1, row[-1] + 1,
                           previous[j-1] + (left != right)))
        previous = row
    return previous[-1]


def test_distance_agrees_with_independent_dynamic_programming():
    rng = random.Random(428)
    for _ in range(500):
        a = ''.join(rng.choices('ađé3🙂', k=rng.randrange(30)))
        b = ''.join(rng.choices('ađé3🙂', k=rng.randrange(30)))
        assert character_distance(a, b) == _slow_distance(a, b)


def test_normalization_retains_accents_numbers_case_and_width():
    assert normalized_text('  ti\u0301n\nchỉ  3 ') == 'tín chỉ 3'
    assert normalized_text('３ TÍN CHỈ') != normalized_text('3 tín chỉ')


def test_missing_region_counts_all_characters_and_line_is_not_reused():
    gold = [{'id': 'left', 'text': 'ABC', 'bbox': [0, 0, 10, 10]},
            {'id': 'right', 'text': 'DEF', 'bbox': [10, 0, 20, 10]}]
    report = score_text_regions(gold, [{'text': 'ABC', 'bbox': [1, 1, 9, 9]}])
    assert report['gold_characters'] == 6 and report['edits'] == 3
    assert report['micro_character_accuracy'] == .5
    assert report['rows'][1]['prediction'] == ''


def test_overlapping_reference_tie_cannot_duplicate_correct_prediction():
    gold = [{'id': key, 'text': 'ABC', 'bbox': [0, 0, 10, 10]}
            for key in ('one', 'two')]
    report = score_text_regions(gold, [{'text': 'ABC', 'bbox': [1, 1, 9, 9]}])
    assert report['edits'] == 6
    assert len(report['unassigned_prediction_lines']) == 1


def test_outside_output_is_retained_without_claiming_full_page_accuracy():
    report = score_text_regions([{'id': 'body', 'text': 'ABC', 'bbox': [0, 0, 10, 10]}],
                                [{'text': 'extra', 'bbox': [20, 20, 30, 30]}])
    assert report['micro_character_accuracy'] == 0
    assert report['unassigned_prediction_lines'][0]['text'] == 'extra'
    assert 'not release acceptance' in report['scope']


@pytest.mark.parametrize('boxes', [[0, 0, 0, 1], [0, 0, float('nan'), 2],
                                  [False, 0, 2, 2], [0, 0, float('inf'), 2]])
def test_bad_coordinates_fail_closed(boxes):
    with pytest.raises(ValueError):
        score_text_regions([{'id': 'a', 'text': 'ABC', 'bbox': boxes}], [])


@pytest.mark.parametrize('gold', [[], [{'id': 'a', 'text': ' ', 'bbox': [0, 0, 1, 1]}],
    [{'id': 'a', 'text': 'A', 'bbox': [0, 0, 1, 1]}] * 2])
def test_empty_or_duplicate_reference_cannot_produce_green_metric(gold):
    with pytest.raises(ValueError):
        score_text_regions(gold, [])


def test_native_hybrid_and_ocr_are_distinct_denominators():
    assert recognition_route('body', False) == 'native'
    assert recognition_route('body', True) == 'hybrid'
    assert recognition_route('', True) == 'ocr'
    assert recognition_route('', False) == 'empty'
    with pytest.raises(ValueError):
        recognition_route('body', 'true')
