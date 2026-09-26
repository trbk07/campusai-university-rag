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
