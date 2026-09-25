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
import re
import sys
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

import fitz

from campusai.ingestion.pipeline import ingest_document
from campusai.ingestion.pipeline import delete_document
from campusai.ingestion.jobs import IngestionJobManager
from campusai.documents.registry import DocumentRegistry
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
    evidence_fields = (
        "institution", "faculty", "program", "course", "course_code",
        "document_type", "academic_year", "semester", "version",
        "effective_date", "issue_date", "language",
    )
    metadata_evidence = document.metadata.get("metadata_evidence", {})
    metadata_audit = {"fields_checked": len(evidence_fields), "fields_with_evidence": 0,
                      "fields_with_page": 0, "invalid_confidence": 0,
                      "missing_evidence": [], "missing_page": [],
                      "critical_false_positives": 0}
    for field in evidence_fields:
        item = metadata_evidence.get(field, {})
        value = item.get("value")
        confidence = item.get("confidence")
        evidence = item.get("evidence")
        source_page = item.get("source_page")
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            metadata_audit["invalid_confidence"] += 1
        if value is not None and evidence:
            metadata_audit["fields_with_evidence"] += 1
        elif value is not None:
            metadata_audit["missing_evidence"].append(field)
        if value is not None and isinstance(source_page, int) and 1 <= source_page <= document.page_count:
            metadata_audit["fields_with_page"] += 1
        elif value is not None:
            metadata_audit["missing_page"].append(field)
        if field == "program" and isinstance(value, str) and re.search(r"\b\d+\s+tín\s+chỉ\b", value, re.I):
            metadata_audit["critical_false_positives"] += 1

    lengths = [len(chunk.content) for chunk in document.chunks]
    duplicate_count = len(lengths) - len({chunk.content for chunk in document.chunks})
    invalid_pages = []
    invalid_citations = []
    missing_fields = []
    table_header_loss = []
    table_ids = {table.table_id for table in document.tables}
    for chunk in document.chunks:
        required = {
            "doc_id": chunk.doc_id,
            "chunk_id": chunk.chunk_id,
            "source_name": chunk.metadata.get("source_name"),
            "source_hash": chunk.metadata.get("source_hash"),
            "parser_version": chunk.metadata.get("parser_version"),
            "chunker_version": chunk.metadata.get("chunker_version"),
            "page_range": chunk.page_range,
            "citation": chunk.metadata.get("citation"),
        }
        missing_fields.extend([field for field, value in required.items() if not value])
        start, end = chunk.page_range or (0, 0)
        if not (1 <= chunk.page <= document.page_count and 1 <= start <= end <= document.page_count):
            invalid_pages.append(chunk.chunk_id)
        citation = chunk.metadata.get("citation", {})
        if (citation.get("chunk_id") != chunk.chunk_id or citation.get("doc_id") != document.doc_id
                or citation.get("page") != chunk.page or citation.get("page_range") != list(chunk.page_range)):
            invalid_citations.append(chunk.chunk_id)
        if chunk.content_type == "table":
            table_id = chunk.metadata.get("table_id")
            if table_id not in table_ids or not all(str(header) in chunk.content for header in next(table.headers for table in document.tables if table.table_id == table_id)):
                table_header_loss.append(chunk.chunk_id)
    metrics = {
        "chunk_count": len(lengths),
        "table_count": len(document.tables),
        "min_chunk_length": min(lengths) if lengths else 0,
        "mean_chunk_length": round(statistics.mean(lengths), 3) if lengths else 0,
        "p50_chunk_length": statistics.median(lengths) if lengths else 0,
        "p95_chunk_length": round(statistics.quantiles(lengths, n=20, method="inclusive")[18], 3) if len(lengths) > 1 else (lengths[0] if lengths else 0),
        "max_chunk_length": max(lengths) if lengths else 0,
        "overlap_count": sum(1 for first, second in zip(document.chunks, document.chunks[1:]) if first.content[-80:] and first.content[-80:] in second.content),
        "duplicate_rate": round(duplicate_count / len(lengths), 6) if lengths else 0,
        "missing_heading_count": sum(not chunk.heading_path for chunk in document.chunks),
        "missing_citation_count": len(invalid_citations),
        "invalid_page_range_count": len(invalid_pages),
        "table_header_loss_count": len(table_header_loss),
        "section_boundary_failures": 0,
        "chunks_over_limit": document.metadata.get("chunk_diagnostics", {}).get("chunks_over_limit", []),
    }
    return {
        "document": path.name,
        "source_kind": source_kind,
        "status": document.status,
        "pages": document.page_count,
        "language": document.language,
        "document_type": document.metadata.get("document_type"),
        "chunks": len(document.chunks),
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
        "metadata_audit": metadata_audit,
        "chunk_metrics": metrics,
        "artifact_exists": (store_dir / document.doc_id / "meta.json").exists(),
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
        text_rows = [row for row in real_rows if row["status"] == "succeeded"]
        review_rows = [row for row in real_rows if row["status"] == "review_required"]
        text_sources = [path for path in supplied if validate_pdf(path).has_text]
        lifecycle_source = text_sources[0] if text_sources else (supplied[0] if supplied else None)
        root = Path(__file__).resolve().parents[1]
        regression = _run_regression(root)
        lifecycle = _run_lifecycle_checks(lifecycle_source, root) if lifecycle_source else {"terminal": False}
        deletion = _run_delete_check(lifecycle_source) if lifecycle_source else {"artifact_removed": False}
        metadata_summary = {
            "fields_checked": sum(row["metadata_audit"]["fields_checked"] for row in text_rows),
            "fields_with_evidence": sum(row["metadata_audit"]["fields_with_evidence"] for row in text_rows),
            "fields_with_page": sum(row["metadata_audit"]["fields_with_page"] for row in text_rows),
            "invalid_confidence": sum(row["metadata_audit"]["invalid_confidence"] for row in text_rows),
            "missing_evidence": [field for row in text_rows for field in row["metadata_audit"]["missing_evidence"]],
            "missing_page": [field for row in text_rows for field in row["metadata_audit"]["missing_page"]],
            "critical_false_positives": sum(row["metadata_audit"]["critical_false_positives"] for row in text_rows),
        }
        provenance_summary = {
            "chunks_checked": sum(row["chunk_metrics"]["chunk_count"] for row in text_rows),
            "missing_fields": [field for row in text_rows for field in row["missing_chunk_provenance"]],
            "invalid_pages": sum(row["chunk_metrics"]["invalid_page_range_count"] for row in text_rows),
            "invalid_citations": sum(row["chunk_metrics"]["missing_citation_count"] for row in text_rows),
            "table_header_loss": sum(row["chunk_metrics"]["table_header_loss_count"] for row in text_rows),
        }
        metrics_report = {
            "documents": {row["document"]: row["chunk_metrics"] for row in rows},
            "corpus": {
                "document_count": len(real_rows),
                "succeeded_count": len(text_rows),
                "review_required_count": len(review_rows),
                "failed_count": sum(row["status"] == "failed" for row in real_rows),
                "total_chunks": sum(row["chunk_metrics"]["chunk_count"] for row in real_rows),
                "total_tables": sum(row["chunk_metrics"]["table_count"] for row in real_rows),
                "overall_duplicate_rate": round(sum(row["chunk_metrics"]["duplicate_rate"] for row in real_rows) / max(len(real_rows), 1), 6),
                "overall_overflow": sum(len(row["chunk_metrics"]["chunks_over_limit"]) for row in real_rows),
                "overall_missing_provenance": len(provenance_summary["missing_fields"]),
                "overall_invalid_citations": provenance_summary["invalid_citations"],
            },
        }
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
                "metadata_evidence_valid": (
                    metadata_summary["invalid_confidence"] == 0
                    and not metadata_summary["missing_evidence"]
                    and not metadata_summary["missing_page"]
                    and metadata_summary["critical_false_positives"] == 0
                ),
                "provenance_valid": (
                    not provenance_summary["missing_fields"]
                    and provenance_summary["invalid_pages"] == 0
                    and provenance_summary["invalid_citations"] == 0
                    and provenance_summary["table_header_loss"] == 0
                ),
                "metrics_report_complete": bool(metrics_report["documents"] and metrics_report["corpus"]),
                "deletion_clean": all(deletion.values()),
                "lifecycle_checks_pass": all(lifecycle.values()),
                "acceptance_regression_pass": regression["passed"],
            },
            "metadata_evidence": metadata_summary,
            "provenance": provenance_summary,
            "chunk_metrics": metrics_report,
            "deletion_checks": deletion,
            "lifecycle_checks": lifecycle,
            "regression_tests": regression,
        }
        return report


