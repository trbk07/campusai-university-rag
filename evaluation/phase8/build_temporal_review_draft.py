"""Build a source-bound, owner-review draft of Phase 8 temporal questions.

This is a review artifact, not a frozen benchmark or a quality PASS. Questions
are derived from one dated 2021 correction table and remain subject to owner
review and source-exposure audit.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from evaluation.benchmarks.connected_groups import connected_groups
from evaluation.phase8.run_retrieval_baseline import select_rows


ROOT = Path(__file__).resolve().parents[2]
CORPUS_MANIFEST = ROOT / "data/corpus/university/manifest.json"
SOURCE_PDF = ROOT / "data/corpus/university/uet_program_adjustments_2021.pdf"
SOURCE_SHA256 = "fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79"
INDEX_DIR = ROOT / ".tmp/hybrid-index" / SOURCE_SHA256
JSONL_OUTPUT = ROOT / "evaluation/phase8/temporal_comparison_review_draft_v4.jsonl"
FACTUAL_JSONL_OUTPUT = ROOT / "evaluation/phase8/single_hop_fact_review_draft_v4.jsonl"
COMBINED_JSONL_OUTPUT = ROOT / "evaluation/phase8/benchmark_candidate_v4.jsonl"
REPORT_OUTPUT = ROOT / "evaluation/results/phase8-benchmark-review-candidate-v4.json"
REVIEW_PACKET_OUTPUT = ROOT / "evaluation/phase8/benchmark_owner_review_v4.md"
BASELINE_REPORT = ROOT / "evaluation/results/phase8-r18-retrieval-baseline-v1.json"

# old code, adjusted code, course, adjusted credit value, page, table chunk.
FACTS = [
    ("ELT3213", "ELT3067", "Truyền thông quang", 3, 1, 1),
    ("ELT3214", "ELT3062", "Mạng truyền thông máy tính 2", 3, 1, 1),
    ("ELT3215", "ELT3163", "Mạng truyền thông di động", 3, 1, 1),
    ("RBE1003", "RBE1001", "Trải nghiệm và Khám phá về Robot", 2, 1, 1),
    ("RBE2023", "RBE2021", "Thực hành thiết kế và xây dựng Robot 1", 2, 2, 2),
    ("RBE2024", "RBE2022", "Thực hành thiết kế và xây dựng Robot 2", 2, 2, 2),
    ("RBE3023", "RBE3021", "Đồ án 1: Thiết kế và xây dựng Robot 1", 2, 2, 2),
    ("RBE3024", "RBE3022", "Đồ án 2: Thiết kế và xây dựng Robot 2", 2, 2, 2),
    ("REB3016", "RBE3016", "Thiết kế kiểu dáng công nghiệp", 3, 2, 2),
    ("ELT3212E", "ELT3046E", "Mạng truyền thông máy tính 1", 3, 2, 2),
    ("ELT3214E", "ELT3062E", "Mạng truyền thông máy tính 2", 3, 2, 2),
    ("AER1002", "AER1001", "Giới thiệu về Hàng không Vũ trụ", 3, 2, 2),
    ("AER2002", "EMA2008", "Cơ học chất lỏng", 4, 3, 3),
    ("AER2009", "AER2005", "Cơ học kỹ thuật cho Công nghệ Hàng không Vũ trụ", 4, 3, 3),
    ("AER2006", "EMA2032", "Hình hoạ kỹ thuật và CAD", 3, 3, 3),
    ("AER3039", "AER3003", "Hệ thống đẩy", 3, 3, 3),
    ("AER3040", "EMA3048", "Thử nghiệm kết cấu thiết bị không gian", 3, 3, 3),
    ("AER3037", "EMA3014", "Cơ học quỹ đạo bay", 3, 3, 3),
    ("AER3041", "EMA3064", "Điều khiển điện thủy khí", 3, 3, 3),
]
THESIS_CODE = "INT4050"

REWARDS_PDF = ROOT / "data/corpus/university/uet_student_rewards_2023.pdf"
REWARDS_SHA256 = "7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b"
TRAINING_PDF = ROOT / "data/corpus/university/uet_training_regulation_2014.pdf"
TRAINING_SHA256 = "3d2d91de10423ddd460d64aa7ddeea48af872d97a52eb8dfe716940da99748e1"

# qid, split, source file/hash, chunk, page/range, source-group, question,
# expected answer, exact source quote. These are one-step factual lookups.
FACTUAL_CASES = [
    ("p8-fact-awards-effective-date", "test", "uet_student_rewards_2023.pdf", REWARDS_SHA256,
     f"{REWARDS_SHA256}_p1_s8_c1", 1, [1, 1], "rewards-article-2",
     "Theo Điều 2 của Quyết định khen thưởng ban hành năm 2023, quy định được áp dụng từ tháng/năm nào?",
     "09/2023", "được áp dụng từ tháng 09 năm 2023."),
    ("p8-fact-valedictorian-average", "holdout", "uet_student_rewards_2023.pdf", REWARDS_SHA256,
     f"{REWARDS_SHA256}_p2_s16_c1", 2, [2, 3], "rewards-article-3",
     "Theo Điều 3, danh hiệu Thủ khoa ngành học dựa trên điểm trung bình toàn khóa cao nhất trong phạm vi nào?",
     "Trong ngành học.", "có điểm trung bình toàn khóa học cao nhất trong ngành học"),
    ("p8-fact-excellent-student-floor", "test", "uet_student_rewards_2023.pdf", REWARDS_SHA256,
     f"{REWARDS_SHA256}_p2_s16_c1", 2, [2, 3], "rewards-article-4",
     "Theo Điều 4, sinh viên đạt danh hiệu Sinh viên Xuất sắc không được có học phần nào dưới mức điểm nào?",
     "C+.", "không có học phần nào có điểm dưới C+"),
    ("p8-fact-good-student-conduct", "holdout", "uet_student_rewards_2023.pdf", REWARDS_SHA256,
     f"{REWARDS_SHA256}_p2_s16_c1", 2, [2, 3], "rewards-article-5",
     "Theo Điều 5, kết quả rèn luyện tối thiểu để đạt danh hiệu Sinh viên Giỏi là mức nào?",
     "Tốt trở lên.", "kết quả rèn luyện đạt loại Tốt trở lên"),
    ("p8-fact-collective-contribution-gpa", "test", "uet_student_rewards_2023.pdf", REWARDS_SHA256,
     f"{REWARDS_SHA256}_p2_s16_c1", 2, [2, 3], "rewards-article-6",
     "Theo Điều 6, điểm trung bình học tập tối thiểu để xét danh hiệu Sinh viên có đóng góp cho công tác tập thể là bao nhiêu?",
     "Từ 3.0 trở lên.", "kết quả học tập trong năm học/toàn khóa từ 3.0 trở lên"),
    ("p8-fact-thesis-excellence-result", "holdout", "uet_student_rewards_2023.pdf", REWARDS_SHA256,
     f"{REWARDS_SHA256}_p2_s16_c2", 2, [2, 3], "rewards-article-7",
     "Theo Điều 7, Hội đồng chấm phải công nhận kết quả bảo vệ khóa luận/đồ án ở mức nào để đủ điều kiện danh hiệu Xuất sắc?",
     "Xuất sắc.", "được Hội đồng chấm khóa luận/đồ án công nhận đạt kết quả Xuất sắc"),
    ("p8-fact-collective-advanced-share", "holdout", "uet_student_rewards_2023.pdf", REWARDS_SHA256,
     f"{REWARDS_SHA256}_p2_s16_c2", 2, [2, 3], "rewards-article-8",
     "Theo Điều 8, tối thiểu bao nhiêu phần trăm sinh viên của tập thể phải đạt học tập và rèn luyện loại Khá trở lên?",
     "70%.", "Có 70% sinh viên đạt kết quả học tập và rèn luyện loại Khá trở lên"),
    ("p8-fact-collective-excellent-share", "holdout", "uet_student_rewards_2023.pdf", REWARDS_SHA256,
     f"{REWARDS_SHA256}_p2_s16_c2", 2, [2, 3], "rewards-article-9",
     "Theo Điều 9, tỷ lệ tối thiểu sinh viên đạt danh hiệu Sinh viên Giỏi trong tập thể Xuất sắc là bao nhiêu?",
     "10%.", "có từ 10% sinh viên trở lên đạt danh hiệu “Sinh viên Giỏi”"),
    ("p8-fact-entrance-award-amount", "test", "uet_student_rewards_2023.pdf", REWARDS_SHA256,
     f"{REWARDS_SHA256}_p4_s18_c1", 4, [4, 4], "rewards-article-10",
     "Theo Điều 10, phần thưởng cho sinh viên đạt tiêu chí thành tích tuyển sinh tương đương khoản học phí của thời gian nào?",
     "Năm học đầu tiên trong khóa học.", "bằng học phí của năm học đầu tiên trong khóa học"),
    ("p8-fact-exam-warning-deduction", "test", "uet_training_regulation_2014.pdf", TRAINING_SHA256,
     f"{TRAINING_SHA256}_p1_s4_c1", 1, [1, 1], "training-regulation-article-32-4",
     "Theo trích đoạn Quy chế đào tạo 2014, sinh viên bị khiển trách do nhìn bài người khác hoặc trao đổi bài trong giờ thi bị trừ bao nhiêu phần trăm điểm bài thi?",
     "25%.", "bị trừ 25% số điểm đạt được của bài thi học phần đó"),
]

TEMPLATES = (
    "Theo bảng đính chính ban hành ngày 27/08/2021, mã điều chỉnh của học phần {course} (mã cũ {old}) là gì?",
    "Đối chiếu cột khung hiện hành với cột thông tin điều chỉnh năm 2021 cho {course}: mã mới thay {old} là mã nào?",
    "Trong phụ lục đính chính chương trình đào tạo năm 2021, {old} được đổi thành mã nào cho học phần {course}?",
    "Với học phần {course}, mã điều chỉnh theo văn bản UET năm 2021 là gì (mã trước đính chính: {old})?",
    "Bản đính chính ngày 27 tháng 8 năm 2021 ghi mã nào ở cột điều chỉnh cho {course}, khi cột hiện hành ghi {old}?",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def jsonl_sha256(rows: list[dict]) -> str:
    payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _generated_bytes(path: Path, text: str) -> bytes:
    """Encode generated text with the existing file's newline convention."""
    newline = "\n"
    if path.exists():
        raw = path.read_bytes()
        if b"\r\n" in raw and b"\n" not in raw.replace(b"\r\n", b""):
            newline = "\r\n"
    return text.replace("\n", newline).encode("utf-8")


