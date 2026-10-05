"""Build isolated physical-source evidence; never a release model measurement."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from campusai.documents.registry import DocumentRegistry
from campusai.ingestion.chunker import make_chunks
from campusai.ingestion.docling_parser import parse_pdf
from campusai.ingestion.pipeline import ingest_document
from campusai.retrieval.index_builder import build_document_indexes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--store-dir", type=Path, required=True)
    parser.add_argument("--index-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.store_dir.exists() or args.index_dir.exists():
        parser.error("refusing to overwrite source evidence")
    source = json.loads((Path(__file__).parent / "source_manifest.json").read_text(encoding="utf-8"))
    doc = ingest_document(args.pdf.resolve(), args.store_dir)
    # Course-code digits are not academic years. Metadata comes from the
    # official page title and narrative, with its applicability kept explicit.
    doc.metadata = {
        "document_type": "curriculum", "language": "vi",
        "institution": "University of Engineering and Technology, Vietnam National University Hanoi",
        "program": "Robotics Engineering", "version": "QH-2025",
        "curriculum_applicability": "cohorts QH-2025 onward",
        "source_url": source["source_url"],
        "source_html_sha256": source["artifacts"]["html"]["sha256"],
        "source_pdf_sha256": doc.doc_id,
    }
    doc.language = "vi"
    diagnostics = {}
    doc.chunks = make_chunks(parse_pdf(args.pdf), doc.doc_id, doc.metadata, doc.tables,
                             diagnostics=diagnostics)
    doc.metadata["chunk_diagnostics"] = diagnostics
    (args.store_dir / doc.doc_id / "meta.json").write_text(
        json.dumps(doc.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    DocumentRegistry(args.store_dir / "registry.json").add(doc)
    build_document_indexes(doc, args.index_dir, dense_model="fallback-hash-256")
    print(json.dumps({"doc_id": doc.doc_id, "chunks": len(doc.chunks),
                      "source_index": str(args.index_dir), "release_eligible": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
