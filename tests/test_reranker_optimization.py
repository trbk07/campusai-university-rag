from dataclasses import replace
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from pathlib import Path
from uuid import uuid4

import pytest

from campusai.retrieval.cross_encoder_provider import (
    ModelIdentity, OfflineCrossEncoderReranker, RerankCandidate, snapshot_sha256,
)
from campusai.rag.service import CampusAIQueryService
from campusai.api import CampusAIApplication
from campusai.web import make_wsgi_app
from tests.test_web import call


def test_precision_is_bound_to_identity_and_rejects_cpu_half():
    identity = ModelIdentity("BAAI/bge-reranker-v2-m3", "rev", "a"*64, "rev", device="cuda:0")
    assert len({replace(identity, dtype=dtype).fingerprint for dtype in ("float32", "float16", "bfloat16")}) == 3
    with pytest.raises(ValueError):
        replace(identity, device="cpu", dtype="float16")
    assert replace(identity, batch_size=32).batch_size == 32
    with pytest.raises(ValueError):
        replace(identity, device="cpu", batch_size=32)
    for invalid in ({"batch_size":True},{"batch_size":8.5},{"max_length":True},{"max_length":512.5}):
        with pytest.raises(ValueError):
            replace(identity,**invalid)


def test_offline_runtime_shares_a_snapshot_without_reusing_a_different_precision(tmp_path, monkeypatch):
    import sys
    from campusai.retrieval.model_runtime import RetrievalModelRuntime
    loaded = []
    def encoder(path, **settings):
        loaded.append((path, settings))
        return object()
    monkeypatch.setitem(sys.modules,"sentence_transformers",SimpleNamespace(CrossEncoder=encoder))
    runtime = RetrievalModelRuntime()
    def load(_number):
        return runtime.get_offline_reranker(tmp_path, device="cuda:0", dtype="float16", snapshot_sha256="a"*64)
    with ThreadPoolExecutor(max_workers=10) as workers:
        models = list(workers.map(load,range(20)))
    assert all(model is models[0] for model in models)
    assert len(loaded) == 1 and loaded[0][1]["local_files_only"] is True
    assert loaded[0][1]["model_kwargs"] == {"torch_dtype":"float16"}
    assert runtime.get_offline_reranker(tmp_path,device="cuda:0",dtype="float32",snapshot_sha256="a"*64) is not models[0]
    assert runtime.get_offline_reranker(tmp_path,device="cuda:0",dtype="float16",snapshot_sha256="b"*64) is not models[0]
    assert len(loaded) == 3
    assert all(item["model_name"] == "[local-snapshot]" for item in runtime.loaded_models())
    with pytest.raises(ValueError):
        runtime.get_offline_reranker(tmp_path,device="cpu",dtype="float16")
    runtime.clear()
    assert runtime.loaded_models() == []


def test_dynamic_batches_keep_each_requests_scores_and_provenance(tmp_path):
    (tmp_path / "config.json").write_text("{}")
    identity = ModelIdentity("BAAI/bge-reranker-v2-m3", tmp_path.name, snapshot_sha256(tmp_path), tmp_path.name,
        batch_window_ms=10, max_batch_pairs=40)
    calls = []
    class Model:
        def predict(self, pairs, **kwargs):
            calls.append(pairs)
            return [float(query) + len(content) for query, content in pairs]
    provider = OfflineCrossEncoderReranker(identity, tmp_path, model_loader=Model,
        queue_limit=19, timeout_ms=2000, batch_window_ms=10, max_batch_pairs=40)
    barrier = Barrier(10)
    def request(number):
        barrier.wait(timeout=3)
        candidate = RerankCandidate(str(number), f"doc{number}", str(number), 1, "evidence", 1, .5)
        result = provider.score(str(number), [candidate])[0]
        assert result.doc_id == f"doc{number}" and result.reranker_score == number + 8
    try:
        with ThreadPoolExecutor(max_workers=10) as workers:
            list(workers.map(request, range(10)))
        assert len(calls) < 10
        assert provider.metrics_snapshot()["max_batch_requests"] > 1
    finally:
        provider.close()
        provider.drain()


