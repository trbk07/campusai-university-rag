"""Preserve Phase 5 gold and prepare an unapproved repair/review packet.

Source fidelity, generation provenance and independent annotation are separate
facts. This tool creates no reviewer identities, signatures or approval records.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import csv
import hashlib
import json
from pathlib import Path
import re

from evaluation.benchmarks.benchmark_schema import question_template, RELEASE_SPLIT_MINIMUMS
from evaluation.benchmarks.families import intent_family, record_families
from evaluation.common.release_artifacts import source_identity, write_json


def stable_hash(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode()).hexdigest()


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def grouped_split(rows: list[dict]) -> tuple[list[dict], dict]:
    """Connected families stay together even when release balance is infeasible."""
    rows = sorted(deepcopy(rows), key=lambda row: row["id"])
    parent = list(range(len(rows)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    seen = {}
    for index, row in enumerate(rows):
        for family in record_families(row):
            if family in seen:
                parent[find(index)] = find(seen[family])
            else:
                seen[family] = index
    components = defaultdict(list)
    for index, row in enumerate(rows):
        components[find(index)].append(row)
    ordered = sorted(components.values(), key=lambda group: (-len(group), group[0]["id"]))
    counts = Counter()
    candidate = []
    groups = []
    for group in ordered:
        # Stable largest-deficit allocation; infeasible components are never
        # split, deleted or assigned different labels to manufacture balance.
        split = max(RELEASE_SPLIT_MINIMUMS, key=lambda name: (
            RELEASE_SPLIT_MINIMUMS[name] - counts[name], name))
        group_id = stable_hash([row["id"] for row in group])
        groups.append({"family_id": group_id, "split": split,
                       "records": len(group), "ids": [row["id"] for row in group]})
        for row in group:
            row.update(legacy_split=row["split"], legacy_review_status=row.get("review_status"),
                       legacy_annotator_id=row.get("annotator_id"),
                       legacy_template_group=row.get("template_group"),
                       split=split, family_id=group_id,
                       template_group=stable_hash(question_template(row["question"])),
                       review_status="review_required", exposure_status="previously_exposed",
                       fresh_holdout=False, official_evaluation_eligible=False)
            candidate.append(row)
        counts[split] += len(group)
    assigned = defaultdict(set)
    for row in candidate:
        for family in record_families(row):
            assigned[family].add(row["split"])
    leakage = [list(family) for family, splits in sorted(assigned.items()) if len(splits) > 1]
    distributions = {}
    for split in RELEASE_SPLIT_MINIMUMS:
        subset = [row for row in candidate if row["split"] == split]
        distributions[split] = {"records": len(subset),
            "answerable": sum(bool(row["answerable"]) for row in subset),
            "abstention": sum(not bool(row["answerable"]) for row in subset),
            "categories": dict(Counter(row["category"] for row in subset)),
            "difficulty": dict(Counter(row.get("difficulty", "not_recorded") for row in subset)),
            "temporal": sum(row["category"] == "temporal/stale_source" for row in subset)}
    feasible = all(counts[split] >= minimum for split, minimum in RELEASE_SPLIT_MINIMUMS.items())
    return sorted(candidate, key=lambda row: row["id"]), {
        "policy": "connected-source-template-intent-paraphrase-v1", "seed": "stable-id-order-v1",
        "records_preserved": len(candidate), "connected_components": groups,
        "cross_split_family_leakage": len(leakage), "leaking_families": leakage,
        "split_distributions": distributions, "minimums_feasible": feasible,
        "status": "CANDIDATE_REVIEW_REQUIRED" if feasible else "BLOCKED_INSEPARABLE_FAMILIES",
        "fresh_holdout_restored": False, "exposure_history_preserved": True,
        "independent_review_complete": False,
    }


def temporal_source_review(rows: list[dict], corpus: Path) -> list[dict]:
    import pymupdf
    manifest = json.loads((corpus / "manifest.json").read_text(encoding="utf-8"))
    docs = {item["sha256"]: item for item in manifest["documents"]}
    result = []
    for row in rows:
        if row["category"] != "temporal/stale_source":
            continue
        flagged = "current academic year" in row["question"].casefold() and not any(
            re.search(r"\b(?:19|20)\d{2}\b", claim["text"]) for claim in row["gold_claims"])
        sources = []
        for claim in row["gold_claims"]:
            for evidence in claim["evidence"]:
                info = docs.get(evidence["doc_id"], {})
                path = corpus / info.get("filename", "missing.pdf")
                matches = path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == evidence["doc_id"]
                text = ""
                clauses = []
                if matches:
                    with pymupdf.open(path) as pdf:
                        if 1 <= evidence["page"] <= len(pdf):
                            text = pdf[evidence["page"] - 1].get_text()
                        for page_number, page in enumerate(pdf, 1):
                            page_text = page.get_text()
                            for match in re.finditer(r"[^\n]*(?:hiệu lực|áp dụng từ|effective from|effective date)[^\n]*",
                                                     page_text, re.I):
                                clauses.append({"page": page_number, "text": match[0]})
                sources.append({"document": info.get("filename"), **evidence,
                    "source_hash_verified": matches, "source_page_text": text,
                    "declared_document_year": info.get("academic_year"),
                    "potential_effective_date_clauses": clauses,
                    "verified_effective_date": None,
                    "effective_date_status": "review_required_not_inferred_from_document_year"})
        result.append({"id": row["id"], "question": row["question"], "current_gold": row["gold_claims"],
            "sources": sources, "flagged_among_21": flagged, "review_status": "review_required",
            "reason": ("Gold states a title/topic but does not establish current-year applicability."
                       if flagged else "Date/version wording requires source and applicability review."),
            "proposed_correction": ("Consider unsupported_claim abstention unless an authoritative applicability clause establishes the requested year."
                                    if flagged else "Confirm that the stated year is a version, issue date or effective period before approval."),
            "correction_approved": False})
    return result


def prepare(root: Path, benchmark: Path, draft: Path, corpus: Path, output: Path) -> dict:
    if output.exists() and any(output.iterdir()):
        raise ValueError("review packet exists; use a new revision to preserve reviewer edits")
    rows, drafts = load_rows(benchmark), {row["id"]: row for row in load_rows(draft)}
    provenance = []
    templates = defaultdict(list)
    for row in rows:
        prior = drafts.get(row["id"])
        normalized = deepcopy(row["gold_claims"])
        for claim in normalized:
            for evidence in claim.get("evidence", []):
                evidence.pop("page_range", None)
        provenance.append({"id": row["id"], "gold_sha256": stable_hash(row["gold_claims"]),
            "source_benchmark_record_sha256": stable_hash(row),
            "draft_record_sha256": stable_hash(prior) if prior else None,
            "source_group": row.get("source_group"),
            "evidence": deepcopy([evidence for claim in row["gold_claims"] for evidence in claim.get("evidence", [])]),
            "gold_generation": {"kind": "ai_generated_owner_reported", "provider": "Gemini",
                                "raw_generation_evidence_located": False},
            "draft_record_present": prior is not None,
            "draft_gold_match_except_page_range": prior is not None and normalized == prior.get("gold_claims"),
            "legacy_review_status": row.get("review_status"), "legacy_annotator_id": row.get("annotator_id"),
            "review_evidence_located": [], "human_verified": False, "independently_reviewed": False,
            "review_status": "review_required", "historical_review_claim_invalidated": False,
            "declared_review_classification": "claimed_reviewed_not_independently_proven"})
        templates[question_template(row["question"])].append(row)
    leakage = [{"template": template, "splits": sorted({row["split"] for row in group}),
                "ids": [row["id"] for row in group], "intent_family": intent_family(group[0]["question"]),
                "resolution": "connected-family allocation; original splits preserved in legacy_split"}
               for template, group in sorted(templates.items()) if len({row["split"] for row in group}) > 1]
    candidate, allocation = grouped_split(rows)
    temporal = temporal_source_review(rows, corpus)
    assert {row["id"]: row["gold_claims"] for row in candidate} == {row["id"]: row["gold_claims"] for row in rows}
    output.mkdir(parents=True, exist_ok=True)
    for name, values in (("provenance.jsonl", provenance), ("grouped-candidate.jsonl", candidate)):
        (output / name).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in values), encoding="utf-8")
    write_json(output / "template-leakage.json", {"families": leakage, "count": len(leakage)})
    write_json(output / "grouped-split.json", allocation)
    write_json(output / "temporal-review.json", {"records": temporal, "count": len(temporal),
                                               "flagged_count": sum(row["flagged_among_21"] for row in temporal)})
    fields = ["id", "question", "current_gold", "document_page_evidence", "effective_date", "reason",
              "proposed_correction", "review_status"]
    with (output / "temporal-21-review.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in temporal:
            if row["flagged_among_21"]:
                writer.writerow({"id": row["id"], "question": row["question"],
                    "current_gold": json.dumps(row["current_gold"], ensure_ascii=False),
                    "document_page_evidence": json.dumps(row["sources"], ensure_ascii=False),
                    "effective_date": "UNKNOWN - human review required", "reason": row["reason"],
                    "proposed_correction": row["proposed_correction"], "review_status": row["review_status"]})
    report = {"status": "REVIEW_REQUIRED_RELEASE_BLOCKED", "records_preserved_for_reuse": len(rows),
        "official_independently_reviewed_records_proven": 0, "provenance_records": len(provenance),
        "template_leakage_families_original": len(leakage), "grouped_split": allocation,
        "temporal_records": len(temporal), "temporal_review_required": len(temporal),
        "temporal_flagged_21": sum(row["flagged_among_21"] for row in temporal),
        "original_gold_modified": False, "review_approvals_created": 0, "fresh_holdout_required": True,
        "benchmark_sha256": hashlib.sha256(benchmark.read_bytes()).hexdigest(),
        "draft_sha256": hashlib.sha256(draft.read_bytes()).hexdigest(), "source_identity": source_identity(root),
        "review_process_source": {"path": "scripts/benchmarks/review_benchmark.py",
                                  "sha256": hashlib.sha256((root / "scripts/benchmarks/review_benchmark.py").read_bytes()).hexdigest(),
                                  "finding": "Script checks quote coordinates and accepts caller annotator_id; it does not supply independent signed row decisions."},
        "owner_provenance_statement": "Owner reports Gemini-generated gold followed by checking; independent-review evidence remains unproven."}
    write_json(output / "manifest.json", report)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=Path("data/benchmark/grounding_reviewed.jsonl"))
    parser.add_argument("--draft", type=Path, default=Path("data/benchmark/grounding_draft.jsonl"))
    parser.add_argument("--corpus", type=Path, default=Path("data/corpus/university"))
    parser.add_argument("--output", type=Path, default=Path("evaluation/results/phase5-repair-20261016"))
    args = parser.parse_args()
    report = prepare(Path.cwd(), args.benchmark, args.draft, args.corpus, args.output)
    print(json.dumps({key: report[key] for key in ("status", "records_preserved_for_reuse",
                     "official_independently_reviewed_records_proven", "template_leakage_families_original",
                     "temporal_records", "temporal_flagged_21")}, indent=2))


if __name__ == "__main__":
    main()
