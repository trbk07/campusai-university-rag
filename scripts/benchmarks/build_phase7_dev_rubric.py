"""Reproduce source-grounded dev claims without opening held-out or model outputs.

Manual claim decisions are attributable analyst review under standing owner
authorization. Structured claims are replayed against physical source rows.
Historical negative labels without mechanical absence proofs remain disclosed
as inherited reviews, not newly completed corpus-wide semantic absence audits.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from campusai.rag.context import benchmark_retrieval_request
from evaluation.benchmarks.dev_inheritance import rows_at
from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence
from evaluation.benchmarks.human_benchmark_intake import digest_record
from evaluation.benchmarks.owner_generation import curriculum_facts, corpus_absence_proof, render_generated_question
from evaluation.benchmarks.source_course_generation import validate_spec, render_question
from evaluation.benchmarks.source_course_rows import source_course_rows
from evaluation.common.release_artifacts import read_json, sha256, write_json

BASE = Path("data/benchmark/phase7_dev_gold_revision_20261007")
INDEX = Path(".tmp/phase7-curated-source-20261005-v2/index")
CURRICULUM_TEMPLATES = {
    "curriculum_combined": (
        "Find {course} in the partnership curriculum and report its semester and credits.",
        "For {course}, give both the semester placement and credit total in the VNU-UET/MAI curriculum.",
        "The joint MAI study plan lists {course}; what term and number of credits does it show?",
        "What semester and credit value are recorded for {course} in the VNU-UET-MAI table?"),
    "curriculum_credits": (
        "According to the MAI partnership curriculum, state the number of credits for {course}.",
        "Find {course} in the VNU-UET-MAI study plan and report its credit count.",
        "In the VNU-UET/MAI curriculum, how many credits are assigned to {course}?",
        "What credit value does the joint MAI program list for the subject {course}?"),
    "curriculum_semester": (
        "According to the partnership curriculum, when is {course} taught? Give the semester.",
        "In which semester is {course} scheduled in the joint VNU-UET/MAI plan?",
        "Locate {course} in the MAI curriculum table and give its semester number.",
        "Which term does the VNU-UET-MAI study plan assign to {course}?"),
}
NEGATIVE_TEMPLATES = (
    "According to the available academic documents, how many credits does {code} carry?",
    "Can the provided records establish when course {code} is taught? Give its semester if available.",
    "Do the available university sources specify a credit value for {code}? State that value.",
    "Does the indexed curriculum state a title for course code {code}? If so, give it.",
    "Find the program term associated with subject {code} in the supplied university records.",
    "Look up {code} across the supplied study plans and state its listed subject title.",
    "Search the university materials for {code}. Which semester is it assigned to?",
    "The student has code {code}; report the credit count shown in the indexed documents.",
    "Use the indexed source documents to identify the semester number for {code}.",
    "What academic program includes the course identified as {code}, according to these files?",
    "What credit total is listed for course {code}?",
    "Which course name appears beside code {code} in the frozen curriculum corpus?",
)


def curriculum_claims(row, fact):
    """Only score fields requested by the template, not every expected_claim field."""
    kind = row["source_validation"]["kind"]
    fields = {"curriculum_credits": ("credits",), "curriculum_semester": ("semester",),
              "curriculum_combined": ("credits", "semester")}[kind]
    return [{"field": field, "value": fact[field], "course_name": fact["name"],
             "evidence": [{key: fact[key] for key in ("doc_id", "chunk_id", "page")}],
             "source_cells_sha256": fact["cells_sha256"]} for field in fields]


def build():
    manifest = read_json(BASE / "packet/manifest.json")
    for name, digest in manifest["outputs"].items():
        if sha256(BASE / "packet" / name) != digest:
            raise ValueError("dev revision bytes changed")
    if sha256(INDEX / "manifest.json") != manifest["index_sha256"]:
        raise ValueError("physical index changed")
    manual = read_json(BASE / "manual_rubric_decisions.json")
    authored = {}
    for group in manual["groups"]:
        for number in group["qids"]:
            qid = f"human-candidate-{number:04d}"
            if qid in authored or not group["claims"]:
                raise ValueError("duplicate/empty manual rubric")
            authored[qid] = group["claims"]
    if set(authored) != {f"human-candidate-{i:04d}" for i in range(46, 156)}:
        raise ValueError("manual rubric coverage changed")
    partial = read_json(BASE / "packet/rubric.partial.json")
    rows = rows_at(BASE / "packet/human_retrieval_dev.jsonl")
    evidence = frozen_evidence(INDEX)
    documents = read_json(INDEX / "manifest.json")["documents"]
    curricula = {digest_record(fact) for doc in documents for fact in curriculum_facts(evidence, document_id=doc)}
    course_rows = {digest_record(fact) for fact in source_course_rows(evidence)}
    claims, reviews, modes = {}, {}, Counter()
    for row in rows:
        if row["split"] != "dev" or row["release_eligible"]:
            raise ValueError("rubric must remain dev-only and release-ineligible")
        qid = row["qid"]
        refs = row["gold_evidence"]
        for ref in refs:
            source = evidence[ref["doc_id"], ref["chunk_id"]]
            if source["page"] != ref["page"] or ref["doc_id"] not in row["doc_ids"]:
                raise ValueError("gold source/scope mismatch")
        spec = row.get("source_validation", {})
        kind = spec.get("kind")
        proof = None
        if qid in authored:
            value = [{"text": text, "evidence": refs} for text in authored[qid]]
            mode = "manual_source_claims_delegated_ai_review"
        elif qid in partial["claims"]:
            value = [{k: v for k, v in claim.items() if k != "claim_id"} for claim in partial["claims"][qid]]
            mode = "manual_source_course_name_credit_review"
        elif kind in {"curriculum_credits", "curriculum_semester", "curriculum_combined"}:
            facts = spec["facts"]
            if (len(facts) != 1 or digest_record(facts[0]) not in curricula
                    or row["question"] not in {text.format(course=facts[0]["name"]) for text in CURRICULUM_TEMPLATES[kind]}):
                raise ValueError("curriculum fact/question differs from frozen source")
            fact = facts[0]
            expected = [{"course_name": fact["name"], "credits": fact["credits"], "semester": fact["semester"]}]
            if row["expected_claims"] != expected:
                raise ValueError("curriculum expected claim changed")
            value = curriculum_claims(row, fact)
            mode = "source_row_template_replay_requested_fields_only"
        elif kind in {"source_course_credit", "source_course_compare", "source_course_absent_field_single"}:
            validate_spec(spec, evidence, manifest["index_sha256"], actual=course_rows)
            if render_question(spec) != row["question"]:
                raise ValueError("explicit source question changed")
            value = []
            if row["answerable"]:
                for fact in spec["facts"]:
                    value.append({"field": "credits", "value": fact["credits"], "course_code": fact["code"],
                                  "course_name": fact["name"], "evidence": [{key: fact[key] for key in ("doc_id", "chunk_id", "page")}],
                                  "source_cells_sha256": fact["cells_sha256"]})
                if kind == "source_course_compare":
                    a, b = spec["facts"]
                    value.append({"field": "credit_difference_second_minus_first", "value": b["credits"] - a["credits"],
                                  "calculation": f"{b['credits']} - {a['credits']}", "evidence": refs,
                                  "requires_all_hops": True})
            else:
                proof = spec["absence_proof"]
            mode = "explicit_source_row_and_scoped_absence_replay"
        elif kind == "corpus_absent_code":
            if (row["answerable"] or refs
                    or row["question"] not in {text.format(code=spec["missing_code"]) for text in NEGATIVE_TEMPLATES}):
                raise ValueError("negative code question/labels changed")
            # Check the full expanded index as well as the original scoped corpus.
            proof = corpus_absence_proof(spec["missing_code"], evidence, manifest["index_sha256"])
            value = []
            mode = "expanded_index_code_absence_reproved"
        elif not row["answerable"] and qid.startswith("human-candidate-"):
            if not 1 <= int(qid.rsplit("-", 1)[1]) <= 45 or refs:
                raise ValueError("unexpected inherited negative")
            value = []
            mode = "inherited_f0_negative_label_not_new_corpus_semantic_audit"
        else:
            raise ValueError(f"unreviewed rubric kind: {qid}")
        if bool(value) != row["answerable"]:
            raise ValueError("positive rubric empty or negative rubric affirmative")
        for number, claim in enumerate(value, 1):
            claim["claim_id"] = f"{qid}-c{number}"
        claims[qid] = value
        reviews[qid] = {"mode": mode, "record_sha256": digest_record(row),
                        "request_sha256": digest_record(benchmark_retrieval_request(row, documents)),
                        "question": row["question"], "answerable": row["answerable"],
                        "negative_expected_behavior": row["expected_behavior"] if not row["answerable"] else None,
                        "source_content_hashes": {ref["chunk_id"]: hashlib.sha256(evidence[ref["doc_id"], ref["chunk_id"]]["content"].encode()).hexdigest() for ref in refs},
                        "absence_proof_sha256": digest_record(proof) if proof else None}
        modes[mode] += 1
    return {"schema_version": 1, "status": "DEV_CLAIMS_SOURCE_CHECKED_NEGATIVE_LABELS_PARTLY_INHERITED",
            "release_eligible": False, "full_release_rubric_approved": False,
            "decision_analyst": "Codex AI assistant", "owner_manual_row_review_claim": False,
            "independent_human_review_claim": False, "test_or_holdout_read": False,
            "source_review_only": True, "model_outputs_read": False,
            "rows": len(rows), "positive_rows": sum(row["answerable"] for row in rows),
            "negative_rows": sum(not row["answerable"] for row in rows), "claim_count": sum(map(len, claims.values())),
            "review_modes": dict(modes), "gold_claim_ids": {qid: [part["claim_id"] for part in value] for qid, value in claims.items()},
            "claims": claims, "row_reviews": reviews,
            "bindings": {path.resolve().relative_to(Path.cwd()).as_posix(): sha256(path) for path in (BASE / "packet/manifest.json", BASE / "packet/human_retrieval_dev.jsonl",
                         BASE / "manual_rubric_decisions.json", BASE / "review_decisions.json", INDEX / "manifest.json", Path(__file__))},
            "criteria": ["Evaluate every factual answer claim and citation, including unstructured answer text.",
                         "Preserve the selected document, program, year and user's context; historical policy dates are not current policy.",
                         "Positive abstention fails answer accuracy; empty answers cannot evade denominators.",
                         "Each requested field must be complete. Extra unrequested source fields are not mandatory for recall.",
                         "Comparisons/calculations require both premises and the stated direction of subtraction.",
                         "Negative answers must abstain/clarify as specified and must not invent personal or institution-wide facts."],
            "limitations": ["45 historical human negative labels are inherited from F0; no new full-corpus semantic absence review is claimed.",
                            "Gold revisions remain dev-only and need lineage integration before any future release.",
                            "No live paired output review or S4/S5 PASS follows from a source rubric."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    report = build()
    if args.verify:
        if read_json(args.output) != report:
            raise ValueError("rubric replay mismatch")
    else:
        if args.output.exists():
            raise FileExistsError(args.output)
        write_json(args.output, report)
    print(json.dumps({key: report[key] for key in ("status", "rows", "positive_rows", "negative_rows", "claim_count", "review_modes")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
