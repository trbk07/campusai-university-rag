import hashlib
import json

from evaluation.freeze_retrieval_baseline import model_tree_hash, stable_metrics


def test_phase7_baseline_ignores_runtime_latency_but_not_quality():
    source = {"benchmark_sha256": {"test": "a", "holdout": "b"},
              "index_sha256": "index", "calibration_sha256": "calibration",
              "model": "BAAI/bge-m3", "model_revision": "1",
              "rrf": {"k": 3, "candidate_limit": 40},
              "primary_test": {"quality": {"mrr_answerable": .8},
                               "negative": {"false_positive_rate": 0}},
              "primary_holdout": {"quality": {"mrr_answerable": .7},
                                  "negative": {"false_positive_rate": 0}},
              "ablation": {"auto": {"mrr": .8, "ndcg_at_5": .85, "p95_ms": 100}}}
    changed_latency = json.loads(json.dumps(source))
    changed_latency["ablation"]["auto"]["p95_ms"] = 900
    assert stable_metrics(source) == stable_metrics(changed_latency)
    changed_latency["primary_holdout"]["quality"]["mrr_answerable"] = .6
    assert stable_metrics(source) != stable_metrics(changed_latency)


def test_phase7_model_tree_hash_is_content_bound(tmp_path):
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    first = model_tree_hash(tmp_path)
    (tmp_path / "config.json").write_text('{"revision":"new"}', encoding="utf-8")
    assert model_tree_hash(tmp_path) != first
    expected = hashlib.sha256(json.dumps(
        [("config.json", hashlib.sha256(b'{"revision":"new"}').hexdigest())],
        separators=(",", ":")).encode()).hexdigest()
    assert model_tree_hash(tmp_path) == expected