def test_batched_timeout_cancellation_and_shutdown_prevent_new_inference(tmp_path):
    from campusai.retrieval.cross_encoder_provider import RerankerUnavailable
    (tmp_path / "config.json").write_text("{}")
    identity = ModelIdentity("BAAI/bge-reranker-v2-m3", tmp_path.name, snapshot_sha256(tmp_path), tmp_path.name,
        batch_window_ms=2)
    entered, release = Event(), Event()
    class Model:
        def predict(self, pairs, **kwargs):
            entered.set()
            release.wait(3)
            return [1.] * len(pairs)
    provider = OfflineCrossEncoderReranker(identity, tmp_path, model_loader=Model,
        queue_limit=1, timeout_ms=30, batch_window_ms=2)
    candidate = [RerankCandidate("a", "doc", "a", 1, "evidence", 1, .5)]
    try:
        with ThreadPoolExecutor(max_workers=1) as workers:
            first = workers.submit(provider.score, "first", candidate)
            assert entered.wait(3)
            with pytest.raises(RerankerUnavailable, match="timeout"):
                provider.score("queued", candidate)
            with pytest.raises(RerankerUnavailable, match="timeout"):
                first.result(timeout=3)
            provider.close()
            release.set()
        provider.drain()
        metrics = provider.metrics_snapshot()
        assert metrics["cancelled_requests"] == 1
        assert metrics["active_requests"] == metrics["queue_depth"] == 0
        with pytest.raises(RerankerUnavailable, match="feature_disabled"):
            provider.score("new", candidate)
    finally:
        release.set()
        provider.close()


def test_score_cache_binds_content_scope_and_rebuilds_rank_provenance(tmp_path):
    (tmp_path / "config.json").write_text("{}")
    identity = ModelIdentity("BAAI/bge-reranker-v2-m3", tmp_path.name, snapshot_sha256(tmp_path), tmp_path.name)
    calls = []
    class Model:
        def predict(self, pairs, **kwargs):
            calls.append(pairs)
            return [float(len(text)) for _, text in pairs]
    provider = OfflineCrossEncoderReranker(identity, tmp_path, model_loader=Model, score_cache_size=2)
    candidate = RerankCandidate("a", "doc", "a", 1, "evidence", 1, .5)
    try:
        provider.score("query", [candidate])
        changed_rank = replace(candidate, original_rank=2, original_rrf_score=.3)
        assert provider.score("query", [changed_rank])[0].original_rank == 2
        assert len(calls) == 1
        provider.score("query", [replace(candidate, content="changed evidence")])
        provider.score("query", [replace(candidate, doc_id="other")])
        assert len(calls) == 3
        assert provider.metrics_snapshot()["score_cache_hits"] == 1
        assert provider.metrics_snapshot()["score_cache_entries"] == 2
    finally:
        provider.close()
    assert provider.metrics_snapshot()["score_cache_entries"] == 0


def test_service_shutdown_closes_provider_even_when_cache_cleanup_follows():
    closed = []
    service = CampusAIQueryService(SimpleNamespace(phase7_provider=SimpleNamespace(close=lambda:closed.append("provider"))),
        SimpleNamespace(llm=SimpleNamespace(close=lambda:closed.append("llm"))))
    service.close()
    assert closed == ["provider", "llm"]


def test_service_shutdown_releases_llm_when_other_cleanup_fails():
    closed = []
    def fail(name):
        closed.append(name)
        raise RuntimeError(name + " cleanup failed")
    service = CampusAIQueryService(SimpleNamespace(phase7_provider=SimpleNamespace(close=lambda:fail("provider"))),
        SimpleNamespace(llm=SimpleNamespace(close=lambda:closed.append("llm"))),
        cache=SimpleNamespace(close=lambda:fail("cache")))
    with pytest.raises(RuntimeError,match="cache"):
        service.close()
    assert closed == ["provider","cache","llm"]


def test_web_assigns_server_identity_and_forwards_scope_without_mode_override():
    seen = []
    class Service:
        metrics = SimpleNamespace(as_dict=lambda:{})
        last_cache_hit = False
        def ask(self, question, **options):
            seen.append(options)
            return SimpleNamespace(to_dict=lambda:{"answer":"OK", "citations":[]})
    app = make_wsgi_app(CampusAIApplication(Service()))
    payload = {"question":"tuition", "doc_ids":["uploaded"], "top_k":3,
               "request_id":"force-cohort", "mode":"phase7"}
    assert call(app, "/api/query", "POST", payload)["status"].startswith("200")
    assert seen[0]["doc_ids"] == ["uploaded"] and seen[0]["top_k"] == 3
    assert len(seen[0]["request_id"]) == 32 and seen[0]["request_id"] != "force-cohort"
    assert "mode" not in seen[0]
    for invalid in ({"doc_ids":[]}, {"top_k":True}, {"filters":[]}, {"language":"xx"}):
        assert call(app, "/api/query", "POST", {"question":"tuition", **invalid})["status"].startswith("400")
    assert len(seen) == 1


