"""Create Phase 3 corpus provenance from verified source PDFs and its own index."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from campusai.retrieval.bm25_index import BM25Index
from campusai.retrieval.dense_index import DenseIndex


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-dir", type=Path, default=Path("data/corpus/university"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/phase3-clean/phase3-index"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/benchmark"))
    args = parser.parse_args()
    source_manifest = json.loads((args.corpus_dir / "manifest.json").read_text(encoding="utf-8"))
    index_manifest_path = args.index_dir / "manifest.json"
    index = json.loads(index_manifest_path.read_text(encoding="utf-8"))
    entries = []
    seen_hashes = set()
    for source in source_manifest["documents"]:
        path = args.corpus_dir / source["filename"]
        checksum = digest(path)
        if checksum != source["sha256"]:
            raise SystemExit(f"source checksum mismatch: {path}")
        if checksum in seen_hashes:
            raise SystemExit(f"duplicate PDF content: {path}")
        seen_hashes.add(checksum)
        entries.append({"filename": source["filename"], "sha256": checksum,
                        "language": source.get("language"), "document_type": source.get("document_type"),
                        "benchmark_split": source.get("benchmark_split"), "usage_status": source.get("usage_status")})
    indexed_ids = set(index["documents"])
    source_ids = {entry["sha256"] for entry in entries}
    if not indexed_ids <= source_ids:
        raise SystemExit("index includes documents outside the verified Phase 3 corpus")
    indexed = [entry for entry in entries if entry["sha256"] in indexed_ids]
    if len(indexed) < 8:
        raise SystemExit("Phase 3 requires at least 8 indexed documents")
    document_rows = []
    for entry in indexed:
        doc_id = entry["sha256"]
        dense_path = args.index_dir / doc_id / "dense.json"
        bm25_path = args.index_dir / doc_id / "bm25.json"
        dense = DenseIndex.load(dense_path)
        BM25Index.load(bm25_path)
        if dense.manifest["document_id"] != doc_id:
            raise SystemExit(f"index document mismatch: {doc_id}")
        document_rows.append({**entry, "document_id": doc_id,
                              "chunks": len(dense.items), "dense_sha256": digest(dense_path),
                              "bm25_sha256": digest(bm25_path),
                              "chunk_corpus_hash": dense.manifest["corpus_hash"]})
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    manifest = {"schema_version": 1, "phase": 3, "source_manifest_sha256": digest(args.corpus_dir / "manifest.json"),
                "index_manifest_sha256": digest(index_manifest_path), "documents": len(indexed),
                "source_documents": len(entries), "chunks": sum(row["chunks"] for row in document_rows),
                "languages": sorted({str(row["language"]) for row in indexed}),
                "model": index["model_name"], "model_revision": index["model_revision"],
                "source_hashes": {row["filename"]: row["sha256"] for row in entries},
                "created_from_commit": commit,
                "corpus_hash": hashlib.sha256(json.dumps(document_rows, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "phase3_documents_manifest.json").write_text(json.dumps(document_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "phase3_corpus_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "phase3_corpus.sha256").write_text(manifest["corpus_hash"] + "\n", encoding="utf-8")
    print(json.dumps({"documents": manifest["documents"], "chunks": manifest["chunks"], "corpus_hash": manifest["corpus_hash"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
