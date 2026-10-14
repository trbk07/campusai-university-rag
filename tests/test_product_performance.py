"""Performance collector boundaries; no credentials, GPU or external calls."""
from copy import deepcopy
import io
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest

from campusai.llm.client import GeminiClient, LLMError
from campusai.llm.cache import SQLiteLLMCache
from evaluation.common.release_artifacts import read_json, sha256, write_json
from scripts.benchmarks import product_performance as collector


@pytest.fixture
def packet(tmp_path, monkeypatch):
    legacy = deepcopy(collector.read_json_config())
    legacy['max_retries'] = 0
    legacy.pop('retry_only_503', None)
    monkeypatch.setattr(collector, 'read_json_config', lambda: deepcopy(legacy))
    monkeypatch.setattr(collector, "ROOT", tmp_path)
    monkeypatch.setattr(collector, "entries", lambda: {})
    monkeypatch.setattr(collector, "source_identity", lambda _: {"runtime_sha256": "test-runtime"})
    output = tmp_path / "packet.json"
    collector.prepare(output, collector.BASE / "product-performance-workload-20261009.json")
    p = read_json(output)
    p["output_dir"] = str(tmp_path / "run")
    write_json(output, p)
    return output


@pytest.mark.parametrize("field,value", [
    ("max_provider_calls", 55), ("max_retries", 1),
    ("minimum_provider_start_interval_seconds", 0), ("endpoint", "https://example.com"),
    ("prompt_chars", 1),
])
def test_budget_or_endpoint_drift_fails_before_execution(packet, field, value):
    p = read_json(packet)
    p[field] = value
    with pytest.raises(ValueError):
        collector.validate_packet(p)


def test_same_counts_cannot_hide_reordered_cache_lifecycle(packet):
    p = read_json(packet)
    p["workload"][0]["condition"], p["workload"][1]["condition"] = (
        p["workload"][1]["condition"], p["workload"][0]["condition"])
    with pytest.raises(ValueError, match="lifecycle"):
        collector.validate_packet(p)


def test_missing_physical_raw_still_consumes_archived_run(tmp_path, monkeypatch):
    monkeypatch.setattr(collector, "ROOT", tmp_path)
    monkeypatch.setattr(collector, "entries", lambda: {"run/summary.json": {"sha256": "consumed"}})
    with pytest.raises(FileExistsError, match="consumed"):
        collector.available_output(tmp_path / "run/summary.json")


def test_bad_consent_digest_never_starts_child_or_creates_run(packet, monkeypatch):
    monkeypatch.setattr(collector.subprocess, "run", lambda *_a, **_kw: pytest.fail("child started"))
    with pytest.raises(ValueError, match="authorization"):
        collector.collect(packet, "incorrect")


def mock_worker_runtime(packet, monkeypatch, *, drift=False):
    p = read_json(packet)
    case = p["cases"][p["workload"][0]["qid"]]
    parent = Path(p["output_dir"])
    parent.mkdir()
    write_json(parent / "summary.json", {"packet_sha256": sha256(packet), "active_cycle": 1})
    client = GeminiClient("offline-unit-key-only", model=p["llm_config"]["model"],
        generation_config=p["llm_config"]["generation_config"], max_retries=0,
        cache=SQLiteLLMCache())
    service = SimpleNamespace(cache=collector._NoAnswerCache(),
        answer_generator=SimpleNamespace(llm=client),
        retriever=SimpleNamespace(query_cache_size=128, last_trace=None),
        last_retrieval=[], last_cache_hit=False)
    def query(_question, **_options):
        try:
            client.generate_json(case["prompt"] + ("unapproved drift" if drift else ""), schema=case["schema"])
        except LLMError:
            pass
        return {"ok": True, "cache_hit": False, "answer": {
            "answer": "Service temporarily unavailable.", "citations": [], "confidence": "low",
            "abstained": True, "abstention_reason": "provider_abstention", "claims": [],
            "schema_version": "grounding-public-v2"}}
    app = SimpleNamespace(query_service=service, query=query,
        close=lambda: (client.close(), service.cache.close()))
    monkeypatch.setattr(collector, "build_application", lambda: app)
    class Sampler:
        def __init__(self):
            self.thread = SimpleNamespace(start=lambda: None)
        def finish(self):
            return {"peak_rss_bytes": 1, "physical_ram_bytes": 10, "rss_samples": 1}
    monkeypatch.setattr(collector, "ResourceSampler", Sampler)
    monkeypatch.setitem(__import__("sys").modules, "torch", SimpleNamespace(
        set_num_threads=lambda _n: None, cuda=SimpleNamespace(
            is_available=lambda: True, reset_peak_memory_stats=lambda: None)))
    return app


