"""Create a fresh owner-directed benchmark cycle before any inference run."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil

from evaluation.benchmarks.connected_groups import connected_groups, normalized_question
from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence, assign_grouped_splits, validate_rows
from evaluation.benchmarks.owner_generation import course_facts, generated_row, generated_audit, load_generation
from evaluation.benchmarks.owner_review import load_confirmation
from evaluation.common.release_artifacts import read_json, sha256, write_json


def write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def create(source: Path, destination: Path, index: Path, *, pairs: int = 30) -> dict:
    if destination.exists() or not 20 <= pairs <= 100:
        raise ValueError("use an absent cycle directory and at least 20 source pairs")
    confirmation, _ = load_confirmation(source)
    old_rows = load_rows(source / "human_retrieval.jsonl")
    prior_registry = read_json(source / "phase7_exposure_registry.json")
    prior_by_qid = {r["qid"]: r for r in prior_registry["records"]}
    if (set(prior_by_qid) != {r["qid"] for r in old_rows} or prior_registry["status"] != "pass"
            or any(not str(r["status"]).startswith("known_exposed") or r["heldout_eligible"] is not False
                   for r in prior_by_qid.values())):
        raise ValueError("prior exposure must be resolved before extending the benchmark")
    history = []
    study_inventory = []
    for path in sorted(source.glob("*.jsonl")):
        history.extend({"question": r.get("question", r.get("query", "")), "qid": r.get("qid"),
                        "dataset": path.as_posix(), "dataset_sha256": sha256(path)} for r in load_rows(path))
    for path in sorted(Path(".release/reranker/studies").rglob("*.json")):
        study_inventory.append({"path": path.as_posix(), "sha256": sha256(path)})
    used_codes = set()
    for entry in history:
        used_codes.update(re.findall(r"\b[A-Z]{2,5}\s*\d{3,5}[A-Z]?\b", entry["question"].upper()))
    used_codes = {re.sub(r"\s+", "", code) for code in used_codes}
    facts_by_code = {}
    evidence = frozen_evidence(index)
    for fact in course_facts(evidence):
        if fact["code"] not in used_codes:
            facts_by_code.setdefault(fact["code"], fact)
    facts = sorted(facts_by_code.values(), key=lambda f: (f["doc_id"], f["table_row"], f["code"]))
    if len(facts) < pairs * 2:
        raise ValueError(f"only {len(facts)} unused course facts; need {pairs * 2}")
    bank = []
    for number in range(pairs):
        pair = facts[2 * number:2 * number + 2]
        family = "owner-source-pair-" + "-".join(f["code"] for f in pair)
        for variant, (kind, selected) in enumerate((("credit", pair[:1]), ("credit", pair[1:]),
                                                  ("sum", pair), ("absent_course", pair)), 1):
            spec = {"qid": f"human-ownerfresh-{number + 1:03d}-{variant}", "family": family,
                    "kind": kind, "facts": selected}
            if kind == "absent_course":
                spec["missing_code"] = f"ZZ{90000 + number}"
            bank.append(spec)
    destination.mkdir(parents=True)
    for path in source.glob("hybrid_retrieval_*.jsonl"):
        shutil.copyfile(path, destination / path.name)
    for name in ("phase7_review_policy.json", "phase7_owner_confirmation.json"):
        shutil.copyfile(source / name, destination / name)
    shutil.copytree(source / "owner_confirmed_inputs", destination / "owner_confirmed_inputs")
    write_json(destination / "owner_generated_source_bank.json", {"records": bank})
    history_path = destination / "owner_generation_history_snapshot.json"
    write_json(history_path, {"recorded_at": datetime.now(timezone.utc).isoformat(), "questions": history,
                              "studies": study_inventory, "prior_registry_sha256": sha256(source / "phase7_exposure_registry.json"),
                              "meaning": "pre-generation inventory; no inference has run on the new questions"})
    auth = {"schema_version": 1, "profile": "personal_owner_source_checked_ai",
            "owner_identity": confirmation["owner_identity"], "approval_source": "project_owner_chat_instruction",
            "approval_statement": "t duyệt hết nên bạn cứ nhập tên tác giải là t",
            "generation_statement": "nếu k có thì tự tạo đi, t cho phép",
            "recorded_at": datetime.now(timezone.utc).isoformat(), "independent_human_review_claim": False,
            "review_policy_sha256": sha256(destination / "phase7_review_policy.json"),
            "index_sha256": sha256(index / "manifest.json"),
            "source_bank_sha256": sha256(destination / "owner_generated_source_bank.json"),
            "history_snapshot_sha256": sha256(history_path)}
    write_json(destination / "phase7_generation_authorization.json", auth)
    _, generated = load_generation(destination, index)
    fresh = list(generated.values())
    # A template family is identified by its disjoint source facts. Reject
    # lexical overlap with any prior question before allocating fresh splits.
    for row in fresh:
        tokens = set(normalized_question(row["question"]).split())
        for entry in history:
            old_tokens = set(normalized_question(entry["question"]).split())
            if tokens == old_tokens or (min(len(tokens), len(old_tokens)) >= 6
                    and len(tokens & old_tokens) / len(tokens | old_tokens) >= .85):
                raise ValueError("new question overlaps historical dataset: " + row["qid"])
    rows = [{**row, "split": "dev"} for row in old_rows] + fresh
    groups = connected_groups(rows)
    registry_rows = []
    for row in rows:
        qid = row["qid"]
        if qid in prior_by_qid:
            entry = {**prior_by_qid[qid], "connected_group": groups[qid]}
        else:
            entry = {"qid": qid, "connected_group": groups[qid], "status": "unexposed_audited",
                     "heldout_eligible": True, "authorship_inferred": False,
                     "history_audit": {"complete": True, "archive_reference": history_path.as_posix(),
                                       "archive_sha256": sha256(history_path),
                                       "study_manifest_sha256": sha256(history_path),
                                       "basis": "new source facts and question bytes checked against pre-generation inventory"}}
        registry_rows.append(entry)
    rows = assign_grouped_splits(rows, {r["qid"]: r for r in registry_rows})
    write_rows(destination / "human_retrieval.jsonl", rows)
    write_rows(destination / "human_candidate_pool.jsonl", rows)
    write_json(destination / "human_candidate_lineage.json", {"schema_version": 3,
               "dataset_sha256": sha256(destination / "human_candidate_pool.jsonl"),
               "index_sha256": sha256(index / "manifest.json"), "connected_groups": groups,
               "qid_mapping": [{"qid": r["qid"], "candidate_id": r["candidate_id"],
                                "source_record_id": r.get("source_record_id", r["qid"])} for r in rows]})
    write_json(destination / "phase7_exposure_registry.json", {"schema_version": 2, "status": "pass",
               "dataset_sha256": sha256(destination / "human_candidate_pool.jsonl"),
               "lineage_sha256": sha256(destination / "human_candidate_lineage.json"),
               "index_sha256": sha256(index / "manifest.json"), "records": registry_rows,
               "counts": dict(Counter(r["status"] for r in registry_rows))})
    audit = load_rows(source / "human_retrieval_review_audit.jsonl") + generated_audit(auth, generated)
    write_rows(destination / "human_retrieval_review_audit.jsonl", audit)
    report = validate_rows(rows, evidence, owner_identity=confirmation["owner_identity"], generated_records=generated)
    write_json(destination / "owner_generation_preflight.json", report)
    if report["status"] != "pass":
        raise ValueError("fresh cycle validation failed: " + ", ".join(report["errors"]))
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("data/benchmark"))
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/hybrid-index"))
    parser.add_argument("--pairs", type=int, default=30)
    args = parser.parse_args(argv)
    print(json.dumps(create(args.source, args.destination, args.index_dir, pairs=args.pairs), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
