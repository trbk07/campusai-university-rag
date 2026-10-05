from pathlib import Path

import pytest

from evaluation.common.release_artifacts import write_json, source_identity
from evaluation.reranker.active_cycle import active_cycle


def test_active_cycle_has_legacy_fallback_and_explicit_safe_paths(tmp_path):
    assert active_cycle(tmp_path)["results_dir"] == Path("evaluation/results")
    record = {"schema_version": 1, "status": "active", "results_dir": "evaluation/results/cycle",
              "benchmark_dir": "data/benchmark/cycle", "index_dir": ".tmp/index"}
    write_json(tmp_path / "configs/phase7_release_cycle.json", record)
    assert active_cycle(tmp_path)["benchmark_dir"] == Path("data/benchmark/cycle")


@pytest.mark.parametrize("path", ["../outside", "C:/outside", "/absolute", "\\outside", "", None])
def test_active_cycle_rejects_paths_outside_repository(tmp_path, path):
    record = {"schema_version": 1, "status": "active", "results_dir": path,
              "benchmark_dir": "data/benchmark/cycle", "index_dir": ".tmp/index"}
    write_json(tmp_path / "configs/phase7_release_cycle.json", record)
    with pytest.raises(ValueError):
        active_cycle(tmp_path)


def test_local_credential_is_excluded_from_source_identity_but_public_config_is_bound(tmp_path, monkeypatch):
    monkeypatch.setattr("evaluation.common.release_artifacts.subprocess.check_output", lambda *a, **k: "fixed-commit")
    config = tmp_path / "configs"
    config.mkdir()
    secret = config / "gemini.yaml"
    public = config / "default.yaml"
    secret.write_text("local-example-key-1", encoding="utf-8")
    public.write_text("llm: {}", encoding="utf-8")
    original = source_identity(tmp_path)["source_sha256"]
    secret.write_text("local-example-key-2", encoding="utf-8")
    assert source_identity(tmp_path)["source_sha256"] == original
    public.write_text("llm: {provider: gemini}", encoding="utf-8")
    assert source_identity(tmp_path)["source_sha256"] != original