def test_real_http_provider_503_keeps_attempt_and_stops_without_retry(packet, tmp_path, monkeypatch):
    mock_worker_runtime(packet, monkeypatch)
    sent = []
    def unavailable(request, **_options):
        sent.append(request)
        raise HTTPError(request.full_url, 503, "private details", {}, io.BytesIO())
    monkeypatch.setattr("urllib.request.urlopen", unavailable)
    output = Path(read_json(packet)["output_dir"]) / "cycle-1.json"
    collector.worker(packet, output, 1, 0, None, sha256(packet))
    r = read_json(output)
    assert r["status"] == "FAILURE_STOPPED"
    assert len(sent) == r["external_provider_calls"] == 1
    assert len(r["observations"]) == 1
    assert r["observations"][0]["calls"][0]["provider_http_status"] == 503
    assert "private details" not in output.read_text(encoding="utf8")
    with pytest.raises(FileExistsError):
        collector.worker(packet, output, 1, 0, None, sha256(packet))


def test_drifted_prompt_never_reaches_provider(packet, tmp_path, monkeypatch):
    mock_worker_runtime(packet, monkeypatch, drift=True)
    monkeypatch.setattr("urllib.request.urlopen", lambda *_a, **_kw: pytest.fail("unapproved egress"))
    output = Path(read_json(packet)["output_dir"]) / "cycle-1.json"
    collector.worker(packet, output, 1, 0, None, sha256(packet))
    r = read_json(output)
    assert r["status"] == "FAILURE_STOPPED" and r["external_provider_calls"] == 0
    assert r["observations"][0]["provider_transport_attempts"] == 0


def test_http_timeout_remains_an_observation(packet, tmp_path, monkeypatch):
    mock_worker_runtime(packet, monkeypatch)
    class TimeoutConnection:
        def __init__(self, *_a, **_kw):
            pass
        def request(self, *_a, **_kw):
            raise TimeoutError("private connection detail")
        def close(self):
            pass
    monkeypatch.setattr(collector.http.client, "HTTPConnection", TimeoutConnection)
    output = Path(read_json(packet)["output_dir"]) / "cycle-1.json"
    collector.worker(packet, output, 1, 0, None, sha256(packet))
    r = read_json(output)
    assert r["status"] == "FAILURE_STOPPED" and len(r["observations"]) == 1
    assert r["observations"][0]["error_type"] == "TimeoutError"
    assert r["observations"][0]["http_ms"] >= 0
    assert r["external_provider_calls"] == 0
    assert "private connection detail" not in output.read_text(encoding="utf8")


def test_worker_cannot_bypass_parent_authorization(packet, tmp_path, monkeypatch):
    monkeypatch.setattr(collector, "build_application", lambda: pytest.fail("application started"))
    with pytest.raises(ValueError, match="authorization"):
        collector.worker(packet, tmp_path / "unauthorized.json", 1, 0, None, None)


def scheduled_packet(packet, used=7):
    p = read_json(packet)
    history = packet.with_name('shared-history.json')
    write_json(history, {'offline': False, 'external_provider_calls': used,
                        'observations': [{'provider_start': collector.time.time()} for _ in range(used)]})
    p['free_tier_schedule'] = {'daily_attempt_cap': 18, 'timezone': 'America/Los_Angeles',
        'billing_changes': False, 'paid_fallback': False, 'history': {str(history): sha256(history)}}
    p['bindings'][str(history)] = sha256(history)
    write_json(packet, p)
    return p


def simulated_cycle(packet, monkeypatch, sent):
    p = read_json(packet)
    def run(command, **_kwargs):
        cycle = int(command[command.index('--cycle') + 1])
        assert cycle not in sent, 'completed cycle sent twice'
        sent.append(cycle)
        rows = [w for w in p['workload'] if w.get('cycle', 18) == cycle]
        now = collector.time.time()
        child = {'cycle': cycle, 'status': 'PENDING_SOURCE_AND_PERFORMANCE_REVIEW',
            'source_identity': p['source_identity'], 'pid': 123, 'last_provider_start': now,
            'provider_starts': [now] * 3, 'external_provider_calls': 3,
            'observations': [dict(w, valid=True, http_ms=10,
                provider_transport_attempts=int(w['planned_provider_call'])) for w in rows]}
        write_json(Path(command[command.index('--output') + 1]), child)
        return SimpleNamespace(returncode=0, stdout='', stderr='')
    monkeypatch.setattr(collector.subprocess, 'run', run)


