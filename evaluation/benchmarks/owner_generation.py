"""Source checked questions generated under a personal owner's standing approval.

The author attribution identifies the commissioning owner. AI origin remains
explicit, and this profile never claims independent human authorship/review.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from evaluation.common.release_artifacts import read_json, sha256
from evaluation.benchmarks.human_benchmark_intake import digest_record, REVIEW_CHECKS


def plain(value: str) -> str:
    return " ".join("".join(c for c in unicodedata.normalize("NFD", value).lower()
                            if not unicodedata.combining(c)).split())


def course_facts(evidence: dict) -> list[dict]:
    """Accept explicit course/code/credit headers, never infer credits from hours."""
    facts = []
    for (doc, chunk), item in sorted(evidence.items()):
        start = item["content"].find('{"headers"')
        if start < 0:
            continue
        table = json.loads(item["content"][start:])
        headers = [plain(h) for h in table["headers"]]
        credit_columns = [i for i, h in enumerate(headers) if h == "so tin chi"]
        code_columns = [i for i, h in enumerate(headers) if h in {"ma hoc phan", "ma so hoc phan"}]
        if len(credit_columns) != 1 or len(code_columns) != 1:
            continue
        credit_col, code_col = credit_columns[0], code_columns[0]
        for number, cells in enumerate(table["rows"]):
            if len(cells) <= max(credit_col, code_col + 1):
                continue
            code = re.sub(r"\s+", "", cells[code_col])
            if (not re.fullmatch(r"[A-Z]{2,5}\d{3,5}[A-Z]?", code)
                    or not cells[credit_col].isdigit() or not 0 < int(cells[credit_col]) < 30):
                continue
            name = " ".join(cells[code_col + 1].split())
            if len(name) < 5:
                continue
            facts.append({"doc_id": doc, "chunk_id": chunk, "page": item["page"],
                          "table_row": number, "code": code, "name": name,
                          "credits": int(cells[credit_col]), "cells_sha256": digest_record({"cells": cells})})
    return facts


def curriculum_facts(evidence: dict, *, document_id: str) -> list[dict]:
    """Extract unique semester/credit rows from a frozen curriculum table."""
    candidates = {}
    for (doc, chunk), item in sorted(evidence.items()):
        if doc != document_id or item.get("content_type") != "table":
            continue
        start = item["content"].find('{"headers"')
        if start < 0:
            continue
        table = json.loads(item["content"][start:])
        headers = [plain(value) for value in table.get("headers", [])]
        if not {"discipline", "credits"} <= set(headers):
            continue
        name_col, credits_col = headers.index("discipline"), headers.index("credits")
        semester = None
        for number, cells in enumerate(table.get("rows", [])):
            marker = re.search(r"\bsemester\s*(\d+)\b", " ".join(map(str, cells)), re.IGNORECASE)
            if marker:
                semester = int(marker.group(1))
                continue
            if max(name_col, credits_col) >= len(cells) or semester is None:
                continue
            name = " ".join(str(cells[name_col]).split())
            credit_text = str(cells[credits_col]).strip()
            if (not name or len(name) < 5 or not credit_text.isdigit()
                    or not 0 < int(credit_text) < 30
                    or plain(name) in {"compulsory subjects", "elective subjects", "credits per semester"}):
                continue
            fact = {"doc_id": doc, "chunk_id": chunk, "page": item["page"],
                    "table_row": number, "name": name, "credits": int(credit_text),
                    "semester": semester, "cells_sha256": digest_record({"cells": cells})}
            key = (doc, plain(name), semester, int(credit_text))
            candidates.setdefault(key, fact)
    return [candidates[key] for key in sorted(candidates)]


def source_course_text_facts(evidence: dict) -> list[dict]:
    """Extract code/title/credit triples from text chunks that preserve table rows."""
    code_line = re.compile(r"^([A-Z]{2,5}\s*\d{3,5}[A-Z]?)[\s.:,]*(.*)$", re.IGNORECASE)
    facts = {}
    for (doc, chunk), item in sorted(evidence.items()):
        content = item.get("content", "")
        if item.get("content_type") != "text" or "Document type: curriculum" not in content:
            continue
        body = content.split("]", 1)[-1]
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        for offset, line in enumerate(lines):
            match = code_line.fullmatch(line)
            if not match:
                continue
            code = re.sub(r"\s+", "", match.group(1)).upper()
            tail = match.group(2).strip()
            title_parts = []
            credits = int(tail) if tail.isdigit() else None
            if tail and credits is None:
                title_parts.append(tail)
            for following in lines[offset + 1:]:
                if credits is not None or code_line.fullmatch(following):
                    break
                if re.fullmatch(r"\d{1,2}", following):
                    credits = int(following)
                    break
                title_parts.append(following)
            name = " ".join(" ".join(title_parts).split())
            if not name or len(name) < 6 or credits is None or not 0 < credits <= 12:
                continue
            if re.match(r"^(?:[IVX]+\.?\s*)?(?:kh[oố]i ki[eế]n th[uứ]c|group|section)\b", plain(name)):
                continue
            fact = {"doc_id": doc, "chunk_id": chunk, "page": item["page"],
                    "code": code, "name": name, "credits": credits,
                    "source_content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                    "row_sha256": digest_record({"code": code, "name": name, "credits": credits})}
            facts.setdefault((doc, chunk, code), fact)
    return [facts[key] for key in sorted(facts)]


def corpus_absence_proof(code: str, evidence: dict, index_sha256: str) -> dict:
    """Bind a negative code claim to every frozen document and indexed chunk."""
    chunks = []
    for (doc, chunk), item in sorted(evidence.items()):
        chunks.append({"doc_id": doc, "chunk_id": chunk, "page": item["page"],
                       "content_sha256": hashlib.sha256(item["content"].encode("utf-8")).hexdigest()})
    corpus_text = "".join(item["content"] for item in evidence.values()).upper()
    if re.sub(r"\s+", "", code.upper()) in re.sub(r"\s+", "", corpus_text):
        raise ValueError("negative course code is present in the frozen corpus")
    return {"method": "all_indexed_chunks_exact_code_absence_v1", "missing_code": code,
            "index_sha256": index_sha256, "document_ids": sorted({doc for doc, _ in evidence}),
            "chunk_count": len(chunks), "chunk_manifest_sha256": digest_record(chunks)}


def render_question(kind: str, facts: list[dict], missing_code: str | None = None) -> str:
    if kind == "credit":
        f = facts[0]
        return f"Môn {f['name']} ({f['code']}) trong bảng này có mấy tín chỉ?"
    a, b = facts
    if kind == "sum":
        return (f"Mình định học {a['name']} ({a['code']}) cùng {b['name']} ({b['code']}). "
                "Theo hai dòng học phần trong tài liệu, tổng số tín chỉ của chúng là bao nhiêu?")
    if kind == "absent_course":
        return (f"Tài liệu có {a['name']} ({a['code']}) và {b['name']} ({b['code']}); "
                f"còn học phần mang mã {missing_code} thì được ghi bao nhiêu tín chỉ?")
    raise ValueError("unsupported source question kind")


def render_generated_question(spec: dict) -> str:
    kind, facts = spec["kind"], spec["facts"]
    from .source_course_generation import KINDS, render_question as source_question
    if kind in KINDS:
        return source_question(spec)
    if kind in {"credit", "sum", "absent_course"}:
        return render_question(kind, facts, spec.get("missing_code"))
    if kind in {"curriculum_credits", "curriculum_semester", "curriculum_combined"}:
        f = facts[0]
        variant = int(spec.get("template_variant", 0))
        if kind == "curriculum_credits":
            prompts = (
                f"In the VNU-UET/MAI curriculum, how many credits are assigned to {f['name']}?",
                f"What credit value does the joint MAI program list for the subject {f['name']}?",
                f"Find {f['name']} in the VNU-UET-MAI study plan and report its credit count.",
                f"According to the MAI partnership curriculum, state the number of credits for {f['name']}.",
            )
            return prompts[variant % len(prompts)]
        if kind == "curriculum_semester":
            prompts = (
                f"In which semester is {f['name']} scheduled in the joint VNU-UET/MAI plan?",
                f"Locate {f['name']} in the MAI curriculum table and give its semester number.",
                f"Which term does the VNU-UET-MAI study plan assign to {f['name']}?",
                f"According to the partnership curriculum, when is {f['name']} taught? Give the semester.",
            )
            return prompts[variant % len(prompts)]
        prompts = (
            f"For {f['name']}, give both the semester placement and credit total in the VNU-UET/MAI curriculum.",
            f"The joint MAI study plan lists {f['name']}; what term and number of credits does it show?",
            f"Find {f['name']} in the partnership curriculum and report its semester and credits.",
            f"What semester and credit value are recorded for {f['name']} in the VNU-UET-MAI table?",
        )
        return prompts[variant % len(prompts)]
    if kind == "corpus_absent_code":
        code = spec["missing_code"]
        prompts = (
            f"What credit total is listed for course {code}?",
            f"Search the university materials for {code}. Which semester is it assigned to?",
            f"Does the indexed curriculum state a title for course code {code}? If so, give it.",
            f"According to the available academic documents, how many credits does {code} carry?",
            f"Find the program term associated with subject {code} in the supplied university records.",
            f"Which course name appears beside code {code} in the frozen curriculum corpus?",
            f"The student has code {code}; report the credit count shown in the indexed documents.",
            f"Can the provided records establish when course {code} is taught? Give its semester if available.",
            f"Look up {code} across the supplied study plans and state its listed subject title.",
            f"What academic program includes the course identified as {code}, according to these files?",
            f"Do the available university sources specify a credit value for {code}? State that value.",
            f"Use the indexed source documents to identify the semester number for {code}.",
        )
        return prompts[int(spec.get("template_variant", 0)) % len(prompts)]
    raise ValueError("unsupported source question kind")


def generated_row(spec: dict, authorization: dict) -> dict:
    facts, kind = spec["facts"], spec["kind"]
    from .source_course_generation import KINDS, generated_row as source_row
    if kind in KINDS:
        return source_row(spec, authorization)
    answerable = kind not in {"absent_course", "corpus_absent_code"}
    gold = list({(f["doc_id"], f["chunk_id"]): {k: f[k] for k in ("doc_id", "chunk_id", "page")}
                 for f in facts}.values()) if answerable else []
    scope = spec.get("document_ids") or sorted({f["doc_id"] for f in facts})
    owner = authorization["owner_identity"]
    expected_claims = []
    if answerable and kind in {"credit", "sum"}:
        expected_claims = [{"course_code": f["code"], "credits": f["credits"]} for f in facts]
        if kind == "sum":
            expected_claims.append({"total_credits": sum(f["credits"] for f in facts)})
    elif answerable and kind.startswith("curriculum_"):
        fact = facts[0]
        expected_claims = [{"course_name": fact["name"], "credits": fact["credits"],
                            "semester": fact["semester"]}]
    return {"schema_version": 3, "qid": spec["qid"], "candidate_id": spec["qid"].removeprefix("human-"),
            "question": render_generated_question(spec),
            "split": "dev", "author": owner, "author_type": "ai",
            "authoring_mode": "owner_directed_ai_generation", "generator": "Codex",
            "question_source": "owner_directed_generation", "evidence_source": "frozen_pdf",
            "reviewer": owner, "reviewer_role": "project_owner", "review_status": "approved",
            "reviewed_at": authorization["recorded_at"], "review_checks": {k: True for k in REVIEW_CHECKS},
            "review_evidence_kind": "owner_directed_generation", "release_eligible": True,
            "generation_authorization_sha256": digest_record(authorization),
            "paraphrase_group": spec["family"], "source_group": spec["family"],
            "doc_ids": sorted(set(scope)), "filters": {},
            "answerable": answerable, "gold_evidence": gold,
            "expected_behavior": "answer_grounded" if answerable else "abstain",
            "difficulty": "hard" if kind in {"sum", "curriculum_combined"} else "easy",
            "tags": (["natural", "table", "exact_code", "multi_hop", "hard"] if kind == "sum" else
                     ["natural", "table", "hard", "multi_hop"] if kind == "curriculum_combined" else
                     ["natural", "table", "easy", "curriculum"] if kind in {"curriculum_credits", "curriculum_semester"} else
                     ["natural", "exact_code", "negative", "abstention", "easy"]),
            "source_validation": {key: value for key, value in spec.items() if key != "template_variant"},
            "expected_claims": expected_claims}


def validate_generation(authorization: dict, bank: list[dict], evidence: dict, owner: str,
                        *, index_sha256: str | None = None) -> dict[str, dict]:
    stamp = datetime.fromisoformat(authorization["recorded_at"])
    if (authorization.get("profile") != "personal_owner_source_checked_ai"
            or authorization.get("owner_identity") != owner
            or authorization.get("approval_source") != "project_owner_chat_instruction"
            or authorization.get("approval_statement") != "t duyệt hết nên bạn cứ nhập tên tác giải là t"
            or authorization.get("generation_statement") != "nếu k có thì tự tạo đi, t cho phép"
            or authorization.get("independent_human_review_claim") is not False
            or stamp.tzinfo is None or stamp > datetime.now(timezone.utc)):
        raise ValueError("invalid personal generation authorization")
    actual_facts = {digest_record(f) for f in course_facts(evidence)}
    curriculum_doc = authorization.get("curriculum_document_id", "")
    actual_curriculum = {digest_record(f) for f in curriculum_facts(evidence, document_id=curriculum_doc)}
    expected = {}
    from .source_course_generation import KINDS, validate_spec
    from .source_course_rows import source_course_rows
    actual_source = {digest_record(f) for f in source_course_rows(evidence)} if any(
        spec.get('kind') in KINDS for spec in bank) else set()
    for spec in bank:
        facts, kind = spec["facts"], spec["kind"]
        if kind in KINDS:
            validate_spec(spec, evidence, index_sha256 or authorization.get('index_sha256', ''),
                          actual=actual_source)
            if authorization.get('dev_only') is True and spec['dev_only'] is not True:
                raise ValueError('dev-only authorization cannot generate heldout-eligible questions')
            row = generated_row(spec, authorization)
            if row['qid'] in expected:
                raise ValueError('duplicate generated qid')
            expected[row['qid']] = row
            continue
        course_kind = kind in {"credit", "sum", "absent_course"}
        curriculum_kind = kind in {"curriculum_credits", "curriculum_semester", "curriculum_combined"}
        absent_kind = kind == "corpus_absent_code"
        if not (course_kind or curriculum_kind or absent_kind):
            raise ValueError("generated fact differs from frozen source")
        if course_kind and (len(facts) != (1 if kind == "credit" else 2)
                or any(digest_record(f) not in actual_facts for f in facts)
                or len({f["code"] for f in facts}) != len(facts)):
            raise ValueError("generated fact differs from frozen source")
        if curriculum_kind and (len(facts) != 1 or digest_record(facts[0]) not in actual_curriculum):
            raise ValueError("curriculum fact differs from frozen source")
        if kind == "absent_course":
            code = spec.get("missing_code", "")
            corpus = "".join(item["content"] for item in evidence.values()).upper()
            if not re.fullmatch(r"ZZ\d{5}", code) or code in re.sub(r"\s+", "", corpus):
                raise ValueError("negative course is not absent from corpus")
        if absent_kind:
            code = spec.get("missing_code", "")
            proof = corpus_absence_proof(code, evidence, index_sha256 or authorization.get("index_sha256", ""))
            if (not re.fullmatch(r"[A-Z]{2,5}\d{4,5}[A-Z]?", code)
                    or spec.get("absence_proof") != proof):
                raise ValueError("negative course absence proof is invalid")
        row = generated_row(spec, authorization)
        if row["qid"] in expected:
            raise ValueError("duplicate generated qid")
        expected[row["qid"]] = row
    if not expected:
        raise ValueError("empty generation bank")
    return expected


def load_generation(benchmark_dir: Path, index_dir: Path) -> tuple[dict | None, dict[str, dict]]:
    path = benchmark_dir / "phase7_generation_authorization.json"
    if not path.exists():
        return None, {}
    from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence
    policy = read_json(benchmark_dir / "phase7_review_policy.json")
    auth = read_json(path)
    if any(key.startswith('_validated_') for key in auth):
        raise ValueError('internal generation validation metadata cannot be supplied by an artifact')
    if (policy.get("project_scope") != "single_owner_personal_project"
            or policy.get("owner_self_review_allowed") is not True
            or auth.get("review_policy_sha256") != sha256(benchmark_dir / "phase7_review_policy.json")
            or auth.get("index_sha256") != sha256(index_dir / "manifest.json")):
        raise ValueError("generation authorization policy/index binding changed")
    bank_path = benchmark_dir / "owner_generated_source_bank.json"
    if auth.get("source_bank_sha256") != sha256(bank_path):
        raise ValueError("generated source bank changed")
    history_path = benchmark_dir / "owner_generation_history_snapshot.json"
    if auth.get("history_snapshot_sha256") != sha256(history_path):
        raise ValueError("pre-generation history snapshot changed")
    history = read_json(history_path)
    if datetime.fromisoformat(history["recorded_at"]) > datetime.fromisoformat(auth["recorded_at"]):
        raise ValueError("history must precede generated question approval")
    evidence = frozen_evidence(index_dir)
    expected = validate_generation(auth, read_json(bank_path)["records"], evidence, policy["owner_identity"],
                                   index_sha256=sha256(index_dir / "manifest.json"))
    from evaluation.benchmarks.connected_groups import normalized_question
    historical_tokens = None
    for row in expected.values():
        if row.get('source_validation', {}).get('dev_only') is True:
            # These validated source questions explicitly make no novelty
            # claim. Both export validation and review audit enforce dev-only.
            continue
        tokens = set(normalized_question(row["question"]).split())
        if historical_tokens is None:
            # Repeated archived occurrences do not change the exact/Jaccard
            # overlap predicate. Normalize each unique question only once.
            historical_tokens = {
                frozenset(normalized_question(question).split())
                for question in {entry["question"] for entry in history["questions"]}
            }
        for other in historical_tokens:
            if tokens == other or (min(len(tokens), len(other)) >= 6
                                  and len(tokens & other) / len(tokens | other) >= .85):
                raise ValueError("generated question overlaps historical inputs")
    from .dev_evidence_extension import load_dev_extension
    dev_auth, dev_expected = load_dev_extension(benchmark_dir, index_dir, policy, evidence)
    if set(expected) & set(dev_expected):
        raise ValueError('dev extension collides with existing generated qids')
    if dev_auth:
        auth = {**auth, '_validated_dev_authorization': dev_auth}
        expected.update(dev_expected)
    from .dev_inheritance import load_dev_inheritance
    inherited = load_dev_inheritance(benchmark_dir, index_dir, policy, auth)
    if inherited:
        if set(expected) & set(inherited['rows']):
            raise ValueError('inherited dev records collide with new generated qids')
        auth = {**auth, '_validated_dev_inheritance': inherited}
        expected.update(inherited['rows'])
    return auth, expected


def generated_audit(auth: dict, expected: dict[str, dict]) -> list[dict]:
    inherited = auth.get('_validated_dev_inheritance')
    inherited_qids = set(inherited['rows']) & set(expected) if inherited else set()
    if any(expected[qid] != inherited['rows'][qid] for qid in inherited_qids):
        raise ValueError('inherited export differs from validated dev origin')
    audit = [{"qid": qid, "review_evidence_kind": "owner_directed_generation",
             "generation_authorization_sha256": row['generation_authorization_sha256'],
             "exported_record_sha256": digest_record(row)} for qid, row in expected.items() if qid not in inherited_qids]
    if inherited_qids:
        from .dev_inheritance import inheritance_audit
        audit.extend(item for item in inheritance_audit(inherited) if item['qid'] in inherited_qids)
    return audit
