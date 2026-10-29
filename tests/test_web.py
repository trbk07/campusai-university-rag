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
    assert '/assets/scripts/app.js' in page
    app = make_wsgi_app(CampusAIApplication(service))
    chat = call(app, '/assets/features/chat.js')['body'].decode('utf-8')
    api = call(app, '/assets/scripts/api.js')['body'].decode('utf-8')
    assert "answer.abstention_reason === 'provider_abstention'" in chat
    assert '45000' in api and 'controller.abort()' in api
    assert "error.name === 'TimeoutError' || error.name === 'AbortError'" in api
    assert 'Chưa đủ bằng chứng trong tài liệu đã chọn.' in chat


@pytest.mark.parametrize('timeout, expected', [(20,75000),(30,105000),(60,195000),
    (1000,300000),(float('nan'),45000),(True,45000),(None,45000)])
def test_browser_deadline_covers_the_configured_provider_wait(timeout,expected):
    service=Service()
    service.answer_generator=SimpleNamespace(llm=SimpleNamespace(timeout=timeout))
    application=CampusAIApplication(service)
    assert application.query_timeout_ms()==expected


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


def test_four_natural_language_queries_can_run_in_parallel_without_corpus_race(tmp_path):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from types import SimpleNamespace

    rendezvous = threading.Barrier(4)

    class Answer:
        def __init__(self, question): self.question = question
        def to_dict(self):
            return {'answer': self.question, 'citations': [], 'abstained': False}

    class ConcurrentService:
        metrics = type('Metrics', (), {'as_dict': lambda self: {}})()
        retriever = type('Retriever', (), {'index_root': tmp_path, '_indexes': {}})()
        answer_generator = SimpleNamespace(llm=object())
        _request_local = threading.local()
        last_cache_hit = False
        def ask(self, question, **_kwargs):
            rendezvous.wait(timeout=5)
            return Answer(question)

    app = make_wsgi_app(CampusAIApplication(ConcurrentService()), max_concurrent_queries=4)
    questions = [
        'Could you tell me what this policy says?',
        'Mình muốn hỏi tài liệu giải thích quy định này thế nào?',
        'Can you walk me through the relevant requirement?',
        'Cho mình hỏi, nội dung này áp dụng ra sao vậy?',
    ]
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda question: call(app, '/api/query', 'POST',
            {'question': question, 'language': 'en' if question.startswith('Could') or question.startswith('Can') else 'vi'}), questions))
    assert all(response['status'].startswith('200') for response in responses)
    answers = [json.loads(response['body'])['answer']['answer'] for response in responses]
    assert answers == questions


def test_unconfigured_server_abstains_over_http_without_a_provider_exception(tmp_path, monkeypatch):
    from scripts.operations import serve
    from tests.test_basic_rag import evidence

    monkeypatch.delenv("CAMPUSAI_LLM_CONFIG", raising=False)
    (tmp_path/"index").mkdir()
    monkeypatch.setenv("CAMPUSAI_INDEX_DIR", str(tmp_path/"index"))
    monkeypatch.setenv("CAMPUSAI_STORE_DIR", str(tmp_path/"store"))
    monkeypatch.setenv("CAMPUSAI_RETRIEVAL_CALIBRATION", str(tmp_path / "missing.json"))
    monkeypatch.delenv("CAMPUSAI_INGESTION_WORKERS", raising=False)
    monkeypatch.delenv("CAMPUSAI_INGESTION_PENDING", raising=False)
    monkeypatch.setenv("RERANKER_ENABLED", "false")
    application = serve.build_application()
    assert application.jobs.max_workers == 3
    assert application.jobs.max_pending == 8
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


@pytest.mark.parametrize("path", ["/api/query", "/api/feedback",
    "/api/documents/" + "a" * 64 + "/ocr",
    "/api/documents/" + "a" * 64 + "/locate"])
def test_deeply_nested_json_is_rejected_without_exception_or_lost_capacity(tmp_path, path):
    service = Service()
    service.retriever = SimpleNamespace(index_root=tmp_path, _indexes={})
    app = make_wsgi_app(CampusAIApplication(service), max_concurrent_queries=1)
    # A small request can still exceed the JSON decoder's recursion boundary.
    # Build raw bytes so the test encoder does not fail before reaching WSGI.
    body = b'{"question":"hello","history":' + b'[' * 20000 + b'0' + b']' * 20000 + b'}'
    captured = {}
    response = b''.join(app({"PATH_INFO": path, "REQUEST_METHOD": "POST",
        "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)},
        lambda status, headers: captured.update(status=status, headers=dict(headers))))
    assert captured['status'].startswith('400')
    assert json.loads(response) == {'ok': False, 'error_code': 'invalid_json'}
    assert captured['headers']['Cache-Control'] == 'no-store'
    assert call(app, '/health')['status'].startswith('200')
    assert call(app, '/api/query', 'POST', {'question': 'hello'})['status'].startswith('200')


def test_http_recovers_after_concurrent_malformed_json_requests(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Thread
    from urllib.error import HTTPError
    from urllib.request import Request, urlopen
    from wsgiref.simple_server import WSGIRequestHandler, make_server
    from evaluation.reranker.measure_reranker_http import _ThreadedHTTPServer

    errors = []
    class Quiet(WSGIRequestHandler):
        def log_message(self, *_args): pass
    class ObservedServer(_ThreadedHTTPServer):
        def handle_error(self, *_args): errors.append(True)
    service = Service()
    service.retriever = SimpleNamespace(index_root=tmp_path, _indexes={})
    app = make_wsgi_app(CampusAIApplication(service), max_concurrent_queries=1)
    bad = b'{"history":' + b'[' * 20000 + b'0' + b']' * 20000 + b'}'
    with make_server('127.0.0.1', 0, app, server_class=ObservedServer, handler_class=Quiet) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def send(data):
            request = Request(f'http://127.0.0.1:{server.server_port}/api/query',
                data=data, headers={'Content-Type': 'application/json'})
            try: response = urlopen(request, timeout=5)
            except HTTPError as error: response = error
            with response:
                return response.status, json.loads(response.read())
        try:
            with ThreadPoolExecutor(max_workers=4) as pool:
                responses = list(pool.map(send, [bad] * 20))
            assert responses == [(400, {'ok': False, 'error_code': 'invalid_json'})] * 20
            status, body = send(b'{"question":"hello"}')
            assert status == 200 and body['ok']
            assert errors == []
        finally:
            server.shutdown()
            thread.join(timeout=5)
        assert not thread.is_alive()


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
