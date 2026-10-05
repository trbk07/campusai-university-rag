from argparse import Namespace
from types import SimpleNamespace

import pytest

from evaluation.reranker.release_workflow import commands, main
from evaluation.reranker.measure_reranker_capacity import select_hard_workload, resource_sample


def options(tmp_path, stage):
    return Namespace(stage=stage, results_dir=tmp_path / "results", index_dir=tmp_path / "index",
                     benchmark_dir=tmp_path / "benchmark", model_dir=tmp_path / "model", model_name="model", device="cpu",
                     llm_config=tmp_path / "llm.yaml", rubric=tmp_path / "rubric.json",
                     observations=tmp_path / "results/raw/paired.json", deployment_ram_bytes=10000,
                     profile="fixture", environment_id="fixture", http_p95_budget_ms=1000)


def test_quality_collection_freezes_protocol_before_any_heldout_ranking(tmp_path):
    args = options(tmp_path, "quality-collect")
    planned = commands(args)
    assert [row[2] for row in planned] == ["evaluation.reranker.collect_paired_answers",
        "evaluation.retrieval.compare_retrieval_quality", "evaluation.reranker.build_supplemental_report",
        "evaluation.reranker.build_supplemental_report", "evaluation.reranker.collect_paired_answers"]
    assert "--prepare-only" in planned[0] and "--prepare-only" not in planned[-1]
    assert planned[2][-1] == "S3" and planned[3][-1] == "S5"
    assert str(args.rubric) in planned[0] and str(args.rubric) in planned[-1]


def test_final_quality_stage_consumes_existing_reviews_without_recollecting(tmp_path):
    args = options(tmp_path, "quality")
    planned = commands(args)
    assert len(planned) == 1 and planned[0][2] == "evaluation.reranker.paired_answer_quality"
    assert str(args.observations) in planned[0]


def test_performance_collects_real_resources_and_builds_s6_after_http(tmp_path):
    planned = commands(options(tmp_path, "performance"))
    assert [row[2] for row in planned] == ["evaluation.reranker.measure_reranker_capacity",
        "evaluation.reranker.measure_reranker_http", "evaluation.reranker.build_supplemental_report"]
    assert "--http-p95-budget-ms" in planned[0] and "--p95-budget-ms" in planned[1]
    assert "S6" in planned[-1] and planned[-1][-1].endswith("reranker_observability_observations.json")


@pytest.mark.parametrize("stage", ["quality", "quality-collect"])
def test_quality_stage_rejects_missing_rubric_before_measurement(stage):
    with pytest.raises(SystemExit) as error:
        main([stage, "--model-dir", "model"])
    assert error.value.code == 2


def test_hard_workload_uses_actual_route_even_when_code_tag_is_present():
    rows = [{"qid": "multi", "question": "Combine ABC123 and ABC124", "doc_ids": ["doc"],
             "answerable": True, "difficulty": "hard", "tags": ["exact_code"]},
            {"qid": "exact", "question": "ABC123", "doc_ids": ["doc"], "answerable": True,
             "difficulty": "hard", "tags": []},
            {"qid": "negative", "question": "Absent", "doc_ids": ["doc"], "answerable": False,
             "difficulty": "hard", "tags": []}]
    class Retriever:
        def search(self, **kwargs):
            assert kwargs["mode"] == "auto"
            self.last_trace = SimpleNamespace(route="hybrid_rrf" if "Combine" in kwargs["query"] else "exact_code",
                                             abstained=False)
            return [object(), object()]
    selected, probes = select_hard_workload(rows, Retriever(), ["doc"])
    assert selected == rows[:1]
    assert [p["qid"] for p in probes] == ["multi", "exact"]
    assert [p["eligible"] for p in probes] == [True, False]


def test_resource_sample_uses_actual_process_values():
    process = SimpleNamespace(pid=123, memory_info=lambda: SimpleNamespace(rss=456))
    observed = resource_sample(process, "cpu")
    assert observed["pid"] == 123 and observed["rss_bytes"] == 456
    assert "vram_allocated_bytes" not in observed
    from datetime import datetime
    assert datetime.fromisoformat(observed["at"]).tzinfo is not None
