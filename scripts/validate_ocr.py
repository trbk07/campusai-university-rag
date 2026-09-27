"""Run bounded OCR acceptance evidence without storing recognized text."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from campusai.ingestion.ocr import ocr_pdf


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--max-pages", type=int, default=50)
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--output", type=Path, default=Path("evaluation/ocr_acceptance.json"))
    args = parser.parse_args()
    started = time.perf_counter()
    result = ocr_pdf(
        args.input,
        max_pages=args.max_pages,
        timeout_seconds=args.timeout_seconds,
    )
    non_empty = sum(bool(str(page.get("text", "")).strip()) for page in result.pages)
    report = {
        "schema_version": 1,
        "status": "success" if result.pages and non_empty == len(result.pages) else "failed",
        "source": str(args.input.resolve()),
        "source_sha256": sha256(args.input),
        "engine": result.engine,
        "pages_processed": len(result.pages),
        "pages_with_text": non_empty,
        "average_confidence": result.average_confidence,
        "ocr_seconds": result.elapsed_seconds,
        "acceptance_seconds": round(time.perf_counter() - started, 6),
        "limits": {
            "max_pages": args.max_pages,
            "timeout_seconds": args.timeout_seconds,
        },
        "text_persisted": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    if report["status"] != "success":
        raise SystemExit("OCR acceptance failed")


if __name__ == "__main__":
    main()
