"""Temporal mechanics are synthetic contracts, not real-source model quality."""
from datetime import date


def test_legacy_index_cohort_uses_exact_source_proof_without_inventing_effective_date():
    from campusai.rag.temporal import document_from_items, verified_documents, parse_temporal_intent, resolve_temporal
    item = {'chunk_id': 'legacy-clause', 'page': 2, 'content': 'The curriculum applies from cohort 2024.', 'metadata': {}}
    document = document_from_items('legacy-source', [item])
    verified = verified_documents([document])
    assert verified[0]['cohort_start'] == 2024
    assert verified[0]['evidence_ids'] == ('legacy-clause',)
    assert 'effective_start' not in verified[0]
    intent = parse_temporal_intent('For cohort 2024, what is the duration?', reference_date=date(2026, 1, 1))
    assert resolve_temporal(intent, [document]).status == 'resolved'
    intent = parse_temporal_intent('What is current?', reference_date=date(2026, 1, 1))
    assert resolve_temporal(intent, [document]).status == 'insufficient_evidence'
import pytest
from campusai.rag.temporal import TemporalIntent, parse_temporal_intent, resolve_temporal, temporal_fingerprint


def document(doc_id, version, start=None, end=None, family='Campus/Engineering', replaces=(), published=None):
    block = dict(family_id=family, version_label=version, proofs={})
    values = dict(family_id=family, version_label=version, effective_start=start,
                  effective_end=end, published_on=published, replaces=list(replaces) or None)
    phrases = dict(family_id='Program: '+family, version_label='Version: '+version,
                   effective_start='Effective from: '+str(start), effective_end='Effective until: '+str(end),
                   published_on='Published: '+str(published), replaces='Replaces previous version: '+','.join(replaces))
    items = []
    for field, value in values.items():
        if value is not None:
            chunk_id=doc_id+'-'+field
            items.append(dict(chunk_id=chunk_id,page=1,content=phrases[field]))
            block[field]=value
            block['proofs'][field]=dict(chunk_id=chunk_id,page=1,quote=phrases[field])
    return dict(doc_id=doc_id, items=items, temporal=block)


def test_intent_does_not_turn_a_mentioned_fact_year_into_filter():
    assert parse_temporal_intent('When was the decision issued in 2023?',reference_date=date(2026,10,14)).kind=='none'
    intent=parse_temporal_intent('So sánh thời gian của bản 2023 và bản QH-2025.',reference_date=date(2026,10,14))
    assert intent.kind=='compare' and intent.versions==('2023','QH-2025')
    assert parse_temporal_intent('Theo bản chương trình năm 2023',reference_date=date(2026,10,14),filters={'academic_year':2024}).conflict
    for text in ['Cột khung hiện hành và cột thông tin điều chỉnh năm 2021 khác nhau thế nào?',
                 'Theo văn bản UET năm 2021, mã mới là gì?',
                 'Khóa luận tốt nghiệp của chương trình Nhật Bản có mã nào?',
                 'Điểm trung bình toàn khóa cao nhất là bao nhiêu?']:
        assert parse_temporal_intent(text,reference_date=date(2026,10,14)).kind=='none'


@pytest.mark.parametrize('day,want',[('2025-08-31','old'),('2025-09-01','new'),('2025-09-02','new')])
def test_as_of_boundaries_include_start_exclude_end(day,want):
    docs=[document('old','2020','2020-01-01','2025-09-01'),document('new','2025','2025-09-01')]
    r=resolve_temporal(TemporalIntent('as_of',as_of=day),docs)
    assert r.status=='resolved' and r.eligible_doc_ids==(want,)
    assert resolve_temporal(TemporalIntent('as_of',as_of=day),list(reversed(docs)))==r


def test_latest_published_can_be_future_effective_but_current_cannot():
    docs=[document('old','2020','2020-01-01',published='2020-01-01'),
          document('new','2027','2027-01-01',published='2026-09-01')]
    assert resolve_temporal(TemporalIntent('latest',reference_date='2026-10-14'),docs).eligible_doc_ids==('new',)
    assert resolve_temporal(TemporalIntent('as_of',as_of='2026-10-14'),docs).eligible_doc_ids==('old',)


