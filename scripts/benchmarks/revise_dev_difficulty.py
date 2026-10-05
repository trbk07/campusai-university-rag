"""Create a new cycle for source-proved dev metadata corrections only."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from evaluation.benchmarks.difficulty_audit import audit_dev_difficulty, apply_dev_difficulty, revision_errors
from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence, exposure_registry_errors
from evaluation.benchmarks.owner_review import load_confirmation, confirm_existing, confirmed_row, confirmation_audit
from evaluation.benchmarks.owner_generation import load_generation, generated_audit
from evaluation.common.release_artifacts import read_json, sha256, write_json
from evaluation.reranker.supplemental_gates import review_audit_errors
from scripts.benchmarks.create_owner_source_benchmark import load_rows

APPROVAL = "t duyệt hết nên bạn cứ nhập tên tác giải là t"


def write_rows(path: Path, rows: list[dict]) -> None:
    # The freeze publisher uses canonical LF bytes on every operating system.
    path.write_bytes("".join(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False)
                             + "\n" for row in rows).encode("utf-8"))


def create(source: Path, destination: Path, index: Path) -> dict:
    """Retain the parent's inputs and heldout bytes; never claim new exposure."""
    if destination.exists():
        raise ValueError("use an absent cycle directory; frozen inputs cannot be overwritten")
    parent, original = load_confirmation(source)
    original_qids = {row["qid"] for row in original}
    if parent.get("dev_metadata_revision"):
        raise ValueError("a revision must start from the retained original owner inputs")
    regression = {split: load_rows(source / f"hybrid_retrieval_{split}.jsonl")
                  for split in ("dev", "test", "holdout")}
    relevant = {row.get("source_record_id") for row in original}
    records = {row["qid"]: row for rows in regression.values() for row in rows if row["qid"] in relevant}
    old_rows = load_rows(source / "human_retrieval.jsonl")
    by_qid = {row["qid"]: row for row in old_rows}
    dev_qids = {row["qid"] for row in load_rows(source / "human_retrieval_dev.jsonl")}
    if any(by_qid[row["qid"]]["split"] != "dev" or row["qid"] not in dev_qids for row in original):
        raise ValueError("owner input contains a heldout row")
    evidence = frozen_evidence(index)
    audit = audit_dev_difficulty(original, records, evidence, allocated_dev_qids=original_qids)
    if not audit["changes"]:
        raise ValueError("no source-proved dev corrections")
    corrected = apply_dev_difficulty(original, audit)
    destination.mkdir(parents=True)
    # Copy each original artifact before updating its explicitly named successor.
    for path in sorted(source.iterdir()):
        if path.is_file() and path.name != "phase7_owner_confirmation.json":
            shutil.copyfile(path, destination / path.name)
    shutil.copytree(source / "owner_confirmed_inputs", destination / "owner_confirmed_inputs")
    shutil.copyfile(source / "phase7_owner_confirmation.json", destination / "parent_owner_confirmation.json")
    parent_dev = [{**confirmed_row(row, parent), "split": "dev"} for row in original]
    if {row["qid"] for row in parent_dev} != original_qids:
        raise ValueError("parent dev allocation does not cover owner-confirmed inputs")
    write_rows(destination / "parent_human_retrieval_dev.jsonl", parent_dev)
    corrected_path = destination / "owner_dev_metadata_corrected.jsonl"
    write_rows(corrected_path, corrected)
    confirmation = confirm_existing(corrected_path, destination, owner_statement=parent["statement"])
    confirmation["dev_metadata_revision"] = {
        "schema_version": 1, "owner_identity": parent["owner_identity"],
        "approval_source": "project_owner_standing_chat_instruction", "approval_statement": APPROVAL,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "index_sha256": sha256(index / "manifest.json"),
        "original_source_snapshot": parent["source_snapshot"], "original_dev_records": original,
        "allocated_dev_qids": sorted(original_qids),
        "original_dev_allocation": {"path": "parent_human_retrieval_dev.jsonl",
                                    "sha256": sha256(destination / "parent_human_retrieval_dev.jsonl")},
        "source_regression_sha256": {split: sha256(destination / f"hybrid_retrieval_{split}.jsonl") for split in regression},
        "source_regression_records": records, "audit": audit,
        "parent_confirmation_sha256": sha256(destination / "parent_owner_confirmation.json"),
        "review_method": "source audit under the owner's standing approval; no independent review claimed"}
    write_json(destination / "phase7_owner_confirmation.json", confirmation)
    replacements = {row["qid"]: {**confirmed_row(row, confirmation), "split": "dev"} for row in corrected}
    rows = [replacements.get(row["qid"], row) for row in old_rows]
    write_rows(destination / "human_retrieval.jsonl", rows)
    write_rows(destination / "human_candidate_pool.jsonl", rows)
    write_rows(destination / "human_retrieval_dev.jsonl", [row for row in rows if row["split"] == "dev"])
    auth, generated = load_generation(destination, index)
    review = confirmation_audit(confirmation, corrected) + generated_audit(auth, generated)
    write_rows(destination / "human_retrieval_review_audit.jsonl", review)
    lineage = read_json(destination / "human_candidate_lineage.json")
    lineage["dataset_sha256"] = sha256(destination / "human_candidate_pool.jsonl")
    write_json(destination / "human_candidate_lineage.json", lineage)
    registry = read_json(destination / "phase7_exposure_registry.json")
    registry.update(dataset_sha256=lineage["dataset_sha256"],
                    lineage_sha256=sha256(destination / "human_candidate_lineage.json"))
    write_json(destination / "phase7_exposure_registry.json", registry)
    errors = revision_errors(confirmation, corrected, evidence, sha256(index / "manifest.json"))
    errors += review_audit_errors(rows, review, index, owner_identity=parent["owner_identity"],
                                 owner_confirmation=confirmation, confirmed_sources=corrected,
                                 generation_authorization=auth, generated_records=generated)
    errors += exposure_registry_errors(rows, registry, source_pool=destination / "human_candidate_pool.jsonl",
                                       source_lineage=destination / "human_candidate_lineage.json",
                                       index_manifest=index / "manifest.json")
    # Reopen all physical provenance bindings, rather than trusting in-memory objects.
    load_confirmation(destination)
    heldout = {}
    for split in ("test", "holdout"):
        name = f"human_retrieval_{split}.jsonl"
        if (source / name).read_bytes() != (destination / name).read_bytes():
            errors.append("heldout_bytes_changed:" + split)
        heldout[split] = sha256(destination / name)
    report = {"schema_version": 1, "status": "fail" if errors else "pass", "errors": errors,
              "parent_benchmark_dir": source.as_posix(), "parent_dataset_sha256": sha256(source / "human_retrieval.jsonl"),
              "dev_changed_fields": ["difficulty", "tags"], "dev_corrections": len(audit["changes"]),
              "new_heldout_claim": False, "heldout_reused_unchanged": True, "heldout_sha256": heldout,
              "audit": audit, "review_authority": "project_owner_standing_chat_instruction"}
    write_json(destination / "dev_metadata_revision_preflight.json", report)
    if errors:
        raise ValueError("dev metadata revision rejected: " + ", ".join(errors))
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/hybrid-index"))
    args = parser.parse_args(argv)
    report = create(args.source, args.destination, args.index_dir)
    print(f"Dev corrections: {report['dev_corrections']}; heldout bytes unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
