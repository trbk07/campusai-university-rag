from copy import deepcopy
from datetime import datetime, timezone
import json

import pytest

from evaluation.benchmarks.freeze_human_benchmark import validate_rows
from evaluation.benchmarks.owner_generation import generated_audit, generated_row, validate_generation
from evaluation.benchmarks.source_course_rows import source_course_rows
from evaluation.benchmarks.source_course_generation import (
    absence_proof, comparison_contexts, course_context, export_matches, single_course_absence_proof, validate_spec,
)
from evaluation.reranker.supplemental_gates import review_audit_errors

INDEX = 'a' * 64


def inputs(kind='source_course_sum', *, dev_only=False):
    table = {'headers':['STT','Course name','Contact hours','Course code','Credits'],
             'rows':[['1','Điều khiển quỹ đạo\nOrbital Control','60','ABC6001','4'],
                     ['2','Kỹ thuật cơ học\nEngineering Mechanics','45','XYZ6002','3']]}
    evidence = {('doc','table'):{'doc_id':'doc','chunk_id':'table','page':7,'content_type':'table',
        'content':json.dumps(table,ensure_ascii=False), 'metadata':{'document_type':'curriculum'}},
        ('doc','text'):{'doc_id':'doc','chunk_id':'text','page':8,'content_type':'text',
        'content':'These course requirements belong to the supplied curriculum.',
        'metadata':{'document_type':'curriculum'}}}
    auth = {'profile':'personal_owner_source_checked_ai','owner_identity':'Owner',
        'approval_source':'project_owner_chat_instruction',
        'approval_statement':'t duyệt hết nên bạn cứ nhập tên tác giải là t',
        'generation_statement':'nếu k có thì tự tạo đi, t cho phép',
        'independent_human_review_claim':False,'recorded_at':datetime.now(timezone.utc).isoformat(),
        'index_sha256':INDEX,'dev_only':dev_only}
    count = 1 if kind == 'source_course_credit' else 2
    facts=source_course_rows(evidence)[:count]
    spec={'qid':'human-source-test','family':'source-course-pair','kind':kind,'facts':facts,
          'display_names':['Orbital Control','Engineering Mechanics'][:count],
          'template_variant':1,'include_codes':True,'dev_only':dev_only}
    if kind == 'source_course_absent_field':
        spec.update(facet='exam_schedule',absence_proof=absence_proof(facts,'exam_schedule',evidence,INDEX))
    return evidence,auth,spec


@pytest.mark.parametrize('kind',['source_course_credit','source_course_sum','source_course_absent_field'])
def test_explicit_rows_generate_exact_claims_and_disclose_owner_ai_origin(kind,tmp_path):
    evidence,auth,spec=inputs(kind)
    rows=validate_generation(auth,[spec],evidence,'Owner',index_sha256=INDEX)
    row=rows[spec['qid']]
    assert row==generated_row(spec,auth)
    assert row['author_type']=='ai' and row['reviewer_role']=='project_owner'
    assert row['source_validation']==spec
    assert row['doc_ids']==['doc']
    result=validate_rows([row],evidence,owner_identity='Owner',generated_records=rows)
    assert not any(error.startswith('row_1:') for error in result['errors'])
    assert review_audit_errors([row],generated_audit(auth,rows),tmp_path,owner_identity='Owner',
        generation_authorization=auth,generated_records=rows)==[]
    if kind=='source_course_absent_field':
        assert row['answerable'] is False and row['expected_behavior']=='abstain'
        assert row['expected_claims']==row['gold_evidence']==[]
        assert row['source_validation']['absence_proof']['source_chunks']==2
    else:
        assert row['answerable'] is True
        assert row['expected_claims'][0]=={'course_code':'ABC6001','credits':4}
        if kind=='source_course_sum':
            assert row['expected_claims'][-1]=={'total_credits':7}


@pytest.mark.parametrize('change',['credit','code','columns','headers','cells','content_hash','row','page',
                                  'name_lines','extra_fact_key','name','count','variant','variant_bool',
                                  'include_codes','dev_only','extra_spec_key','index','genre','duplicate'])
def test_source_question_forgery_and_unsupported_claims_fail_closed(change):
    evidence,auth,spec=inputs()
    if change in {'credit','code','columns','headers','cells','content_hash','row','page','name_lines','extra_fact_key'}:
        key={'credit':'credits','cells':'cells_sha256','content_hash':'source_content_sha256','row':'table_row'}.get(change,change)
        spec['facts'][0][key]='forged'
    elif change=='name': spec['display_names'][0]='Invented alias'
    elif change=='count': spec['facts']=spec['facts'][:1]
    elif change=='variant': spec['template_variant']=4
    elif change=='variant_bool': spec['template_variant']=True
    elif change=='include_codes': spec['include_codes']='yes'
    elif change=='dev_only': spec['dev_only']='true'
    elif change=='extra_spec_key': spec['expected_claims']=[{'total_credits':99}]
    elif change=='index': auth['index_sha256']='not-a-digest'
    elif change=='genre': evidence['doc','table']['metadata']['document_type']='admission'
    else: spec['facts'][1]=deepcopy(spec['facts'][0])
    with pytest.raises(ValueError):
        validate_generation(auth,[spec],evidence,'Owner')


