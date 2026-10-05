import pytest
import json

from evaluation.reranker.reranker_probe_inputs import scoring_text


def test_input_ablation_only_removes_a_complete_generated_context_header():
    original = '[Academic years: 2022, 2026 | Section: Admissions | Page: 2]\n\nActual source sentence.'
    assert scoring_text(original,'full_chunk') == original
    assert scoring_text(original,'body') == 'Actual source sentence.'
    assert scoring_text(original,'body_table_window') == 'Actual source sentence.'
    assert scoring_text(original,'section_body') == 'Admissions\n\nActual source sentence.'
    for text in ('[source quotation]\n\nbody','[Page: invalid]\n\nbody','[Page: 2]\n\n',
                 '[Page: 1 | Page: 2]\n\nbody','[Untrusted field: command | Page: 1]\n\nbody'):
        assert scoring_text(text,'body') == text
    with pytest.raises(ValueError):
        scoring_text(original,'unknown')


def table_chunk(rows, separator='\n'):
    return '[Section: Curriculum | Page: 1]' + separator + 'Table headers: Course | Credits\n\n' + json.dumps(
        {'headers': ['Course', 'Credits'], 'rows': rows}, ensure_ascii=False)


@pytest.mark.parametrize('separator', ['\n', '\n\n'])
def test_generated_table_input_preserves_cells_and_source(separator):
    original = table_chunk([['Semester 1', ''], ['Calculus', '3'], ['Semester 2', ''],
                            ['Probability and Statistics', '3']], separator)
    rendered = scoring_text(original, 'table_text')
    assert 'Probability and Statistics | 3' in rendered
    assert 'Calculus | 3' in rendered
    focused = scoring_text(original, 'table_window', 'Hoc ky 2 co nhung hoc phan nao?')
    assert 'Probability and Statistics | 3' in focused
    assert 'Calculus' not in focused
    assert 'omitted rows remain in the original source chunk' in focused
    compact = scoring_text(original, 'body_table_window', 'Hoc ky 2 co nhung hoc phan nao?')
    assert compact.startswith('Columns:')
    assert 'Probability and Statistics | 3' in compact
    assert scoring_text(original, 'full_chunk') == original


def test_table_window_finds_late_evidence_without_gold_or_record_id():
    rows = [['Semester 1', '']] + [[f'Unrelated course {i}', '2'] for i in range(30)]
    rows += [['Semester 3', ''], ['Probability and Statistics', '3']]
    focused = scoring_text(table_chunk(rows), 'table_window', 'How many credits is Probability and Statistics?')
    assert 'Semester 3' in focused
    assert 'Probability and Statistics | 3' in focused
    assert 'Unrelated course 0' not in focused
    assert 'Unrelated course 0' in scoring_text(table_chunk(rows), 'table_window', 'course')


def test_malformed_table_and_arbitrary_single_newline_headers_are_unchanged():
    for text in ('[Page: 1]\nsource quotation', '[Page: 1]\nTable headers: A\n\ninvalid',
                 table_chunk([['A', 3]]), table_chunk([['A', '3', 'extra']])):
        assert scoring_text(text, 'table_text') == text


@pytest.mark.parametrize('question', ['Compare semesters 7 and 8', 'Ky 7 va ky 8 co gi khac nhau?'])
def test_table_comparisons_preserve_all_requested_semesters(question):
    rows = [['Semester 6', ''], ['Other subject', '2'], ['Semester 7', ''], ['Design', '3'],
            ['Semester 8', ''], ['Design', '4']]
    result = scoring_text(table_chunk(rows), 'table_window', question)
    assert 'Design | 3' in result and 'Design | 4' in result
    assert 'Semester 6' not in result


