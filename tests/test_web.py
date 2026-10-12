import io
import json
import hashlib
from types import SimpleNamespace
import pytest

from campusai.api import CampusAIApplication
from campusai.web import make_wsgi_app


class Service:
    metrics = type("Metrics", (), {"as_dict": lambda self: {}})()
    last_cache_hit = False
    retriever = type("Retriever", (), {"index_root": None, "_indexes": {}})()

    def ask(self, question, **kwargs):
        return type("Answer", (), {"to_dict": lambda self: {"answer": "OK", "citations": [], "abstained": False}})()


def call(app, path, method="GET", payload=None):
    body = json.dumps(payload).encode() if payload is not None else b""
    result = {}
    def start(status, headers):
        result["status"] = status
        result["headers"] = headers
    environ = {"PATH_INFO": path, "REQUEST_METHOD": method, "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
    result["body"] = b"".join(app(environ, start))
    return result


def test_wsgi_health_query_and_not_found(tmp_path):
    service = Service()
    service.retriever.index_root = tmp_path
    app = make_wsgi_app(CampusAIApplication(service))
    assert call(app, "/health")["status"].startswith("200")
    assert json.loads(call(app, "/api/query", "POST", {"question": "hello"})["body"])["ok"]
    assert call(app, "/missing")["status"].startswith("404")


def test_ui_distinguishes_provider_overload_from_missing_evidence(tmp_path):
    service = Service()
    service.retriever.index_root = tmp_path
    response = call(make_wsgi_app(CampusAIApplication(service)), "/")
    page = response['body'].decode('utf-8')
    assert "d.answer.abstention_reason==='provider_abstention'" in page
    assert "AbortSignal.timeout(45000)" in page
    assert "err.name==='TimeoutError'||err.name==='AbortError'" in page
    assert "Chưa đủ bằng chứng." in page


def test_wsgi_telemetry_is_request_local_and_not_exposed_in_answer(tmp_path):
    service = Service()
    service.retriever.index_root = tmp_path
    records = []
    app = make_wsgi_app(CampusAIApplication(service), telemetry_hook=records.append)
    response = call(app, "/api/query", "POST", {"question": "hello"})
    body = json.loads(response["body"])
    request_id = dict(response["headers"])["X-Request-ID"]
    assert request_id == records[0]["request_id"]
    assert records[0]["stage_calls"]["serialization"] == 1
    assert records[0]["server_total_ms"] >= records[0]["stages_ms"]["serialization"]
    assert "stages_ms" not in body and "retrieval_trace" not in body


def test_threaded_wsgi_http_transport_records_matching_request_id(tmp_path):
    from threading import Thread
    from urllib.request import Request, urlopen
    from wsgiref.simple_server import WSGIRequestHandler, make_server
    from evaluation.reranker.measure_reranker_http import _ThreadedHTTPServer

    class Quiet(WSGIRequestHandler):
        def log_message(self, *_args):
            pass

    service = Service()
    service.retriever.index_root = tmp_path
    records = []
    with make_server("127.0.0.1", 0, make_wsgi_app(CampusAIApplication(service), telemetry_hook=records.append),
                     server_class=_ThreadedHTTPServer, handler_class=Quiet) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            request = Request(f"http://127.0.0.1:{server.server_port}/api/query",
                              data=b'{"question":"hello"}', headers={"Content-Type": "application/json"})
            with urlopen(request, timeout=5) as response:
                assert response.status == 200
                request_id = response.headers["X-Request-ID"]
                assert json.loads(response.read())["ok"]
            assert [record["request_id"] for record in records] == [request_id]
        finally:
            server.shutdown()
            thread.join(timeout=5)


def test_unconfigured_server_abstains_over_http_without_a_provider_exception(tmp_path, monkeypatch):
    from scripts.operations import serve
    from tests.test_basic_rag import evidence

    monkeypatch.delenv("CAMPUSAI_LLM_CONFIG", raising=False)
    monkeypatch.setenv("CAMPUSAI_INDEX_DIR", str(tmp_path))
    monkeypatch.setenv("CAMPUSAI_RETRIEVAL_CALIBRATION", str(tmp_path / "missing.json"))
    monkeypatch.setenv("RERANKER_ENABLED", "false")
    application = serve.build_application()
    monkeypatch.setattr(application.query_service.retriever, "search", lambda *_args, **_kwargs: [evidence()])
    try:
        app = make_wsgi_app(application)
        response = call(app, "/api/query", "POST", {"question": "Which course?", "language": "en"})
        assert response["status"].startswith("200")
        answer = json.loads(response["body"])["answer"]
        assert answer["abstained"] and answer["citations"] == []
        assert call(app, "/ready")["status"].startswith("503")
        assert application.query_service.answer_generator.llm is None
    finally:
        application.close()


def test_calibration_mismatch_is_service_unavailable_without_private_error_details(tmp_path):
    from campusai.retrieval.calibration import CalibrationError

    class MisconfiguredService(Service):
        def ask(self, *_args, **_kwargs):
            raise CalibrationError("private calibration path and fingerprint")

    service = MisconfiguredService()
    service.retriever = SimpleNamespace(index_root=tmp_path, _indexes={})
    app = make_wsgi_app(CampusAIApplication(service))
    response = call(app, "/api/query", "POST", {"question": "Which course?"})
    assert response["status"].startswith("503")
    assert json.loads(response["body"]) == {"ok": False, "error_code": "retrieval_not_ready"}
    response = call(app, "/api/query", "POST", ["malformed request"])
    assert response["status"].startswith("400")


def test_readiness_rejects_calibration_from_another_index_and_rechecks_after_change(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_bytes(b'{"documents": {}}')
    service = Service()
    service.retriever = SimpleNamespace(index_root=tmp_path, _indexes={}, policies={
        "hybrid_rrf": SimpleNamespace(index_sha256="a" * 64)})
    service.answer_generator = SimpleNamespace(llm=object())
    application = CampusAIApplication(service)
    app = make_wsgi_app(application)
    assert call(app, "/ready")["status"].startswith("503")


    service.retriever.policies["hybrid_rrf"].index_sha256 = hashlib.sha256(manifest.read_bytes()).hexdigest()
    assert call(app, "/ready")["status"].startswith("200")
    manifest.unlink()
    assert call(app, "/ready")["status"].startswith("503")


@pytest.mark.parametrize("failure", [FileNotFoundError("private/index/bm25.json"),
                                    json.JSONDecodeError("private index corruption", "not-json", 0)])
def test_index_failure_is_service_unavailable_while_request_json_errors_stay_bad_requests(failure):
    class BrokenIndexService(Service):
        def ask(self, *_args, **_kwargs):
            raise failure
    app = make_wsgi_app(CampusAIApplication(BrokenIndexService()))
    response = call(app, "/api/query", "POST", {"question": "Which course?"})
    assert response["status"].startswith("503")
    assert json.loads(response["body"]) == {"ok": False, "error_code": "retrieval_not_ready"}
    captured = {}
    body = b"{not-json"
    result = b"".join(app({"PATH_INFO": "/api/query", "REQUEST_METHOD": "POST",
        "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)},
        lambda status, headers: captured.update(status=status)))
    assert captured["status"].startswith("400")
    assert json.loads(result)["error_code"] == "invalid_json"


def test_invalid_language_container_is_a_bad_request():
    app = make_wsgi_app(CampusAIApplication(Service()))
    assert call(app, "/api/query", "POST", {"question": "hello", "language": []})["status"].startswith("400")


def test_rejected_request_cannot_attach_the_previous_workers_evidence(tmp_path):
    from campusai.rag.service import CampusAIQueryService
    from campusai.rag.grounding import GroundedAnswerGenerator
    from tests.test_basic_rag import FakeLLM, evidence, valid_payload
    retriever = SimpleNamespace(index_root=tmp_path, _indexes={}, reranker=None,
                               search=lambda *_a, **_kw: [evidence()])
    service = CampusAIQueryService(retriever, GroundedAnswerGenerator(FakeLLM(valid_payload())))
    records = []
    def capture(trace):
        records.append({**trace, "evidence": list(service.last_retrieval)})
    web = make_wsgi_app(CampusAIApplication(service), telemetry_hook=capture)
    def denied(environ, start_response):
        environ['campusai.authorized_doc_ids'] = ['another-document']
        return web(environ, start_response)
    try:
        assert call(web, '/api/query', 'POST', {'question': 'Which course?'})['status'].startswith('200')
        assert records[-1]['evidence']
        assert call(denied, '/api/query', 'POST', {'question': 'Which course?', 'doc_ids': ['doc-1']})['status'].startswith('400')
        assert records[-1]['evidence'] == [] and records[-1]['retrieval_trace'] is None
        assert records[-1]['cache_hit'] is False
        assert call(web, '/api/query', 'POST', {'question': 'Which course?'})['status'].startswith('200')
        assert call(web, '/api/query', 'POST', {'question': 'Which course?', 'language': []})['status'].startswith('400')
        assert records[-1]['evidence'] == [] and records[-1]['retrieval_trace'] is None
        assert records[-1]['cache_hit'] is False
    finally:
        service.close()