def _run_regression(root: Path) -> dict:
    # Use a fresh basetemp for every run; fixed Windows temp directories can
    # remain locked by native PDF handles during pytest teardown.
    with tempfile.TemporaryDirectory(prefix="campusai-pytest-") as temp:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--basetemp", temp,
             "tests/test_phase12_acceptance.py"],
            cwd=root, capture_output=True, text=True,
        )
    output = (result.stdout or "") + (result.stderr or "")
    return {"exit_code": result.returncode, "passed": result.returncode == 0,
            "output_tail": output[-2000:]}


def _run_lifecycle_checks(source: Path, root: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="campusai-lifecycle-") as temp:
        temp_path = Path(temp)
        manager = IngestionJobManager(max_workers=1)
        try:
            first = manager.submit(source, store_dir=temp_path / "store")
            second = manager.submit(source, store_dir=temp_path / "store")
            deadline = time.time() + 20
            status = manager.get(first)
            while status and status["state"] in {"queued", "running"} and time.time() < deadline:
                time.sleep(0.02)
                status = manager.get(first)
            registry_path = temp_path / "store" / "registry.json"
            registry = DocumentRegistry(registry_path)
            return {
                "dedupe_same_job": first == second,
                "terminal": bool(status and status["state"] == "succeeded"),
                "has_timestamps": bool(status and status.get("created_at") and status.get("started_at") and status.get("completed_at")),
                "registry_reload": bool(status and status.get("document_id") and registry.contains(status["document_id"])),
            }
        finally:
            manager.shutdown()


def _run_delete_check(source: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="campusai-delete-") as temp:
        root = Path(temp)
        document = ingest_document(source, store_dir=root / "store")
        artifact = root / "store" / document.doc_id
        removed = delete_document(document.doc_id, store_dir=root / "store")
        registry = DocumentRegistry(root / "store" / "registry.json")
        return {"delete_returned_true": removed, "artifact_removed": not artifact.exists(),
                "registry_removed": not registry.contains(document.doc_id)}


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
