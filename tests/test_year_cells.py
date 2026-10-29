"""Header years must identify cells, never excuse unrelated row numbers."""
from dataclasses import replace
import json

import pytest

from campusai.rag.grounding import GroundedAnswerGenerator, validate_citation, validate_quote
from campusai.rag.source_citations import source_quote
from campusai.rag.year_cells import binding
from tests.test_basic_rag import FakeLLM, evidence


TABLE = {'headers': ['Sector', '2016 Flathead sole', '2016 Rock sole',
                     '2017 Flathead sole', '2017 Rock sole'],
         'rows': [['ABC', '66,250', '161,100', '64,580', '145,000'],
                  ['ABC reserve ........', '49,860', '105,920', '43,580', '87,900'],
                  ['CDQ ABC reserve ....', '5,552', '12,023', '4,663', '9,405'],
                  ['Amendment 80 ABC reserve', '44,308', '93,897', '38,917', '78,495']]}
QUESTION = 'What is the ABC reserve for Flathead sole in 2016?'
GOOD = 'In 2016, the ABC reserve for Flathead sole is 49,860.'


def result(table=None):
    return replace(evidence(content=json.dumps(TABLE if table is None else table)), content_type='table')


def answer(text=GOOD, question=QUESTION, *, mode='source', table=None, quote=None):
    item = result(table)
    payload = {'answer': text, 'confidence': 'high', 'abstained': False,
               'claims': [{'claim_id': 'one', 'text': text, 'citation_ids': ['c1']}],
               'citations': [{'chunk_id': 'c1'}]}
    if mode == 'legacy':
        payload['citations'][0].update(page=item.page, quote=quote or json.dumps(TABLE['rows'][1]))
    elif mode == 'compact':
        payload['citations'][0]['chunk_id'] = 'ev1'
        payload['claims'][0]['citation_ids'] = ['ev1']
    return GroundedAnswerGenerator(FakeLLM(payload), source_citations=mode != 'legacy',
                                  compact_citation_ids=mode == 'compact').answer(question, [item], 'en')


@pytest.mark.parametrize('mode', ['source', 'legacy', 'compact'])
@pytest.mark.parametrize('year,amount', [('2016', '49,860'), ('2017', '43,580')])
def test_correct_header_year_is_supported_and_quote_preserves_originals(mode, year, amount):
    text = f'In {year}, the ABC reserve for Flathead sole is {amount}.'
    response = answer(text, QUESTION.replace('2016', year), mode=mode)
    assert not response.abstained, response.reason
    assert response.citations[0].chunk_id == 'c1'
    assert validate_citation(response.citations[0], result(), require_quote=True).valid
    if mode != 'legacy':
        assert json.loads(response.citations[0].quote) == {'headers': TABLE['headers'], 'rows': [TABLE['rows'][1]]}


@pytest.mark.parametrize('mode', ['source', 'legacy', 'compact'])
@pytest.mark.parametrize('text', [
    GOOD.replace('49,860', '43,580'),  # right row, wrong year
    GOOD.replace('49,860', '105,920'),  # right row/year, wrong field
    GOOD.replace('49,860', '66,250'),  # right column, different row
    GOOD.replace('2016', '2017'),  # contradict requested year
    GOOD.replace('Flathead', 'Rock'),  # contradict requested column
    GOOD.replace('ABC reserve', 'CDQ ABC reserve').replace('49,860', '5,552'),
    GOOD.replace('49,860', '49860'),  # no guessed grouping/locale
    GOOD.replace('is', 'is not'),
    GOOD.replace('is', 'is at least'),
    GOOD.replace('49,860.', '49,860 and 87,900.'),
    GOOD.replace('49,860.', '49,860 dollars.'),
    GOOD.replace('49,860.', '49,860%.')])
def test_wrong_cells_and_extra_assertions_fail_closed(mode, text):
    assert answer(text, mode=mode).abstained


