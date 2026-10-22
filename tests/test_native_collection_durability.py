"""Offline crash tests: spent attempts/raw returns survive process loss."""
import json,subprocess,sys,textwrap
import pytest
from campusai.llm.client import GeminiClient
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.service import CampusAIQueryService
from evaluation.grounding.collect_native_predictions import collect
from evaluation.grounding.native_artifacts import load_native_run
from tests.test_basic_rag import FakeRetriever,evidence,valid_payload


def recovery_fixture(tmp_path, monkeypatch, statuses, *, budget=2):
    """Fictional transport/owner evidence only; no external requests."""
    import io
    from datetime import datetime as RealDatetime
    from urllib.error import HTTPError
    from campusai.llm.client import LLMProviderError, LLMRateLimitError
    from evaluation.grounding import collect_native_predictions as module
    clock = [1_800_000_000.0]
    sleeps = []
    monkeypatch.setattr(module.time, 'time', lambda: clock[0])
    def sleep(seconds):
        sleeps.append(seconds)
        clock[0] += seconds
    monkeypatch.setattr(module.time, 'sleep', sleep)
    class ClockDatetime:
        @staticmethod
        def now(tz=None): return RealDatetime.fromtimestamp(clock[0], tz)
    monkeypatch.setattr(module, 'datetime', ClockDatetime)
    llm = GeminiClient(api_key='offline-placeholder', max_retries=0, cache=None,
                       overload_circuit_path=tmp_path/'health.sqlite3')
    service = CampusAIQueryService(FakeRetriever([evidence()]), GroundedAnswerGenerator(llm))
    calls = []
    def transport(*args, **kwargs):
        calls.append(1)
        status = statuses[len(calls)-1]
        if status:
            cause = HTTPError('https://fictional.invalid/unit', status, 'Fictional unit fault', {},
                              io.BytesIO(b'{"error":{"code":503,"message":"Fictional unit fault"}}'))
            error = LLMRateLimitError('Fictional unit fault') if status == 429 else LLMProviderError('Fictional unit fault')
            raise error from cause
        payload = valid_payload()
        payload['citations'] = [{'chunk_id':'c1','page':3,'quote':'MATH101 is required.'}]
        return {'candidates':[{'content':{'parts':[{'text':json.dumps(payload)}]}}]}
    grant = {'path':'fictional-authorization.json','sha256':'f'*64,'decision':{
        'status':'authorized','recover_http503_once':True,'owner_id':'fictional-unit-owner',
        'decision_reference':'fictional-scoped-transport-recovery', 'packet_budgets':{'e'*64:budget}}}
    return llm, service, transport, grant, calls, sleeps


def test_authorized_http503_recovery_retains_failure_waits_and_uses_same_budget(tmp_path, monkeypatch):
    llm, service, transport, grant, calls, sleeps = recovery_fixture(tmp_path, monkeypatch, [503, None])
    try:
        output = tmp_path/'recovered'
        collect(service,[{'id':'offline','question':'Which prerequisite course?'}],llm,
                max_provider_calls=2,output=output,transport=transport,http503_recovery=grant,
                run_metadata={'egress_packet_sha256':'e'*64})
        run, predictions, raw, posts = load_native_run(output)
        assert len(calls) == len(posts) == 2 and sum(sleeps) >= 60
        assert raw[0]['success'] is False and raw[0]['http_status'] == 503
        assert raw[1]['success'] is True and len(predictions) == 1
        assert predictions[0]['recovered_http503_capture_indices'] == [0]
        assert run['http503_recoveries_attempted'] == run['http503_recoveries_successful'] == 1
        assert run['stop_reason'] is None and run['official_predictions'] == 0
        # Failure/cooldown evidence cannot be removed from the final capture.
        broken = json.loads((output/'run.json').read_text(encoding='utf-8'))
        broken.pop('http503_recovery_policy')
        (output/'run.json').write_text(json.dumps(broken),encoding='utf-8')
        with pytest.raises(ValueError,match='recovered HTTP503'):
            load_native_run(output)
    finally: service.close()


