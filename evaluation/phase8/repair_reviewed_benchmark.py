"""Create and verify the narrowly repaired v5 regression benchmark.

The v4 review remains immutable. Only its two rejected questions are changed;
gold, evidence, IDs, splits and thresholds are retained. Review authority is
the owner's explicit Phase 8 AI-review delegation, never a human signature.
"""
from __future__ import annotations

import argparse
import copy
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path

from evaluation.benchmarks.connected_groups import connected_groups
from evaluation.phase8.validate_automated_review import (
    ROOT, DEFAULT_REPORT, row_hash, sha256, require, validate, validate_decisions,
)

OUT = Path("evaluation/phase8/benchmark_candidate_v5.jsonl")
REVIEW = Path("evaluation/results/phase8-automated-review-v5.json")
PACKET = Path("evaluation/phase8/benchmark_review_v5.md")
FREEZE = Path("evaluation/results/phase8-benchmark-freeze-v5.json")
REPAIRS = {
    "p8-fact-valedictorian-average": {
        "question": "Theo Điều 3 của Quy định khen thưởng UET năm 2023, khi xét danh hiệu dành cho sinh viên có điểm trung bình toàn khóa cao nhất, điểm đó được so sánh trong phạm vi nào?",
        "rationale": "Điều 3 ở trang 2 ghi điểm trung bình toàn khóa cao nhất trong ngành học. Câu mới bỏ tên danh hiệu có chứa phạm vi trả lời; vẫn hỏi chính phạm vi so sánh trong điều khoản, nên gold Trong ngành học không đổi. Không hỏi điểm số hay đổi đối tượng so sánh.",
        "clarity": "Nêu văn bản, năm và Điều 3; hỏi phạm vi so sánh điểm toàn khóa, không dùng tên danh hiệu để gợi phạm vi.",
        "leakage": "Cụm ngành học và tên danh hiệu Thủ khoa ngành học đều đã bỏ khỏi câu hỏi; câu hỏi không liệt kê lựa chọn chứa đáp án.",
    },
    "p8-fact-thesis-excellence-result": {
        "question": "Theo Điều 7 của Quy định khen thưởng UET năm 2023, Hội đồng chấm phải công nhận kết quả bảo vệ khóa luận/đồ án ở mức nào để sinh viên được xét danh hiệu quy định tại điều này?",
        "rationale": "Điều 7 ở trang 3 yêu cầu Hội đồng công nhận kết quả bảo vệ khóa luận/đồ án Xuất sắc. Câu mới hỏi đúng mức kết quả này nhưng bỏ tên danh hiệu làm lộ mức xếp loại. Gold Xuất sắc và nguồn giữ nguyên; không biến một điều kiện thành toàn bộ điều kiện đủ.",
        "clarity": "Xác định Điều 7 của quy định khen thưởng 2023 và kết quả do Hội đồng chấm công nhận; không cần tên danh hiệu trong câu hỏi.",
        "leakage": "Từ Xuất sắc đã bỏ hoàn toàn khỏi câu hỏi; tên văn bản và số điều chỉ định nguồn, không cho biết mức đánh giá.",
    },
}


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))


def rows_at(path):
    return [json.loads(s) for s in (ROOT / path).read_text(encoding="utf-8-sig").splitlines() if s]


def binding(path):
    return {"path": path.as_posix(), "sha256": sha256(ROOT / path)}


def repaired_rows(before):
    after = copy.deepcopy(before)
    require(set(REPAIRS) <= {r["qid"] for r in before}, "repair qids missing")
    for row in after:
        if row["qid"] in REPAIRS:
            row["question"] = REPAIRS[row["qid"]]["question"]
    return after


