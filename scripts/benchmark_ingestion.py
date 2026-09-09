"""Run a resumable, metrics-only ingestion benchmark over PDFs.

The report is checkpointed after every file and never contains extracted text.
"""
import argparse
import json
import os
import re
import time
from pathlib import Path
from agentic_rag.ingestion.pdf_parser import parse_pdf


def classify_warnings(warnings: list[str]) -> dict[str, int]:
    groups = {"ocr": 0, "table": 0, "pdf": 0, "numeric": 0, "other": 0}
    for warning in warnings:
        lower = warning.casefold()
        if "ocr" in lower:
            groups["ocr"] += 1
        elif "table" in lower or "header" in lower:
            groups["table"] += 1
        elif "pdf" in lower or "encrypted" in lower:
            groups["pdf"] += 1
        elif "numeric" in lower or "unparsed" in lower:
            groups["numeric"] += 1
        else:
            groups["other"] += 1
    return groups


def _summary(documents: list[dict], elapsed: float, expected: int) -> dict:
    return {"files": expected, "processed": len(documents),
            "ok": sum(x["status"] == "ok" for x in documents),
            "failed": sum(x["status"] == "failed" for x in documents),
            "pages": sum(x["pages"] for x in documents),
            "chunks": sum(x["chunks"] for x in documents),
            "tables": sum(x["tables"] for x in documents),
            "warnings": sum(x["warnings"] for x in documents),
            "warning_categories": {key: sum(x["warning_categories"].get(key, 0) for x in documents)
                                   for key in ("ocr", "table", "pdf", "numeric", "other")},
            "coverage": round(len(documents) / expected, 3) if expected else 1.0,
            "complete": len(documents) == expected,
            "runtime_seconds": round(elapsed, 3)}


def _write_report(path: Path, documents: list[dict], started: float, expected: int) -> None:
    report = {"schema_version": 1, "documents": documents,
              "summary": _summary(documents, time.perf_counter() - started, expected)}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ocr", action="store_true")
    parser.add_argument("--resume", action="store_true", help="reuse completed files in an existing report")
    args = parser.parse_args()
    paths = sorted(args.input_dir.glob("*.pdf"))
    documents: list[dict] = []
    if args.resume and args.output.exists():
        try:
            old = json.loads(args.output.read_text(encoding="utf-8"))
            documents = [item for item in old.get("documents", [])
                         if item.get("file") in {path.name for path in paths}]
        except (OSError, json.JSONDecodeError):
            documents = []
    done = {item["file"] for item in documents}
    started = time.perf_counter()
    _write_report(args.output, documents, started, len(paths))
    for path in paths:
        if path.name in done:
            continue
        item = {"file": path.name, "bytes": path.stat().st_size}
        begin = time.perf_counter()
        try:
            parsed = parse_pdf(path, use_ocr=args.ocr)
            categories = classify_warnings(parsed.warnings)
            item.update({"status": "ok", "pages": parsed.pages,
                         "chunks": len(parsed.chunks), "tables": len(parsed.tables),
                         "warnings": len(parsed.warnings), "warning_categories": categories,
                         "ocr_pages": len(parsed.ocr_diagnostics),
                         "runtime_seconds": round(time.perf_counter() - begin, 3)})
        except Exception as exc:
            item.update({"status": "failed", "pages": 0, "chunks": 0, "tables": 0,
                         "warnings": 1, "warning_categories": {"ocr": 0, "table": 0, "pdf": 0, "numeric": 0, "other": 1},
                         "ocr_pages": 0, "error_type": type(exc).__name__,
                         "error_message": re.sub(r"\s+", " ", str(exc))[:300],
                         "runtime_seconds": round(time.perf_counter() - begin, 3)})
        documents.append(item)
        _write_report(args.output, documents, started, len(paths))
    print(json.dumps(_summary(documents, time.perf_counter() - started, len(paths))))


if __name__ == "__main__":
    main()
