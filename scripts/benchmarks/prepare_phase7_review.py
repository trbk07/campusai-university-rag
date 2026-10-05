"""Build a pending human review dossier without changing benchmark decisions.

The dossier is an audit/preparation artifact, never an intake approval or a
release dataset. No model is called and no split is assigned during preparation.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path

from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence
from evaluation.benchmarks.human_benchmark_intake import REVIEW_CHECKS, digest_record
from evaluation.common.release_artifacts import read_json, sha256, write_json
from scripts.benchmarks.prepare_human_candidates import load_rows

ROOT = Path(__file__).resolve().parents[2]


def build_draft(dataset: Path, staging: Path, lineage_path: Path, exposure_path: Path,
                index_dir: Path, corpus_manifest: Path) -> dict:
    raw, rows = load_rows(dataset), load_rows(staging)
    lineage, exposure = read_json(lineage_path), read_json(exposure_path)
    raw_hash = sha256(dataset)
    if (lineage.get("dataset_sha256") != raw_hash or exposure.get("dataset_sha256") != raw_hash
            or lineage.get("index_sha256") != sha256(index_dir / "manifest.json")
            or exposure.get("lineage_sha256") != sha256(lineage_path)):
        raise ValueError("review inputs have changed; regenerate lineage/exposure before preparation")
    originals = {"human-" + row["candidate_id"]: row for row in raw}
    exposures = {entry["qid"]: entry for entry in exposure["records"]}
    if (len(originals) != len(raw) or len(rows) != len(raw) or len(exposure["records"]) != len(raw)
            or len({row["qid"] for row in rows}) != len(rows)
            or set(exposures) != set(originals) or set(lineage["connected_groups"]) != set(originals)):
        raise ValueError("review qids must cover original candidates exactly once")
    evidence = frozen_evidence(index_dir)
    index = read_json(index_dir / "manifest.json")
    files = {doc["sha256"]: doc for doc in read_json(corpus_manifest)["documents"]}
    documents = []
    for doc_id in sorted(index["documents"]):
        document = files.get(doc_id)
        if document is None:
            raise ValueError("indexed document missing from source corpus manifest")
        name = document["filename"]
        if not isinstance(name, str) or Path(name).name != name or name in {".", ".."}:
            raise ValueError("invalid corpus filename")
        pdf = corpus_manifest.parent / name
        if not pdf.is_file() or sha256(pdf) != doc_id:
            raise ValueError("source PDF is missing or changed")
        documents.append({"doc_id": doc_id, "filename": name, "academic_year": document.get("academic_year"),
                          "pages": document["page_count"], "pdf_sha256": sha256(pdf),
                          "bm25_sha256": sha256(index_dir / doc_id / "bm25.json")})
    records, catalog = [], {}
    for row in rows:
        qid = row["qid"]
        source = originals.get(qid)
        if source is None or row["question"] != source["question"]:
            raise ValueError("staging must retain every original question verbatim")
        if exposures[qid]["connected_group"] != lineage["connected_groups"][qid]:
            raise ValueError("exposure connected group does not bind current lineage")
        gold_keys = []
        for gold in row["gold_evidence"]:
            frozen = evidence.get((gold["doc_id"], gold["chunk_id"]))
            if frozen is None or frozen["page"] != gold["page"] or gold["doc_id"] not in row["doc_ids"]:
                raise ValueError("gold evidence does not bind current page/scope")
            key = gold["doc_id"] + "/" + gold["chunk_id"]
            catalog[key] = {"doc_id": gold["doc_id"], "chunk_id": gold["chunk_id"], "page": frozen["page"],
                            "page_range": frozen.get("page_range"), "content": frozen["content"],
                            "content_type": frozen.get("content_type"), "metadata": frozen.get("metadata", {}),
                            "frozen_item_sha256": digest_record(frozen)}
            gold_keys.append(key)
        records.append({"qid": qid, "candidate_id": source["candidate_id"], "original_author_alias": source["author"],
                        "source_record_id": source.get("source_record_id"), "record": row,
                        "record_sha256": digest_record(row), "connected_group": lineage["connected_groups"][qid],
                        "gold_evidence_keys": gold_keys, "exposure": exposures[qid],
                        "scope_proposal": {"status": "pending_owner_review", "doc_ids": row["doc_ids"] or index["documents"],
                                           "basis": "existing_explicit_scope" if row["doc_ids"] else "proposal_all_indexed_documents",
                                           "label_requires_recheck": not bool(row["doc_ids"])},
                        "decision": {"status": "pending", "actual_author_ids": [], "reviewer_id": "",
                                     "reviewer_role": "pending", "reviewed_at": None,
                                     "review_checks": {key: None for key in REVIEW_CHECKS}, "scope_status": "pending",
                                     "confirmed_doc_ids": [], "confirmed_expected_behavior": None,
                                     "exposure_status": "pending", "exposure_history_reference": "", "gold_claims": [], "notes": ""}})
    counts = Counter(entry["exposure"]["status"] for entry in records)
    return {"schema_version": 1, "phase": 7, "artifact_type": "pending_review_dossier",
            "status": "pending_owner_review", "release_eligible": False, "split_assignment": None,
            "purpose": "Verify existing inputs, scope, evidence and history before F0; no tuning or held-out measurement",
            "inputs": {"dataset_sha256": raw_hash, "staging_sha256": sha256(staging),
                       "lineage_sha256": sha256(lineage_path), "exposure_sha256": sha256(exposure_path),
                       "index_sha256": sha256(index_dir / "manifest.json"), "corpus_manifest_sha256": sha256(corpus_manifest)},
            "counts": {"records": len(records), "positive": sum(row["record"]["answerable"] for row in records),
                       "negative": sum(not row["record"]["answerable"] for row in records),
                       "contextual": sum(bool(row["record"].get("context") or row["record"].get("selected_text")) for row in records),
                       "groups": len(set(lineage["connected_groups"].values())), "exposure": dict(sorted(counts.items()))},
            "documents": documents, "evidence_catalog": catalog, "records": records}


def render_dossier(draft: dict, docs_dir: Path = ROOT / "docs/benchmarks") -> str:
    resolved_docs = Path(docs_dir).resolve()
    try:
        relative_docs = resolved_docs.relative_to(ROOT.resolve())
    except ValueError:
        relative_docs = Path("docs/benchmarks")
    root_link = "../" * len(relative_docs.parts)
    group_guide = Path(os.path.relpath(ROOT / "docs/benchmarks/phase7_group_review.draft.md",
                                       ROOT / relative_docs)).as_posix()
    lines = ["# Hồ sơ duyệt từng câu Phase 7 — bản chờ owner review", "",
             f"Trạng thái: **CHỜ DUYỆT TỪNG RECORD**. Owner self-review được phép; chọn rõ vai trò `project_owner` và không gọi là independent. Đọc [hướng dẫn và quyết định chung]({group_guide}) trước khi ghi review.", "",
             "Câu hỏi giữ nguyên; nhãn/gold dưới đây là đề xuất hiện có cần người review kiểm chứng.",
             "Không có kết quả model, split hoặc quyết định nghiệm thu trong hồ sơ này.", "",
             "## Danh mục tài liệu được index", "",
             "Scope đề xuất cho negative là các tài liệu trong bảng này. PDF scan-only chưa index không nằm trong scope này.", "",
             "| Mã | PDF | Năm | Trang | SHA-256 / doc ID |", "|---|---|---|---:|---|"]
    aliases = {}
    for number, doc in enumerate(draft["documents"], 1):
        alias = f"D{number:02}"
        aliases[doc["doc_id"]] = alias
        lines.append(f"| {alias} | [{doc['filename']}]({root_link}data/corpus/university/{doc['filename']}) | {doc['academic_year']} | {doc['pages']} | `{doc['doc_id']}` |")
    scope_range = f"D01–D{len(draft['documents']):02}"
    lines += ["", f"## {draft['counts']['negative']} câu negative cần duyệt scope và hành vi", "",
              f"Scope `{scope_range}` là **đề xuất**, không khẳng định tất cả câu đều negative trên corpus mở rộng.",
              "Nếu có bằng chứng trả lời, ghi sửa nhãn/gold; nếu thiếu đối tượng/ngành/năm, ghi câu cần làm rõ.", "",
              "| Câu | Câu hỏi nguyên văn | Hành vi hiện có | Scope đề xuất |", "|---|---|---|---|"]
    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", "<br>")
    for entry in draft["records"]:
        row = entry["record"]
        if not row["answerable"]:
            lines.append(f"| [{entry['candidate_id']}](#{entry['qid']}) | {cell(row['question'])} | `{row['expected_behavior']}` | {scope_range} |")
    lines += ["", "## Danh sách chưa rõ exposure", "",
              "Cần ghi cycle/dataset/split, thời điểm, mục đích và hồ sơ liên quan; chưa biết không đồng nghĩa chưa dùng.",
              "Các câu đã exposure được giữ nguyên trạng thái; nhóm chưa thể chọn held-out mới trước khi audit hoàn tất.", "",
              "| Câu | ID nguồn | Connected group | Group đã exposure |", "|---|---|---|---|"]
    for entry in draft["records"]:
        if entry["exposure"]["status"].startswith("unknown"):
            lines.append(f"| [{entry['candidate_id']}](#{entry['qid']}) | `{entry['source_record_id']}` | `{entry['connected_group']}` | {'Có' if entry['exposure']['group_known_exposed'] else 'Chưa ghi nhận'} |")
    lines += ["", "## Câu hỏi, context và bằng chứng", ""]
    for entry in draft["records"]:
        row = entry["record"]
        docs = ", ".join(aliases[doc] for doc in entry["scope_proposal"]["doc_ids"])
        lines += [f"### {entry['qid']}", "", f"**Câu hỏi:** {row['question']}", "",
                  f"Nhãn hiện có: {'positive' if row['answerable'] else 'negative'}; `{row['difficulty']}`; hành vi `{row['expected_behavior']}`.",
                  f"Scope {'hiện có' if row['doc_ids'] else 'đề xuất cần duyệt'}: {docs}. Filters: `{json.dumps(row['filters'], ensure_ascii=False)}`.",
                  f"Nhóm: `{entry['connected_group']}`. Exposure: `{entry['exposure']['status']}`.",
                  f"Author alias gốc: `{entry['original_author_alias']}`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.", ""]
        if row.get("context") or row.get("selected_text"):
            lines += ["**Context/selection cần review cùng câu hỏi:**", "", "```json",
                      json.dumps({"context": row.get("context", []), "selected_text": row.get("selected_text")}, ensure_ascii=False, indent=2), "```", ""]
        if not entry["gold_evidence_keys"]:
            lines += ["**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.", ""]
        for key in entry["gold_evidence_keys"]:
            item = draft["evidence_catalog"][key]
            lines += [f"**Gold: {aliases[item['doc_id']]}, trang {item['page']}**, `{item['chunk_id']}`.", "",
                      "<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>", "", "````text", item["content"], "````", "", "</details>", ""]
        lines += ["**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.",
                  "Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.",
                  "Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.",
                  "Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.", "",
                  f"Binding record: `{entry['record_sha256']}`.", ""]
    return "\n".join(lines).rstrip() + "\n"


def publish(draft: dict, data_dir: Path, docs_dir: Path, *, verify: bool = False) -> dict:
    json_path = data_dir / "phase7_review_draft.json"
    dossier_path = docs_dir / "phase7_review_questions.draft.md"
    manifest_path = data_dir / "phase7_review_bundle.manifest.json"
    json_text = json.dumps(draft, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    dossier = render_dossier(draft, docs_dir)
    if verify:
        if json_path.read_text(encoding="utf-8") != json_text or dossier_path.read_text(encoding="utf-8") != dossier:
            raise ValueError("review draft changed; keep completed decisions separately from generated templates")
        manifest = read_json(manifest_path)
        if (manifest["inputs"] != draft["inputs"] or manifest["draft_sha256"] != sha256(json_path)
                or manifest["dossier_sha256"] != sha256(dossier_path)):
            raise ValueError("review bundle manifest does not bind current files")
        return manifest
    if any(path.exists() for path in (json_path, dossier_path, manifest_path)):
        raise ValueError("review draft already exists; retain it and use --verify or a new cycle directory")
    data_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json_text, encoding="utf-8")
    dossier_path.write_text(dossier, encoding="utf-8")
    manifest = {"schema_version": 1, "status": "pending_owner_review", "release_eligible": False,
                "inputs": draft["inputs"], "counts": draft["counts"],
                "draft_sha256": sha256(json_path), "dossier_sha256": sha256(dossier_path)}
    write_json(manifest_path, manifest)
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-dir", type=Path, default=ROOT / "data/benchmark")
    parser.add_argument("--index-dir", type=Path, default=ROOT / ".tmp/hybrid-index")
    parser.add_argument("--corpus-manifest", type=Path, default=ROOT / "data/corpus/university/manifest.json")
    parser.add_argument("--output-data-dir", type=Path, default=ROOT / "data/benchmark")
    parser.add_argument("--output-docs-dir", type=Path, default=ROOT / "docs/benchmarks")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)
    draft = build_draft(args.benchmark_dir / "human_candidate_pool.jsonl", args.benchmark_dir / "human_candidate_staging.jsonl",
                        args.benchmark_dir / "human_candidate_lineage.json", args.benchmark_dir / "phase7_exposure_registry.json",
                        args.index_dir, args.corpus_manifest)
    result = publish(draft, args.output_data_dir, args.output_docs_dir, verify=args.verify)
    print(json.dumps({"status": result["status"], "counts": result["counts"], "release_eligible": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