def test_missing_dates_never_use_version_or_signing_sort():
    docs=[document('old','2020'),document('new','2099')]
    assert resolve_temporal(TemporalIntent('latest',reference_date='2026-10-14'),docs).status=='insufficient_evidence'
    assert resolve_temporal(TemporalIntent('as_of',as_of='2026-10-14'),docs).status=='insufficient_evidence'
    assert resolve_temporal(TemporalIntent('explicit_period',('2099',)),docs).eligible_doc_ids==('new',)


def test_same_family_comparison_requires_both_sources_and_identity():
    docs=[document('old','2020'),document('new','QH-2025')]
    r=resolve_temporal(TemporalIntent('compare',('2020','QH-2025')),docs)
    assert r.status=='resolved' and r.groups==( ('old',),('new',) )
    assert resolve_temporal(TemporalIntent('compare',('2020','QH-2025')),docs[:1]).status=='insufficient_evidence'
    docs[1]=document('new','QH-2025',family='Different program')
    assert resolve_temporal(TemporalIntent('compare',('2020','QH-2025')),docs).status=='conflict'


def test_overlap_and_partial_amendments_do_not_repeal_whole_parent():
    docs=[document('old','2020','2020-01-01'),document('new','2025','2025-01-01',replaces=['old'])]
    assert resolve_temporal(TemporalIntent('as_of',as_of='2026-10-14'),docs).eligible_doc_ids==('new',)
    docs[1]['temporal']['partial_amendment']=True
    assert resolve_temporal(TemporalIntent('as_of',as_of='2026-10-14'),docs).status=='conflict'
    docs[1]['temporal'].pop('replaces')
    docs[1]['temporal']['partial_amendment']=False
    assert resolve_temporal(TemporalIntent('as_of',as_of='2026-10-14'),docs).status=='conflict'


def test_unproven_values_and_wrong_pages_cannot_select_versions():
    doc=document('only','2025','2025-01-01')
    doc['temporal']['effective_start']='2020-01-01'
    assert resolve_temporal(TemporalIntent('as_of',as_of='2026-10-14'),[doc]).status=='insufficient_evidence'
    doc['temporal']['proofs']['version_label']['page']=2
    assert resolve_temporal(TemporalIntent('explicit_period',('2025',)),[doc]).status=='insufficient_evidence'


def test_non_temporal_unversioned_compatibility_and_version_ambiguity():
    assert resolve_temporal(TemporalIntent(),[dict(doc_id='legacy',items=[])]).status=='not_applicable'
    assert resolve_temporal(TemporalIntent(),[document('old','2020'),document('new','2025')]).status=='needs_clarification'


def test_reference_day_metadata_and_policy_are_bound_into_fingerprint():
    docs=[document('a','2020','2020-01-01')]
    one=TemporalIntent('as_of',as_of='2026-10-14',reference_date='2026-10-14')
    two=TemporalIntent('as_of',as_of='2026-10-15',reference_date='2026-10-15')
    r=resolve_temporal(one,docs)
    assert temporal_fingerprint(one,r,docs)!=temporal_fingerprint(two,resolve_temporal(two,docs),docs)
    docs[0]['temporal']['effective_start']='2026-10-16'
    assert temporal_fingerprint(one,r,docs)!=temporal_fingerprint(one,resolve_temporal(one,docs),docs)


def test_cohort_applicability_does_not_equal_cover_version_year():
    doc=document('a','2023')
    item=dict(chunk_id='a-cohort',page=1,content='Áp dụng từ khóa tuyển sinh năm 2022.')
    doc['items'].append(item)
    doc['temporal']['cohort_start']=2022
    doc['temporal']['proofs']['cohort_start']=dict(chunk_id='a-cohort',page=1,quote=item['content'])
    intent=parse_temporal_intent('Theo khóa 2022, danh hiệu tốt nghiệp là gì?',reference_date=date(2026,10,14))
    assert intent.period_kind=='cohort'
    assert resolve_temporal(intent,[doc]).eligible_doc_ids==('a',)
    # A calendar year cannot stand in for a complete academic-year period.
    period=parse_temporal_intent('Năm học 2024-2025 áp dụng bản nào?',reference_date=date(2026,10,14))
    assert period.period_kind=='academic_year' and period.versions==('2024-2025',)
    assert resolve_temporal(period,[doc]).status=='insufficient_evidence'
