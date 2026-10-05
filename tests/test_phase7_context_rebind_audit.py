"""The S2 provenance audit must diff the measured and target commits."""
from pathlib import Path
import subprocess

from evaluation.benchmarks.audit_context_rebind import changed_paths, uncommitted_source_paths


def test_commit_change_audit_uses_the_requested_two_commit_range(monkeypatch, tmp_path):
    calls = []

    def fake_check_output(args, **kwargs):
        calls.append((args, kwargs))
        return "evaluation/collector.py\nscripts/revision.py\n"

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)
    result = changed_paths(tmp_path, "before", "after", ("src", "evaluation", "scripts"))
    assert result == ["evaluation/collector.py", "scripts/revision.py"]
    assert calls == [(["git", "diff", "--name-only", "before", "after", "--",
                       "src", "evaluation", "scripts"], {"cwd": tmp_path, "text": True})]


def test_actual_s2_rebind_range_does_not_report_the_old_commit_contents():
    root = Path.cwd()
    paths = changed_paths(root, "b79543764fc7551729503129b650f66a3b77b4f6",
                          "618a6ef0b62390574937dcd1a197208b8fe96b08",
                          ("src", "evaluation", "scripts", "tests", "configs"))
    assert paths == ["configs/phase7_release_cycle.json",
                     "scripts/benchmarks/revise_dev_difficulty.py"]


def test_source_inventory_also_accounts_for_uncommitted_evaluation_tools(monkeypatch, tmp_path):
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs:
                        " M evaluation/benchmarks/audit_context_rebind.py\n"
                        "?? scripts/benchmarks/new_audit.py\n"
                        "?? evaluation/results/raw.json\n"
                        " M configs/phase7_release_cycle.json\n")
    assert uncommitted_source_paths(tmp_path) == [
        "configs/phase7_release_cycle.json",
        "evaluation/benchmarks/audit_context_rebind.py",
        "scripts/benchmarks/new_audit.py",
    ]
