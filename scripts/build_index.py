"""Build per-document BM25 and dense indexes from ingestion stores."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finrag.schemas import Chunk, Document, Table
from finrag.retrieval.index_builder import build_document_indexes


def load_document(meta_path: Path) -> Document:
    data = json.loads(meta_path.read_text(encoding="utf-8"))
    data["chunks"] = [Chunk(**chunk) for chunk in data.get("chunks", [])]
    data["tables"] = [Table(**table) for table in data.get("tables", [])]
    return Document(**data)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store-dir", default="data/store")
    parser.add_argument("--index-dir", default="data/index")
    parser.add_argument("--doc-id", action="append")
    parser.add_argument("--dense-model", default="fallback-hash-256")
    args = parser.parse_args()
    root = Path(args.store_dir)
    selected = set(args.doc_id or [])
    for meta_path in root.glob("*/meta.json"):
        document = load_document(meta_path)
        if selected and document.doc_id not in selected:
            continue
        target = build_document_indexes(document, args.index_dir, args.dense_model)
        print(f"indexed {document.doc_id} -> {target}")


if __name__ == "__main__":
    main()
