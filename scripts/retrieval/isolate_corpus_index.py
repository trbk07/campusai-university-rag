"""Isolate the freshly indexed PDF corpus from pre-existing local index data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from campusai.retrieval.index_builder import _write_corpus_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path(".tmp/baseline-index"))
    parser.add_argument("--target", type=Path, default=Path(".tmp/baseline-clean/baseline-index"))
    args = parser.parse_args()
    if args.target.exists():
        raise SystemExit(f"target already exists: {args.target}")
    report = json.loads((args.source / "corpus_build_report.json").read_text(encoding="utf-8"))
    manifest = json.loads((args.source / "manifest.json").read_text(encoding="utf-8"))
    source_manifest = json.loads(Path("data/corpus/university/manifest.json").read_text(encoding="utf-8"))
    allowed = {row["sha256"] for row in source_manifest["documents"]}
    doc_ids = report["indexed_doc_ids"]
    if report.get("status") != "pass" or len(doc_ids) < 8 or len(set(doc_ids)) != len(doc_ids):
        raise SystemExit("source build report is not a valid Phase 3 corpus")
    if not set(doc_ids) <= allowed or not set(doc_ids) <= set(manifest["documents"]):
        raise SystemExit("source index contains an unverified document")
    args.target.mkdir(parents=True)
    for doc_id in doc_ids:
        shutil.copytree(args.source / doc_id, args.target / doc_id)
    first = json.loads((args.target / doc_ids[0] / "dense.json").read_text(encoding="utf-8"))
    _write_corpus_manifest(args.target, doc_ids[0], first["items"], first["manifest"])
    isolated = json.loads((args.target / "manifest.json").read_text(encoding="utf-8"))
    if set(isolated["documents"]) != set(doc_ids):
        raise SystemExit("isolated index document set differs from the build report")
    print(json.dumps({"documents": len(doc_ids), "corpus_hash": isolated["corpus_hash"],
                      "index_dir": str(args.target)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
