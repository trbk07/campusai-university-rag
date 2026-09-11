"""Create ten deterministic PDF ingestion fixtures and their annotation manifest."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pymupdf

CASES = [
    ("native_text", "native text extraction", "text"),
    ("vietnamese", "Báo cáo doanh thu và lợi nhuận", "text"),
    ("two_column", "LEFT COLUMN\nLEFT DETAIL\nRIGHT COLUMN\nRIGHT DETAIL", "text"),
    ("text_image", "Text surrounding an embedded image", "figure"),
    ("simple_table", "Year | Revenue\n2024 | 100\n2025 | 120", "table"),
    ("merged_table", "Result | 2024 | 2025\nRevenue | 100 | 120", "table"),
    ("multipage_table", "Year | Revenue\n2024 | 100", "table"),
    ("chart", "Revenue chart (image artifact)", "chart"),
    ("scanned_like", "OCR review fixture", "ocr"),
    ("mixed_layout", "Heading\nText and table-like evidence", "mixed"),
]


def make_case(path: Path, text: str, kind: str) -> None:
    document = pymupdf.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((60, 80), text, fontsize=14)
    if kind in {"figure", "chart"}:
        pix = pymupdf.Pixmap(pymupdf.csRGB, (0, 0, 80, 50), 0)
        pix.clear_with(0x336699)
        page.insert_image(pymupdf.Rect(350, 100, 530, 220), pixmap=pix)
    document.save(path)
    document.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("data/fixtures/pdf"))
    parser.add_argument("--annotations", type=Path, default=Path("data/fixtures/pdf-ground-truth.json"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cases = []
    for case_id, text, kind in CASES:
        make_case(args.output_dir / f"{case_id}.pdf", text, kind)
        cases.append({"id": case_id, "file": f"{case_id}.pdf", "expected": {
            "pages": 1, "content_types": [kind], "bbox_required": True,
            "text_contains": text.split("\n")[0]}})
    args.annotations.parent.mkdir(parents=True, exist_ok=True)
    args.annotations.write_text(json.dumps({"schema_version": 1, "cases": cases}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"cases": len(cases), "output": str(args.output_dir)}))


if __name__ == "__main__":
    main()
