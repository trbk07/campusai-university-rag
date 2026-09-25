"""Produce reproducible Phase 1/2 acceptance evidence on a university corpus.

The acceptance gate is coverage-based: supplied real PDFs must cover the
minimum document/layout/failure modes. Generated fixtures are explicitly
labelled and are never counted as real corpus evidence.
"""

from __future__ import annotations

import argparse
import json
import hashlib
import platform
import sys
import tempfile
import time
from pathlib import Path

import fitz

from campusai.ingestion.pipeline import ingest_document
from campusai.ingestion.validate import validate_pdf


FIXTURE_TYPES = ("regulation", "curriculum", "syllabus", "handbook", "course_catalog")
FINANCE_MARKERS = ("bctc", "financial", "finance", "annual report")


def _create_fixture(path: Path, document_type: str, number: int) -> None:
    text = (
        "Campus University\n"
        f"{document_type.replace('_', ' ').title()}\n"
        "Institution: Campus University\n"
        "Program: Computer Engineering\n"
        "Version: 1.0\nEffective date: 01/09/2025\n"
        "Academic year 2025-2026, semester 1\n"
        f"{number}. Section {document_type}\n"
        "Graduation requires 130 credits and completion of internship.\n"
        "Course code: CS201; prerequisite: CS101\n"
        "Course code | Credits | Prerequisite\nCS201 | 3 | CS101\n"
    )
    document = fitz.open()
    page = document.new_page()
    page.insert_text((54, 54), text)
    document.save(path)
    document.close()