def _write_generated_outputs(outputs: list[tuple[Path, bytes]]) -> None:
    """Refuse the whole write if regeneration would overwrite any review edit."""
    changed = [path for path, content in outputs
               if path.exists() and path.read_bytes() != content]
    if changed:
        names = ", ".join(path.as_posix() for path in changed)
        raise FileExistsError(f"refusing to overwrite changed Phase 8 artifacts: {names}")
    for path, content in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def _table_for_page(page: int) -> dict:
    chunk = INDEX_DIR / "dense.json"
    items = json.loads(chunk.read_text(encoding="utf-8-sig"))["items"]
    table_item = next(item for item in items
                      if item.get("chunk_id") == f"{SOURCE_SHA256}_p{page}_t1")
    table = json.loads(table_item["content"].split("\n\n", 1)[1])
    return table


def _historical_exposure_audit() -> dict:
    """Find known-code overlap in retained Phase 3/6/7 benchmark JSONL files.

    This is deliberately conservative: a code appearing anywhere in a prior
    record is reported as content exposure. It does not claim to audit provider
    request logs or prove the absence of exposure outside these files.
    """
    files = sorted(set((ROOT / "data/benchmark").rglob("*.jsonl")) |
                   set((ROOT / "evaluation/results").glob("phase7*/**/*.jsonl")))
    pairs = FACTS + [("", THESIS_CODE, "Khóa luận tốt nghiệp", 7, 1, 1)]
    hits = {f"{old}->{new}" if old else f"new:{new}": [] for old, new, *_ in pairs}
    parsed_records = 0
    parse_errors = []
    for path in files:
        try:
            records = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines()
                       if line.strip()]
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            parse_errors.append({"path": path.relative_to(ROOT).as_posix(), "error": type(exc).__name__})
            continue
        parsed_records += len(records)
        for record in records:
            blob = json.dumps(record, ensure_ascii=False).casefold()
            for old, new, *_ in pairs:
                if (old and old.casefold() in blob) or new.casefold() in blob:
                    key = f"{old}->{new}" if old else f"new:{new}"
                    hits[key].append({
                        "path": path.relative_to(ROOT).as_posix(),
                        "qid": record.get("qid") or record.get("id"),
                    })
    return {
        "status": "historical_content_overlap_detected_regression_only",
        "method": "conservative case-insensitive old/new course-code search in retained benchmark JSONL rows",
        "scope": "data/benchmark/**/*.jsonl and evaluation/results/phase7*/**/*.jsonl",
        "files_scanned": len(files) - len(parse_errors),
        "records_scanned": parsed_records,
        "parse_errors": parse_errors,
        "correction_facts_with_any_prior_code_overlap": sum(bool(items) for items in hits.values()),
        "correction_fact_count": len(hits),
        "hits_by_fact": hits,
        "prior_index_contains_source": True,
        "provider_egress_logs_audited": False,
        "fresh_validation": False,
    }