def render(report, rows):
    lines = ["# Phase 8 v5 automated benchmark review", "",
             "**AUTOMATED_REVIEW_COMPLETE. OFFICIALLY_APPROVED: false.**", "",
             "- Reviewer: Codex — Automated AI Review (owner_delegated_ai).",
             f"- Reviewed at: {report['reviewed_at']} (UTC).",
             f"- Benchmark SHA-256: `{report['benchmark']['sha256']}`",
             "- 30 Accept / 0 Reject / 0 Pending; no human signature is claimed.",
             "- V4's 28 unchanged decisions are retained after hash/provenance revalidation. Only its two rejected questions are repaired and re-reviewed here.",
             "- Regression only; historical source exposure remains. Automated review completion is separate from the evaluation freeze manifest and product acceptance.", ""]
    by_qid = {r["qid"]: r for r in rows}
    for i, d in enumerate(report["decisions"], 1):
        r = by_qid[d["qid"]]
        e = r["gold_claims"][0]["evidence"][0]
        lines += [f"## {i:02}. `{d['qid']}`", "", f"- Question: {r['question']}",
                  f"- Expected answer: `{r['gold_answer']}`", f"- Gold claim: {r['gold_claims'][0]['text']}",
                  f"- Evidence: `{e['doc_id']}`, chunk `{e['chunk_id']}`, page {e['page']}, range {e.get('page_range', [e['page'], e['page']])}.",
                  f"- Source row: {e['quote']}", f"- Source check: {d['source_locator']}; physical PDF page {d['pdf_page']}.",
                  "- Decision: [x] Accept  [ ] Reject", f"- Reviewer note: {d['rationale']}"]
        for key, item in d["criteria"].items():
            lines.append(f"- {key}: **{item['status']}** — {item['reason']}")
        if "repair_review" in d:
            lines.append(f"- v5_repair_review: **PASS** — {d['repair_review']}")
        lines.append("")
    lines += ["## Review disposition", "", "- Human signature: NOT_PROVIDED.",
              "- OFFICIALLY_APPROVED: false; Phase 8 PASS: false.",
              "- Owner-delegated AI review is complete. The separate freeze records only the immutable regression-evaluation population, not human approval or product quality.",
              "- A gate explicitly requiring human signoff remains PENDING_HUMAN_APPROVAL; this report cannot satisfy it.", ""]
    return "\n".join(lines)


def verify_successor():
    validate(DEFAULT_REPORT)
    previous = load(DEFAULT_REPORT)
    current = load(REVIEW)
    before, after = rows_at(previous["benchmark"]["path"]), rows_at(OUT)
    require(after == repaired_rows(before), "successor changes exceed two question repairs")
    require(current["prior_review"] == binding(DEFAULT_REPORT), "prior review binding mismatch")
    require(current["sources"] == previous["sources"] and
            current["corpus_manifest"] == previous["corpus_manifest"], "review source binding drift")
    require(current["benchmark"] == binding(OUT) and current["review_packet"] == binding(PACKET),
            "successor artifact binding mismatch")
    validate_decisions(after, current, (ROOT / PACKET).read_text(encoding="utf-8"))
    earlier = {d["qid"]: d for d in previous["decisions"]}
    for d in current["decisions"]:
        if d["qid"] not in REPAIRS:
            require(d == earlier[d["qid"]], "unchanged review decision drift")
        else:
            require(d["decision"] == "Accept" and bool(d.get("repair_review")), "missing repair review")
    # All evidence/gold fields are identical to v4, whose PDF/index bindings were
    # revalidated above. This transfers provenance, not a new semantic judgment.
    return {"status": "PASS", "reviewed": 30, "accept": 30, "reject": 0,
            "changed_questions": sorted(REPAIRS), "accepted_provenance_pass": 30,
            "benchmark": binding(OUT), "review": binding(REVIEW), "provider_calls": 0}


def verify_freeze(freeze=None):
    validation = verify_successor()
    freeze = load(FREEZE) if freeze is None else freeze
    require(freeze["status"] == "FROZEN_FOR_REGRESSION_EVALUATION" and freeze["frozen"] is True,
            "benchmark not frozen for evaluation")
    require(all(freeze[k] is False for k in ("officially_approved", "product_baseline_pass",
                "phase8_pass", "fresh_validation", "human_signature_added")), "freeze must not promote release")
    require(freeze["benchmark"] == binding(OUT) and freeze["review"] == binding(REVIEW)
            and freeze["review_packet"] == binding(PACKET), "freeze binding mismatch")
    require(freeze["review_validation"] == validation, "freeze validation mismatch")
    rows = rows_at(OUT)
    groups = connected_groups(rows)
    splits = defaultdict(set)
    for row in rows:
        splits[groups[row["qid"]]].add(row["split"])
    require(all(len(s) == 1 for s in splits.values()) and freeze["cross_split_groups"] == 0,
            "freeze group leakage")
    require(freeze["rows"] == len(rows) == 300 and
            freeze["split_counts"] == dict(Counter(r["split"] for r in rows)) and
            freeze["connected_groups"] == len(splits) and
            freeze["largest_group"] == max(Counter(groups.values()).values()), "freeze population mismatch")
    for key in ("historical_review_manifest", "historical_dataset"):
        require(freeze[key] == binding(Path(freeze[key]["path"])), "historical binding drift")
    historic = load(freeze["historical_review_manifest"]["path"])
    require(historic["dataset_sha256"] == freeze["historical_dataset"]["sha256"] and
            historic["review_mode"] == freeze["historical_review_mode"] and historic["review_complete"]
            and historic["frozen"] and historic["status"] == "pass", "historical review invalid")
    return {**validation, "freeze_status": freeze["status"], "freeze": binding(FREEZE)}


