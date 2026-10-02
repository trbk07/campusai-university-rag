"""Synthetic transport fixture for the M7 runner; never release evidence."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread, local
from types import SimpleNamespace

from campusai.retrieval.cross_encoder_provider import ModelIdentity, snapshot_sha256
from campusai.retrieval.hybrid import RetrievalResult
from campusai.retrieval.routing import RoutingTrace
from evaluation import measure_phase7_http


def test_http_runner_exercises_rag_llm_and_raw_concurrency_matrix(tmp_path, monkeypatch):
    answer = {"answer": "Fact.", "confidence": "high", "abstained": False,
              "citations": [{"chunk_id": "c1", "page": 1, "quote": "Fact."}],
              "claims": [{"claim_id": "a", "text": "Fact.", "type": "fact", "citation_ids": ["c1"]}]}
    class LLMHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers["Content-Length"])
            self.rfile.read(length)
            body = json.dumps({"choices": [{"message": {"content": json.dumps(answer)}}],
                               "usage": {"total_tokens": 8}}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *_args):
            pass
    upstream = ThreadingHTTPServer(("127.0.0.1", 0), LLMHandler)
    upstream_thread = Thread(target=upstream.serve_forever, daemon=True)
    upstream_thread.start()
    try:
        model_dir = tmp_path / ("e" * 40)
        model_dir.mkdir()
        (model_dir / "config.json").write_text("{}", encoding="utf-8")
        identity = ModelIdentity("BAAI/bge-reranker-v2-m3", model_dir.name,
                                 snapshot_sha256(model_dir), model_dir.name)
        index, benchmark, results = (tmp_path / name for name in ("index", "benchmark", "results"))
        for directory in (index, benchmark, results):
            directory.mkdir()
        (index / "manifest.json").write_text(json.dumps({"documents": ["doc"]}), encoding="utf-8")
        (results / "phase6_retrieval_calibration.json").write_text("{}", encoding="utf-8")
        (results / "reranker_score_calibration.json").write_text('{"rerank_candidate_cap":10}', encoding="utf-8")
        (results / "model_snapshot_smoke.json").write_text(json.dumps({"model_identity": identity.to_dict()}), encoding="utf-8")
        rows = [{"qid": f"q{i}", "split": "test",
                 "question": f"negative question {i}" if i < 10 else f"positive question {i}",
                 "answerable": i >= 10, "difficulty": "hard" if i % 2 else "easy",
                 "doc_ids": ["doc"], "filters": {}, "language": "en"} for i in range(30)]
        (benchmark / "human_retrieval_test.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        llm_config = tmp_path / "llm.json"
        llm_config.write_text(json.dumps({"llm": {"provider": "openai-compatible", "model": "test-live-http",
            "api_key_env": "TEST_PHASE7_LLM_KEY", "endpoint": f"http://127.0.0.1:{upstream.server_port}/v1/chat/completions",
            "requests_per_minute": 0, "max_retries": 0, "timeout_seconds": 5,
            "cache_path": str(tmp_path / "llm-cache.sqlite")}}), encoding="utf-8")
        monkeypatch.setenv("TEST_PHASE7_LLM_KEY", "fixture-only")
        monkeypatch.setattr(measure_phase7_http, "require_previous_gates", lambda *_args, **_kwargs: None)
        monkeypatch.setattr(measure_phase7_http, "source_identity", lambda *_args: {"source_sha256": "a"*64})
        monkeypatch.setattr(measure_phase7_http, "policy_bindings", lambda *_args: {})
        class Provider:
            def warm_up(self): pass
            def drain(self): pass
            def close(self): pass
            def metrics_snapshot(self): return {"fixture": True}
        class Retriever:
            phase7_enabled = True
            phase7_policy = SimpleNamespace(rerank_candidate_cap=10)
            phase7_cache_fingerprint = "fixture"
            phase7_provider = Provider()
            query_cache_size = 0
            def __init__(self):
                self.index_root = index
                self._local = local()
            @property
            def last_trace(self):
                return getattr(self._local, "trace", RoutingTrace(route="uninitialized"))
            def search(self, query, **_kwargs):
                negative = query.startswith("negative")
                self._local.trace = RoutingTrace(route="hybrid_rrf", rerank_selected=not negative,
                    latency_ms={"parse": .1, "bm25": .1, "dense": .1, "fusion": .1, "total": .5})
                return [] if negative else [RetrievalResult("c1", "doc", 1, "Fact.", "text", .9,
                                                             "hybrid_rrf", {"page_range": [1, 1]})]
        from campusai.retrieval import reranker_activation
        monkeypatch.setattr(reranker_activation, "build_phase7_retriever", lambda *_a, **_k: Retriever())
        output = tmp_path / "http-report.json"
        monkeypatch.setattr("sys.argv", ["measure_phase7_http", "--index-dir", str(index),
            "--benchmark-dir", str(benchmark), "--results-dir", str(results),
            "--model-dir", str(model_dir), "--llm-config", str(llm_config),
            "--deployment-ram-bytes", str(10**12), "--output", str(output)])
        assert measure_phase7_http.main() == 0
        report = json.loads(output.read_text(encoding="utf-8"))
        assert report["status"] == "pass"
        assert [p["concurrency"] for p in report["profiles"]] == [1, 5, 10, 20]
        assert all(p["summary"]["requests"] == 100 and p["summary"]["grounded_answers"] >= 30
                   and p["summary"]["llm_calls"] >= 30 for p in report["profiles"])
        assert all(sample["stages_ms"]["llm"] > 0 for profile in report["profiles"]
                   for sample in profile["samples"] if not sample["abstained"])
    finally:
        upstream.shutdown()
        upstream.server_close()
        upstream_thread.join(timeout=5)
