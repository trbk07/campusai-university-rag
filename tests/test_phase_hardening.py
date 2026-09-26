import json

from campusai.documents.registry import DocumentRegistry
from campusai.observability import MetricsRegistry
from campusai.retrieval.calibration import RetrievalPolicy


def test_calibration_policy_is_explicit_and_auditable(tmp_path):
    report = tmp_path / "calibration.json"
    report.write_text(json.dumps({
        "mode": "hybrid_rerank",
        "constraints": {"min_recall": 0.9, "max_false_positive_rate": 0.02},
        "result": {"threshold": 0.46367466},
    }), encoding="utf-8")
    policy = RetrievalPolicy.from_report(report, expected_mode="hybrid_rerank")
    assert policy.accepts(0.5)
    assert not policy.accepts(0.2)
    assert policy.to_dict()["source"] == str(report)


def test_registry_reads_updates_across_instances(tmp_path):
    path = tmp_path / "registry.json"
    first = DocumentRegistry(path)
    second = DocumentRegistry(path)
    document = type("Doc", (), {"doc_id": "doc-1", "to_dict": lambda self: {"doc_id": self.doc_id}})()
    first.add(document)
    assert second.contains("doc-1")
    assert second.get("doc-1")["doc_id"] == "doc-1"


def test_metrics_capture_latency_and_errors():
    metrics = MetricsRegistry()
    with metrics.observe("query"):
        pass
    try:
        with metrics.observe("query"):
            raise RuntimeError("expected")
    except RuntimeError:
        pass
    snapshot = metrics.as_dict()["query"]
    assert snapshot["count"] == 2
    assert snapshot["errors"] == 1
    assert snapshot["p95_ms"] is not None