def build_factual_rows() -> list[dict]:
    """Create direct-fact candidates bound to exact indexed source chunks."""
    manifest = json.loads(CORPUS_MANIFEST.read_text(encoding="utf-8-sig"))
    documents = {doc["filename"]: doc for doc in manifest["documents"]}
    chunk_cache: dict[tuple[str, str], dict] = {}
    rows = []
    for qid, split, filename, doc_id, chunk_id, page, page_range, group, question, answer, quote in FACTUAL_CASES:
        source_path = ROOT / "data/corpus/university" / filename
        source = documents.get(filename)
        if not source or source.get("sha256") != doc_id or sha256(source_path) != doc_id:
            raise ValueError(f"factual source hash changed for {filename}")
        key = (doc_id, chunk_id)
        if key not in chunk_cache:
            index_file = ROOT / ".tmp/hybrid-index" / doc_id / "bm25.json"
            index = json.loads(index_file.read_text(encoding="utf-8-sig"))
            chunk_cache[key] = next(
                (item for item in index.get("items", []) if item.get("chunk_id") == chunk_id),
                None,
            )
        item = chunk_cache[key]
        if item is None:
            raise ValueError(f"factual evidence chunk missing from index: {chunk_id}")
        if item.get("page") != page or item.get("page_range") != page_range:
            raise ValueError(f"factual evidence coordinates changed for {chunk_id}")
        if " ".join(quote.split()).casefold() not in " ".join(item.get("content", "").split()).casefold():
            raise ValueError(f"factual evidence quote is not in indexed content: {qid}")
        rows.append({
            "schema_version": 1,
            "qid": qid,
            "split": split,
            "question": question,
            "answerable": True,
            "expected_behavior": "answer_grounded",
            "expected_claims": [{"fact": answer}],
            "gold_answer": answer,
            "gold_claims": [{
                "claim_id": f"{qid}-claim-1",
                "text": answer,
                "answerable": True,
                "evidence": [{
                    "doc_id": doc_id,
                    "chunk_id": chunk_id,
                    "page": page,
                    "page_range": page_range,
                    "quote": quote,
                }],
            }],
            "gold_evidence": [{
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "page": page,
                "page_range": page_range,
            }],
            "tags": ["fact", "single_hop"],
            "source_group": group,
            "paraphrase_group": qid,
            "source_document_sha256": doc_id,
            "source_review_status": "draft_pending_owner_review",
            "exposure_status": "source_previously_indexed; provider_logs_not_audited; regression_only",
        })
    return rows