def test_measurement_environment_disables_score_cache_and_binds_dtype(tmp_path, monkeypatch):
    from evaluation.reranker.release_workflow import measurement_environment
    from evaluation.common.release_artifacts import write_json
    snapshot = tmp_path / ("a"*40)
    snapshot.mkdir()
    (snapshot / "config.json").write_text("{}")
    identity = ModelIdentity("BAAI/bge-reranker-v2-m3", snapshot.name, snapshot_sha256(snapshot), snapshot.name,
        device="cuda:0", dtype="bfloat16")
    write_json(tmp_path / "model_snapshot_smoke.json", {"model_identity":identity.to_dict()})
    monkeypatch.setenv("RERANKER_SCORE_CACHE_SIZE", "4096")
    args = SimpleNamespace(model_dir=snapshot, results_dir=tmp_path, model_name=identity.model_name, device=identity.device)
    env = measurement_environment(args)
    assert env["RERANKER_DTYPE"] == "bfloat16" and env["RERANKER_SCORE_CACHE_SIZE"] == "0"
    assert env["RERANKER_QUEUE_LIMIT"] == "19"


def test_release_commands_propagate_every_inference_setting():
    from evaluation.reranker.release_workflow import commands
    args = SimpleNamespace(stage="model", model_dir="snapshot", model_name="model/repo", device="cuda:0",
        dtype="float16", batch_size=32, max_length=512, batch_window_ms=2, max_batch_pairs=200,
        results_dir=__import__("pathlib").Path("results"), index_dir="index", benchmark_dir="benchmark")
    command = commands(args)[0]
    for flag, value in (("--dtype","float16"),("--batch-size","32"),("--max-length","512"),
                        ("--batch-window-ms","2"),("--max-batch-pairs","200")):
        assert command[command.index(flag)+1] == value


