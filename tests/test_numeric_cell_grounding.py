"""New optical scalar cells retain row/field/unit proof in every protocol."""
import copy
from dataclasses import replace
import json

import pytest

from campusai.rag.grounding import GroundedAnswerGenerator
from tests.test_basic_rag import FakeLLM, evidence

TABLE = {'headers': ['No.', 'Region', 'Stock (Billions of US Dollars)', 'Share (%)'],
         'rows': [['1', 'North', '86.02', '37.5'], ['2', 'South', '67.38', '29.4'],
                  ['3', 'East', '36.18', '15.8']]}
GOOD = 'The Stock of North is 86.02.'
QUESTION = 'What is the Stock of North?'


def answer(text=GOOD, *, public=None, mode='source', table=None, question=QUESTION, quoted=None):
    table = TABLE if table is None else table
    item = replace(evidence(content=json.dumps(table), metadata={'numeric_cell_policy': 'ruled-ocr-numeric-v1'}),
                   content_type='table')
    identity = 'ev1' if mode == 'compact' else 'c1'
    citation = {'chunk_id': identity}
    if mode == 'legacy': citation.update(page=3, quote=json.dumps(quoted or table['rows'][0]))
    payload = {'answer': public or text, 'abstained': False, 'confidence': 'high',
               'claims': [{'claim_id': 'one', 'text': text, 'citation_ids': [identity]}],
               'citations': [citation]}
    return GroundedAnswerGenerator(FakeLLM(payload), source_citations=mode != 'legacy',
                                  compact_citation_ids=mode == 'compact').answer(question, [item], 'en')


@pytest.mark.parametrize('mode', ['source', 'compact', 'legacy'])
@pytest.mark.parametrize('text', [GOOD, 'The Stock of North is 86.02 billion USD.',
                                'North Stock | 86.02', 'The Stock of North is 86.02 billions of US Dollars.'])
def test_supported_cell_and_explicit_source_units_stay_answerable(mode, text):
    response = answer(text, mode=mode)
    assert not response.abstained, response.reason
    assert response.citations[0].chunk_id == 'c1'


@pytest.mark.parametrize('mode', ['source', 'compact', 'legacy'])
@pytest.mark.parametrize('text', [GOOD.replace('86.02', '67.38'), GOOD.replace('86.02', '37.5'),
                                GOOD.replace('86.02', '1'), GOOD.replace('North', 'South'),
                                GOOD.replace('Stock', 'Share'), GOOD.replace('is', 'is not'),
                                GOOD.replace('is', 'is at least'), GOOD.replace('86.02.', '86.02 and 37.5.'),
                                GOOD.replace('86.02.', '86.02 dollars.'),
                                GOOD.replace('86.02.', '86.02 million USD.'),
                                GOOD.replace('86.02.', '86.02%.')])
def test_other_rows_columns_modifiers_and_scales_are_not_support(mode, text):
    assert answer(text, mode=mode).abstained


@pytest.mark.parametrize('mode', ['source', 'compact', 'legacy'])
@pytest.mark.parametrize('unit', ['dollars', 'million USD', 'trillion USD', 'percent', '%', 'trieu USD', 'VND'])
def test_correct_claim_cannot_hide_wrong_units_in_public_answer(mode, unit):
    assert answer(public=GOOD.replace('86.02.', f'86.02 {unit}.'), mode=mode).abstained


@pytest.mark.parametrize('public', [GOOD, GOOD.replace('86.02.', '86.02 billion USD.'),
                                   GOOD.replace('86.02.', '86.02 ty USD.'),
                                   GOOD.replace('86.02.', '86,02 ty USD.'),
                                   GOOD.replace('86.02.', '86,02.'),
                                   'On page 3, ' + GOOD])
def test_supported_public_currency_scale_aliases_keep_source_value(public):
    assert not answer(public=public).abstained


@pytest.mark.parametrize('text', ['North Share is 37.5.', 'North Share is 37.5%.'])
def test_percent_header_proves_the_same_percent_without_changing_numeric_value(text):
    assert not answer(text, question='What is the Share of North?').abstained


def test_duplicate_original_identity_cannot_hide_behind_one_legacy_row():
    table = copy.deepcopy(TABLE)
    table['rows'].append(['4', 'North', '12.0', '2.0'])
    assert answer(table=table).abstained and answer(table=table, mode='legacy').abstained
    assert answer(mode='legacy', quoted=TABLE['rows'][1]).abstained


def test_question_comparison_does_not_relax_each_claims_cell_binding():
    assert not answer(question='Compare Stock of North and South.').abstained
    assert answer(GOOD.replace('86.02', '67.38'), question='Compare Stock of North and South.').abstained


@pytest.mark.parametrize('mode', ['source', 'compact', 'legacy'])
@pytest.mark.parametrize('quantity', ['86,02 million USD', '86,020 billion USD', '86,020',
                                     '86020', '0.08602 billion USD'])
def test_public_locale_or_grouping_cannot_hide_changed_scale_or_value(mode, quantity):
    assert answer(public=GOOD.replace('86.02.', quantity+'.'), mode=mode).abstained


@pytest.mark.parametrize('mode', ['source', 'compact', 'legacy'])
@pytest.mark.parametrize('text,question', [
    ('Course ABC101 has 3 credits.', 'How many credits does ABC101 have?'),
    ('M\u00f4n ABC101 c\u00f3 3 t\u00edn ch\u1ec9.', 'ABC101 c\u00f3 bao nhi\u00eau t\u00edn ch\u1ec9?'),
    ('Course code ABC101.', 'What is the course code ABC101?')])
def test_numeric_ocr_tables_preserve_existing_code_and_course_credit_contracts(mode, text, question):
    table = {'headers': ['Course code', 'Credits', 'Hours'],
             'rows': [['ABC101', '3', '30'], ['ABC102', '4', '45'], ['ABC103', '2', '20']]}
    response = answer(text, mode=mode, table=table, question=question)
    assert not response.abstained, response.reason
    wrong = answer('Course ABC101 has 30 credits.', mode=mode, table=table,
                   question='How many credits does ABC101 have?')
    # The existing source-cell resolver may answer correctly before inference.
    assert wrong.abstained or ('3 credits' in wrong.answer and '30 credits' not in wrong.answer)
