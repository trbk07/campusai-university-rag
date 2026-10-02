import io
import json

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
