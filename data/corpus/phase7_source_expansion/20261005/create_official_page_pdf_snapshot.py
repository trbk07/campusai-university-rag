"""Create a paginated, text-preserving PDF snapshot from a saved official HTML page.

The untouched HTML remains the authoritative byte-level source. The PDF is a
derived local rendering used to create page-grounded chunks for this corpus.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import re

import pymupdf as fitz
from bs4 import BeautifulSoup, NavigableString


FONT = Path(r"C:\Windows\Fonts\arial.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\arialbd.ttf")


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def source_text(html_path: Path) -> tuple[str, list[tuple[str, str, list[str] | None]]]:
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8", errors="replace"), "html.parser")
    article = soup.find("article")
    if article is None:
        raise ValueError("official article element missing from captured HTML")
    title = (article.find("h1") or soup.title)
    title_text = title.get_text(" ", strip=True) if title else ""
    content = article.select_one(".td-post-content") or article
    for table_number, table in enumerate(content.find_all("table"), start=1):
        rows: list[list[str]] = []
        for tr in table.find_all("tr"):
            cells = [" ".join(cell.stripped_strings) for cell in tr.find_all(["th", "td"], recursive=False)]
            if cells:
                rows.append(cells)
        if table_number == 2 and rows:
            # Expand the official two-row header into explicit column roles.
            # The source HTML remains authoritative; this makes the derived
            # PDF table machine-readable without changing any course cells.
            headers = ["STT", "Mã học phần", "Học phần", "Số tín chỉ", "Mã học phần tiên quyết"]
            formatted = [("HEADER", " | ".join(headers))]
            formatted.append(("TROW", "Số giờ học tập: Lý thuyết; Thực hành; Bài tập; Tự học"))
            for cells in rows[2:]:
                if cells[0].strip().isdigit() and len(cells) >= 9 and cells[1].strip():
                    formatted.append(("ROW", " | ".join([cells[0], cells[1], cells[2], cells[3], cells[8]])))
                    workload = (f"Workload {cells[1]}: Lý thuyết {cells[4]}; Thực hành {cells[5]}; "
                                f"Bài tập {cells[6]}; Tự học {cells[7]}")
                    formatted.append(("TROW", workload))
                else:
                    # Preserve section labels, totals and notes as non-course rows.
                    formatted.append(("TROW", " | ".join(cell for cell in cells if cell)))
        else:
            formatted = [("HEADER" if index == 0 else "ROW", " | ".join(cells))
                         for index, cells in enumerate(rows)]
        marker = "\n".join(f"__P7_{kind}__{value}" for kind, value in formatted)
        table.replace_with(NavigableString("\n" + marker + "\n"))
    for node in content.select("script,style,iframe,form,nav,button,svg"):
        node.decompose()
    text = content.get_text("\n", strip=True)
    lines: list[tuple[str, str, list[str] | None]] = []
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if not line:
            continue
        marker = re.match(r"^__P7_(HEADER|ROW|TROW|TEXT)__(.*)$", line)
        if marker:
            kind, value = marker.groups()
            headers = value.split(" | ") if kind == "HEADER" else None
            lines.append((kind, value, headers))
        else:
            lines.append(("TEXT", line, None))
    return title_text, lines


def wrap_line(text: str, font: fitz.Font, size: float, width: float) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    result, line = [], ""
    for word in words:
        trial = f"{line} {word}" if line else word
        if line and font.text_length(trial, fontsize=size) > width:
            result.append(line)
            line = word
        else:
            line = trial
    if line:
        result.append(line)
    return result


def create_snapshot(html_path: Path, output_path: Path, source_url: str) -> dict:
    if not html_path.is_file() or not FONT.is_file() or not FONT_BOLD.is_file():
        raise FileNotFoundError("captured HTML or Arial font files missing")
    title, body = source_text(html_path)
    source_hash = digest(html_path)
    portrait = fitz.paper_rect("a4")
    page_size = fitz.Rect(0, 0, portrait.height, portrait.width)
    margin_x, top, bottom = 42, 48, 44
    content_width = page_size.width - 2 * margin_x
    font = fitz.Font(fontfile=str(FONT))
    bold = fitz.Font(fontfile=str(FONT_BOLD))
    doc = fitz.open()
    page = doc.new_page(width=page_size.width, height=page_size.height)
    page_no = 1

    def new_page():
        nonlocal page, page_no, y
        page.insert_text((margin_x, page_size.height - 24), f"Source snapshot page {page_no}",
                         fontname="arial", fontfile=str(FONT), fontsize=7, color=(0.35, 0.35, 0.35))
        page_no += 1
        page = doc.new_page(width=page_size.width, height=page_size.height)
        y = top

    page.insert_font(fontname="arial", fontfile=str(FONT))
    page.insert_font(fontname="arial-bold", fontfile=str(FONT_BOLD))
    y = top
    page.insert_text((margin_x, y), "OFFICIAL WEBPAGE TEXT SNAPSHOT", fontname="arial-bold", fontsize=15)
    y += 24
    note = "Derived from the saved official HTML response. The HTML file is preserved separately as the source bytes."
    for line in wrap_line(note, font, 9, content_width):
        page.insert_text((margin_x, y), line, fontname="arial", fontsize=9)
        y += 13
    y += 4
    for label, value in [("Source URL", source_url), ("Snapshot generated UTC", datetime.now(timezone.utc).isoformat()),
                         ("Source HTML SHA-256", source_hash)]:
        for line in wrap_line(f"{label}: {value}", font, 8, content_width):
            page.insert_text((margin_x, y), line, fontname="arial", fontsize=8)
            y += 12
    y += 10
    for line in wrap_line(title, bold, 13, content_width):
        page.insert_text((margin_x, y), line, fontname="arial-bold", fontsize=13)
        y += 17
    y += 8

    heading = re.compile(r"^(?:[IVX]+\.|\d+(?:\.\d+)*\.?\s|[A-Z](?:\.|\s)|[A-Z]\. |[â€“-]\s|MÃ£ PLO\s*\|)")
    table_headers: dict[int, str] = {}
    active_table: int | None = None
    table_counter = 0
    for kind, raw, header_cells in body:
        if kind == "HEADER":
            table_counter += 1
            active_table = table_counter
            table_headers[active_table] = raw
        elif kind in {"ROW", "TROW"} and active_table is None:
            active_table = 0
        is_table = kind in {"HEADER", "ROW", "TROW"}
        is_heading = kind == "HEADER" or (kind == "TEXT" and bool(heading.match(raw)) and len(raw) < 140)
        size = 8.2 if is_table else (10 if is_heading else 8.5)
        active_font = bold if is_heading else font
        rendered_raw = raw
        if active_table == 2 and kind == "HEADER":
            rendered_raw = f"{raw} | Source page {page_no}"
        elif active_table == 2 and kind == "ROW":
            rendered_raw = f"{raw} | {page_no}"
        lines = wrap_line(rendered_raw, active_font, size, content_width)
        line_height = size * 1.45
        if y + line_height * len(lines) > page_size.height - bottom:
            new_page()
            page.insert_font(fontname="arial", fontfile=str(FONT))
            page.insert_font(fontname="arial-bold", fontfile=str(FONT_BOLD))
            if is_table and kind in {"ROW", "TROW"} and active_table in table_headers:
                repeated_header = table_headers[active_table]
                if active_table == 2:
                    repeated_header = f"{repeated_header} | Source page {page_no}"
                repeated = wrap_line(repeated_header, bold, 8.2, content_width)
                for header_line in repeated:
                    page.insert_text((margin_x, y), header_line, fontname="arial-bold",
                                     fontsize=8.2, color=(0.08, 0.08, 0.08))
                    y += 8.2 * 1.45
                y += 2
            # The row may have moved after its page annotation was calculated.
            if active_table == 2 and kind == "ROW":
                lines = wrap_line(f"{raw} | {page_no}", active_font, size, content_width)
            elif active_table == 2 and kind == "HEADER":
                lines = wrap_line(f"{raw} | Source page {page_no}", active_font, size, content_width)
        for line in lines:
            page.insert_text((margin_x, y), line, fontname="arial-bold" if is_heading else "arial",
                             fontsize=size, color=(0.08, 0.08, 0.08))
            y += line_height
        y += 2 if is_heading else 0.5
        if kind == "TEXT":
            active_table = None

    page.insert_text((margin_x, page_size.height - 24), f"Source snapshot page {page_no}",
                     fontname="arial", fontsize=7, color=(0.35, 0.35, 0.35))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.set_metadata({"title": title, "author": "UET official webpage snapshot", "subject": source_url,
                      "keywords": "UET, Robotics Engineering, QH-2025, source snapshot"})
    doc.save(output_path, deflate=True, garbage=4)
    page_count = len(doc)
    doc.close()
    source = BeautifulSoup(html_path.read_text(encoding="utf-8", errors="replace"), "html.parser")
    article = source.find("article")
    tables = article.select(".td-post-content table") if article else []
    course_rows = []
    expected_cells = []
    for table in tables:
        rows = []
        for tr in table.find_all("tr"):
            cells = [" ".join(cell.stripped_strings) for cell in tr.find_all(["th", "td"], recursive=False)]
            if cells:
                rows.append(cells)
                expected_cells.extend(cell for cell in cells if cell)
        if table is tables[-1]:
            course_rows = rows
    with fitz.open(output_path) as rendered:
        extracted = " ".join(page.get_text() for page in rendered)
    normalize = lambda value: re.sub(
        r"\s+", " ", value.replace("\u00ad", "-").replace("\u037e", ";")
    ).strip().casefold()
    searchable = normalize(extracted)
    missing_cells = [cell for cell in expected_cells if normalize(cell) not in searchable]
    if missing_cells:
        raise ValueError(f"PDF text validation failed for {len(missing_cells)} source table cells")
    return {"title": title, "source_html_sha256": source_hash, "pdf_sha256": digest(output_path),
            "pdf_bytes": output_path.stat().st_size, "pages": page_count,
            "html_table_count": len(tables), "course_table_rows_including_header": len(course_rows),
            "numbered_course_rows": sum(bool(row and row[0].strip().isdigit()) for row in course_rows),
            "table_cell_text_validation": "PASS"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--source-url", required=True)
    args = parser.parse_args(argv)
    if args.pdf.exists():
        parser.error("refusing to overwrite existing source snapshot")
    result = create_snapshot(args.html, args.pdf, args.source_url)
    print(ascii(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

