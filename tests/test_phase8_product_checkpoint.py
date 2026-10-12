"""Exercise the real Gemini serializer with a fake network and small product app."""
import io
import json
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest

from campusai.llm.client import GeminiClient
from evaluation.phase8 import run_product_baseline as runner


CONFIG = {"provider": "gemini", "model": "gemini-3.8-flash", "timeout_seconds": 15,
          "generation_config": {"temperature": 1, "maxOutputTokens": 1024}}


class Answer:
    def to_dict(self):
        return {"answer": "captured output", "abstained": False, "citations": []}

    to_public_dict = to_dict


class Application:
    def __init__(self):
        self.query_service = SimpleNamespace(
            cache=SimpleNamespace(close=lambda: None),
            retriever=SimpleNamespace(query_cache_size=32), last_retrieval=[],
            answer_generator=SimpleNamespace(llm=GeminiClient(
                "fake-test-credential", model=CONFIG["model"], generation_config=CONFIG["generation_config"],
                max_retries=1, retry_only_503=True, retry_min_wait_seconds=0, retry_max_wait_seconds=0)))
        self.query_service.ask = self.ask

    def ask(self, question, **_options):
        self.query_service.answer_generator.llm.generate_json(question, schema={"type": "object"})
        return Answer()

    def query(self, question, **options):
        return {"ok": True, "answer": self.query_service.ask(question, **options).to_public_dict()}

    def close(self):
        pass


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "verify_inputs", lambda *_args: None)
    monkeypatch.setattr(runner, "source_identity", lambda _root: {"source": "fixed"})
    for name in ("MANIFEST", "STATE", "PREFLIGHT", "PREDICTIONS", "FREEZE", "AMENDMENT"):
        monkeypatch.setattr(runner, name, tmp_path / (name.lower() + ".json"))
    runner.FREEZE.write_text("{}", encoding="utf-8")
    config_path = tmp_path / "product.yaml"
    config_path.write_text(json.dumps({"llm": CONFIG}), encoding="utf-8")
    cases = [{"qid": f"q{i}", "request": {"question": f"prompt{i}", "filters": {}},
              "planned_provider_call": True, "prompt": f"prompt{i}", "schema": {"type": "object"}}
             for i in range(20)]
    packet = {"llm_config": {"path": str(config_path)}, "cases": cases,
              "profile": {}, "source_identity": {"source": "fixed"},
              "prompt_characters": sum(len(c["prompt"]) for c in cases),
              "benchmark": {"sha256": "benchmark"},
              "index": {"manifest_sha256": "manifest", "tree_sha256": "tree"}}
    runner.write(runner.PREFLIGHT, packet)
    sent = []
    clock = [100.0]
    monkeypatch.setattr(runner.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(runner.time, "sleep", lambda duration: clock.__setitem__(0, clock[0] + duration))
    day = ["2026-10-12"]
    monkeypatch.setattr(runner, "pacific_day", lambda *_args: day[0])
    monkeypatch.setenv("GEMINI_API_KEY", "fake-test-credential")
    monkeypatch.setattr("scripts.operations.serve.build_application", Application)

    def transport(request, **_options):
        sent.append((clock[0], json.loads(request.data)))
        return io.BytesIO(json.dumps({"candidates": [{"content": {"parts": [{"text": "{}"}]},
                                                       "finishReason": "STOP"}],
                                      "usageMetadata": {"totalTokenCount": 2},
                                      "modelVersion": "fake-version"}).encode())
    monkeypatch.setattr("urllib.request.urlopen", transport)
    result = runner.prepare()
    assert result["planned_calls"] == 20 and not sent
    return day, sent


def test_checkpoint_spans_days_without_resending_completed_questions(prepared):
    day, sent = prepared
    result = runner.run()
    assert result["rows_completed"] == 18 and result["attempts"] == 18
    assert all(b[0] - a[0] >= 30 for a, b in zip(sent, sent[1:]))
    with pytest.raises(ValueError, match="daily shard already used"):
        runner.run()
    assert len(sent) == 18
    day[0] = "2026-10-13"
    result = runner.run()
    assert result["status"] == "completed" and result["attempts"] == 20
    rows = runner.read(runner.STATE)["predictions"]
    assert [row["qid"] for row in rows] == [f"q{i}" for i in range(20)]
    assert [i for i, row in enumerate(rows) if row["cold_start"]] == [0, 18]
    assert rows[0]["provider_output"]["model_version"] == "fake-version"
    assert rows[0]["provider_output"]["usage"]["totalTokenCount"] == 2
    assert len({json.dumps(body, sort_keys=True) for _, body in sent}) == 20
    assert runner.PREDICTIONS.exists()


def test_503_never_consumes_an_immediate_retry_or_creates_a_prediction(prepared, monkeypatch):
    _day, sent = prepared
    def unavailable(request, **_options):
        sent.append(request.full_url)
        raise HTTPError(request.full_url, 503, "unavailable", {}, io.BytesIO(b"{}"))
    monkeypatch.setattr("urllib.request.urlopen", unavailable)
    result = runner.run()
    state = runner.read(runner.STATE)
    assert len(sent) == 1 and result["attempts"] == 1
    assert result["rows_completed"] == 0
    assert state["attempts"][0]["http_status"] == 503
    assert state["attempts"][0]["transport_latency_ms"] >= 0
    assert state["shards"][0]["status"] == "stopped_on_error"
    assert not runner.PREDICTIONS.exists()


def test_failed_provider_keeps_actual_fallback_timing_and_no_success_prediction(prepared, monkeypatch):
    from campusai.llm.client import LLMError
    _, sent = prepared
    def unavailable(request, **_options):
        sent.append(request.full_url)
        raise HTTPError(request.full_url, 503, 'unavailable', {}, io.BytesIO(b'{}'))
    original_ask = Application.ask
    def fallback(self, question, **options):
        self.query_service.answer_generator.llm.max_retries = 0
        try:
            return original_ask(self, question, **options)
        except LLMError:
            return Answer()
    monkeypatch.setattr('urllib.request.urlopen', unavailable)
    monkeypatch.setattr(Application, 'ask', fallback)
    runner.run()
    state = runner.read(runner.STATE)
    failed = state['failed_product_response']
    assert failed['request_latency_ms'] >= 0
    assert failed['latency_ms'] >= failed['request_latency_ms']
    assert failed['cold_start'] is True and failed['provider_output'] is None
    assert state['peak_working_set_bytes'] > 0
    assert len(sent) == 1 and state['predictions'] == []


def test_worker_lock_and_checkpoint_corruption_stop_before_network(prepared):
    _day, sent = prepared
    with runner.exclusive_run():
        with pytest.raises(FileExistsError):
            runner.run()
    state = runner.read(runner.STATE)
    state["predictions"] = [{"qid": "wrong-order"}]
    runner.write(runner.STATE, state)
    with pytest.raises(ValueError, match="unique benchmark prefix"):
        runner.run()
    assert not sent


def test_payload_drift_does_not_send_a_request(prepared):
    _day, sent = prepared
    manifest = runner.read(runner.MANIFEST)
    manifest["provider_body_sha256_by_qid"]["q0"] = "wrong-hash"
    runner.write(runner.MANIFEST, manifest)
    state = runner.read(runner.STATE)
    state["manifest_sha256"] = runner.sha256(runner.MANIFEST)
    runner.write(runner.STATE, state)
    result = runner.run()
    assert not sent and result["attempts"] == 0 and result["rows_completed"] == 0


def test_total_attempt_budget_is_enforced_even_on_a_new_day(prepared):
    _day, sent = prepared
    state = runner.read(runner.STATE)
    state["attempts"] = [{}] * runner.read(runner.MANIFEST)["max_attempts"]
    runner.write(runner.STATE, state)
    with pytest.raises(ValueError, match="total attempt budget exhausted"):
        runner.run()
    assert not sent


def authorize_pool(monkeypatch):
    import hashlib
    keys = {'key_2': 'fake-test-credential', 'key_3': 'third-test-credential',
            'key_1': 'first-test-credential'}
    monkeypatch.setattr('scripts.operations.with_gemini_key.read_key', lambda _path, name: keys[name])
    monkeypatch.setattr(runner, 'execution_packet', lambda _manifest: runner.read(runner.PREFLIGHT))
    runner.write(runner.AMENDMENT, {
        'status': 'APPROVED_OWNER_RELIABILITY_AMENDMENT',
        'credential_order': list(keys),
        'credential_fingerprints': {name: hashlib.sha256(key.encode()).hexdigest() for name, key in keys.items()}})
    return keys


def test_credential_rotation_is_rejected_before_any_new_attempt(prepared, monkeypatch):
    day, sent = prepared
    runner.run()
    day[0] = "2026-10-13"
    monkeypatch.setenv("GEMINI_API_KEY", "different-fake-credential")
    with pytest.raises(ValueError, match="credential changed"):
        runner.run()
    assert len(sent) == 18


def test_pool_uses_shared_cap_and_never_resends_completed_rows(prepared, monkeypatch):
    day, sent = prepared
    authorize_pool(monkeypatch)
    result = runner.run_pool()
    assert result['attempts'] == 18 and result['rows_completed'] == 18
    assert [event['credential_name'] for event in runner.read(runner.STATE)['attempts']] == (
        ['key_2'] * 6 + ['key_3'] * 6 + ['key_1'] * 6)
    with pytest.raises(ValueError, match='daily shard already used'):
        runner.run_pool()
    assert len(sent) == 18
    day[0] = '2026-10-13'
    result = runner.run_pool()
    assert result['status'] == 'completed' and result['attempts'] == 20
    assert len({json.dumps(body, sort_keys=True) for _, body in sent}) == 20


def test_pool_stops_on_503_without_trying_another_key(prepared, monkeypatch):
    _, sent = prepared
    keys = authorize_pool(monkeypatch)
    def unavailable(request, **_):
        sent.append(request.get_header('X-goog-api-key'))
        raise HTTPError(request.full_url, 503, 'busy', {}, io.BytesIO())
    monkeypatch.setattr('urllib.request.urlopen', unavailable)
    result = runner.run_pool()
    assert sent == [keys['key_2']]
    assert result['rows_completed'] == 0 and result['attempts'] == 1
    assert runner.read(runner.STATE)['attempts'][0]['credential_name'] == 'key_2'


def test_pool_rejects_unapproved_key_changes_before_network(prepared, monkeypatch):
    _, sent = prepared
    keys = authorize_pool(monkeypatch)
    keys['key_3'] = 'unapproved-test-credential'
    with pytest.raises(ValueError, match='approved credential changed'):
        runner.run_pool()
    assert not sent


def authorize_availability(monkeypatch):
    keys = authorize_pool(monkeypatch)
    amendment = runner.read(runner.AMENDMENT)
    amendment.update(allow_remaining_daily_attempts=True,
                     availability_pacific_day=runner.pacific_day(),
                     availability_order=['key_3', 'key_2', 'key_1'])
    runner.write(runner.AMENDMENT, amendment)
    return keys


def test_same_day_continuation_uses_only_remaining_aggregate_budget(prepared, monkeypatch):
    day, sent = prepared
    authorize_availability(monkeypatch)
    state = runner.read(runner.STATE)
    state['attempts'] = [{'pacific_day': day[0], 'http_status': 503, 'qid': 'q0'}]
    state['shards'] = [{'pacific_day': day[0], 'status': 'stopped_on_error'}]
    runner.write(runner.STATE, state)
    result = runner.run_pool()
    assert result['attempts'] == 18 and result['rows_completed'] == 17
    assert len(sent) == 17
    assert {event['credential_name'] for event in runner.read(runner.STATE)['attempts'][1:]} == {'key_3'}
    with pytest.raises(ValueError, match='aggregate daily attempt budget exhausted'):
        runner.run_pool()
    assert len(sent) == 17


def test_quota_failure_allows_different_key_without_repeating_success(prepared, monkeypatch):
    _, sent = prepared
    keys = authorize_availability(monkeypatch)
    original = __import__('urllib.request', fromlist=['urlopen']).urlopen
    def quota(request, **options):
        if request.get_header('X-goog-api-key') == keys['key_3']:
            sent.append(('quota', json.loads(request.data)))
            raise HTTPError(request.full_url, 429, 'quota', {}, io.BytesIO())
        return original(request, **options)
    monkeypatch.setattr('urllib.request.urlopen', quota)
    first = runner.run_pool()
    assert first['attempts'] == 1 and first['rows_completed'] == 0
    second = runner.run_pool()
    assert second['attempts'] == 18 and second['rows_completed'] == 17
    events = runner.read(runner.STATE)['attempts']
    assert events[0]['credential_name'] == 'key_3'
    assert {e['credential_name'] for e in events[1:]} == {'key_2'}
    assert len({json.dumps(body, sort_keys=True) for _, body in sent[1:]}) == 17


def test_same_day_exception_is_date_bound(prepared, monkeypatch):
    day, _ = prepared
    authorize_availability(monkeypatch)
    day[0] = '2026-10-13'
    state = runner.read(runner.STATE)
    state['shards'] = [{'pacific_day': day[0]}]
    runner.write(runner.STATE, state)
    with pytest.raises(ValueError, match='daily shard already used'):
        runner.run_pool()