def test_same_name_duplicate_cannot_be_hidden_by_one_legacy_row():
    table = {**TABLE, 'rows': TABLE['rows'] + [['ABC reserve', '49,860', '1', '2', '3']]}
    assert answer(table=table).abstained
    assert answer(mode='legacy', table=table).abstained


@pytest.mark.parametrize('row', [0, 2, 3])
def test_uncited_row_cannot_support_scalar(row):
    assert answer(mode='legacy', quote=json.dumps(TABLE['rows'][row])).abstained


def test_short_scalar_binds_question_but_still_runs_normal_claim_validation():
    proof = binding('49,860', result().content, QUESTION)
    assert proof.supported and proof.row == 1 and proof.column == 1
    assert not binding('43,580', result().content, QUESTION).supported
    assert binding('49,860', result().content, 'What is the ABC reserve in 2016?').supported is False


def test_numeric_row_label_is_not_the_asserted_year_or_amount():
    text = 'In 2016, the Amendment 80 ABC reserve for Flathead sole is 44,308.'
    query = 'What is the Amendment 80 ABC reserve for Flathead sole in 2016?'
    assert not answer(text, query).abstained


@pytest.mark.parametrize('value', ['-12', '(12)', '12.50', '12%', '2016'])
def test_literal_signed_decimal_percent_and_amount_equal_year(value):
    table = {'headers': ['Metric', '2016 Revenue', '2017 Revenue'], 'rows': [['North', value, '7']]}
    text = f'In 2016, North Revenue is {value}.'
    assert binding(text, json.dumps(table), 'North Revenue in 2016?').supported


@pytest.mark.parametrize('headers,rows', [
    (['Name', '2016 A', '2017 A'], [['North', '1']]),
    (['Name', '2016 A', '2017 A'], [['North', 1, '2']]),
    (['Name', '2016 A', '2016 A', '2017 A'], [['North', '1', '1', '2']])])
def test_malformed_or_duplicate_columns_never_establish_a_cell(headers, rows):
    proof = binding('In 2016, North A is 1.', json.dumps({'headers': headers, 'rows': rows}))
    assert proof is not None and not proof.supported


def test_other_table_formats_keep_existing_resolvers():
    assert binding('ABC has 3 credits.', json.dumps({'headers': ['Course', 'Credits'],
                                                         'rows': [['ABC', '3']]})) is None
    table = {'headers': ['Metric', '2016 A', '2017 A'], 'rows': [['North', 'Yes', 'No']]}
    assert binding('In 2016, North A is Yes.', json.dumps(table)) is None


def test_year_only_header_is_a_unique_column_without_inventing_a_field():
    table = {'headers': ['Region', '2016', '2017'], 'rows': [['North', '1', '2']]}
    assert binding('In 2016, North is 1.', json.dumps(table)).supported
    assert not binding('In 2016, North is 2.', json.dumps(table)).supported


@pytest.mark.parametrize('change', ['header', 'cell', 'order', 'duplicate', 'foreign', 'splice'])
def test_headed_quote_requires_unchanged_source_ordered_whole_rows(change):
    selected = json.loads(json.dumps({'headers': TABLE['headers'], 'rows': TABLE['rows'][:2]}))
    if change == 'header': selected['headers'][1] = '2017 Flathead sole'
    elif change == 'cell': selected['rows'][0][1] = '49,860'
    elif change == 'order': selected['rows'].reverse()
    elif change == 'duplicate': selected['rows'] *= 2
    elif change == 'foreign': selected['rows'][0][0] = 'Other'
    elif change == 'splice': selected['rows'][0][2] = TABLE['rows'][1][2]
    assert not validate_quote(json.dumps(selected), result().content)


