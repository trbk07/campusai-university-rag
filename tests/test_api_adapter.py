from campusai.api import CampusAIApplication
from campusai.observability import MetricsRegistry


class FakeAnswer:
    def to_dict(self):
        return {"answer": "ok", "citations": []}


class FakeService:
    metrics = MetricsRegistry()
    last_cache_hit = False
    retriever = type("Retriever", (), {"index_root": None, "_indexes": {}})()
    answer_generator = type("Generator", (), {"llm": object()})()

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


def test_readiness_requires_llm_configuration_even_with_an_existing_index(tmp_path):
    from campusai.rag.grounding import GroundedAnswerGenerator
    from campusai.rag.service import CampusAIQueryService
    from campusai.retrieval.hybrid import HybridRetriever

    service = CampusAIQueryService(HybridRetriever(tmp_path), GroundedAnswerGenerator(None))
    try:
        app = CampusAIApplication(service)
        assert app.liveness()["status"] == "alive"
        assert app.readiness()["status"] == "not_ready"
        assert app.readiness()["llm_configured"] is False
    finally:
        service.close()
