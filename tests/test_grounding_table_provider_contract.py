"""Native LLM schema citations must resolve trusted table identity safely."""
from copy import deepcopy
import pytest

from campusai.rag.grounding import GroundedAnswerGenerator, validate_citation, validate_quote
from campusai.retrieval.hybrid import RetrievalResult


class Provider:
    def __init__(self, payload):
        self.payload = payload

    def generate_json(self, *_args, **_options):
        return self.payload


def table():
    return RetrievalResult('table-chunk', 'document', 2, 'CS201 requires CS101.', 'table', .9, 'hybrid',
                           {'table_id': 'table-2', 'page_range': [2, 2], 'source_name': 'catalog.pdf'})


def payload():
    return {'answer': 'CS201 requires CS101.', 'confidence': 'high', 'abstained': False,
            'claims': [{'claim_id': '1', 'text': 'CS201 requires CS101.', 'citation_ids': ['table-chunk']}],
            'citations': [{'chunk_id': 'table-chunk', 'page': 2, 'quote': 'CS201 requires CS101.'}]}


def test_schema_only_table_citation_derives_identity_from_exact_chunk():
    answer = GroundedAnswerGenerator(Provider(payload())).answer('What is required for CS201?', [table()])
    assert not answer.abstained
    citation = answer.to_public_dict()['citations'][0]
    assert citation['table_id'] == 'table-2'
    assert citation['doc_id'] == 'document' and citation['page'] == 2
    assert validate_citation(citation, table()).valid


@pytest.mark.parametrize('mutation', [
    {'table_id': 'wrong-table'}, {'doc_id': 'other-document'}, {'page': 3},
    {'chunk_id': 'absent'}, {'quote': 'CS201 requires CS102.'}, {'page_range': [2, 3]},
])
def test_table_enrichment_never_overrides_contradictory_provider_coordinates(mutation):
    value = deepcopy(payload())
    value['citations'][0].update(mutation)
    assert GroundedAnswerGenerator(Provider(value)).answer('What is required for CS201?', [table()]).abstained


def test_direct_validator_stays_strict_for_missing_table_identity():
    assert not validate_citation(payload()['citations'][0], table()).valid


def test_non_object_citation_fails_closed():
    value = payload()
    value['citations'] = ['table-chunk']
    assert GroundedAnswerGenerator(Provider(value)).answer('What is required for CS201?', [table()]).abstained


def test_source_table_quote_decodes_cell_linebreaks_without_joining_other_rows():
    import json
    content = json.dumps({'headers': ['Course code', 'Name', 'Credits'],
                          'rows': [['CS201', 'Advanced\nComputing', '3'], ['CS202', 'Networks', '4']]})
    assert validate_quote('CS201 Advanced Computing 3', content)
    assert not validate_quote('CS201 Advanced Computing 4', content)
    assert not validate_quote('Advanced Computing 3 CS202 Networks', content)
    assert not validate_quote('CS201 Advanced Computation 3', content)


@pytest.mark.parametrize('escaped', ['\\n', '\\\\n'])
def test_pipe_table_quote_preserves_one_original_row_and_escaped_cell_whitespace(escaped):
    import json
    content = json.dumps({'headers': ['Code', 'Name', 'Credits', 'Prerequisite'],
                         'rows': [['CS201', 'Advanced\nComputing', '3', ''],
                                  ['CS202', 'Networks', '4', 'CS201']]})
    assert validate_quote(f'CS201 | Advanced{escaped}Computing | 3 | ', content)
    assert not validate_quote(f'CS201 | Advanced{escaped}Computing | 4 | ', content)
    assert not validate_quote(f'CS201 | Advanced{escaped}Computing | 3 | CS201', content)
    assert not validate_quote('CS201 | Advanced Computing | 3 | CS202 | Networks', content)


@pytest.mark.parametrize('decoded_linebreaks', [False, True])
def test_json_array_quote_matches_complete_multiline_source_row(decoded_linebreaks):
    import json
    row = ['CS201', 'Advanced\nComputing', '3']
    content = json.dumps({'headers': ['Code', 'Name', 'Credits'],
                          'rows': [row, ['CS202', 'Networks', '4']]})
    quote = json.dumps(row)
    if decoded_linebreaks:
        quote = quote.replace('\\n', '\n')
    assert validate_quote(quote, content)
    for wrong in (['CS201', 'Advanced\nComputing', '4'],
                  ['CS202', 'Advanced\nComputing', '3'],
                  ['CS201', 'Advanced\nComputing', 3],
                  ['CS201', 'Advanced\nComputing', '3', 'CS202']):
        assert not validate_quote(json.dumps(wrong).replace('\\n', '\n'), content)
