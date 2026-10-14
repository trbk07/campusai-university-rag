"""Audit source/candidate/context readiness separately from model quality."""
import argparse
import json

from evaluation.common.release_artifacts import source_identity
from evaluation.phase10.prepare import ROOT, OUT, RAW, prepare, read, sha


def check(path):
    prepare()
    receipt=read(path)
    assert receipt['source_identity']['runtime_sha256']==source_identity(ROOT)['runtime_sha256']
    rubric={r['qid']:r for r in read(OUT/'source-rubric.json')['cases']}
    assert len(receipt['observations'])==len(rubric)==24
    assert len({r['qid'] for r in receipt['observations']})==24
    checked=[]
    for row in receipt['observations']:
        qid=row['qid'];gold=rubric[qid];trace=row['multi_hop_trace'] or {}
        assert row['public_schema_valid'],qid
        assert len(row['searches'])<=2,qid
        assert all(s['top_k']<=20 and s['returned_candidates']<=20 for s in row['searches']),qid
        assert sum(s['returned_candidates'] for s in row['searches'])<=40,qid
        assert row['generation_boundary_calls']<=1,qid
        if not gold['answerable']:
            assert row['public']['abstained'] and row['generation_boundary_calls']==0,qid
            checked.append(dict(qid=qid,status='SAFE_LOCAL_NEGATIVE',model_quality_measured=False))
            continue
        assert not trace['problem'],(qid,trace['problem'])
        for required in gold['required_facts']:
            assert any(all(actual[k]==required[k] for k in (
                'doc_id','chunk_id','page','table_row','code','credits','headers','cells'))
                for actual in trace['premises']),qid
        if gold['required_edge']:
            edge=gold['required_edge']
            assert trace['edge']['kind']==edge['kind'] and trace['edge']['bridge_code']==edge['bridge_code'],qid
            proof=edge['proof'];actual=trace['edge']['parent']
            assert all(actual[k]==proof[k] for k in ('doc_id','chunk_id','page','table_row','code','cells')),qid
        if gold['operation']:
            assert row['generation_boundary_calls']==0 and not row['public']['abstained'],qid
            values=[p['credits'] for p in trace['premises']]
            result=sum(values) if gold['operation']=='sum' else values[0]-values[1]
            assert result==gold['expected_result'],qid
            checked.append(dict(qid=qid,status='LOCAL_SOURCE_ARITHMETIC_PASS',model_quality_measured=False))
        else:
            assert qid in receipt['captures'] and row['generation_boundary_calls']==1,qid
            capture=receipt['captures'][qid]
            assert '[truncated=true]' not in capture['prompt'],qid
            for p in trace['premises']:
                assert 'chunk_id='+p['chunk_id']+'\n' in capture['prompt'],qid
            checked.append(dict(qid=qid,status='READY_AWAITING_RAW_CHAT_OUTPUT',model_quality_measured=False))
    report=dict(status='CAPTURE_SOURCE_READINESS_PASS_NOT_MODEL_QUALITY',
        reviewer='Codex — Automated AI Review',officially_human_approved=False,
        source_identity=source_identity(ROOT),provider_posts=0,cases=checked,
        source_premise_ready=12,safe_negatives=12,local_arithmetic_pass=4,missing_model_outputs=8,
        model_quality_pass=False,bindings={str(p.relative_to(ROOT)).replace('\\','/'):sha(p)
            for p in [path,OUT/'protocol.json',OUT/'benchmark.jsonl',OUT/'source-rubric.json']})
    destination=RAW/'capture-readiness.json'
    assert not destination.exists(), 'readiness receipt immutable'
    destination.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('status','source_premise_ready','safe_negatives','local_arithmetic_pass','missing_model_outputs')}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('capture');args=parser.parse_args()
    check(ROOT/args.capture)
