"""Validate saved AI review decisions and source bindings; never approve a release.

Semantic judgments are made by the named AI reviewer and stored in the report.
This offline validator checks completeness, contradictions, drift and provenance;
passing it is not another semantic review or a human signature.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path

from evaluation.benchmarks.human_record_contract import expected_behavior_error

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = Path("evaluation/results/phase8-automated-review-v4.json")
CRITERIA = {"question_answer_correctness", "evidence_support", "clarity",
            "schema_and_corpus", "no_answer_leakage", "v4_revision_integrity"}
REVISED = {f"p8-temporal-2021-adjustment-{n:02}" for n in (4, 9, 14, 19)}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row_hash(row: dict) -> str:
    return hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def normalized(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines()
            if line.strip()]


def validate_decisions(rows: list[dict], report: dict, markdown: str) -> None:
    supplements = {r["qid"]: r for r in rows if r["qid"].startswith("p8-")}
    decisions = report["decisions"]
    require(len(rows) == 300 and len({r["qid"] for r in rows}) == 300,
            "expected 300 unique benchmark rows")
    require(len(supplements) == len(decisions) == 30 and
            {d["qid"] for d in decisions} == set(supplements), "review qid coverage mismatch")
    require(report["status"] == "AUTOMATED_REVIEW_COMPLETE", "review not complete")
    require(report["reviewer"] == "Codex — Automated AI Review" and
            report["review_mode"] == "owner_delegated_ai", "review identity mismatch")
    require(report["officially_approved"] is False and report["human_signed"] is False
            and report["frozen"] is False, "automated review must not promote approval")
    require("AUTOMATED_REVIEW_COMPLETE" in markdown and "OFFICIALLY_APPROVED: false" in markdown,
            "Markdown approval distinction missing")
    sections = re.split(r"(?=^## \d{2}\. `)", markdown, flags=re.M)
    by_qid = {}
    for section in sections[1:]:
        qid = re.match(r"## \d{2}\. `([^`]+)`", section)[1]
        require(qid not in by_qid, "duplicate Markdown row")
        by_qid[qid] = section.split("## Review disposition", 1)[0]
    require(set(by_qid) == set(supplements), "Markdown qid coverage mismatch")
    for d in decisions:
        qid = d["qid"]
        row = supplements[qid]
        require(row_hash(row) == d["benchmark_row_sha256"], f"{qid}: row drift")
        require(row.get("schema_version") == 1 and row.get("answerable") is True and
                expected_behavior_error(row) is None and row.get("split") in {"test", "holdout"}
                and all(row.get(k) for k in ("question", "gold_answer", "gold_claims",
                                            "gold_evidence", "tags", "source_group", "paraphrase_group")),
                f"{qid}: benchmark schema invalid")
        criteria = d["criteria"]
        require(set(criteria) == CRITERIA, f"{qid}: missing review criterion")
        require(all(c.get("status") in {"PASS", "FAIL", "NOT_APPLICABLE"}
                    and isinstance(c.get("reason"), str) and c["reason"].strip()
                    for c in criteria.values()), f"{qid}: incomplete criterion")
        require(all(c["status"] != "NOT_APPLICABLE" for k, c in criteria.items()
                    if k != "v4_revision_integrity"), f"{qid}: skipped criterion")
        require((criteria["v4_revision_integrity"]["status"] != "NOT_APPLICABLE") == (qid in REVISED),
                f"{qid}: revised question not reviewed")
        failed = [k for k, c in criteria.items() if c["status"] == "FAIL"]
        require(d["decision"] == ("Reject" if failed else "Accept"), f"{qid}: decision contradicts criteria")
        require(bool(d.get("rationale")) and bool(d.get("source_locator")), f"{qid}: missing rationale/source")
        if d["decision"] == "Accept":
            require(normalized(row["gold_answer"]).rstrip(".") not in normalized(row["question"]),
                    f"{qid}: literal answer leakage")
        for span in d.get("leakage_spans", []):
            require(normalized(span) in normalized(row["question"]) and
                    criteria["no_answer_leakage"]["status"] == "FAIL", f"{qid}: invalid leakage finding")
        box = "[x] Accept  [ ] Reject" if d["decision"] == "Accept" else "[ ] Accept  [x] Reject"
        section = by_qid[qid]
        require(section.count("- Decision:") == 1 and f"- Decision: {box}" in section,
                f"{qid}: Markdown decision mismatch")
        require(d["rationale"] in section and row["question"] in section and
                row["gold_answer"] in section, f"{qid}: Markdown review mismatch")
    counts = {v: sum(d["decision"] == v for d in decisions) for v in ("Accept", "Reject")}
    require(report["counts"] == {"reviewed": 30, "accept": counts["Accept"],
                                 "reject": counts["Reject"], "pending": 0}, "review totals mismatch")


def validate(report_path: Path = DEFAULT_REPORT, *, root: Path = ROOT) -> dict:
    import pymupdf

    report_path = root / report_path
    report = _json(report_path)
    benchmark = root / report["benchmark"]["path"]
    require(sha256(benchmark) == report["benchmark"]["sha256"], "benchmark hash mismatch")
    packet = root / report["review_packet"]["path"]
    require(sha256(packet) == report["review_packet"]["sha256"], "Markdown hash mismatch")
    rows = _rows(benchmark)
    validate_decisions(rows, report, packet.read_text(encoding="utf-8"))
    prior = report["previous_benchmark"]
    require(sha256(root / prior["path"]) == prior["sha256"], "previous benchmark hash mismatch")
    before = {r["qid"]: r for r in _rows(root / prior["path"])}
    require(set(before) == {r["qid"] for r in rows}, "v3/v4 qid set mismatch")
    differences = {r["qid"]: [k for k in r.keys() | before[r["qid"]].keys()
                              if r.get(k) != before[r["qid"]].get(k)]
                   for r in rows if r != before[r["qid"]]}
    require(differences == {qid: ["question"] for qid in REVISED}, "unexpected v4 changes")
    corpus = root / report["corpus_manifest"]["path"]
    require(sha256(corpus) == report["corpus_manifest"]["sha256"], "corpus manifest hash mismatch")
    documents = {d["sha256"]: d for d in _json(corpus)["documents"]}
    chunks, pdf_text = {}, {}
    for src in report["sources"]:
        path = root / src["path"]
        require(sha256(path) == src["sha256"] and
                documents[src["sha256"]]["filename"] == path.name, "source PDF/corpus mismatch")
        index_file = root / src["index_path"]
        require(sha256(index_file) == src["index_sha256"], "index content hash mismatch")
        for item in _json(index_file)["items"]:
            chunks[(item["doc_id"], item["chunk_id"])] = item
        with pymupdf.open(path) as pdf:
            require(len(pdf) == src["pages_visually_reviewed"], "PDF review coverage mismatch")
            pdf_text[src["sha256"]] = [normalized(p.get_text()) for p in pdf]
    by_qid = {r["qid"]: r for r in rows}
    results = []
    for d in report["decisions"]:
        row = by_qid[d["qid"]]
        require(len(row["gold_claims"]) == len(row["gold_evidence"]) == 1,
                f"{d['qid']}: unexpected evidence shape")
        evidence = row["gold_claims"][0]["evidence"][0]
        require({k: v for k, v in evidence.items() if k != "quote"} == row["gold_evidence"][0],
                f"{d['qid']}: gold/claim provenance mismatch")
        doc = row["source_document_sha256"]
        require(doc == evidence["doc_id"], f"{d['qid']}: source doc mismatch")
        chunk = chunks[(doc, evidence["chunk_id"])]
        bounds = evidence.get("page_range", [evidence["page"], evidence["page"]])
        require(chunk["page"] == evidence["page"] and chunk["page_range"] == bounds and
                bounds[0] <= d["pdf_page"] <= bounds[-1], f"{d['qid']}: page provenance mismatch")
        quote = evidence["quote"]
        content = chunk["content"]
        if chunk["content_type"] == "table":
            table = json.loads(content.split("\n\n", 1)[1])
            matched = [cells for cells in table["rows"]
                       if normalized(" ".join(cells)) == normalized(quote)]
            require(len(matched) == 1, f"{d['qid']}: table quote not unique")
            cells = matched[0]
            claim = row["expected_claims"][0]
            require(cells[4] == row["gold_answer"], f"{d['qid']}: wrong adjusted-code column")
            if "old_course_code" in claim:
                require(cells[1] == claim["old_course_code"] and
                        cells[3] == cells[6] == str(claim["credits"]), f"{d['qid']}: table fact mismatch")
            require(all(normalized(cells[k]) in pdf_text[doc][d["pdf_page"]-1] for k in (1, 4)),
                    f"{d['qid']}: PDF codes missing")
        else:
            require(normalized(quote) in normalized(content), f"{d['qid']}: index quote missing")
            require(normalized(quote) in pdf_text[doc][d["pdf_page"]-1], f"{d['qid']}: PDF quote missing")
        results.append({"qid": d["qid"], "decision": d["decision"], "provenance": "PASS",
                        "pdf_page": d["pdf_page"], "chunk_id": evidence["chunk_id"]})
    return {"status": "PASS", "scope": "review completeness and mechanical provenance; not release approval",
            "review_report_sha256": sha256(report_path), "review_packet_sha256": sha256(packet),
            "benchmark_sha256": sha256(benchmark), "counts": report["counts"],
            "accepted_provenance_pass": sum(r["decision"] == "Accept" for r in results),
            "v4_revision_integrity": "PASS", "officially_approved": False,
            "provider_calls": 0, "rows": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = validate(args.report)
    if args.output:
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
