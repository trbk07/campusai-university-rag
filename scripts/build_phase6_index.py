"""Build the pinned Phase 6 corpus index from verified real PDFs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from campusai.ingestion.pipeline import ingest_document
from campusai.retrieval.dense_index import HASH_MODEL
from campusai.retrieval.index_builder import build_document_indexes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-dir", type=Path, default=Path("data/corpus/university"))
    parser.add_argument("--store-dir", type=Path, default=Path(".tmp/phase6-store"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/phase6-index"))
    parser.add_argument("--model", default="BAAI/bge-m3")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--allow-hash", action="store_true")
    args = parser.parse_args()
    if args.model == HASH_MODEL and not args.allow_hash:
        raise SystemExit("fallback hash embeddings are forbidden for Phase 6 release evidence")
    manifest = json.loads((args.corpus_dir / "manifest.json").read_text(encoding="utf-8"))
    indexed = []
    scan_only = []
    for entry in manifest["documents"]:
        source = args.corpus_dir / entry["filename"]
        if hashlib.sha256(source.read_bytes()).hexdigest() != entry["sha256"]:
            raise SystemExit(f"corpus checksum mismatch: {entry['filename']}")
        document = ingest_document(source, store_dir=args.store_dir, enable_ocr=False)
        year_match = re.search(r"20\d{2}", entry["filename"])
        document.metadata.update({
            "institution": manifest.get("institution"),
            "document_type": entry.get("document_type"),
            "language": entry.get("language"),
            "academic_year": year_match.group(0) if year_match else "unknown",
            "source_sha256": entry["sha256"],
        })
        for chunk in document.chunks:
            chunk.metadata.update(document.metadata)
        if not document.chunks:
            scan_only.append({"doc_id": document.doc_id, "source_name": entry["filename"],
                              "status": document.status, "reason": document.review_reason})
            continue
        build_document_indexes(document, args.index_dir, dense_model=args.model,
                               device=args.device, batch_size=args.batch_size)
        indexed.append(document.doc_id)
    report = {
        "status": "pass" if len(indexed) + len(scan_only) >= 8 and len(indexed) >= 5 else "fail",
        "corpus_documents": len(manifest["documents"]), "indexed_documents": len(indexed),
        "scan_only_documents": scan_only, "model": args.model, "device": args.device,
        "index_dir": str(args.index_dir), "indexed_doc_ids": indexed,
    }
    target = args.index_dir / "phase6_build_report.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