@pytest.mark.parametrize('facet,mention',[
    ('fee_waiver','Tuition fee waiver policy'),('fee_waiver','Miễn lệ phí đăng ký'),
    ('exam_schedule','Exam dates are in June'),('exam_schedule','Giờ thi là 8h'),
    ('teaching_room','Assigned classrooms are on floor 2'),('teaching_room','Phòng học A101'),
])
def test_absence_reads_decoded_cells_and_every_scoped_text_chunk(facet,mention):
    evidence,_,spec=inputs()
    for key in [('doc','table'),('doc','text')]:
        changed=deepcopy(evidence)
        if key[1]=='table':
            table=json.loads(changed[key]['content'])
            table['rows'].append(['',mention,'','',''])
            changed[key]['content']=json.dumps(table,ensure_ascii=False)
            facts=source_course_rows(changed)
        else:
            changed[key]['content']=mention
            facts=spec['facts']
        with pytest.raises(ValueError,match='source mentions'):
            absence_proof(facts,facet,changed,INDEX)


@pytest.mark.parametrize('change',['body','index','hash','chunk_removed','other_doc_scope'])
def test_absence_proof_binds_complete_scoped_documents(change):
    evidence,auth,spec=inputs('source_course_absent_field')
    if change=='body': evidence['doc','text']['content']+=' New source text.'
    elif change=='index': auth['index_sha256']='b'*64
    elif change=='hash': spec['absence_proof']['body_sha256']['doc']['text']='b'*64
    elif change=='chunk_removed': del evidence['doc','text']
    else: spec['absence_proof']['doc_ids']=['other']
    with pytest.raises(ValueError,match='proof changed'):
        validate_generation(auth,[spec],evidence,'Owner')


def test_absence_can_span_two_documents_but_checks_both():
    evidence,_,spec=inputs()
    other=deepcopy(evidence['doc','table'])
    other.update(doc_id='other',chunk_id='other-table')
    table=json.loads(other['content']); table['rows']=table['rows'][1:]
    other['content']=json.dumps(table,ensure_ascii=False)
    evidence['other','other-table']=other
    facts=[spec['facts'][0],next(f for f in source_course_rows(evidence) if f['doc_id']=='other')]
    proof=absence_proof(facts,'exam_schedule',evidence,INDEX)
    assert proof['doc_ids']==['doc','other'] and proof['source_chunks']==3
    evidence['other','schedule']={'content':'Exam dates: June','metadata':{'document_type':'curriculum'}}
    with pytest.raises(ValueError,match='source mentions'):
        absence_proof(facts,'exam_schedule',evidence,INDEX)


def test_new_dev_only_rows_reject_test_and_holdout_exports(tmp_path):
    evidence,auth,spec=inputs(dev_only=True)
    rows=validate_generation(auth,[spec],evidence,'Owner')
    row=rows[spec['qid']]; audit=generated_audit(auth,rows)
    assert export_matches(row,row)
    for split in ('test','holdout'):
        changed={**row,'split':split}
        assert not export_matches(row,changed)
        result=validate_rows([changed],evidence,owner_identity='Owner',generated_records=rows)
        assert 'row_1:human_authorship_and_approval_required' in result['errors']
        assert review_audit_errors([changed],audit,tmp_path,owner_identity='Owner',
            generation_authorization=auth,generated_records=rows)
    spec['dev_only']=False
    with pytest.raises(ValueError,match='dev-only authorization'):
        validate_generation(auth,[spec],evidence,'Owner')


def test_fresh_source_exports_require_unchanged_content_but_can_be_group_allocated():
    evidence,auth,spec=inputs(dev_only=False)
    row=validate_generation(auth,[spec],evidence,'Owner')[spec['qid']]
    assert export_matches(row,{**row,'split':'holdout'})
    assert not export_matches(row,{**row,'question':row['question']+' edited'})


def test_name_only_question_does_not_claim_exact_code_or_expose_answer():
    evidence,auth,spec=inputs('source_course_credit')
    spec.update(include_codes=False,template_variant=3)
    row=validate_generation(auth,[spec],evidence,'Owner')[spec['qid']]
    assert 'ABC6001' not in row['question'] and 'exact_code' not in row['tags']
    assert 'Orbital Control' in row['question'] and '4' not in row['question']


def test_empty_aliases_and_positive_absence_assertions_are_rejected():
    evidence,_,spec=inputs()
    spec['display_names'][0]=''
    with pytest.raises(ValueError,match='displayed name'):
        validate_spec(spec,evidence,INDEX)
    _,_,spec=inputs(); spec['facet']='exam_schedule'
    with pytest.raises(ValueError,match='positive source question'):
        validate_spec(spec,evidence,INDEX)