@pytest.mark.parametrize('statuses,budget,authorized,expected_calls',[
    ([503,None],2,False,1), ([429,None],2,True,1),
    ([503,503,None],3,True,2), ([503,None],1,True,1),
])
def test_recovery_is_opt_in_503_only_once_and_never_resets_the_call_cap(
        tmp_path, monkeypatch, statuses, budget, authorized, expected_calls):
    llm, service, transport, grant, calls, sleeps = recovery_fixture(tmp_path, monkeypatch, statuses, budget=budget)
    try:
        output = tmp_path/'bounded'
        run = collect(service,[{'id':'offline','question':'Which prerequisite course?'}],llm,
            max_provider_calls=budget,output=output,transport=transport,
            http503_recovery=grant if authorized else None,
            run_metadata={'egress_packet_sha256':'e'*64})
        assert len(calls) == expected_calls
        assert run['stop_reason'] == 'provider_failure'
        assert run['official_predictions'] == 0
        load_native_run(output)
    finally: service.close()


def test_provider_attempt_and_model_response_are_durable_before_pipeline_returns(tmp_path):
    output=tmp_path/'durable';llm=GeminiClient(api_key='offline-placeholder',max_retries=0,cache=None)
    service=CampusAIQueryService(FakeRetriever([evidence()]),GroundedAnswerGenerator(llm))
    def transport(*_args,**_kwargs):
        assert len((output/'provider-posts.jsonl').read_text(encoding='utf-8').splitlines())==1
        assert json.loads((output/'run-started.json').read_text(encoding='utf-8'))['official_predictions']==0
        payload=valid_payload();payload['citations']=[{'chunk_id':'c1','page':3,'quote':'MATH101 is required.'}]
        return {'candidates':[{'content':{'parts':[{'text':json.dumps(payload)}]}}]}
    ask=service.ask
    def inspect(**kwargs):
        result=ask(**kwargs)
        capture=json.loads((output/'raw-model.jsonl').read_text(encoding='utf-8'))
        assert capture['success'] is True and capture['parsed_model_json']
        assert (output/'predictions.jsonl').read_text(encoding='utf-8')==''
        return result
    service.ask=inspect
    try:
        collect(service,[{'id':'offline','question':'Which prerequisite course?'}],llm,
            max_provider_calls=1,output=output,transport=transport,run_metadata={'model':'offline-transport-fixture'})
        run,predictions,raw,posts=load_native_run(output)
        assert len(predictions)==len(raw)==len(posts)==1 and run['model']=='offline-transport-fixture'
    finally:service.close()


def test_abrupt_process_exit_preserves_capture_and_forbids_implicit_resume(tmp_path):
    output=tmp_path/'interrupted'
    # Simulate the observed loss after a returned provider response but before
    # publication. This child uses a local transport fixture, never a real API.
    program=textwrap.dedent('''
        import json,os,sys
        from pathlib import Path
        from campusai.llm.client import GeminiClient
        from campusai.rag.grounding import GroundedAnswerGenerator
        from campusai.rag.service import CampusAIQueryService
        from evaluation.grounding.collect_native_predictions import collect
        from tests.test_basic_rag import FakeRetriever,evidence,valid_payload
        llm=GeminiClient(api_key='offline-placeholder',max_retries=0,cache=None)
        service=CampusAIQueryService(FakeRetriever([evidence()]),GroundedAnswerGenerator(llm))
        def transport(*args,**kwargs):
            p=valid_payload();p['citations']=[{'chunk_id':'c1','page':3,'quote':'MATH101 is required.'}]
            return {'candidates':[{'content':{'parts':[{'text':json.dumps(p)}]}}]}
        ask=service.ask
        def crash(**kwargs):
            ask(**kwargs)
            os._exit(37)
        service.ask=crash
        collect(service,[{'id':'offline-crash','question':'Which prerequisite course?'}],llm,
            output=Path(sys.argv[1]),max_provider_calls=1,transport=transport)
    ''')
    child=subprocess.run([sys.executable,'-c',program,str(output)],capture_output=True,timeout=30)
    assert child.returncode==37,child.stderr.decode(errors='replace')
    assert len((output/'provider-posts.jsonl').read_text(encoding='utf-8').splitlines())==1
    assert json.loads((output/'raw-model.jsonl').read_text(encoding='utf-8'))['success'] is True
    assert (output/'predictions.jsonl').read_text(encoding='utf-8')=='' and not (output/'run.json').exists()
    with pytest.raises(FileNotFoundError):load_native_run(output)
    llm=GeminiClient(api_key='offline-placeholder',max_retries=0,cache=None)
    try:
        with pytest.raises(ValueError,match='never overwrite'):
            collect(None,[],llm,max_provider_calls=1,output=output)
    finally:llm.close()