def test_new_grounding_cache_policy_does_not_reuse_pre_fix_entries():
    from campusai.rag.cache import build_rag_cache_key
    args = dict(question=QUESTION, language='en', doc_ids=['doc-1'], filters={}, top_k=5,
                mode='hybrid', model='fake-model', corpus_version='v1', context_budget={})
    assert build_rag_cache_key(**args) != build_rag_cache_key(**args, grounding_policy_version='grounding-v37')


@pytest.mark.parametrize('question', [
    'Compare the ABC reserve for Flathead sole in 2016 and 2017.',
    'What is the ABC reserve for Flathead sole and Rock sole in 2016?',
    'Compare ABC reserve and CDQ ABC reserve for Flathead sole in 2016.'])
@pytest.mark.parametrize('mode', ['source', 'legacy', 'compact'])
def test_comparison_question_allows_a_unique_claim_cell_but_keeps_wrong_values_blocked(question, mode):
    assert not answer(GOOD, question, mode=mode).abstained
    assert answer(GOOD.replace('49,860', '43,580'), question, mode=mode).abstained


def test_comparison_without_asserted_year_or_field_stays_ambiguous():
    assert not binding('The ABC reserve for Flathead sole is 49,860.', result().content,
                       'Compare the ABC reserve for Flathead sole in 2016 and 2017.').supported
    assert not binding('In 2016, ABC reserve is 49,860.', result().content,
                       'What is ABC reserve for Flathead sole and Rock sole in 2016?').supported


def test_two_year_answer_keeps_each_claim_bound_to_its_own_source_cell():
    second = 'In 2017, the ABC reserve for Flathead sole is 43,580.'
    payload = {'answer': GOOD + ' ' + second, 'confidence': 'high', 'abstained': False,
               'claims': [{'claim_id': str(i), 'text': t, 'citation_ids': ['c1']}
                          for i, t in enumerate((GOOD, second))],
               'citations': [{'chunk_id': 'c1'}]}
    query = 'Compare ABC reserve for Flathead sole in 2016 and 2017.'
    generator = GroundedAnswerGenerator(FakeLLM(payload), source_citations=True)
    response = generator.answer(query, [result()], 'en')
    assert not response.abstained and len(response.claims) == 2
    payload['claims'][1]['text'] = second.replace('43,580', '49,860')
    payload['answer'] = GOOD + ' ' + payload['claims'][1]['text']
    assert generator.answer(query, [result()], 'en').abstained


def test_two_year_answer_keeps_each_claim_bound_to_its_own_source_cell():
    second = 'In 2017, the ABC reserve for Flathead sole is 43,580.'
    payload = {'answer': GOOD + ' ' + second, 'confidence': 'high', 'abstained': False,
               'claims': [{'claim_id': str(i), 'text': t, 'citation_ids': ['c1']}
                          for i, t in enumerate((GOOD, second))],
               'citations': [{'chunk_id': 'c1'}]}
    query = 'Compare ABC reserve for Flathead sole in 2016 and 2017.'
    generator = GroundedAnswerGenerator(FakeLLM(payload), source_citations=True)
    response = generator.answer(query, [result()], 'en')
    assert not response.abstained and len(response.claims) == 2
    payload['claims'][1]['text'] = second.replace('43,580', '49,860')
    payload['answer'] = GOOD + ' ' + payload['claims'][1]['text']
    assert generator.answer(query, [result()], 'en').abstained


def test_multiple_claims_keep_whole_rows_and_unknown_or_foreign_claims_reject():
    item = result()
    claims = [{'text': GOOD, 'citation_ids': ['c1']},
              {'text': 'In 2016, the ABC for Rock sole is 161,100.', 'citation_ids': ['c1']}]
    quote = source_quote(item, claims)
    assert json.loads(quote)['rows'] == TABLE['rows'][:2]
    assert source_quote(item, claims + [{'text': 'Unrelated assertion.', 'citation_ids': ['c1']}]) is None
    assert source_quote(item, [{**claims[0], 'citation_ids': ['foreign']}]) is None
