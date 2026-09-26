from campusai.api import CampusAIApplication
from campusai.observability import MetricsRegistry


class FakeAnswer:
    def to_dict(self):
        return {"answer": "ok", "citations": []}


class FakeService:
    metrics = MetricsRegistry()
    last_cache_hit = False
    retriever = type("Retriever", (), {"index_root": None, "_indexes": {}})()

    def ask(self, question, **options):
        return FakeAnswer()


def test_application_exposes_safe_structured_contract(tmp_path):
    service = FakeService()
    service.retriever.index_root = tmp_path
    app = CampusAIApplication(service)
    assert app.health()["status"] == "ok"
    assert app.readiness()["status"] == "ready"
    assert app.query("hello")["answer"]["answer"] == "ok"
    assert app.query(" ")["error_code"] == "empty_question"
