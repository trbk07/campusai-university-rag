"""Synthetic request/scope contracts; no model-quality assertions."""
from dataclasses import replace
import pytest

from campusai.rag.multi_hop import plan_request, request_fingerprint


def docs():
    return [dict(doc_id=d,items=[dict(metadata={'source_name':name})])
            for d,name in [('A','alpha_2023.pdf'),('B','beta_2020.pdf')]]


@pytest.mark.parametrize('question,kind',[
    ('Trong alpha_2023.pdf và beta_2020.pdf, so sánh tín chỉ CS201.', 'compare'),
    ('Lấy tín chỉ CS201 từ alpha_2023.pdf và CS202 từ beta_2020.pdf. Tổng là bao nhiêu?', 'sum'),
    ('Lấy tín chỉ CS201 trong alpha_2023.pdf trừ CS202 trong beta_2020.pdf.', 'difference'),
    ('Theo alpha_2023.pdf, tiên quyết của CS201 có bao nhiêu tín chỉ?', 'prerequisite_lookup'),
    ('Theo alpha_2023.pdf, chứng minh CS101 là tiên quyết trực tiếp của CS201.', 'prerequisite_assertion'),
    ('Tìm mã môn Xử lý tín hiệu trong alpha_2023.pdf; môn mang mã đó trong beta_2020.pdf có mấy tín chỉ?', 'name_code_lookup'),
    ('From alpha_2023.pdf and beta_2020.pdf, confirm automatic equivalence.', 'unsupported_relation'),
])
def test_natural_requests_resolve_only_source_roles_not_source_facts(question,kind):
    plan=plan_request(question,docs())
    assert plan.kind==kind
    assert {r.doc_id for r in plan.roles}<={'A','B'}


def test_missing_or_ambiguous_named_source_never_borrows_another_program():
    q='Compare CS201 credits in alpha_2023.pdf and beta_2020.pdf.'
    assert plan_request(q,docs()[:1]).problem=='source_not_in_selected_scope'
    duplicate=docs()+[dict(doc_id='other',items=[dict(metadata={'source_name':'alpha_2023.pdf'})])]
    assert plan_request(q,duplicate).problem=='source_identity_ambiguous'


def test_operand_roles_keep_order_and_do_not_treat_filename_year_as_code():
    plan=plan_request('Credits for CS201 in alpha_2023.pdf minus CS201 in beta_2020.pdf.',docs())
    assert [(r.doc_id,r.code) for r in plan.roles]==[('A','CS201'),('B','CS201')]
    reversed_plan=replace(plan,roles=tuple(reversed(plan.roles)))
    assert request_fingerprint(plan)!=request_fingerprint(reversed_plan)
    assert request_fingerprint(plan)!=request_fingerprint(replace(plan,policy_version='future'))


def test_unassigned_operands_are_not_guessed_from_document_order():
    plan=plan_request('Total credits for CS201 and CS202 in alpha_2023.pdf and beta_2020.pdf?',docs())
    assert plan.problem=='operand_source_assignment_ambiguous'
    # Source-free direct sums remain on the existing deterministic path.
    assert plan_request('Total credits for CS201 and CS202?',docs()).kind=='single'


def test_more_than_two_groups_requires_clarification_without_model():
    extra=docs()+[dict(doc_id='C',items=[dict(metadata={'source_name':'gamma.pdf'})])]
    assert plan_request('Compare CS201 in alpha_2023.pdf, beta_2020.pdf and gamma.pdf.',extra).problem=='more_than_two_source_groups'


def test_compare_uses_both_explicitly_selected_documents_without_filename_scaffolding():
    plan=plan_request('Compare CS201 credits in the selected documents.',docs())
    assert plan.kind=='compare' and [(r.doc_id,r.code) for r in plan.roles]==[('A','CS201'),('B','CS201')]
    assert plan_request('How many credits does CS201 have?',docs()).kind=='single'