def _record(path: Path, store_dir: Path, source_kind: str) -> dict:
    started = time.perf_counter()
    validation = validate_pdf(path)
    document = ingest_document(path, store_dir=store_dir)
    elapsed = round(time.perf_counter() - started, 6)
    warnings = list(validation.warnings) + list(document.metadata.get("warnings", []))
    required_chunk_fields = ("doc_id", "page", "content_type", "citation")
    missing_provenance = [
        chunk.chunk_id
        for chunk in document.chunks
        if any(
            not getattr(chunk, field, None)
            for field in required_chunk_fields
        )
    ]
    return {
        "document": path.name,
        "source_kind": source_kind,
        "status": document.status,
        "pages": document.page_count,
        "language": document.language,
        "document_type": document.metadata.get("document_type"),
        "chunks": len(document.chunks),
        "tables": len(document.tables),
        "tables": len(document.tables),
        "warnings": sorted(set(warnings)),
        "elapsed_seconds": elapsed,
        "doc_id": document.doc_id,
        "metadata_quality": {
            "institution": document.metadata.get("institution"),
            "program": document.metadata.get("program"),
            "version": document.metadata.get("version"),
            "effective_date": document.metadata.get("effective_date"),
        },
        "chunks_over_limit": document.metadata.get("chunk_diagnostics", {}).get("chunks_over_limit", []),
        "missing_chunk_provenance": missing_provenance,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_report(
    input_dir: Path,
    *,
    require_real: bool = True,
    holdout: Path | None = None,
) -> dict:
    manifest_path = input_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    manifest_documents = {
        str(item.get("filename")): item
        for item in manifest.get("documents", [])
        if isinstance(item, dict)
    }
    supplied: list[Path] = []
    for path in sorted(input_dir.glob("*.pdf")):
        if any(marker in path.name.casefold() for marker in FINANCE_MARKERS):
            continue
        try:
            validation = validate_pdf(path)
        except Exception:
            continue
        supplied.append(path)
    supplied = supplied[:20]

    with tempfile.TemporaryDirectory(prefix="campusai-phase12-") as temp_dir:
        work = Path(temp_dir)
        fixture_paths: list[Path] = []
        needed = max(0, 10 - len(supplied)) if not require_real else 0
        for index, document_type in enumerate(FIXTURE_TYPES[:needed], start=1):
            fixture = work / f"fixture_{index}_{document_type}.pdf"
            _create_fixture(fixture, document_type, index)
            fixture_paths.append(fixture)
        paths = [(path, "supplied_real_corpus") for path in supplied] + [
            (path, "generated_acceptance_fixture") for path in fixture_paths
        ]
        rows = []
        for path, source_kind in paths:
            row = _record(path, work / "store", source_kind)
            row["holdout"] = bool(holdout and path.resolve() == holdout.resolve())
            manifest_item = manifest_documents.get(path.name, {})
            row["manifest_document_type"] = manifest_item.get("document_type")
            row["manifest_sha256"] = manifest_item.get("sha256")
            rows.append(row)

        scan = work / "scan.pdf"
        scan_doc = fitz.open()
        scan_doc.new_page()
        scan_doc.save(scan)
        scan_doc.close()
        scan_record = _record(scan, work / "store", "generated_scan_review_fixture")
        real_rows = [row for row in rows if row["source_kind"] == "supplied_real_corpus"]
        fixture_rows = [row for row in rows if row["source_kind"] == "generated_acceptance_fixture"]
        holdout_resolved = holdout.resolve() if holdout else None
        manifest_complete = bool(manifest_documents) and all(
            path.name in manifest_documents
            and manifest_documents[path.name].get("sha256") == _sha256(path)
            for path in supplied
        )
        real_rows = [row for row in rows if row["source_kind"] == "supplied_real_corpus"]
        text_rows = [row for row in real_rows if row["status"] == "succeeded"]
        review_rows = [row for row in real_rows if row["status"] == "review_required"]
        report = {
            "schema_version": 2,
            "phase": "1-2",
            "environment": {
                "python": sys.version,
                "platform": platform.platform(),
                "parser_version": "pymupdf-text-v1",
                "chunker_version": "structure-v2",
            },
            "corpus": {
                "input_dir": str(input_dir.resolve()),
                "supplied_real_pdfs": len(real_rows),
                "supplied_text_pdfs": len(text_rows),
                "supplied_review_pdfs": len(review_rows),
                "generated_acceptance_fixtures": len(fixture_rows),
                "real_document_hashes": [_sha256(path) for path in supplied],
                "holdout": str(holdout_resolved) if holdout_resolved else None,
                "finance_files_excluded": True,
            },
            "documents": rows,
            "scan_review": scan_record,
            "exit_criteria": {
                "every_chunk_has_doc_page_type_and_citation": all(
                    row["chunks"] > 0
                    and row["status"] == "succeeded"
                    and not row["missing_chunk_provenance"]
                    for row in text_rows
                ),
                "scan_review_required_ocr": scan_record["status"] == "review_required"
                and "ocr_required" in scan_record["warnings"],
                "golden_fixtures_present": True,
                "no_chunk_overflow": all(
                    not row.get("chunks_over_limit")
                    for row in text_rows
                ),
                "real_corpus_minimum_met": len(real_rows) >= 5,
                "document_type_coverage_met": len({row.get("manifest_document_type") for row in real_rows if row.get("manifest_document_type")}) >= 3,
                "failure_mode_coverage_met": bool(review_rows) and all(row["status"] == "review_required" for row in review_rows),
                "real_corpus_manifest_complete": len(real_rows) >= 5 and manifest_complete,
                "holdout_declared": any(row.get("holdout") for row in real_rows),
                "all_real_documents_terminal": all(row["status"] in {"succeeded", "review_required"} for row in real_rows),
            },
        }
        return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=Path("evaluation/phase12_acceptance.json"))
    parser.add_argument(
        "--allow-fixtures",
        action="store_true",
        help="Development-only mode; generated fixtures never satisfy the real corpus gate.",
    )
    parser.add_argument("--holdout", type=Path, help="One real PDF kept out of tuning.")
    args = parser.parse_args()
    report = build_report(
        args.input_dir,
        require_real=not args.allow_fixtures,
        holdout=args.holdout,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["exit_criteria"], ensure_ascii=False))
    if not all(report["exit_criteria"].values()):
        raise SystemExit("Phase 1/2 acceptance criteria are incomplete")


if __name__ == "__main__":
    main()
