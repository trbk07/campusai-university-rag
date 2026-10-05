"""Inventory physical workspace bytes and reachable Git blobs without mutation."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import subprocess


def git(*args: str, input: bytes | None = None) -> bytes:
    return subprocess.run(["git", *args], input=input, capture_output=True, check=True).stdout


def audit(root: Path) -> dict:
    tracked = set(git("ls-files", "-z").decode("utf-8").split("\0"))
    files, directories = [], Counter()
    for base, _, names in os.walk(root):
        for name in names:
            path = Path(base) / name
            size = path.stat().st_size
            relative = path.relative_to(root).as_posix()
            files.append({"path": relative, "bytes": size, "tracked": relative in tracked})
            for parent in path.parents:
                if parent == root:
                    break
                directories[parent.relative_to(root).as_posix()] += size
    objects = git("rev-list", "--objects", "--all")
    checked = git("cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize) %(rest)", input=objects)
    blobs = []
    for line in checked.decode("utf-8").splitlines():
        parts = line.split(" ", 3)
        if len(parts) == 4 and parts[1] == "blob":
            blobs.append({"oid": parts[0], "bytes": int(parts[2]), "path": parts[3]})
    return {"total_bytes": sum(f["bytes"] for f in files), "git_bytes": directories[".git"],
            "tracked_bytes": sum(f["bytes"] for f in files if f["tracked"]),
            "top_files": sorted(files, key=lambda f: -f["bytes"])[:20],
            "top_directories": [{"path": p, "bytes": s} for p, s in directories.most_common(20)],
            "tracked_largest": sorted([f for f in files if f["tracked"]], key=lambda f: -f["bytes"])[:50],
            "history_largest": sorted(blobs, key=lambda f: -f["bytes"])[:30],
            "history_over_10mib": [f for f in blobs if f["bytes"] >= 10 * 1024**2],
            "file_count": len(files)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(Path.cwd())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