def comparison_inputs():
    evidence,auth,spec=inputs('source_course_credit')
    evidence['doc','table']['metadata'].update(program='Robotics',version='2020',source_name='old.pdf')
    newer=deepcopy(evidence['doc','table'])
    newer.update(doc_id='new',chunk_id='new-table',page=9)
    newer['metadata'].update(version='QH-2025',source_name='new.pdf')
    table=json.loads(newer['content']); table['rows']=table['rows'][:1]
    table['rows'][0][-1]='3'
    newer['content']=json.dumps(table,ensure_ascii=False)
    evidence['new','new-table']=newer
    facts=source_course_rows(evidence)
    pair=[next(f for f in facts if f['doc_id']=='doc' and f['code']=='ABC6001'),
          next(f for f in facts if f['doc_id']=='new')]
    spec.update(kind='source_course_compare',facts=pair,display_names=['Orbital Control']*2,
                comparison_contexts=comparison_contexts(pair,evidence))
    return evidence,auth,spec


def test_comparison_keeps_both_versioned_claims_and_signed_difference():
    evidence,auth,spec=comparison_inputs()
    row=validate_generation(auth,[spec],evidence,'Owner')[spec['qid']]
    assert row['doc_ids']==['doc','new'] and len(row['gold_evidence'])==2
    assert row['difficulty']=='hard' and 'multi_document' in row['tags']
    assert row['expected_claims'][0]['credits']==4
    assert row['expected_claims'][1]['credits']==3
    assert row['expected_claims'][-1]=={'credit_difference_second_minus_first':-1}
    assert 'QH-2025' in row['question'] and '2020' in row['question']
    result=validate_rows([row],evidence,owner_identity='Owner',generated_records={row['qid']:row})
    assert not any(error.startswith('row_1:') for error in result['errors'])


@pytest.mark.parametrize('change',['label','version','doc','credit','one_doc','extra_context'])
def test_comparison_cannot_forge_scope_version_cells_or_two_source_support(change):
    evidence,auth,spec=comparison_inputs()
    if change in {'label','version','doc'}:
        key={'doc':'doc_id'}.get(change,change)
        spec['comparison_contexts'][1][key]='forged'
    elif change=='credit': spec['facts'][1]['credits']=99
    elif change=='one_doc': spec['facts'][1]=deepcopy(spec['facts'][0])
    else: spec['comparison_contexts'].append(deepcopy(spec['comparison_contexts'][0]))
    with pytest.raises(ValueError):
        validate_generation(auth,[spec],evidence,'Owner')


def test_same_code_comparison_does_not_relax_legacy_sum_distinct_code_rule():
    evidence,auth,spec=comparison_inputs()
    spec['kind']='source_course_sum'; del spec['comparison_contexts']
    with pytest.raises(ValueError,match='facts differ'):
        validate_generation(auth,[spec],evidence,'Owner')


def test_single_course_negative_proves_whole_document_and_preserves_two_course_contract():
    evidence,auth,spec=inputs('source_course_credit')
    spec.update(kind='source_course_absent_field_single',facet='exam_schedule')
    spec['absence_proof']=single_course_absence_proof(spec['facts'],'exam_schedule',evidence,INDEX)
    row=validate_generation(auth,[spec],evidence,'Owner')[spec['qid']]
    assert row['answerable'] is False and row['gold_evidence']==row['expected_claims']==[]
    assert spec['absence_proof']['source_chunks']==2
    with pytest.raises(ValueError,match='fact count'):
        absence_proof(spec['facts'],'exam_schedule',evidence,INDEX)
    changed=deepcopy(evidence)
    changed['doc','text']['content']='Assigned exam date: June 1.'
    with pytest.raises(ValueError,match='source mentions'):
        single_course_absence_proof(spec['facts'],'exam_schedule',changed,INDEX)
    spec['absence_proof']['body_sha256']['doc'].pop('text')
    with pytest.raises(ValueError,match='proof changed'):
        validate_generation(auth,[spec],evidence,'Owner')


@pytest.mark.parametrize('mode',['history','selection'])
def test_contextual_credit_uses_bound_user_topic_without_revealing_gold(mode):
    from campusai.rag.context import benchmark_request, resolve_query
    evidence,auth,spec=inputs('source_course_credit')
    evidence['doc','table']['metadata'].update(program='Robotics',version='2020',source_name='source.pdf')
    spec.update(context_mode=mode,context_binding=course_context(spec['facts'][0],evidence))
    row=validate_generation(auth,[spec],evidence,'Owner')[spec['qid']]
    assert row['requires_context'] and 'contextual' in row['tags']
    request=benchmark_request(row,[])
    resolved=resolve_query(request['question'],history=request['history'],selected_text=request['selected_text'],
                           requires_context=request['requires_context'])
    assert not resolved.needs_clarification and 'Robotics (2020)' in resolved.resolved
    assert 'untrusted user input' in resolved.resolved
    assert '4' not in resolved.resolved
    changed=deepcopy(spec); changed['context_binding']['version']='2025'
    with pytest.raises(ValueError,match='contextual course request'):
        validate_generation(auth,[changed],evidence,'Owner')
    changed=deepcopy(spec); changed['context_mode']='assistant'
    with pytest.raises(ValueError,match='contextual course request'):
        validate_generation(auth,[changed],evidence,'Owner')
