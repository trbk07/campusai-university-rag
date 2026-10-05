"""Verify every structured course fact against the saved official HTML source."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence
from evaluation.benchmarks.source_course_rows import source_course_rows


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(value: str) -> str:
    value = value.replace("\u00ad", "-").replace("\u00a0", " ")
    return " ".join(unicodedata.normalize("NFKC", value).split()).casefold()


def audit(html_path: Path, index_dir: Path, pdf_path: Path | None = None) -> dict:
    html_bytes_hash = digest(html_path)
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8", errors="replace"), "html.parser")
    article = soup.find("article")
    tables = article.select(".td-post-content table") if article else []
    if len(tables) < 2:
        raise ValueError("official course table is absent")
    expected = []
    code_pattern = re.compile(r"(?:[A-Z]{2,5}\.)?[A-Z]{2,5}\d{3,5}[A-Z]?\Z")
    for number, tr in enumerate(tables[-1].select("tr")[2:], start=2):
        cells = [" ".join(cell.stripped_strings) for cell in tr.find_all(["th", "td"], recursive=False)]
        if len(cells) < 9 or not code_pattern.fullmatch(re.sub(r"\s+", "", cells[1])):
            continue
        if not cells[3].strip().isdigit() or not 0 < int(cells[3]) < 30:
            continue
        prerequisite_text = cells[8].strip()
        codes = [candidate.strip() for candidate in re.split(r"[,;]", prerequisite_text)
                 if code_pattern.fullmatch(candidate.strip())]
        expected.append({"source_table_row": number, "code": re.sub(r"\s+", "", cells[1]),
                         "name": cells[2], "credits": int(cells[3]),
                         "prerequisite_codes": codes or None})

    evidence = frozen_evidence(index_dir)
    facts = source_course_rows(evidence)
    expected_by_code = {item["code"]: item for item in expected}
    actual_by_code = {item["code"]: item for item in facts}
    mismatches = []
    for code in sorted(set(expected_by_code) | set(actual_by_code)):
        exp, got = expected_by_code.get(code), actual_by_code.get(code)
        if exp is None or got is None:
            mismatches.append({"code": code, "missing_from": "source_index" if got is None else "official_html"})
            continue
        same = (normalize(exp["name"]) == normalize(got["name"])
                and exp["credits"] == got["credits"]
                and exp["prerequisite_codes"] == got["prerequisite_codes"]
                and re.sub(r"\s+", "", ",".join(exp["prerequisite_codes"] or []))
                    == re.sub(r"\s+", "", got["prerequisite_text"].replace(";", ",")))
        if not same:
            mismatches.append({"code": code, "html": exp, "indexed": got})

    index_manifest = index_dir / "manifest.json"
    manifest = json.loads(index_manifest.read_text(encoding="utf-8"))
    if pdf_path is None:
        pdf_path = ROOT / "data/corpus/phase7_source_expansion/20261005/uet_robotics_curriculum_qh2025_snapshot-v2.pdf"
    pdf_hash = digest(pdf_path)
    if manifest["documents"] != [pdf_hash]:
        mismatches.append({"reason": "physical_pdf_hash_does_not_match_index_document_id"})
    import pymupdf as fitz
    page_annotation_errors = []
    with fitz.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf, 1):
            for line in page.get_text().splitlines():
                cells = [cell.strip() for cell in line.split("|")]
                if len(cells) == 6 and cells[0].isdigit() and code_pattern.fullmatch(cells[1]):
                    if cells[-1] != str(page_number):
                        page_annotation_errors.append({"code": cells[1], "page": page_number,
                                                       "annotation": cells[-1]})
    mismatches.extend(page_annotation_errors)
    physical = {"path": pdf_path.resolve().relative_to(ROOT).as_posix(),
                "sha256": manifest["documents"][0] if len(manifest["documents"]) == 1 else None,
                "document_count": len(manifest["documents"])}
    return {
        "schema_version": 1,
        "task": "P7-03-QH2025-source-binding",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if not mismatches and len(expected) == len(facts) else "FAIL",
        "release_eligible": False,
        "scope": "physical source binding only; this does not decide exposure or split eligibility",
        "official_html_sha256": html_bytes_hash,
        "source_index_manifest_sha256": digest(index_manifest),
        "source_index_model": manifest.get("model_name"),
        "source_index_role": "source-evidence extraction only; excluded from release model measurements",
        "source_document": physical,
        "pdf_page_annotations_valid": not page_annotation_errors,
        "html_tables": len(tables),
        "html_numbered_course_rows_with_code_and_credit": len(expected),
        "indexed_source_course_facts": len(facts),
        "unique_indexed_course_codes": len(actual_by_code),
        "indexed_prerequisite_facts": sum(bool(item.get("prerequisite_codes")) for item in facts),
        "source_pages": {str(page): sum(item["page"] == page for item in facts)
                          for page in sorted({item["page"] for item in facts})},
        "mismatches": mismatches,
        "facts": facts,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, default=ROOT / "data/corpus/phase7_source_expansion/20261005/uet_robotics_curriculum_qh2025_source.html")
    parser.add_argument("--index-dir", type=Path, default=ROOT / ".tmp/phase7-source-expansion-20261005/source-index-v6")
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation/results/phase7-completion-20261004/p7-03_qh2025_source_binding_validation-v3.json")
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error("refusing to overwrite source validation; choose a fresh --output path")
    result = audit(args.html, args.index_dir, args.pdf)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "release_eligible", "html_numbered_course_rows_with_code_and_credit", "indexed_source_course_facts", "indexed_prerequisite_facts", "source_pages", "mismatches")}, ensure_ascii=True, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