def create():
    for path in (OUT, REVIEW, PACKET, FREEZE):
        require(not (ROOT / path).exists(), f"refusing to overwrite {path}")
    validate(DEFAULT_REPORT)
    previous = load(DEFAULT_REPORT)
    require({d["qid"] for d in previous["decisions"] if d["decision"] == "Reject"} == set(REPAIRS),
            "repair list does not match rejected questions")
    before = rows_at(previous["benchmark"]["path"])
    # Rebuild the original candidate in memory to verify its derived historical
    # claims without overwriting the reviewed Markdown or baseline artifacts.
    from evaluation.phase8.build_temporal_review_draft import build
    _, _, rebuilt, _ = build()
    require(rebuilt == before, "v4 candidate no longer reproduces")
    after = repaired_rows(before)
    report = copy.deepcopy(previous)
    report.update(benchmark_version="phase8-reviewed-regression-v5",
                  reviewed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"), timezone="UTC",
                  prior_review=binding(DEFAULT_REPORT), candidate_disposition="ACCEPT_FOR_REGRESSION_EVALUATION",
                  counts={"reviewed": 30, "accept": 30, "reject": 0, "pending": 0})
    report.pop("original_review_packet_sha256")
    report["previous_benchmark"] = binding(Path(previous["benchmark"]["path"]))
    by_qid = {r["qid"]: r for r in after}
    for d in report["decisions"]:
        if d["qid"] not in REPAIRS:
            continue
        repair = REPAIRS[d["qid"]]
        d.update(decision="Accept", rationale=repair["rationale"], leakage_spans=[],
                 benchmark_row_sha256=row_hash(by_qid[d["qid"]]),
                 repair_review="Chỉ sửa question để bỏ leakage đã bị Reject; kiểm tra lại điều khoản gốc và giữ nguyên gold, evidence, qid, split. Không dùng output model để lựa chọn cách sửa.")
        for key, reason in (("question_answer_correctness", repair["rationale"]),
                            ("clarity", repair["clarity"]), ("no_answer_leakage", repair["leakage"])):
            d["criteria"][key] = {"status": "PASS", "reason": reason}
    (ROOT / OUT).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in after),
                           encoding="utf-8", newline="\n")
    report["benchmark"] = binding(OUT)
    (ROOT / PACKET).write_text(render(report, after), encoding="utf-8", newline="\n")
    report["review_packet"] = binding(PACKET)
    (ROOT / REVIEW).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8", newline="\n")
    validation = verify_successor()
    groups = connected_groups(after)
    splits = defaultdict(set)
    for row in after:
        splits[groups[row["qid"]]].add(row["split"])
    require(all(len(v) == 1 for v in splits.values()), "cross-split group leakage")
    historical_manifest = Path("evaluation/results/phase7-source-context-20261004-r18/human_benchmark_manifest.json")
    historical_data = Path("data/benchmark/phase7_review_cycles/phase7-release-20261004-r18/human_retrieval.jsonl")
    historic = load(historical_manifest)
    require(historic["status"] == "pass" and historic["review_complete"] and historic["frozen"]
            and historic["dataset_sha256"] == sha256(ROOT / historical_data), "historical review mismatch")
    freeze = {"schema_version": 1, "phase": 8, "version": "phase8-reviewed-regression-v5",
              "status": "FROZEN_FOR_REGRESSION_EVALUATION", "frozen": True,
              "officially_approved": False, "product_baseline_pass": False, "phase8_pass": False,
              "fresh_validation": False, "human_signature_added": False,
              "authority": "Owner explicitly delegated Phase 8 review to Codex; goal authorizes finalizing the reviewed benchmark. This is an evaluation freeze, not human or release approval.",
              "benchmark": binding(OUT), "review": binding(REVIEW), "review_packet": binding(PACKET),
              "review_validation": validation, "rows": len(after),
              "split_counts": dict(Counter(r["split"] for r in after)),
              "connected_groups": len(splits), "largest_group": max(Counter(groups.values()).values()),
              "cross_split_groups": 0, "supplemental_review_mode": "owner_delegated_ai",
              "historical_review_manifest": binding(historical_manifest),
              "historical_dataset": binding(historical_data), "historical_review_mode": historic["review_mode"],
              "historical_rows": 270, "supplemental_rows": 30,
              "limitations": ["Historically exposed regression population; not fresh validation.",
                              "All 20 temporal questions are in holdout.",
                              "AI review is not independent human review; no human signature is created."],
              "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (ROOT / FREEZE).write_text(json.dumps(freeze, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8", newline="\n")
    return verify_freeze()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="Verify saved artifacts without rewriting them")
    args = parser.parse_args()
    print(json.dumps(verify_freeze() if args.verify else create(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
