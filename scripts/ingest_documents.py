"""CLI for parsing PDFs into JSONL chunks and CSV tables."""
import argparse
import json
from pathlib import Path
from agentic_rag.ingestion.pdf_parser import parse_pdf
from agentic_rag.ingestion.table_extractor import save_table


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    chunks_path = args.output_dir / "chunks.jsonl"
    manifests = []
    with chunks_path.open("w", encoding="utf-8") as chunks_file:
        for pdf_path in sorted(args.input_dir.glob("*.pdf")):
            document = parse_pdf(pdf_path)
            for chunk in document.chunks:
                chunks_file.write(json.dumps({"text": chunk.text, "metadata": vars(chunk.metadata)}, ensure_ascii=False) + "\n")
            for table in document.tables:
                save_table(table, args.output_dir / "tables")
            manifests.append(document.to_manifest())
    (args.output_dir / "manifest.json").write_text(json.dumps(manifests, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()

