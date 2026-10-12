"""Build/replay a source-reviewed dev-only revision; never mutate frozen inputs.

This research packet is deliberately not a release benchmark. Original authorship,
questions, groups, scopes and exposure are retained. A changed row's prior review
is not copied as approval of the new gold; the attributable source decision is
stored separately. Full benchmark/rubric acceptance remains a later operation.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from evaluation.benchmarks.dev_inheritance import rows_at
from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence
from evaluation.benchmarks.human_benchmark_intake import digest_record
from evaluation.benchmarks.source_course_rows import source_course_rows
from evaluation.common.release_artifacts import read_json, sha256
from campusai.retrieval.tokenizer_vi import source_body


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def revise_rows(rows: list[dict], review: dict, evidence: dict, facts: list[dict]):
    """Apply only explicitly reviewed replacements after source-coordinate checks."""
    if not rows or any(row.get("split") != "dev" for row in rows):
        raise ValueError("gold revision accepts dev rows only")
    by_id = {row["qid"]: row for row in rows}
    if len(by_id) != len(rows):
        raise ValueError("duplicate dev qids")
    decisions = review["decisions"]
    qids = [f"human-candidate-{part['number']:04d}" for part in decisions]
    if len(set(qids)) != len(qids) or not set(qids) <= set(by_id):
        raise ValueError("review qids must be unique and present in dev")
    revised = deepcopy(by_id)
    for row in revised.values():
        row["release_eligible"] = False
    audit, claims = [], {}
    for qid, decision in zip(qids, decisions):
        old = by_id[qid]
        code, doc = decision["code"], review["document"]
        if (old.get("answerable") is not True or old.get("doc_ids") != [doc]
                or code not in old["question"] or decision["action"] not in {"retain_gold", "replace_gold"}
                or not decision.get("reason")):
            raise ValueError("review question/scope/action mismatch")
        matching = [f for f in facts if f["doc_id"] == doc and f["code"] == code
                    and f["page"] == decision["page"] and f["table_row"] == decision["table_row"]]
        if len(matching) != 1 or matching[0]["credits"] != decision["credits"]:
            raise ValueError("reviewed source row or credit value mismatch")
        fact = matching[0]
        source = evidence[(doc, fact["chunk_id"])]
        if hashlib.sha256(source["content"].encode("utf-8")).hexdigest() != fact["source_content_sha256"]:
            raise ValueError("source content hash mismatch")
        originals = []
        for gold in old["gold_evidence"]:
            original = evidence[(gold["doc_id"], gold["chunk_id"])]
            if original["page"] != gold["page"] or gold["doc_id"] != doc:
                raise ValueError("original gold scope/page mismatch")
            originals.append({"coordinate": gold, "body": source_body(original),
                              "content_sha256": hashlib.sha256(original["content"].encode("utf-8")).hexdigest()})
        coordinate = {key: fact[key] for key in ("doc_id", "chunk_id", "page")}
        if decision["action"] == "replace_gold":
            if old["gold_evidence"] == [coordinate]:
                raise ValueError("replacement must change gold")
            revised[qid]["gold_evidence"] = [coordinate]
            # Historical approvals remain in the parent and audit, never rebound.
            revised[qid].update(review_status="pending", review_checks={}, reviewer="",
                                reviewer_role="pending", reviewed_at=None,
                                review_evidence_kind="dev_revision_source_review_sidecar")
        claims[qid] = [
            {"claim_id": qid + "-name", "course_code": code, "field": "course_name",
             "value": fact["name"], "source_name_lines": fact["name_lines"],
             "criterion": "Identify the requested course by its source name; Vietnamese name alone is sufficient. Preserve source qualifiers; translated variants may be equivalent.",
             "evidence": [coordinate]},
            {"claim_id": qid + "-credits", "course_code": code, "field": "credits",
             "value": fact["credits"], "unit": "tin_chi",
             "criterion": "Exact credits-column value for this code and selected document, not hours or a prerequisite course's credits.",
             "evidence": [coordinate]},
        ]
        audit.append({"qid": qid, "decision": decision, "parent_record_sha256": digest_record(old),
                      "revised_record_sha256": digest_record(revised[qid]), "parent_gold": originals,
                      "source_fact": fact, "new_gold": revised[qid]["gold_evidence"],
                      "prior_review": {key: old.get(key) for key in ("review_status", "reviewer", "reviewed_at")},
                      "approval_scope": "source-only dev correction and claims, not release acceptance"})
    return [revised[row["qid"]] for row in rows], audit, claims


def build(parent: Path, index: Path, decisions: Path) -> dict[str, bytes]:
    review = read_json(decisions)
    stamp = datetime.fromisoformat(review["reviewed_at"])
    if (stamp.tzinfo is None or stamp > datetime.now(timezone.utc)
            or review.get("status") != "source_reviewed_dev_only"
            or review.get("owner_manual_row_review_claim") is not False
            or review.get("independent_human_review_claim") is not False):
        raise ValueError("invalid source review identity/time/scope")
    auth_path = Path(review["authorization_path"])
    auth = read_json(auth_path)
    if not auth.get("delegated_decision_approval_statement") or auth.get("decision_analyst") != review["decision_analyst"]:
        raise ValueError("missing attributable delegated review authorization")
    if sha256(parent) != review["parent_dev_sha256"] or sha256(index / "manifest.json") != review["index_sha256"]:
        raise ValueError("parent/index differs from reviewed identity")
    rows = rows_at(parent)
    evidence = frozen_evidence(index)
    facts = source_course_rows(evidence)
    revised, audit, claims = revise_rows(rows, review, evidence, facts)
    # No model calls, outputs, primary test/holdout files or metrics are read.
    payloads = {
        "human_retrieval_dev.jsonl": b"".join((json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n").encode("utf-8") for row in revised),
        "source_review.json": encoded({"schema_version": 1, "review": review, "observations": audit}),
        "rubric.partial.json": encoded({"schema_version": 1, "status": "source_reviewed_dev_subset_only",
            "release_eligible": False, "full_rubric_complete": False, "decision_analyst": review["decision_analyst"],
            "reviewed_at": review["reviewed_at"], "gold_claim_ids": {qid: [claim["claim_id"] for claim in value] for qid, value in claims.items()},
            "claims": claims, "unreviewed_qids": [row["qid"] for row in rows if row["qid"] not in claims],
            "criteria": ["Answer both name and credit questions; cite a source that supports each factual claim.",
                         "A prerequisite-code occurrence does not establish that course's name or credits.",
                         "Source text spelling is preserved; equivalent Vietnamese names are acceptable.",
                         "No model answer or retrieval ranking was used to author these claims."]}),
    }
    manifest = {"schema_version": 1, "profile": "source_reviewed_dev_gold_revision_v1",
        "dev_only": True, "new_heldout_claim": False, "release_eligible": False,
        "parent_dev": parent.as_posix(), "parent_dev_sha256": sha256(parent),
        "index_dir": index.as_posix(), "index_sha256": sha256(index / "manifest.json"),
        "decisions_path": decisions.as_posix(), "decisions_sha256": sha256(decisions),
        "authorization_path": auth_path.as_posix(), "authorization_sha256": sha256(auth_path),
        "runner_path": Path(__file__).resolve().relative_to(Path.cwd()).as_posix(), "runner_sha256": sha256(__file__),
        "rows": len(rows), "source_reviewed_rows": len(audit), "gold_replacements": sum(part["decision"]["action"] == "replace_gold" for part in audit),
        "claims": sum(map(len, claims.values())), "source_only": True, "test_or_holdout_read": False,
        "historical_reviews_rebound": False, "parent_mutated": False,
        "outputs": {name: hashlib.sha256(value).hexdigest() for name, value in payloads.items()},
        "limitations": ["All consumed groups remain dev-only. Existing frozen benchmark and measurements are immutable.",
                        "Only 25 course-name/credit questions have an authored rubric; remaining rows are unreviewed in this revision.",
                        "Corrected rows require explicit revision-lineage integration before future release preflight; prior inheritance approval cannot be reused.",
                        "No P7-06 live pilot, P7-09 joint feasibility or release-gate PASS is implied."]}
    payloads["manifest.json"] = encoded(manifest)
    return payloads


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-dev", type=Path, required=True)
    parser.add_argument("--index-dir", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--verify", action="store_true", help="recompute every byte without writing")
    args = parser.parse_args(argv)
    output = args.output_dir.resolve()
    for source in (args.parent_dev, args.index_dir, args.decisions):
        if source.resolve().is_relative_to(output) or output.is_relative_to(args.index_dir.resolve()):
            raise ValueError("output must be separate from input files/index")
    payloads = build(args.parent_dev, args.index_dir, args.decisions)
    if args.verify:
        for name, data in payloads.items():
            if (output / name).read_bytes() != data:
                raise ValueError(f"replay mismatch: {name}")
    else:
        output.mkdir(parents=True, exist_ok=False)
        for name, data in payloads.items():
            with (output / name).open("xb") as stream:
                stream.write(data)
    manifest = json.loads(payloads["manifest.json"])
    print(json.dumps({"status": "PASS_REPLAY" if args.verify else "DEV_REVISION_PREPARED", "rows": manifest["rows"],
                      "reviewed": manifest["source_reviewed_rows"], "replacements": manifest["gold_replacements"],
                      "release_eligible": False, "output": str(args.output_dir)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