def test_server_factory_uses_guarded_activation_and_configured_llm(tmp_path, monkeypatch):
    from scripts.operations import serve
    calibration = tmp_path / "phase6.json"
    calibration.write_text('{}')
    monkeypatch.setenv("CAMPUSAI_INDEX_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("CAMPUSAI_STORE_DIR", str(tmp_path / "store"))
    monkeypatch.setenv("CAMPUSAI_RETRIEVAL_CALIBRATION", str(calibration))
    monkeypatch.setenv("CAMPUSAI_LLM_CONFIG", "configured.yaml")
    retriever = SimpleNamespace(phase7_enabled=True, phase7_provider=None)
    calls = []
    def activate(index, baseline, dev):
        calls.append((index, baseline, dev))
        return retriever
    monkeypatch.setattr(serve, "build_phase7_retriever", activate)
    llm = SimpleNamespace(generate_json=lambda *_args, **_kwargs: {})
    monkeypatch.setattr(serve, "create_llm", lambda config: llm if config == "configured.yaml" else None)
    app = serve.build_application()
    try:
        assert calls[0][:2] == (tmp_path / "uploads", calibration)
        assert app.query_service.default_mode is None
        assert app.query_service.canary.traffic_percent == 0
        assert app.query_service.answer_generator.llm is llm
    finally:
        app.close()


def test_server_factory_releases_warmed_provider_when_llm_configuration_fails(tmp_path, monkeypatch):
    from scripts.operations import serve
    calibration = tmp_path / "phase6.json"
    calibration.write_text('{}')
    monkeypatch.setenv("CAMPUSAI_RETRIEVAL_CALIBRATION", str(calibration))
    monkeypatch.setenv("CAMPUSAI_LLM_CONFIG", "invalid.yaml")
    closed = []
    provider = SimpleNamespace(close=lambda:closed.append("provider"))
    monkeypatch.setattr(serve, "build_phase7_retriever", lambda *_args:SimpleNamespace(phase7_provider=provider))
    def invalid(_config):
        raise ValueError("invalid LLM configuration")
    monkeypatch.setattr(serve, "create_llm", invalid)
    with pytest.raises(ValueError, match="LLM"):
        serve.build_application()
    assert closed == ["provider"]


def test_application_shutdown_closes_service_after_job_shutdown_error():
    closed = []
    def failed_shutdown(**_options):
        raise RuntimeError("worker shutdown failed")
    service = SimpleNamespace(metrics=SimpleNamespace(), close=lambda:closed.append("service"))
    app = CampusAIApplication(service, jobs=SimpleNamespace(shutdown=failed_shutdown))
    with pytest.raises(RuntimeError, match="shutdown"):
        app.close()
    assert closed == ["service"]


def test_answer_cache_single_flight_releases_idle_keys_even_after_failure():
    from campusai.rag.cache import RAGAnswerCache
    from threading import Lock
    import time
    entered = []
    guard = Lock()
    active, peak = [0], [0]
    with RAGAnswerCache() as cache:
        barrier = Barrier(20)
        def request(number):
            barrier.wait(timeout=3)
            try:
                with cache.lock("same-query"):
                    with guard:
                        active[0] += 1
                        peak[0] = max(peak[0], active[0])
                        entered.append(number)
                    time.sleep(.001)
                    with guard:
                        active[0] -= 1
                    if number == 7:
                        raise ValueError("generation failed")
            except ValueError:
                assert number == 7
        with ThreadPoolExecutor(max_workers=20) as workers:
            list(workers.map(request,range(20)))
        assert peak[0] == 1 and len(entered) == 20
        for number in range(1000):
            with cache.lock(str(number)):
                pass
        assert not cache._locks


def test_route_search_finds_feasible_policy_using_all_retrieval_boundaries():
    from evaluation.reranker.calibrate_hard_query_route import fit_feature_route
    samples = [{"qid":f"h{i}","difficulty":"hard","confidence":.9,"margin":.1,
                "agreement":.4,"constraints":4} for i in range(3)]
    samples += [{"qid":f"e{i}","difficulty":"easy","confidence":.1,"margin":.01,
                 "agreement":1.,"constraints":1} for i in range(20)]
    config, metrics, feasible = fit_feature_route(samples)
    assert feasible and metrics["hard_recall"] == 1. and metrics["easy_unnecessary_rerank_rate"] == 0.
    assert metrics["selected"] == 3
    assert config["constraint_threshold"] > 1 or config["minimum_agreement"] > .4


def test_policy_research_rejects_heldout_and_invalid_or_duplicate_scores():
    from evaluation.reranker.optimize_reranker_dev import fit, rank_fusion
    with pytest.raises(ValueError, match="dev"):
        fit([{"split":"test"}],[])
    item = {"doc_id":"doc","chunk_id":"a","rank":1}
    with pytest.raises(ValueError, match="finite"):
        rank_fusion([item],{"a":float("nan")},.5,8)
    with pytest.raises(ValueError, match="duplicate"):
        rank_fusion([item,item],{"a":1.},.5,8)


def test_evidence_policy_search_can_abstain_without_fabricating_a_passing_target():
    from evaluation.reranker.optimize_reranker_dev import fit
    gold = {"doc_id":"doc","chunk_id":"positive","page":1}
    def item(name):
        return {"doc_id":"doc","chunk_id":name,"page":1,"rank":1}
    rows = [{"qid":"p","split":"dev","answerable":True,"gold_evidence":[gold]},
            {"qid":"n","split":"dev","answerable":False,"gold_evidence":[]}]
    observations = [{"qid":"p","baseline":[item("wrong")],"pool":[item("wrong")],"scores":{"wrong":2.}},
                    {"qid":"n","baseline":[item("negative")],"pool":[item("negative")],"scores":{"negative":-2.}}]
    report = fit(rows,observations)
    assert report["selected"]["metrics"]["negative_fpr"] == 0.
    assert report["selected"]["metrics"]["recall5"] == 0.
    assert report["feasible"] is False


def test_precision_probe_measures_and_propagates_the_selected_candidate_cap(monkeypatch, tmp_path):
    from evaluation.reranker import benchmark_reranker_precision as probe
    output = Path(__file__).resolve().parents[1] / '.release/reranker/studies' / ('test-cap-' + uuid4().hex)
    captured = []
    monkeypatch.setattr(probe, 'worker', lambda args: captured.append(args.capacity_cap))
    try:
        assert probe.main(['--model-dir', str(tmp_path), '--output', str(output),
                           '--worker', 'float16', '--capacity-cap', '20']) == 0
        assert captured == [20]
        commands = []
        monkeypatch.setattr(probe.subprocess, 'run', lambda cmd, **_kwargs: commands.append(cmd))
        assert probe.main(['--model-dir', str(tmp_path), '--output', str(output),
                           '--capacity-cap', '16']) == 0
        assert len(commands) == 3
        assert all(cmd[cmd.index('--capacity-cap') + 1] == '16' for cmd in commands)
    finally:
        # Only this test's unique attempt file is removed, never model evidence.
        attempt = output / 'attempt.json'
        if attempt.exists():
            attempt.unlink()
        output.rmdir()