def test_daily_shards_preserve_completed_cycles_and_stop_before_cap(packet, monkeypatch):
    scheduled_packet(packet)
    sent = []
    simulated_cycle(packet, monkeypatch, sent)
    first = collector.collect(packet, sha256(packet))
    assert first['status'] == 'WAITING_DAILY_QUOTA'
    assert sent == [1, 2, 3] and first['external_provider_calls'] == 9
    same_day = collector.collect(packet, sha256(packet))
    assert same_day['status'] == 'WAITING_DAILY_QUOTA' and sent == [1, 2, 3]
    next_day = collector.time.time() + 86400
    monkeypatch.setattr(collector.time, 'time', lambda: next_day)
    resumed = collector.collect(packet, sha256(packet))
    assert sent == list(range(1, 10))
    assert resumed['status'] == 'WAITING_DAILY_QUOTA' and resumed['external_provider_calls'] == 27


def test_daily_shards_finish_original_100_requests_without_resending(packet, monkeypatch):
    scheduled_packet(packet, used=7)
    sent = []
    simulated_cycle(packet, monkeypatch, sent)
    now = collector.time.time()
    for offset in range(4):
        monkeypatch.setattr(collector.time, 'time', lambda offset=offset: now + offset * 86400)
        report = collector.collect(packet, sha256(packet))
    assert report['status'] == 'PENDING_INDEPENDENT_SOURCE_RESOURCE_AND_PERFORMANCE_REVIEW'
    assert report['http_requests'] == 100 and report['external_provider_calls'] == 54
    assert report['conditions'] == collector.CONDITIONS and sent == list(range(1, 19))
    with pytest.raises(ValueError, match='clean quota pause'):
        collector.collect(packet, sha256(packet))


@pytest.mark.parametrize('change', ['failure', 'tamper', 'missing', 'wrong_total'])
def test_daily_resume_rejects_failed_or_modified_checkpoint(packet, monkeypatch, change):
    p = scheduled_packet(packet, used=15)
    sent = []
    simulated_cycle(packet, monkeypatch, sent)
    report = collector.collect(packet, sha256(packet))
    child = Path(p['output_dir']) / 'cycle-1.json'
    if change == 'failure':
        report['status'] = 'FAILURE_STOPPED'
    elif change == 'wrong_total':
        report['external_provider_calls'] = 0
    elif change == 'missing':
        child.unlink()
    else:
        child.write_text('{}', encoding='utf8')
    write_json(Path(p['output_dir']) / 'summary.json', report)
    with pytest.raises((ValueError, FileNotFoundError)):
        collector.collect(packet, sha256(packet))
    assert sent == [1]


def test_empty_quota_pause_can_resume_only_when_capacity_exists(packet, monkeypatch):
    scheduled_packet(packet, used=18)
    sent = []
    simulated_cycle(packet, monkeypatch, sent)
    assert collector.collect(packet, sha256(packet))['status'] == 'WAITING_DAILY_QUOTA'
    assert collector.collect(packet, sha256(packet))['status'] == 'WAITING_DAILY_QUOTA'
    assert not sent


def test_daily_count_uses_pacific_date_including_failed_attempts(packet):
    p = scheduled_packet(packet, used=0)
    history = packet.with_name('shared-history.json')
    write_json(history, {'attempts': [
        {'started_at': '2026-10-13T06:59:59+00:00', 'status': 'failed'},
        {'started_at': '2026-10-13T07:00:00+00:00', 'status': 'failed'}]})
    p['free_tier_schedule']['history'][str(history)] = sha256(history)
    assert collector.daily_attempts(p, [], '2026-10-12') == 1
    assert collector.daily_attempts(p, [], '2026-10-13') == 1


def test_existing_dispatcher_lock_prevents_concurrent_run(packet, monkeypatch):
    packet.with_suffix('.collector.lock').write_text('other dispatcher', encoding='utf8')
    monkeypatch.setattr(collector.subprocess, 'run', lambda *_a, **_kw: pytest.fail('concurrent dispatch'))
    with pytest.raises(FileExistsError):
        collector.collect(packet, sha256(packet))
