"""Prepare a new Phase 7 release benchmark without reusing measured heldout rows."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil

from evaluation.benchmarks.connected_groups import connected_groups, normalized_question
from evaluation.benchmarks.freeze_human_benchmark import (
    assign_grouped_splits, frozen_evidence, validate_rows,
)
from evaluation.benchmarks.owner_generation import (
    corpus_absence_proof, curriculum_facts, generated_audit, generated_row, load_generation,
)
from evaluation.benchmarks.owner_review import load_confirmation
from evaluation.common.release_artifacts import read_json, sha256, write_json

ROOT = Path(__file__).resolve().parents[2]
CURRICULUM_DOC = "667de97d9bc8cf4749eaac42a0f1ea3418c80544836708a576d545ecf5635e13"


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
                                   for row in rows), encoding="utf-8")


def overlaps_history(question: str, history: list[dict]) -> bool:
    tokens = set(normalized_question(question).split())
    for item in history:
        other = set(normalized_question(item.get("question", "")).split())
        if tokens == other or (min(len(tokens), len(other)) >= 6
                               and len(tokens & other) / len(tokens | other) >= .85):
            return True
    return False


def source_history(source: Path) -> tuple[list[dict], list[dict]]:
    questions, datasets = [], []
    for path in sorted(source.glob("*.jsonl")):
        digest = sha256(path)
        datasets.append({"path": path.as_posix(), "sha256": digest})
        for row in load_rows(path):
            query = row.get("question", row.get("query", ""))
            if query:
                questions.append({"question": query, "qid": row.get("qid"),
                                  "dataset": path.as_posix(), "dataset_sha256": digest})
    return questions, datasets


def fresh_curriculum_specs(evidence: dict, history: list[dict], index_sha: str,
                           *, target: int = 27, negative_count: int = 300) -> list[dict]:
    facts = curriculum_facts(evidence, document_id=CURRICULUM_DOC)
    selected = []
    seen_course_names = set()
    for fact in facts:
        normalized_name = normalized_question(fact["name"])
        if normalized_name in seen_course_names:
            continue
        family = "fresh-mai-course-" + sha256_bytes(
            f"{fact['name']}|{fact['semester']}|{fact['credits']}".encode("utf-8"))[:18]
        candidate = []
        serial = len(selected) + 1
        for kind, slug in (("curriculum_credits", "credits"),
                           ("curriculum_semester", "semester"),
                           ("curriculum_combined", "combined")):
            for variant in range(4):
                candidate.append({
                    "qid": f"human-p7r18-curriculum-{serial:03d}-{slug}-{variant + 1}",
                    "family": family, "kind": kind, "facts": [fact],
                    "template_variant": variant,
                })
        if any(overlaps_history(rendered_question(spec), history) for spec in candidate):
            continue
        selected.append((fact, candidate))
        seen_course_names.add(normalized_name)
        if len(selected) >= target:
            break
    if len(selected) < target:
        raise ValueError(f"only {len(selected)} unused curriculum facts; need {target}")
    specs = [spec for _, group in selected for spec in group]
    docs = sorted({doc for doc, _ in evidence})
    corpus_text = "".join(row["content"] for row in evidence.values()).upper()
    compact_corpus = re.sub(r"\s+", "", corpus_text)
    used_codes = {re.sub(r"\s+", "", token.upper())
                  for item in history for token in re.findall(r"\b[A-Z]{2,5}\s*\d{4,5}[A-Z]?\b",
                                                               item["question"].upper())}
    next_number = 91000
    while sum(spec["kind"] == "corpus_absent_code" for spec in specs) < negative_count:
        code = f"ZZ{next_number:05d}"
        next_number += 1
        if code in compact_corpus or code in used_codes:
            continue
        serial = sum(spec["kind"] == "corpus_absent_code" for spec in specs) + 1
        spec = {"qid": f"human-p7r18-negative-{serial:04d}", "family": f"fresh-absent-course-{code}",
                "kind": "corpus_absent_code", "facts": [], "missing_code": code,
                "document_ids": docs, "template_variant": (serial - 1) % 12,
                "absence_proof": corpus_absence_proof(code, evidence, index_sha)}
        if overlaps_history(rendered_question(spec), history):
            continue
        specs.append(spec)
        used_codes.add(code)
    return specs


def rendered_question(spec: dict) -> str:
    # The production renderer is also the validation renderer, so history checks
    # use the exact bytes that will be frozen.
    from evaluation.benchmarks.owner_generation import render_generated_question
    return render_generated_question(spec)


def sha256_bytes(payload: bytes) -> str:
    import hashlib
    return hashlib.sha256(payload).hexdigest()


def measured_dev_qids(candidate: dict, previous_dev: Path, index_sha: str) -> set[str]:
    """A failed measurement still exposes its exactly paired development inputs."""
    if candidate.get("status") not in {"pass", "conditional"} or candidate.get("index_sha256") != index_sha:
        raise ValueError("prior M2 evidence does not bind the index or a completed measurement")
    part = candidate["splits"]["human_dev"]
    rows = load_rows(previous_dev)
    pairs = part["caps"]["40"]["per_query"]
    qids = [row["qid"] for row in rows]
    observed = [pair["qid"] for pair in pairs]
    if (part.get("benchmark_sha256") != sha256(previous_dev)
            or len(qids) != len(set(qids)) or len(observed) != len(set(observed))
            or len(qids) != len(observed) or set(qids) != set(observed)
            or any(not isinstance(pair.get("candidates"), list) or len(pair["candidates"]) > 40 for pair in pairs)):
        raise ValueError("prior M2 evidence does not pair the exact development inputs")
    return set(observed)


def create(source: Path, destination: Path, index: Path, prior_results: Path,
           *, positive_families: int = 27, negative_count: int = 300) -> dict:
    if destination.exists():
        raise ValueError("use an absent benchmark cycle directory")
    config = read_json(ROOT / "configs/phase7_release_cycle.json")
    if Path(config["benchmark_dir"]).resolve() != source.resolve():
        raise ValueError("source must be the currently active benchmark cycle")
    confirmation, confirmed_sources = load_confirmation(source)
    source_rows = load_rows(source / "human_retrieval.jsonl")
    old_rows = [row for row in source_rows if row.get("author_type") == "human"]
    if (len(old_rows) < 150 or {row["qid"] for row in old_rows} !=
            set(confirmation.get("source_record_sha256", {}))):
        raise ValueError("source must contain the complete owner-confirmed human question set")
    owner_id = confirmation["owner_identity"]
    evidence = frozen_evidence(index)
    index_sha = sha256(index / "manifest.json")

    # M2 must have consumed every old human item. These are therefore retained
    # only as training/development material in the successor cycle.
    candidate = read_json(prior_results / "candidate_coverage.json")
    previous_dev = source / "human_retrieval_dev.jsonl"
    measured_qids = measured_dev_qids(candidate, previous_dev, index_sha)
    human_qids = {row["qid"] for row in old_rows}
    if not human_qids <= measured_qids:
        raise ValueError("prior M2 evidence does not prove all inherited human rows were exposed")

    history, source_datasets = source_history(source)
    studies = [{"path": path.as_posix(), "sha256": sha256(path)}
               for path in sorted((ROOT / ".release/reranker/studies").rglob("*.json"))]
    prior_evidence = []
    for filename in ("candidate_coverage.json", "hard_query_route_calibration.json",
                     "hard_query_route_confusion.json", "reranker_route_freeze.json"):
        path = prior_results / filename
        if path.is_file():
            prior_evidence.append({"path": path.as_posix(), "sha256": sha256(path)})
    evidence_history = {"recorded_at": datetime.now(timezone.utc).isoformat(),
                        "questions": history, "datasets": source_datasets, "studies": studies,
                        "prior_evaluation_evidence": prior_evidence,
                        "prior_candidate_coverage_sha256": sha256(prior_results / "candidate_coverage.json"),
                        "meaning": "historical inventory captured before generating successor-cycle questions"}

    specs = fresh_curriculum_specs(evidence, history, index_sha,
                                   target=positive_families, negative_count=negative_count)
    destination.mkdir(parents=True)
    for name in ("phase7_review_policy.json", "phase7_owner_confirmation.json"):
        shutil.copyfile(source / name, destination / name)
    for name in ("dev_metadata_revision_preflight.json", "owner_dev_metadata_corrected.jsonl",
                 "parent_human_retrieval_dev.jsonl", "parent_owner_confirmation.json",
                 "phase7_evidence_calibration_dev.jsonl",
                 "phase7_evidence_calibration_dev.manifest.json"):
        path = source / name
        if path.is_file():
            shutil.copyfile(path, destination / name)
    shutil.copytree(source / "owner_confirmed_inputs", destination / "owner_confirmed_inputs")
    for path in source.glob("hybrid_retrieval_*.jsonl"):
        shutil.copyfile(path, destination / path.name)

    write_json(destination / "owner_generated_source_bank.json", {"records": specs})
    write_json(destination / "owner_generation_history_snapshot.json", evidence_history)
    bank_path = destination / "owner_generated_source_bank.json"
    history_path = destination / "owner_generation_history_snapshot.json"
    authorization = {
        "schema_version": 1, "profile": "personal_owner_source_checked_ai",
        "owner_identity": owner_id, "approval_source": "project_owner_chat_instruction",
        "approval_statement": "t duy\u1ec7t h\u1ebft n\u00ean b\u1ea1n c\u1ee9 nh\u1eadp t\u00ean t\u00e1c gi\u1ea3i l\u00e0 t",
        "generation_statement": "n\u1ebfu k c\u00f3 th\u00ec t\u1ef1 t\u1ea1o \u0111i, t cho ph\u00e9p",
        "recorded_at": datetime.now(timezone.utc).isoformat(), "independent_human_review_claim": False,
        "review_policy_sha256": sha256(destination / "phase7_review_policy.json"),
        "index_sha256": index_sha, "curriculum_document_id": CURRICULUM_DOC,
        "source_bank_sha256": sha256(bank_path), "history_snapshot_sha256": sha256(history_path),
        "disclosure": "New records are owner-directed AI drafts, source checked against the frozen index, and approved under the owner's standing instruction; no independent review is claimed.",
    }
    write_json(destination / "phase7_generation_authorization.json", authorization)

    _, generated = load_generation(destination, index)
    rows = [{**row, "split": "dev"} for row in old_rows] + list(generated.values())
    groups = connected_groups(rows)
    prior_registry = read_json(source / "phase7_exposure_registry.json")
    prior_by_qid = {entry["qid"]: entry for entry in prior_registry["records"]}
    if not human_qids <= set(prior_by_qid):
        raise ValueError("prior exposure registry lacks inherited question IDs")
    registry_rows = []
    history_digest = sha256(history_path)
    m2_report_sha = sha256(prior_results / "candidate_coverage.json")
    for row in rows:
        qid = row["qid"]
        if qid in human_qids:
            registry_rows.append({"qid": qid, "connected_group": groups[qid],
                                  "status": "known_exposed_prior_dev", "heldout_eligible": False,
                                  "authorship_inferred": False,
                                  "history_audit": {"complete": True,
                                      "archive_reference": (prior_results / "candidate_coverage.json").as_posix(),
                                      "archive_sha256": m2_report_sha,
                                      "study_manifest_sha256": m2_report_sha,
                                      "basis": "qid appears in completed M2 human_dev candidate observations; acceptance failure also consumes inputs; retained in successor dev"}})
        else:
            registry_rows.append({"qid": qid, "connected_group": groups[qid],
                                  "status": "unexposed_audited", "heldout_eligible": True,
                                  "authorship_inferred": False,
                                  "history_audit": {"complete": True,
                                      "archive_reference": history_path.as_posix(),
                                      "archive_sha256": history_digest,
                                      "study_manifest_sha256": history_digest,
                                      "basis": "question and source fact were created after complete pre-generation inventory and checked against historical questions"}})
    rows = assign_grouped_splits(rows, {row["qid"]: item for row, item in zip(rows, registry_rows)})
    write_rows(destination / "human_retrieval.jsonl", rows)
    write_rows(destination / "human_candidate_pool.jsonl", rows)
    write_json(destination / "human_candidate_lineage.json", {
        "schema_version": 3, "dataset_sha256": sha256(destination / "human_candidate_pool.jsonl"),
        "index_sha256": index_sha, "connected_groups": groups,
        "qid_mapping": [{"qid": row["qid"], "candidate_id": row["candidate_id"],
                         "source_record_id": row.get("source_record_id", row["qid"])} for row in rows]})
    write_json(destination / "phase7_exposure_registry.json", {
        "schema_version": 2, "status": "pass",
        "dataset_sha256": sha256(destination / "human_candidate_pool.jsonl"),
        "lineage_sha256": sha256(destination / "human_candidate_lineage.json"),
        "index_sha256": index_sha, "records": registry_rows,
        "counts": dict(Counter(row["status"] for row in registry_rows))})

    old_audit = load_rows(source / "human_retrieval_review_audit.jsonl")
    old_audit_by_qid = {item["qid"]: item for item in old_audit}
    if not human_qids <= set(old_audit_by_qid):
        raise ValueError("prior owner review audit lacks inherited question IDs")
    audit = [old_audit_by_qid[qid] for qid in sorted(human_qids)] + generated_audit(authorization, generated)
    write_rows(destination / "human_retrieval_review_audit.jsonl", audit)
    report = validate_rows(rows, evidence, [item for path in destination.glob("hybrid_retrieval_*.jsonl")
                                            for item in load_rows(path)],
                           owner_identity=owner_id, generated_records=generated)
    report.update(dataset_sha256=sha256(destination / "human_retrieval.jsonl"),
                  index_sha256=index_sha, review_policy_sha256=sha256(destination / "phase7_review_policy.json"),
                  grouped_split=report.get("grouped_split"),
                  owner_generated_records=len(generated),
                  fresh_positive_families=positive_families, fresh_negative_groups=negative_count,
                  inherited_owner_rows=len(old_rows))
    write_json(destination / "owner_generation_preflight.json", report)
    if report.get("status") != "pass":
        raise ValueError("new cycle failed preflight: " + ", ".join(report.get("errors", [])))
    generated_counts = Counter((row["split"], row["answerable"], row["difficulty"]) for row in rows if row["qid"] in generated)
    return {"status": "pass", "destination": destination.as_posix(), "records": len(rows),
            "generated_records": len(generated), "inherited_dev_records": len(old_rows),
            "fresh_groups": len(set(groups[row["qid"]] for row in rows if row["qid"] in generated)),
            "split_counts": report["split_counts"], "counts": report["counts"],
            "generated_split_strata": {"|".join(map(str, key)): value for key, value in generated_counts.items()},
            "dataset_sha256": sha256(destination / "human_retrieval.jsonl"),
            "exposure_registry_sha256": sha256(destination / "phase7_exposure_registry.json")}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("data/benchmark/phase7_review_cycles/phase7-release-20261003-r11"))
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/hybrid-index"))
    parser.add_argument("--prior-results-dir", type=Path,
                        default=Path("evaluation/results/phase7-source-context-20261003-r17"))
    parser.add_argument("--positive-families", type=int, default=27)
    parser.add_argument("--negative-count", type=int, default=300)
    args = parser.parse_args(argv)
    print(json.dumps(create(args.source, args.destination, args.index_dir, args.prior_results_dir,
                            positive_families=args.positive_families,
                            negative_count=args.negative_count), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