def _trim_historical_cohort(existing: list[dict], group_by_qid: dict[str, str]) -> tuple[list[dict], list[str]]:
    """Free ten slots evenly while retaining each selected connected group."""
    group_sizes = Counter(group_by_qid[row["qid"]] for row in existing)
    excluded = []
    for split in ("test", "holdout"):
        candidates = [row for row in existing
                      if row["split"] == split and group_sizes[group_by_qid[row["qid"]]] > 1]
        candidates.sort(key=lambda row: hashlib.sha256(
            f"phase8-v3-slot:{split}:{row['qid']}".encode("utf-8")).hexdigest())
        used_groups = set()
        for row in candidates:
            group = group_by_qid[row["qid"]]
            if group in used_groups:
                continue
            excluded.append(row["qid"])
            used_groups.add(group)
            if len(used_groups) == 5:
                break
        if len(used_groups) != 5:
            raise ValueError(f"cannot trim five rows from distinct multi-row groups in {split}")
    excluded_set = set(excluded)
    kept = [row for row in existing if row["qid"] not in excluded_set]
    return kept, sorted(excluded)


def _attach_historical_gold_claims(rows: list[dict]) -> None:
    """Derive Phase 8 claim annotations from owner-reviewed structured gold."""
    chunks: dict[tuple[str, str], dict] = {}
    for row in rows:
        if not row.get("answerable"):
            row["gold_claims"] = []
            continue
        expected_claims = row.get("expected_claims") or []
        validation_facts = (row.get("source_validation") or {}).get("facts") or []
        if len(expected_claims) != 1 or len(validation_facts) != 1:
            raise ValueError(f"cannot derive a single claim for historical qid {row['qid']}")
        expected, source_fact = expected_claims[0], validation_facts[0]
        if not {"course_name", "credits", "semester"} <= set(expected):
            raise ValueError(f"unexpected historical claim fields for {row['qid']}")
        evidence = next((item for item in row.get("gold_evidence", [])
                         if item.get("doc_id") == source_fact.get("doc_id")
                         and item.get("chunk_id") == source_fact.get("chunk_id")), None)
        if evidence is None or evidence.get("page") != source_fact.get("page"):
            raise ValueError(f"source-validation evidence mismatch for {row['qid']}")
        key = (evidence["doc_id"], evidence["chunk_id"])
        if key not in chunks:
            dense = json.loads((ROOT / ".tmp/hybrid-index" / evidence["doc_id"] / "dense.json")
                               .read_text(encoding="utf-8-sig"))
            chunks[key] = next((item for item in dense.get("items", [])
                                if item.get("chunk_id") == evidence["chunk_id"]), None)
        item = chunks[key]
        if item is None or item.get("page") != evidence["page"]:
            raise ValueError(f"indexed source evidence missing for {row['qid']}")
        content = item.get("content", "")
        start = content.find('{"headers"')
        if start < 0:
            raise ValueError(f"indexed table payload missing for {row['qid']}")
        table, _ = json.JSONDecoder().raw_decode(content[start:])
        table_row = source_fact.get("table_row")
        table_rows = table.get("rows", [])
        if not isinstance(table_row, int) or not 0 <= table_row < len(table_rows):
            raise ValueError(f"source table row is invalid for {row['qid']}")
        cells = table_rows[table_row]
        digest = hashlib.sha256(json.dumps(
            {"cells": cells}, sort_keys=True, ensure_ascii=False,
            separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
        if digest != source_fact.get("cells_sha256"):
            raise ValueError(f"source cells hash mismatch for {row['qid']}")
        if (str(source_fact.get("name")) != str(expected["course_name"])
                or int(source_fact.get("credits", -1)) != int(expected["credits"])
                or int(source_fact.get("semester", -1)) != int(expected["semester"])):
            raise ValueError(f"structured gold differs from source-validation fact for {row['qid']}")
        quote = " | ".join(str(cell) for cell in cells)
        if "multi_hop" in row.get("tags", []):
            claim_text = (f"{expected['course_name']} is listed in semester {expected['semester']} "
                          f"and carries {expected['credits']} credits.")
        elif "-semester-" in row["qid"]:
            claim_text = f"{expected['course_name']} is listed in semester {expected['semester']}."
        else:
            claim_text = f"{expected['course_name']} carries {expected['credits']} credits."
        page_range = item.get("page_range", [item["page"], item["page"]])
        row["gold_claims"] = [{
            "claim_id": f"{row['qid']}-phase8-claim-1",
            "text": claim_text,
            "answerable": True,
            "evidence": [{
                "doc_id": evidence["doc_id"],
                "chunk_id": evidence["chunk_id"],
                "page": evidence["page"],
                "page_range": page_range,
                "quote": quote,
            }],
        }]
        row["phase8_gold_claim_derivation"] = "structured_owner_reviewed_expected_claim_and_source_validation_row"


def build() -> tuple[list[dict], list[dict], list[dict], dict]:
    corpus = json.loads(CORPUS_MANIFEST.read_text(encoding="utf-8-sig"))
    source = next(doc for doc in corpus["documents"]
                  if doc["filename"] == SOURCE_PDF.name)
    if source["sha256"] != SOURCE_SHA256 or sha256(SOURCE_PDF) != SOURCE_SHA256:
        raise ValueError("the correction PDF differs from its pinned corpus hash")
    tables = {page: _table_for_page(page) for page in (1, 2, 3)}
    rows = []
    for index, (old, new, course, credits, page, table_page) in enumerate(FACTS):
        # Confirm that the exact old/new/course/credit tuple appears in the
        # source table, rather than trusting the curated question text alone.
        table = tables[table_page]
        matching = []
        for source_row in table.get("rows", []):
            cells = [" ".join(str(cell).split()) for cell in source_row]
            if old in cells and new in cells:
                matching.append(cells)
        if not matching or not any(course in " ".join(cells) and str(credits) in cells
                                   for cells in matching):
            raise ValueError(f"source table no longer supports fact: {old} -> {new}")
        source_quote = next(" ".join(cells) for cells in matching
                            if course in " ".join(cells) and str(credits) in cells)
        qid = f"p8-temporal-2021-adjustment-{index + 1:02d}"
        question = TEMPLATES[index % len(TEMPLATES)].format(
            course=course, old=old)
        rows.append({
            "schema_version": 1,
            "qid": qid,
            "split": "holdout",
            "question": question,
            "answerable": True,
            "expected_behavior": "answer_grounded",
            "expected_claims": [{
                "old_course_code": old,
                "adjusted_course_code": new,
                "course_name": course,
                "credits": credits,
                "correction_date": "2021-08-27",
            }],
            "gold_answer": new,
            "gold_claims": [{
                "claim_id": f"{qid}-claim-1",
                "text": f"Theo đính chính năm 2021, học phần {course} đổi mã từ {old} thành {new}, giữ nguyên {credits} tín chỉ.",
                "answerable": True,
                "evidence": [{
                    "doc_id": SOURCE_SHA256,
                    "chunk_id": f"{SOURCE_SHA256}_p{table_page}_t1",
                    "page": page,
                    "quote": source_quote,
                }],
            }],
            "gold_evidence": [{
                "doc_id": SOURCE_SHA256,
                "chunk_id": f"{SOURCE_SHA256}_p{table_page}_t1",
                "page": page,
            }],
            "tags": ["temporal", "comparison", "table", "curriculum"],
            "source_group": qid,
            "paraphrase_group": qid,
            "source_document_sha256": SOURCE_SHA256,
            "source_review_status": "draft_pending_owner_review",
            "exposure_status": "historical_code_exposure_audit_included; regression_only",
        })

    if len(rows) != 19 or len({row["qid"] for row in rows}) != len(rows):
        raise ValueError("the source correction table must yield 19 unique draft facts")
    # Add the distinct row whose previous-code cell is blank. It is still a
    # date-scoped correction lookup, but not represented as a code-to-code pair.
    rows.insert(3, {
        "schema_version": 1,
        "qid": "p8-temporal-2021-adjustment-04a",
        "split": "holdout",
        "question": "Phụ lục đính chính ngày 27/08/2021 bổ sung mã học phần nào cho Khóa luận tốt nghiệp của chương trình CNTT định hướng thị trường Nhật Bản?",
        "answerable": True,
        "expected_behavior": "answer_grounded",
        "expected_claims": [{
            "adjusted_course_code": "INT4050",
            "course_name": "Khóa luận tốt nghiệp",
            "credits": 7,
            "correction_date": "2021-08-27",
        }],
        "gold_answer": "INT4050",
        "gold_claims": [{
            "claim_id": "p8-temporal-2021-adjustment-04a-claim-1",
            "text": "Đính chính năm 2021 bổ sung mã INT4050 cho Khóa luận tốt nghiệp 7 tín chỉ.",
            "answerable": True,
            "evidence": [{
                "doc_id": SOURCE_SHA256,
                "chunk_id": f"{SOURCE_SHA256}_p1_t1",
                "page": 1,
                "quote": next(" ".join(" ".join(str(cell).split()) for cell in row)
                              for row in tables[1]["rows"] if "INT4050" in row),
            }],
        }],
        "gold_evidence": [{
            "doc_id": SOURCE_SHA256,
            "chunk_id": f"{SOURCE_SHA256}_p1_t1",
            "page": 1,
        }],
        "tags": ["temporal", "table", "curriculum"],
        "source_group": "p8-temporal-2021-thesis-int4050",
        "paraphrase_group": "p8-temporal-2021-thesis-int4050",
        "source_document_sha256": SOURCE_SHA256,
        "source_review_status": "draft_pending_owner_review",
        "exposure_status": "historical_code_exposure_audit_included; regression_only",
    })

    exposure = _historical_exposure_audit()
    for row in rows:
        if row["qid"] == "p8-temporal-2021-adjustment-04a":
            fact_key = f"new:{THESIS_CODE}"
        else:
            claim = row["expected_claims"][0]
            fact_key = f"{claim['old_course_code']}->{claim['adjusted_course_code']}"
        row["exposure_status"] = (
            "prior_benchmark_content_overlap; regression_only"
            if exposure["hits_by_fact"][fact_key]
            else "no_exact_code_overlap_in_scanned_rows; source_indexed_previously; regression_only"
        )

    existing, binding = select_rows()
    baseline = json.loads(BASELINE_REPORT.read_text(encoding="utf-8-sig"))
    if len(existing) != 280 or baseline["benchmark"]["selected_ids_sha256"] != binding["selection"]["selected_ids_sha256"]:
        raise ValueError("Phase 8 retrieval cohort no longer matches its frozen selection")
    factual_rows = build_factual_rows()
    if len(factual_rows) != len(FACTUAL_CASES) or len({row["qid"] for row in factual_rows}) != len(factual_rows):
        raise ValueError("factual draft cases must have unique IDs and complete source evidence")
    r18_ids = {row["qid"] for row in existing}
    supplemental_ids = {row["qid"] for row in rows + factual_rows}
    if r18_ids.intersection(supplemental_ids):
        raise ValueError("supplemental draft IDs overlap the historical cohort")
    if len(rows) + len(factual_rows) != 30:
        raise ValueError("supplemental benchmark must contain 20 temporal and 10 factual rows")
    kept_existing, excluded_existing_ids = _trim_historical_cohort(
        existing, binding["selection"]["group_by_qid"])
    _attach_historical_gold_claims(kept_existing)
    combined = kept_existing + rows + factual_rows
    if len(combined) != 300:
        raise ValueError(f"combined benchmark candidate must contain 300 rows, got {len(combined)}")
    groups = connected_groups([{
        "qid": row["qid"],
        "question": row["question"],
        "source_group": row.get("source_group", ""),
        "paraphrase_group": row.get("paraphrase_group", ""),
    } for row in combined])
    group_sizes = Counter(groups.values())
    group_splits: dict[str, set[str]] = {}
    for row in combined:
        group_splits.setdefault(groups[row["qid"]], set()).add(row["split"])
    cross_split_groups = sorted(
        group for group, splits in group_splits.items() if len(splits) > 1
    )
    combined_ids_sha256 = hashlib.sha256(
        "\n".join(sorted(row["qid"] for row in combined)).encode("utf-8")
    ).hexdigest()
    category_predicates = {
        "single_hop_fact": lambda row: (
            row.get("answerable") is True
            and not set(row.get("tags", []))
            & {"table", "calculation", "multi_hop", "prerequisite", "temporal", "comparison"}
        ),
        "table_or_calculation": lambda row: bool(
            set(row.get("tags", [])) & {"table", "calculation"}
        ),
        "prerequisite_or_multi_hop": lambda row: bool(
            set(row.get("tags", [])) & {"prerequisite", "multi_hop"}
        ),
        "temporal_or_comparison": lambda row: bool(
            set(row.get("tags", [])) & {"temporal", "comparison"}
        ),
        "unanswerable_or_adversarial": lambda row: (
            row.get("answerable") is False or "adversarial" in row.get("tags", [])
        ),
    }
    category_coverage = {
        name: {
            "count": sum(predicate(row) for row in combined),
            "by_split": {
                split: sum(predicate(row) for row in combined if row["split"] == split)
                for split in ("test", "holdout")
            },
            "definition": {
                "single_hop_fact": "answerable; not tagged table/calculation/multi_hop/prerequisite/temporal/comparison",
                "table_or_calculation": "tagged table or calculation",
                "prerequisite_or_multi_hop": "tagged prerequisite or multi_hop",
                "temporal_or_comparison": "tagged temporal or comparison",
                "unanswerable_or_adversarial": "unanswerable or tagged adversarial",
            }[name],
        }
        for name, predicate in category_predicates.items()
    }
    missing_query_categories = sorted(
        name for name, metrics in category_coverage.items() if metrics["count"] == 0
    )
    report = {
        "schema_version": 1,
        "phase": 8,
        "candidate_version": "phase8-r18-plus-temporal-and-factual-review-draft-v4",
        "status": "draft_pending_owner_review_and_provider_exposure_audit",
        "gate_eligible": False,
        "benchmark": {
            "rows_if_combined": len(combined),
            "combined_selected_ids_sha256": combined_ids_sha256,
            "combined_candidate": {
                "path": "evaluation/phase8/benchmark_candidate_v4.jsonl",
                "rows": len(combined),
                "file_sha256": jsonl_sha256(combined),
                "owner_review": "pending",
                "frozen": False,
            },
            "excluded_historical_qids": excluded_existing_ids,
            "excluded_historical_qids_sha256": hashlib.sha256(
                "\n".join(excluded_existing_ids).encode("utf-8")).hexdigest(),
            "historical_cohort": {
                "path": "data/benchmark/phase7_review_cycles/phase7-release-20261004-r18/human_retrieval.jsonl",
                "source_sha256": binding["review"]["dataset_sha256"],
                "selected_ids_sha256": binding["selection"]["selected_ids_sha256"],
                "source_selected_rows": len(existing),
                "rows_in_combined_candidate": len(kept_existing),
                "source_selected_split_counts": binding["selection"]["split_counts"],
                "split_counts_in_combined_candidate": dict(sorted(Counter(row["split"] for row in kept_existing).items())),
                "prior_phase7_exposure": True,
                "fresh_validation": False,
            },
            "supplemental_draft": {
                "path": "evaluation/phase8/temporal_comparison_review_draft_v4.jsonl",
                "rows": len(rows),
                "file_sha256": jsonl_sha256(rows),
                "sha256": hashlib.sha256("\n".join(
                    json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows
                ).encode("utf-8")).hexdigest(),
                "split_counts": dict(sorted(Counter(row["split"] for row in rows).items())),
                "source_pdf": "data/corpus/university/uet_program_adjustments_2021.pdf",
                "source_pdf_sha256": SOURCE_SHA256,
                "tags": dict(sorted(Counter(tag for row in rows for tag in row["tags"]).items())),
                "owner_review": "pending",
                "exposure_audit": exposure,
            },
            "factual_supplemental_draft": {
                "path": "evaluation/phase8/single_hop_fact_review_draft_v4.jsonl",
                "rows": len(factual_rows),
                "file_sha256": jsonl_sha256(factual_rows),
                "split_counts": dict(sorted(Counter(row["split"] for row in factual_rows).items())),
                "source_files": sorted({row["source_document_sha256"] for row in factual_rows}),
                "owner_review": "pending",
                "source_previously_indexed": True,
                "provider_egress_logs_audited": False,
                "fresh_validation": False,
            },
            "combined_split_counts_if_adopted": dict(sorted(Counter(row["split"] for row in combined).items())),
            "query_type_coverage_if_combined": category_coverage,
            "missing_required_query_categories": missing_query_categories,
        },
        "connected_groups_if_combined": {
            "count": len(group_sizes),
            "largest_group_size": max(group_sizes.values(), default=0),
            "cross_split_group_count": len(cross_split_groups),
            "cross_split_groups": cross_split_groups,
        },
        "freeze_decision": "not_frozen_review_and_exposure_audit_required",
        "phase8_exit_blockers": [
            "supplemental_draft_requires_owner_review",
            "source_exposure_is_historical_or_provider_logs_unavailable; no_fresh_holdout_claim",
            "answer_citation_groundedness_and_answer_abstention_not_measured",
            "historical_cohort_is_not_fresh_validation",
        ],
    }
    if cross_split_groups:
        report["phase8_exit_blockers"].append("connected_groups_leak_across_splits")
    if missing_query_categories:
        report["phase8_exit_blockers"].append("required_query_type_coverage_incomplete")
    return rows, factual_rows, combined, report


def render_review_packet(temporal_rows: list[dict], factual_rows: list[dict], report: dict, *,
                        temporal_sha256: str, factual_sha256: str) -> str:
    exposure = report["benchmark"]["supplemental_draft"]["exposure_audit"]
    rows = temporal_rows + factual_rows
    lines = [
        "# Phase 8 supplemental benchmark owner review",
        "",
        "**Status: OWNER REVIEW REQUIRED. This packet is not approved or frozen.**",
        "",
        f"- Temporal draft JSONL SHA-256: `{temporal_sha256}`",
        f"- Factual draft JSONL SHA-256: `{factual_sha256}`",
        f"- Exact combined benchmark JSONL SHA-256: `{report['benchmark']['combined_candidate']['file_sha256']}`",
        f"- Source PDF SHA-256 values: `{', '.join(sorted({row['source_document_sha256'] for row in rows}))}`",
        f"- Combined 300-row qid-set SHA-256: `{report['benchmark']['combined_selected_ids_sha256']}`",
        f"- Connected groups / largest / cross-split: `{report['connected_groups_if_combined']['count']}` / `{report['connected_groups_if_combined']['largest_group_size']}` / `{report['connected_groups_if_combined']['cross_split_group_count']}`",
        f"- Query type counts: `{json.dumps({name: values['count'] for name, values in report['benchmark']['query_type_coverage_if_combined'].items()}, sort_keys=True)}`",
        f"- Missing required query types: `{', '.join(report['benchmark']['missing_required_query_categories']) or 'none'}`",
        f"- Historical exact-code overlap in temporal draft: {exposure['correction_facts_with_any_prior_code_overlap']}/{exposure['correction_fact_count']} facts.",
        "- Both source PDFs were previously indexed; provider egress logs are not audited. Do not call this fresh validation.",
        "- Review each question, answer, and evidence row. Mark exactly one decision per row.",
        "",
    ]
    for index, row in enumerate(rows, 1):
        evidence = row["gold_claims"][0]["evidence"][0]
        claim = row["gold_claims"][0]
        quote = evidence["quote"].replace("|", "\\|").replace("\n", " ")
        question = row["question"].replace("|", "\\|").replace("\n", " ")
        lines.extend([
            f"## {index:02d}. `{row['qid']}`",
            "",
            f"- Type: `{'temporal/comparison' if 'temporal' in row['tags'] else 'single-hop factual'}`; split: `{row['split']}`",
            f"- Question: {question}",
            f"- Expected answer: `{row['gold_answer']}`",
            f"- Gold claim: {claim['text']}",
            f"- Evidence: `{evidence['doc_id']}` page {evidence['page']}, range `{evidence.get('page_range', [evidence['page'], evidence['page']])}`, chunk `{evidence['chunk_id']}`",
            f"- Source row: {quote}",
            "- Decision: [ ] Accept  [ ] Reject",
            "- Reviewer note:",
            "",
        ])
    lines.extend([
        "## Review disposition",
        "",
        "- Reviewer identity:",
        "- Reviewed combined benchmark JSONL SHA-256 (must match above):",
        f"- All {len(rows)} rows reviewed: [ ]",
        "- Source exposure classification acknowledged: [ ]",
        "- Overall decision: [ ] Accept for regression benchmark  [ ] Reject",
        "- Signature/date:",
        "",
        "Approval here does not claim fresh validation; provider egress logs remain outside the retained-file exposure scan.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    temporal_rows, factual_rows, combined_rows, report = build()
    temporal_text = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in temporal_rows)
    factual_text = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in factual_rows)
    combined_text = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in combined_rows)
    temporal_bytes = _generated_bytes(JSONL_OUTPUT, temporal_text)
    factual_bytes = _generated_bytes(FACTUAL_JSONL_OUTPUT, factual_text)
    combined_bytes = _generated_bytes(COMBINED_JSONL_OUTPUT, combined_text)
    report["benchmark"]["combined_candidate"]["file_sha256"] = hashlib.sha256(
        combined_bytes).hexdigest()
    report["benchmark"]["supplemental_draft"]["file_sha256"] = hashlib.sha256(
        temporal_bytes).hexdigest()
    report["benchmark"]["factual_supplemental_draft"]["file_sha256"] = hashlib.sha256(
        factual_bytes).hexdigest()
    report_text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    review_text = render_review_packet(temporal_rows, factual_rows, report,
        temporal_sha256=report["benchmark"]["supplemental_draft"]["file_sha256"],
        factual_sha256=report["benchmark"]["factual_supplemental_draft"]["file_sha256"])
    _write_generated_outputs([
        (JSONL_OUTPUT, temporal_bytes), (FACTUAL_JSONL_OUTPUT, factual_bytes),
        (COMBINED_JSONL_OUTPUT, combined_bytes),
        (REPORT_OUTPUT, _generated_bytes(REPORT_OUTPUT, report_text)),
        (REVIEW_PACKET_OUTPUT, _generated_bytes(REVIEW_PACKET_OUTPUT, review_text)),
    ])
    audit = report["benchmark"]["supplemental_draft"]["exposure_audit"]
    print(json.dumps({"status": report["status"], "gate_eligible": report["gate_eligible"],
                      "temporal_rows": len(temporal_rows), "factual_rows": len(factual_rows),
                      "combined_rows": report["benchmark"]["rows_if_combined"],
                      "combined_split_counts": report["benchmark"]["combined_split_counts_if_adopted"],
                      "combined_selected_ids_sha256": report["benchmark"]["combined_selected_ids_sha256"],
                      "historical_code_overlap": f"{audit['correction_facts_with_any_prior_code_overlap']}/{audit['correction_fact_count']}",
                      "query_type_coverage": {name: values["count"] for name, values in
                                              report["benchmark"]["query_type_coverage_if_combined"].items()},
                      "missing_query_categories": report["benchmark"]["missing_required_query_categories"],
                      "connected_groups": report["connected_groups_if_combined"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
