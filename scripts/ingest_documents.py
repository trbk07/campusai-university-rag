"""CLI for parsing PDFs into JSONL chunks, tables, and figure artifacts."""
import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path
from agentic_rag.ingestion.pdf_parser import parse_pdf, materialize_figures
from agentic_rag.ingestion.table_extractor import save_table
from agentic_rag.ingestion.provenance import sha256_file, validate_artifacts


SCHEMA_VERSION = 2
PIPELINE_VERSION = "task1-ingestion-2026-09"


def _clean_output(path: Path) -> None:
    """Remove generated contents only from the explicitly selected output dir."""
    if not path.exists():
        return
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def _artifact_manifest(path: Path, root: Path) -> dict[str, str | int]:
    return {"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)}

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
    # Never expose a partially written run.  The caller sees the previous
    # complete output until validation and promotion finish successfully.
    args.output_dir.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix=f".{args.output_dir.name}-", dir=args.output_dir.parent))
    chunks_path = temp_dir / "chunks.jsonl"
    manifests = []
    source_hashes = {}
    with chunks_path.open("w", encoding="utf-8") as chunks_file:
        for pdf_path in sorted(args.input_dir.glob("*.pdf")):
            source_hashes[pdf_path.stem] = sha256_file(pdf_path)
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
                save_table(table, temp_dir / "tables")
            materialize_figures(document, temp_dir)
            manifest = document.to_manifest()
            manifest["source_sha256"] = source_hashes[pdf_path.stem]
            manifest["pipeline_version"] = PIPELINE_VERSION
            manifest["schema_version"] = SCHEMA_VERSION
            manifests.append(manifest)
    manifest_path = temp_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifests, indent=2, ensure_ascii=False), encoding="utf-8")
    generated = [chunks_path, manifest_path]
    generated.extend(sorted((temp_dir / "tables").glob("*.csv")) if (temp_dir / "tables").exists() else [])
    generated.extend(sorted((temp_dir / "tables").glob("*.raw.json")) if (temp_dir / "tables").exists() else [])
    generated.extend(sorted((temp_dir / "figures").rglob("*.png")) if (temp_dir / "figures").exists() else [])
    run_manifest = {
        "schema_version": SCHEMA_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "documents": manifests,
        "artifacts": [_artifact_manifest(path, temp_dir) for path in generated if path.exists()],
    }
    (temp_dir / "run_manifest.json").write_text(
        json.dumps(run_manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    artifact_errors = validate_artifacts(temp_dir, run_manifest)
    if artifact_errors:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise SystemExit("artifact validation failed: " + "; ".join(artifact_errors))
    failed = [item for item in manifests if item.get("status") == "failed"]
    if failed:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise SystemExit(f"ingestion failed for {len(failed)} document(s); output was not published")
    if args.output_dir.exists():
        if args.clean_output:
            shutil.rmtree(args.output_dir)
        else:
            shutil.rmtree(args.output_dir)
    os.replace(temp_dir, args.output_dir)


if __name__ == "__main__":
    main()

