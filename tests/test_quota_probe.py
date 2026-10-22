"""The live probe must stop at a quota response without racing extra POSTs."""
import hashlib
import io
import json
import sys
import time
from urllib.error import HTTPError

from campusai.llm.cache import SQLiteLLMCache
from campusai.llm.client import GeminiClient
from campusai.llm.quota import QuotaGovernor, QuotaPolicy
from scripts.operations.diagnostics import quota_probe
from tests.test_quota_hints import quota_error


def test_paced_probe_stops_on_third_post_and_retains_shared_accounting(tmp_path, monkeypatch):
    inputs = tmp_path/'qualified'
    inputs.mkdir()
    calls=[]
    for i in range(1,11):
        body={'contents':[{'parts':[{'text':f'Public fixture question {i}'}]}],
              'generationConfig':{'maxOutputTokens':100}}
        path=inputs/f'provider-request-{i:02d}.json'
        path.write_text(json.dumps(body),encoding='utf-8')
        calls.append({'body_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    (inputs/'report.json').write_text(json.dumps({'status':'PASS','manifest':{'doc_ids':['public-fixture']},'calls':calls}))
    tier=tmp_path/'tier.json';tier.write_text('{"tier":"free","existing_campusai_project":true}')
    proof=tmp_path/'public.json';proof.write_text('{"exact_public_source_match":true,"sha256":"public-fixture"}')
    protocol=tmp_path/'protocol.json'
    protocol.write_text(json.dumps({'stages':[{'rpm':15,'count':15},{'rpm':30,'count':30},{'rpm':60,'count':13}],
        'provider_call_cap':58,'prior_phase_provider_attempts':2,'phase_provider_attempt_cap':60,
        'tier_evidence':str(tier),'public_source_evidence':str(proof),'qualified_run':str(inputs),
        'profile':'offline-fixture'}))
    client=GeminiClient('fake',model='gemini-3.5-flash-lite',max_retries=0,
        cache=SQLiteLLMCache(':memory:'),overload_circuit_path=tmp_path/'circuit.db',
        quota_governor=QuotaGovernor(tmp_path/'quota.db','test',QuotaPolicy(0),max_wait_seconds=6))
    monkeypatch.setattr(quota_probe,'configure_local',lambda:None)
    monkeypatch.setattr(quota_probe,'create_llm',lambda _path:client)
    sent=[]
    def transport(request,**kwargs):
        sent.append(time.monotonic())
        if len(sent)==3:
            raise HTTPError(request.full_url,429,'quota',{},io.BytesIO(json.dumps(quota_error()).encode()))
        return io.BytesIO(b'{"candidates":[{"content":{"parts":[{"text":"{\\"answer\\":\\"ok\\",\\"abstained\\":false}"}]}}]}')
    monkeypatch.setattr('urllib.request.urlopen',transport)
    output=tmp_path/'output'
    monkeypatch.setattr(sys,'argv',['quota_probe','--protocol',str(protocol),'--output',str(output),
                                   '--raw-output',str(tmp_path/'raw'),'--live'])
    quota_probe.main()
    report=json.loads((output/'report.json').read_text(encoding='utf-8'))
    assert report['status']=='STOPPED_QUOTA' and len(sent)==3
    assert all(b-a>=3.9 for a,b in zip(sent,sent[1:]))
    assert report['quota_after']['reserved_attempts_today']==3
    assert report['quota_after']['observed_provider_limits']['requests_per_day']['value']==50
    assert all(row['started_at_utc']<=report['first_stop']['at_utc'] for row in report['calls'])
