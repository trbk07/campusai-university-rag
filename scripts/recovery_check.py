"""Verify index recovery behavior without mutating the live corpus."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from campusai.retrieval.dense_index import DenseIndex, IndexCorruptError


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index-root", default="data/index")
    args = parser.parse_args()
    root = Path(args.index_root)
    loaded = 0
    for dense_path in root.glob("*/dense.json"):
        DenseIndex.load(dense_path)
        loaded += 1
    with tempfile.TemporaryDirectory(prefix="campusai-recovery-") as tmp:
        copy = Path(tmp) / "dense.json"
        source = next(root.glob("*/dense.json"), None)
        if source is None:
            raise SystemExit("no dense indexes found")
        shutil.copy2(source, copy)
        data = json.loads(copy.read_text(encoding="utf-8"))
        data["checksum"] = "corrupted"
        copy.write_text(json.dumps(data), encoding="utf-8")
        try:
            DenseIndex.load(copy)
        except IndexCorruptError:
            pass
        else:
            raise SystemExit("corruption was not rejected")
    print(json.dumps({"loaded_indexes": loaded, "corruption_rejected": True}))


if __name__ == "__main__":
    main()
