"""CLI for parsing PDFs into JSONL chunks and CSV tables."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
from agentic_rag.ingestion.pdf_parser import parse_pdf
from agentic_rag.ingestion.table_extractor import save_table


SCHEMA_VERSION = 2
PIPELINE_VERSION = "task1-ingestion-2026-09"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _clean_output(path: Path) -> None:
    """Remove generated contents only from the explicitly selected output dir."""
    if not path.exists():
        return
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def _artifact_manifest(path: Path) -> dict[str, str | int]:
    return {"path": path.name, "bytes": path.stat().st_size, "sha256": _sha256(path)}

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--ocr", action="store_true", help="OCR pages without a text layer")
    parser.add_argument("--ocr-language", default="eng")
    parser.add_argument("--ocr-dpi", type=int, default=200)
    parser.add_argument("--tesseract-cmd", default=None)
    parser.add_argument("--ocr-confidence", action="store_true",
                        help="Record Tesseract word confidence and bounding boxes")
    parser.add_argument("--clean-output", action="store_true",
                        help="Delete existing contents of this output directory before ingestion")
    args = parser.parse_args()
    if args.clean_output:
        _clean_output(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    chunks_path = args.output_dir / "chunks.jsonl"
    manifests = []
    source_hashes = {}
    with chunks_path.open("w", encoding="utf-8") as chunks_file:
        for pdf_path in sorted(args.input_dir.glob("*.pdf")):
            source_hashes[pdf_path.stem] = _sha256(pdf_path)
            try:
                document = parse_pdf(pdf_path, use_ocr=args.ocr, ocr_language=args.ocr_language,
                                     ocr_dpi=args.ocr_dpi, tesseract_cmd=args.tesseract_cmd,
                                     collect_ocr_confidence=args.ocr_confidence)
            except Exception as exc:
                from agentic_rag.ingestion.metadata import ParsedDocument
                document = ParsedDocument(doc_id=pdf_path.stem, source=str(pdf_path),
                                          warnings=[f"document failed: {type(exc).__name__}: {exc}"])
            for chunk in document.chunks:
                chunks_file.write(json.dumps({"text": chunk.text, "metadata": vars(chunk.metadata)}, ensure_ascii=False) + "\n")
            for table in document.tables:
                save_table(table, args.output_dir / "tables")
            manifest = document.to_manifest()
            manifest["source_sha256"] = source_hashes[pdf_path.stem]
            manifest["pipeline_version"] = PIPELINE_VERSION
            manifest["schema_version"] = SCHEMA_VERSION
            manifests.append(manifest)
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifests, indent=2, ensure_ascii=False), encoding="utf-8")
    generated = [chunks_path, manifest_path]
    generated.extend(sorted((args.output_dir / "tables").glob("*.csv")) if (args.output_dir / "tables").exists() else [])
    run_manifest = {
        "schema_version": SCHEMA_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "documents": manifests,
        "artifacts": [_artifact_manifest(path) for path in generated if path.exists()],
    }
    (args.output_dir / "run_manifest.json").write_text(
        json.dumps(run_manifest, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()

