"""Date evidence must establish applicability rather than merely mention years."""
import pytest
from campusai.ingestion.metadata_detector import detect_metadata


def test_issue_date_does_not_establish_effective_date():
    value = detect_metadata('## Page 2\nban hành ngày 01/08/2025')
    assert value['issue_date'] == '2025-08-01'
    assert value['effective_date'] is None
    assert value['metadata_evidence']['issue_date']['source_page'] == 2
    assert value['metadata_evidence']['issue_date']['evidence'] == 'ban hành ngày 01/08/2025'


def test_dates_have_separate_exact_source_clauses():
    value = detect_metadata('Program: Engineering\nIssue date: 01/08/2025\n## Page 3\nEffective date: 01/09/2025')
    assert value['issue_date'] == '2025-08-01'
    assert value['effective_date'] == '2025-09-01'
    assert value['effective_date_source_page'] == 3
    assert value['effective_date_evidence'] == 'Effective date: 01/09/2025'


@pytest.mark.parametrize('raw,expected,precision', [
    ('tháng 09 năm 2025', '2025-09', 'month'), ('năm 2025', '2025', 'year'),
    ('31/02/2025', None, None), ('không được nêu', None, None),
    ('ngày 31 tháng 2 năm 2025', None, None), ('31 February 2025', None, None),
])
def test_partial_and_invalid_dates_never_invent_day(raw, expected, precision):
    value = detect_metadata('ngày hiệu lực: ' + raw)
    assert value['effective_date'] is None
    entry = value['temporal']['dates']['effective_date']
    if expected:
        assert (entry['value'], entry['precision']) == (expected, precision)
    else:
        assert entry is None


def test_signing_rule_requires_explicit_proven_issue_date():
    value = detect_metadata('Issue date: 11/12/2020\nQuyết định có hiệu lực kể từ ngày ký.')
    assert value['effective_date'] == '2020-12-11'
    assert 'ngày ký' in value['effective_date_evidence']
    assert detect_metadata('Quyết định có hiệu lực kể từ ngày ký.')['effective_date'] is None


def test_no_cross_clause_date_borrowing_or_conflict_resolution():
    assert detect_metadata('có hiệu lực từ ngày ký.\nMột văn bản khác ban hành ngày 01/01/2025')['effective_date'] is None
    assert detect_metadata('Effective date: 01/09/2025\nEffective date: 01/10/2025')['effective_date'] is None
    assert detect_metadata('Quy định có hiệu lực.\nLịch sử tham chiếu ngày 01/01/2025')['effective_date'] is None
    assert detect_metadata('Quyết định có hiệu lực kể từ ngày ký.\nMột văn bản khác ban hành ngày 01/01/2025')['effective_date'] is None
    assert detect_metadata('Quyết định chưa có hiệu lực từ 01/01/2025')['effective_date'] is None


def test_cohort_is_separate_from_version_year_and_calendar_year():
    value = detect_metadata('Version: 2023\nÁp dụng cho sinh viên từ khóa tuyển sinh năm 2022.\nNăm học 2024-2025.')
    assert value['version'] == '2023'
    assert value['temporal']['cohort_start']['value'] == 2022
    assert value['temporal']['academic_period']['value'] == '2024-2025'
    assert value['effective_date'] is None
