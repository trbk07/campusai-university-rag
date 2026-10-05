"""Resolve the current evidence cycle for user-facing Phase 7 commands."""
from pathlib import Path, PureWindowsPath

from evaluation.common.release_artifacts import read_json

ROOT = Path(__file__).resolve().parents[2]


def active_cycle(root: Path = ROOT) -> dict[str, Path]:
    defaults = {"results_dir": Path("evaluation/results"), "benchmark_dir": Path("data/benchmark"),
                "index_dir": Path(".tmp/hybrid-index")}
    path = root / "configs/phase7_release_cycle.json"
    if not path.is_file():
        return defaults
    record = read_json(path)
    if record.get("schema_version") != 1 or record.get("status") != "active":
        raise ValueError("invalid active Phase 7 cycle selector")
    for name in defaults:
        value = record.get(name)
        if (not isinstance(value, str) or not value or PureWindowsPath(value).drive
                or PureWindowsPath(value).root or ".." in PureWindowsPath(value).parts
                or not (root / value).resolve().is_relative_to(root.resolve())):
            raise ValueError("unsafe active Phase 7 cycle path")
        defaults[name] = Path(value)
    return defaults
