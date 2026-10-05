import json

import pytest

from evaluation.benchmarks.source_proposals import course_aliases, history_inventory, screen_source_facts
from evaluation.common.release_artifacts import sha256


def source():
    return {('doc','table'):{'content_type':'table','page':7,
        'content':json.dumps({'headers':['Course code','Course name','Credits'],
                             'rows':[['NEW6001','Điều khiển quỹ đạo\nAdvanced Orbital\nControl','3']]},ensure_ascii=False)}}


@pytest.mark.parametrize('question', ['Credits for NEW6001?', 'Credits for NEW 6001?',
                                     'Advanced Orbital Control has how many credits?',
                                     'How many credits for dieu khien quy dao?', 'Advanced-Orbital Control credits?'])
def test_code_or_wrapped_bilingual_alias_is_excluded(question):
    result = screen_source_facts(source(), {'doc'}, [{'question':question}])
    assert result['proposed_rows'] == 0 and len(result['excluded']) == 1
    assert result['excluded'][0]['origin']['question'] == question


def test_code_prefix_is_not_exact_code_and_unknown_source_is_not_proposed():
    result = screen_source_facts(source(), {'doc'}, [{'question':'NEW60010 credits?'}])
    assert result['proposed_rows'] == 1
    assert result['release_eligible'] is False
    assert screen_source_facts(source(), {'other'}, [])['proposed_rows'] == 0


def test_wrapped_aliases_preserve_both_languages():
    aliases = course_aliases({'name':'Điều khiển quỹ đạo Advanced Orbital Control',
                             'name_lines':['Điều khiển quỹ đạo','Advanced Orbital','Control']})
    assert {'dieu khien quy dao','advanced orbital control'} <= aliases


def test_history_includes_owner_inputs_and_deduplicates_overlapping_directories(tmp_path):
    owner = tmp_path/'owner_confirmed_inputs'; owner.mkdir()
    path=owner/'original.jsonl'
    path.write_text(json.dumps({'qid':'prior','query':'Original owner question'})+'\n',encoding='utf8')
    questions, datasets = history_inventory([tmp_path,owner])
    assert len(datasets) == len(questions) == 1
    assert datasets[0]['sha256'] == sha256(path)
    assert questions[0]['line'] == 1 and questions[0]['question'] == 'Original owner question'


def test_malformed_history_is_not_silently_ignored(tmp_path):
    (tmp_path/'invalid.jsonl').write_text('[]\n',encoding='utf8')
    with pytest.raises(ValueError, match='history row must be an object'):
        history_inventory([tmp_path])


def test_exposure_propagates_across_code_and_translated_name_families():
    evidence = {}
    for doc, code, name in [('a','NEW6001','Alias one\nFirst English title'),
                            ('b','NEW6001','Other spelling\nSecond English title'),
                            ('c','NEW6002','Other spelling\nThird English title')]:
        evidence[(doc,'table')] = {'content_type':'table','page':1,
            'content':json.dumps({'headers':['Course code','Course name','Credits'],
                                 'rows':[[code,name,'3']]})}
    result = screen_source_facts(evidence, {'a','b','c'}, [{'question':'Alias one credits?'}])
    assert result['proposed_rows'] == result['proposed_connected_groups'] == 0
    assert len(result['excluded']) == 3
    assert {item['fact']['doc_id'] for item in result['excluded']
            if item['reason'] == 'connected_source_family_exposed'} == {'b','c'}
    unexposed = screen_source_facts(evidence, {'a','b','c'}, [])
    assert unexposed['proposed_rows'] == 3
    assert unexposed['proposed_connected_groups'] == 1


def test_ancestor_alias_exposes_proposed_new_document_row():
    evidence = source()
    evidence[('old','table')] = {'content_type':'table','page':1,
        'content':json.dumps({'headers':['Course code','Course name','Credits'],
                             'rows':[['NEW6001','Historical original title','3']]})}
    result = screen_source_facts(evidence, {'doc'}, [{'question':'Historical original title credits?'}])
    assert result['explicit_course_rows'] == 1
    assert result['indexed_family_rows_checked'] == 2
    assert result['proposed_rows'] == 0
    assert result['excluded'][0]['exposed_source_fact']['doc_id'] == 'old'