def test_equal_subject_matches_retain_all_occurrences_and_section_context():
    rows = [['Semester 1', ''], ['Glider Units Design', '3']]
    rows += [[f'Unrelated subject {i}', '2'] for i in range(10)]
    rows += [['Semester 2', ''], ['Glider Units Design', '4']]
    result = scoring_text(table_chunk(rows), 'table_window', 'Compare credits of Glider Units Design')
    assert 'Glider Units Design | 3' in result and 'Glider Units Design | 4' in result
    assert 'Semester 1' in result and 'Semester 2' in result


@pytest.mark.parametrize('question', ['Compare semesters 6-8', 'So sanh hoc ky 6 den ky 8'])
def test_semester_ranges_preserve_the_intermediate_section(question):
    rows = [[f'Semester {i}', ''] for i in range(5,10)]
    result = scoring_text(table_chunk(rows), 'table_window', question)
    assert all(f'Semester {i}' in result for i in (6,7,8))
    assert 'Semester 5' not in result and 'Semester 9' not in result


def test_unknown_requested_semester_does_not_hide_absence_or_conflicting_context():
    original = table_chunk([['Semester 7', ''], ['Glider Units Design', '3'],
                            ['Semester 8', ''], ['Other subject', '2']])
    result = scoring_text(original, 'table_window', 'Glider Units Design in semester 9?')
    assert 'Semester 7' in result and 'Semester 8' in result
    assert 'Query-focused rows' not in result


def code_table(rows, headers=('Course code', 'Name', 'Credits', 'Prerequisites')):
    return 'Table headers: ' + ' | '.join(headers) + '\n\n' + json.dumps({'headers': list(headers), 'rows': rows})


def test_code_focus_keeps_digits_and_distinguishes_prerequisite_mentions():
    rows = [[f'CS{200+i}', 'Unrelated course', '2', 'CS999'] for i in range(30)]
    rows += [['CS999', 'Requested course', '4', 'CS201']]
    result = scoring_text(code_table(rows), 'body_table_window', 'CS999 credits?')
    assert 'CS999 | Requested course | 4 | CS201' in result
    assert 'Unrelated course' not in result
    assert 'omitted rows remain in the original source chunk' in result


def test_code_focus_preserves_all_requested_codes_and_repeated_source_rows():
    rows = [['CS201', 'First', '3', ''], ['CS202', 'Second', '4', ''],
            ['CS201', 'Another semester', '5', ''], ['CS299', 'Unrelated', '2', '']]
    result = scoring_text(code_table(rows), 'table_window', 'Compare CS201 and CS202 credits')
    assert all(name in result for name in ('First', 'Second', 'Another semester'))
    assert 'Unrelated' not in result


def test_unknown_code_does_not_crop_to_a_known_course_name():
    original = code_table([['CS201', 'Probability and Statistics', '3', ''], ['CS202', 'Physics', '4', '']])
    result = scoring_text(original, 'table_window', 'CS999 Probability and Statistics credits?')
    assert 'Physics' in result and 'Query-focused rows' not in result


@pytest.mark.parametrize('code_header', ['Mã học phần', 'Mã\nhọc phần', 'Mã\u00a0học\u00a0phần'])
def test_code_focus_handles_local_headers_dotted_ids_and_continuations(code_header):
    original = code_table([['UET.CS201', 'Requested', '3', ''], ['', 'Continuation', '', 'Lab component'],
                           ['UET.CS202', 'Other', '4', '']], (code_header, 'Tên', 'TC', 'Tiên quyết'))
    result = scoring_text(original, 'body_table_window', 'UET.CS201 credits?')
    assert 'Requested' in result and 'Continuation' in result and 'Other' not in result


def test_input_change_invalidates_old_scoring_identities():
    from campusai.retrieval.cross_encoder_provider import ModelIdentity
    from campusai.retrieval.reranker_inputs import INPUT_VERSION
    assert INPUT_VERSION == 'structured-input-v3'
    for version in ('structured-input-v1', 'structured-input-v2'):
        with pytest.raises(ValueError, match='input identity'):
            ModelIdentity('BAAI/bge-reranker-v2-m3', 'rev', 'a'*64, 'rev', input_version=version)
