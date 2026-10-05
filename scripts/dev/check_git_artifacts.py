"""Block weights, raw dumps and oversized artifacts in the prospective commit."""
import argparse
import json
from pathlib import Path
import subprocess

from scripts.dev.manage_artifacts import category


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    paths = subprocess.check_output(["git", "ls-files", "-z"]).decode("utf-8").split("\0")
    forbidden = {".safetensors", ".bin", ".pt", ".pth", ".onnx", ".faiss", ".index", ".npy", ".npz", ".pkl", ".pickle"}
    errors = []
    for name in paths:
        path = Path(name)
        if not name or not path.is_file():
            continue
        kind = category(name, path.stat().st_size)
        if (kind or path.suffix in forbidden or path.name in {"dense.json", "bm25.json"}
                or any(part in path.parts for part in ("node_modules", "hf_cache", ".cache", ".local_artifacts"))):
            errors.append({"path": name, "reason": kind or "binary_or_cache"})
        elif (path.stat().st_size > 5 * 1024**2
              and not (name.startswith("data/benchmark/")
                       and path.name == "owner_generation_history_snapshot.json"
                       and path.stat().st_size <= 10 * 1024**2)):
            errors.append({"path": name, "reason": "over_5MiB_requires_external_artifact"})
    if "plan.md" not in paths:
        errors.append({"path": "plan.md", "reason": "roadmap_must_remain_tracked"})
    report = {"status": "fail" if errors else "pass", "errors": errors,
              "scope": "current Git index; history requires separate cleanup"}
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
