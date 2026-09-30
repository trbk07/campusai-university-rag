"""Prepare a reviewable Phase 3 draft; copied labels never count as release gold."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.phase6_schema import validate_dataset


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=Path("data/benchmark"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/benchmark"))
    parser.add_argument("--corpus-manifest", type=Path, default=Path("data/corpus/university/manifest.json"))
    args = parser.parse_args()
    sources = {split: args.source_dir / f"phase6_retrieval_{split}.jsonl" for split in ("dev", "test", "holdout")}
    errors, report = validate_dataset(sources, args.corpus_manifest)
    if errors:
        raise SystemExit(f"source benchmark invalid: {errors}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for split, path in sources.items():
        target = args.output_dir / f"phase3_retrieval_{split}.jsonl"
        if target.exists():
            raise SystemExit(f"will not overwrite existing annotations: {target}")
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        draft = []
        for row in rows:
            row = dict(row)
            row["qid"] = row["qid"].replace("phase6-", "phase3-draft-", 1)
            row["annotation_status"] = "draft_unreviewed"
            row["annotation_version"] = 1
            row["source_annotation"] = f"draft imported from {path.name}; independent reviewer required"
            draft.append(row)
        target.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in draft), encoding="utf-8")
        outputs[split] = {"records": len(draft), "sha256": sha(target), "source_sha256": sha(path)}
    print(json.dumps({"status": "draft_unreviewed", "records": report["records"], "splits": outputs}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
