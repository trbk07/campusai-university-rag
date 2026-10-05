"""Validate and freeze role-reviewed human-natural dev/test/holdout.

This tool never authors questions or assigns reviewer approval. Those are
human inputs; missing review/evidence is a blocking condition, not a score.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import unicodedata
import os
import uuid
from urllib.parse import urlparse

from evaluation.common.release_artifacts import read_json, sha256, write_json
from evaluation.benchmarks.connected_groups import connected_groups



SUPPORTED_TAGS = {
    "natural", "negative", "multi_hop", "exact_code", "ambiguous", "abstention", "curriculum",
    "table", "conflict", "temporal", "out_of_scope", "hard", "easy",
    "medium", "answerable", "contextual", "contextual_followup", "typo",
    "typo_no_accent", "code_switching", "abbreviation", "colloquial",
    "lexical_mismatch", "slang", "conditional", "paraphrase", "long_noisy",
    "course_code", "prerequisite", "multi_document", "ocr_degraded", "short_meaningful",
    "unanswerable",
}
PLACEHOLDER_IDENTITIES = {"", "unknown", "placeholder", "replace_me", "tbd", "reviewer-a", "reviewer-b", "independent reviewer"}
SPLIT_TARGETS = {"dev": .60, "test": .20, "holdout": .20}


def _identity(value) -> str:
    return value.strip().casefold() if isinstance(value, str) else ""


def _group_key(row: dict) -> str:
    """Return the stable leakage group; legacy paraphrase_group is supported."""
    values = []
    for field in ("intent_family", "query_family", "paraphrase_group", "source_group", "template_group"):
        value = row.get(field)
        if isinstance(value, str) and value.strip():
            values.append(f"{field}={value.strip().casefold()}")
    return "|".join(values) or "qid=" + str(row.get("qid", ""))


def assign_grouped_splits(rows: list[dict], exposure_records: dict[str, dict] | None = None) -> list[dict]:
    """Assign connected groups deterministically, keeping exposed/unknown groups in dev."""
    groups = defaultdict(list)
    assignments = connected_groups(rows)
    for row in rows:
        groups[assignments[row["qid"]]].append(row)
    ordered = sorted(groups.items(), key=lambda item: hashlib.sha256(item[0].encode()).hexdigest())
    totals = Counter()
    result = []
    if exposure_records is None:
        fixed_dev, eligible = [], ordered
    else:
        if set(exposure_records) != {row.get("qid") for row in rows}:
            raise ValueError("exposure records must cover every benchmark qid exactly once")
        fixed_dev, eligible = [], []
        for group, members in ordered:
            histories = [exposure_records[row["qid"]] for row in members]
            audited_unexposed = all(
                item.get("status") == "unexposed_audited"
                and item.get("heldout_eligible") is True
                and isinstance(item.get("history_audit"), dict)
                and item["history_audit"].get("complete") is True
                and bool(item["history_audit"].get("archive_reference"))
                and isinstance(item["history_audit"].get("archive_sha256"), str)
                and len(item["history_audit"]["archive_sha256"]) == 64
                and bool(item["history_audit"].get("study_manifest_sha256"))
                for item in histories
            )
            (eligible if audited_unexposed else fixed_dev).append((group, members))
    for group, members in fixed_dev:
        totals["dev"] += len(members)
        result.extend({**row, "split": "dev"} for row in members)
    for group, members in eligible:
        split = min(SPLIT_TARGETS, key=lambda name: (totals[name] - SPLIT_TARGETS[name] * len(rows), name))
        totals[split] += len(members)
        result.extend({**row, "split": split} for row in members)
    return sorted(result, key=lambda row: str(row.get("qid", "")))


def exposure_registry_errors(rows: list[dict], registry: dict, *, source_pool: Path,
                             source_lineage: Path, index_manifest: Path,
                             check_splits: bool = True) -> list[str]:
    """Verify exposure provenance and keep non-audited connected groups dev-only."""
    errors = []
    try:
        pool_hash, lineage_hash, index_hash = sha256(source_pool), sha256(source_lineage), sha256(index_manifest)
        lineage = read_json(source_lineage)
        source_groups = lineage.get("connected_groups", {})
        expected_groups = connected_groups(rows)
        source_records = registry.get("records")
        if (registry.get("status") != "pass"
                or registry.get("dataset_sha256") != pool_hash
                or registry.get("lineage_sha256") != lineage_hash
                or registry.get("index_sha256") != index_hash
                or not isinstance(source_records, list)):
            errors.append("exposure_registry_incomplete_or_unbound")
            return errors
        by_qid = {entry.get("qid"): entry for entry in source_records if isinstance(entry, dict)}
        qids = {row.get("qid") for row in rows}
        if len(by_qid) != len(source_records) or set(by_qid) != qids or set(source_groups) != qids:
            return errors + ["exposure_registry_qid_coverage"]
        grouped_history = defaultdict(list)
        for row in rows:
            qid = row["qid"]
            group = expected_groups[qid]
            entry = by_qid[qid]
            if entry.get("connected_group") != group or source_groups.get(qid) != group:
                errors.append("exposure_group_binding:" + qid)
                continue
            status = entry.get("status")
            if status == "unexposed_audited":
                audit = entry.get("history_audit")
                if (entry.get("heldout_eligible") is not True or not isinstance(audit, dict)
                        or audit.get("complete") is not True or not audit.get("archive_reference")
                        or not isinstance(audit.get("archive_sha256"), str)
                        or len(audit["archive_sha256"]) != 64 or not audit.get("study_manifest_sha256")):
                    errors.append("exposure_history_proof_missing:" + qid)
            elif isinstance(status, str) and (status.startswith("known_exposed") or status == "unknown_pending_history_audit"):
                if entry.get("heldout_eligible") is not False:
                    errors.append("ineligible_exposure_claimed_heldout:" + qid)
            else:
                errors.append("invalid_exposure_status:" + qid)
            grouped_history[group].append(entry)
        if check_splits:
            split_by_qid = {row.get("qid"): row.get("split") for row in rows}
            for group, members in grouped_history.items():
                if any(item.get("status") != "unexposed_audited" for item in members):
                    qids_in_group = [qid for qid in qids if expected_groups[qid] == group]
                    if any(split_by_qid.get(qid) != "dev" for qid in qids_in_group):
                        errors.append("ineligible_exposure_group_not_dev:" + str(group))
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        errors.append("exposure_registry_input_invalid")
    return errors


def grouped_split_report(rows: list[dict]) -> dict:
    groups = defaultdict(set)
    assignments = connected_groups(rows)
    for row in rows:
        groups[assignments[row["qid"]]].add(row.get("split"))
    return {"groups": len(groups), "cross_split_groups": sorted(group for group, splits in groups.items() if len(splits) > 1),
            "split_counts": dict(Counter(row.get("split") for row in rows))}

def normalize_question(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(re.findall(r"\w+", text))


def frozen_evidence(index_dir: Path) -> dict[tuple[str, str], dict]:
    manifest = read_json(index_dir / "manifest.json")
    documents = manifest.get("documents")
    entries = manifest.get("document_manifests")
    if (not isinstance(documents, list) or not documents
            or any(not isinstance(doc_id, str) or not doc_id
                   or Path(doc_id).name != doc_id or doc_id in {".", ".."}
                   or "/" in doc_id or "\\" in doc_id or ":" in doc_id for doc_id in documents)
            or len(documents) != len(set(documents))
            or not isinstance(entries, list) or any(not isinstance(entry, dict) for entry in entries)):
        raise ValueError("invalid frozen index manifest")
    by_doc = {entry.get("document_id"): entry for entry in entries
              if isinstance(entry.get("document_id"), str)}
    if len(by_doc) != len(entries) or set(by_doc) != set(documents):
        raise ValueError("duplicate or missing frozen document binding")
    evidence = {}
    for doc_id in documents:
        # Review must bind the actual evidence bytes, not merely an unchanged
        # manifest sitting beside a modified BM25 payload. Hash exactly the
        # bytes that will be parsed to avoid a separate hash/read race.
        payload = (index_dir / doc_id / "bm25.json").read_bytes()
        if hashlib.sha256(payload).hexdigest() != by_doc[doc_id].get("bm25_sha256"):
            raise ValueError("physical frozen evidence hash mismatch")
        data = json.loads(payload)
        items = data.get("items") if isinstance(data, dict) else None
        if (not isinstance(items, list)
                or ("item_count" in by_doc[doc_id] and by_doc[doc_id]["item_count"] != len(items))):
            raise ValueError("invalid frozen evidence item count")
        for item in items:
            if (not isinstance(item, dict) or not isinstance(item.get("chunk_id"), str)
                    or not item["chunk_id"] or type(item.get("page")) is not int or item["page"] < 1
                    or not isinstance(item.get("content"), str) or not item["content"].strip()):
                raise ValueError("invalid frozen evidence record")
            key = (doc_id, item["chunk_id"])
            if key in evidence or item.get("doc_id") != doc_id:
                raise ValueError("duplicate or incorrect frozen provenance")
            evidence[key] = item
    return evidence


def validate_rows(rows: list[dict], evidence: dict[tuple[str, str], dict],
                  regression_rows: list[dict] | None = None,
                  owner_identity: str | None = None,
                  generated_records: dict[str, dict] | None = None) -> dict:
    from evaluation.benchmarks.human_record_contract import expected_behavior_error, review_role_error
    errors = []
    review_errors = []
    reviewer_roles = set()
    seen_ids, seen_queries, groups = set(), {}, {}
    counts = Counter()
    split_counts = Counter()
    questions = []
    for number, row in enumerate(rows, 1):
        prefix = f"row_{number}"
        if not isinstance(row, dict):
            errors.append(prefix + ":invalid_record")
            continue
        qid, question = row.get("qid"), row.get("question")
        generated_expected = (generated_records or {}).get(qid) if isinstance(qid, str) else None
        from .source_course_generation import export_matches
        owner_generated = bool(generated_expected and owner_identity
                               and generated_expected.get("author") == owner_identity
                               and export_matches(generated_expected, row))
        if not isinstance(qid, str) or not qid.strip() or qid in seen_ids:
            errors.append(prefix + ":duplicate_or_missing_qid")
        if isinstance(qid, str):
            seen_ids.add(qid)
        normalized = normalize_question(question) if isinstance(question, str) else ""
        if not normalized or normalized in seen_queries:
            errors.append(prefix + ":duplicate_or_empty_question")
        split = row.get("split")
        if not isinstance(split, str) or split not in {"dev", "test", "holdout"}:
            errors.append(prefix + ":invalid_split")
        else:
            split_counts[split] += 1
        group = row.get("paraphrase_group")
        if not isinstance(group, str) or not group.strip():
            errors.append(prefix + ":missing_paraphrase_group")
        elif group in groups and groups[group] != split:
            errors.append(prefix + ":paraphrase_group_leakage")
        else:
            groups[group] = split
        if normalized:
            seen_queries[normalized] = split
            questions.append((qid, split, set(normalized.split())))
        role_error = review_role_error(row, owner_identity)
        if role_error:
            errors.append(prefix + ":" + role_error)
            review_errors.append(prefix + ":" + role_error)
        elif row.get("reviewer_role") in {"independent_reviewer", "project_owner"}:
            reviewer_roles.add(row["reviewer_role"])
        if ((row.get("author_type") != "human" and not owner_generated) or row.get("review_status") != "approved"
                or not isinstance(row.get("author"), str) or not row["author"].strip()):
            errors.append(prefix + ":human_authorship_and_approval_required")
            review_errors.append(prefix + ":human_authorship_and_approval_required")
        review = row.get("review_checks", {})
        required = {"natural", "answerability", "evidence_sufficient", "corpus_temporal_scope", "difficulty",
                    "no_paraphrase_leakage", "expected_behavior"}
        tags = row.get("tags")
        if (not isinstance(tags, list) or any(not isinstance(tag, str) or not tag.strip() for tag in tags)
                or any(tag not in SUPPORTED_TAGS for tag in tags) or len(set(tags)) != len(tags)):
            errors.append(prefix + ":invalid_or_unsupported_tags")
            tags = []
        if row.get("release_eligible", True) is not True:
            errors.append(prefix + ":not_release_eligible")
        if (row.get("author_type") in {"generated", "ai", "synthetic", "example"} and not owner_generated) or row.get("is_example") is True:
            errors.append(prefix + ":fake_or_example_record")
        if (_identity(row.get("author")) in PLACEHOLDER_IDENTITIES
                or (_identity(row.get("reviewer")) in PLACEHOLDER_IDENTITIES and row.get("review_status") != "pending")):
            errors.append(prefix + ":placeholder_identity")
        behavior_error = expected_behavior_error(row)
        if behavior_error:
            errors.append(prefix + ":" + behavior_error)
        if not isinstance(review, dict) or any(review.get(key) is not True for key in required):
            errors.append(prefix + ":incomplete_review_checks")
            review_errors.append(prefix + ":incomplete_review_checks")
        direct_authored = row.get("question_source") == "direct_author"
        if direct_authored:
            if row.get("author_type") != "human" or not _identity(row.get("author")):
                errors.append(prefix + ":direct_author_provenance_required")
        elif not owner_generated and (not isinstance(row.get("source_url"), str)
                or urlparse(row["source_url"]).scheme not in {"https", "http"}
                or not urlparse(row["source_url"]).netloc):
            errors.append(prefix + ":missing_source_url")
        if not direct_authored and not owner_generated:
            try:
                retrieved = datetime.fromisoformat(row.get("source_retrieved_at", "").replace("Z", "+00:00"))
                if retrieved.tzinfo is None:
                    raise ValueError("timezone required")
            except (ValueError, TypeError, AttributeError):
                errors.append(prefix + ":invalid_retrieved_at")
        if row.get("evidence_source") != "frozen_pdf":
            errors.append(prefix + ":frozen_pdf_evidence_required")
        if row.get("difficulty") not in {"easy", "medium", "hard"}:
            errors.append(prefix + ":invalid_difficulty")
        tags = row.get("tags")
        if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
            errors.append(prefix + ":invalid_tags")
            tags = []
        gold = row.get("gold_evidence")
        if not isinstance(row.get("answerable"), bool) or not isinstance(gold, list):
            errors.append(prefix + ":invalid_answerability_or_gold")
            gold = []
        if bool(gold) != row.get("answerable"):
            errors.append(prefix + ":answerability_evidence_mismatch")
        doc_ids, filters = row.get("doc_ids"), row.get("filters", {})
        known_docs = {key[0] for key in evidence}
        if (not isinstance(doc_ids, list) or not doc_ids
                or any(not isinstance(doc, str) or doc not in known_docs for doc in doc_ids)
                or len(set(doc_ids)) != len(doc_ids)):
            errors.append(prefix + ":invalid_doc_scope")
            doc_ids = []
        if not isinstance(filters, dict) or any(not isinstance(key, str) for key in filters):
            errors.append(prefix + ":invalid_filters")
            filters = {}
        from campusai.rag.context import benchmark_request, resolve_query
        try:
            request = benchmark_request(row, [])
            resolve_query(request['question'], history=request['history'], selected_text=request['selected_text'],
                          requires_context=request.get('requires_context', False))
        except (ValueError, TypeError, AttributeError, KeyError):
            errors.append(prefix + ':invalid_request_context')
        seen_gold = set()
        for item in gold:
            coordinates = (item.get("doc_id"), item.get("chunk_id")) if isinstance(item, dict) else None
            valid_coordinates = coordinates is not None and all(isinstance(value, str) and value for value in coordinates)
            frozen = evidence.get(coordinates) if valid_coordinates else None
            if valid_coordinates:
                if coordinates in seen_gold:
                    errors.append(prefix + ":duplicate_gold_evidence")
                seen_gold.add(coordinates)
            if (not frozen or type(item.get("page")) is not int or item["page"] != frozen.get("page")):
                errors.append(prefix + ":evidence_provenance_mismatch")
            elif item["doc_id"] not in doc_ids or any(
                    str(frozen.get("metadata", {}).get(key, "")).casefold() != str(value).casefold()
                    for key, value in filters.items()):
                errors.append(prefix + ":evidence_scope_mismatch")
        counts["answerable"] += row.get("answerable") is True
        counts["negative"] += row.get("answerable") is False
        counts["hard"] += row.get("difficulty") == "hard" or "multi_hop" in tags
        counts["exact_code"] += "exact_code" in tags
        counts["ambiguous"] += bool({"ambiguous", "abstention"} & set(tags))
    for name, floor in {"records": 150, "answerable": 100, "negative": 20,
                        "hard": 15, "exact_code": 15, "ambiguous": 10}.items():
        actual = len(rows) if name == "records" else counts[name]
        if actual < floor:
            errors.append(f"insufficient_{name}:{actual}<{floor}")
    # Held-out sets need both positives and negatives and routing labels.
    for split in ("dev", "test", "holdout"):
        subset = [row for row in rows if isinstance(row, dict) and row.get("split") == split]
        if not subset or not all(any(row.get("answerable") is answerable for row in subset)
                                 for answerable in (True, False)):
            errors.append(f"insufficient_split_coverage:{split}")
        if not all(any(row.get("difficulty") == label and row.get("answerable") is True for row in subset)
                   for label in ("easy", "hard")):
            errors.append(f"insufficient_route_coverage:{split}")
    for index, (qid, split, tokens) in enumerate(questions):
        for other_qid, other_split, other in questions[index + 1:]:
            if split != other_split and len(tokens) >= 6 and len(other) >= 6:
                if len(tokens & other) / len(tokens | other) >= .85:
                    errors.append(f"suspected_paraphrase_leakage:{qid}:{other_qid}")
    for row in regression_rows or []:
        query = normalize_question(row["question"])
        if query in seen_queries:
            errors.append(f"regression_query_leakage:{row.get('qid')}")
        tokens = set(query.split())
        if len(tokens) >= 6:
            for qid, _, other in questions:
                if len(other) >= 6 and len(tokens & other) / len(tokens | other) >= .85:
                    errors.append(f"regression_paraphrase_leakage:{row.get('qid')}:{qid}")
    try:
        connected = grouped_split_report(rows)
        if connected["cross_split_groups"]:
            errors.append("connected_family_leakage")
    except (KeyError, TypeError, ValueError):
        errors.append("invalid_connected_families")
    review_complete = not review_errors
    review_mode = ("owner_self_review" if reviewer_roles == {"project_owner"} else
                   "independent_review" if reviewer_roles == {"independent_reviewer"} else
                   "mixed_review" if reviewer_roles else "incomplete")
    return {"schema_version": 3, "phase": 7, "status": "pass" if not errors else "conditional",
            "errors": sorted(set(errors)), "records": len(rows), "counts": dict(counts),
            "split_counts": dict(split_counts), "review_complete": review_complete,
            "authorship_counts": dict(Counter(row.get("author_type") for row in rows if isinstance(row, dict))),
            "benchmark_profile": "personal_owner_source_checked_ai" if generated_records else "human_authored",
            "review_mode": review_mode,
            "independent_review_complete": review_complete and reviewer_roles == {"independent_reviewer"},
            "owner_review_complete": review_complete and reviewer_roles == {"project_owner"}}


@contextmanager
def freeze_transaction(output_dir: Path):
    """One publisher at a time, including the canonical split assignment."""
    output_dir.mkdir(parents=True, exist_ok=True)
    lock = output_dir / "human_benchmark_freeze.lock"
    try:
        with lock.open("x", encoding="utf-8") as stream:
            stream.write("exclusive human benchmark publication\n")
    except FileExistsError as error:
        raise ValueError("human freeze in progress or interrupted; inspect artifacts before recovery") from error
    try:
        yield
    finally:
        lock.unlink()


def freeze_bundle(rows: list[dict], dataset: Path, output_dir: Path, report: dict) -> dict:
    """Publish assigned canonical bytes and exact split union without refreezing."""
    if report.get("status") != "pass":
        raise ValueError("only validated rows may be frozen")
    canonical = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n" for row in rows).encode("utf-8")
    planned = {dataset.parent / f"human_retrieval_{split}.jsonl":
               "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
                       for row in rows if row["split"] == split).encode("utf-8") for split in SPLIT_TARGETS}
    digest = lambda value: hashlib.sha256(value).hexdigest()
    final_report = {**report, "dataset_sha256": digest(canonical), "grouped_split": grouped_split_report(rows)}
    review_bytes = (json.dumps(final_report, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    manifest = {**final_report, "frozen": True,
                "split_sha256": {split: digest(planned[dataset.parent / f"human_retrieval_{split}.jsonl"]) for split in SPLIT_TARGETS},
                "review_sha256": digest(review_bytes), "allocation": "connected_groups_sha256_order_60_20_20_v1"}
    manifest_path = output_dir / "human_benchmark_manifest.json"
    review_path = output_dir / "human_benchmark_review.json"
    with freeze_transaction(output_dir):
        if manifest_path.is_file() and read_json(manifest_path).get("frozen") is True:
            if (read_json(manifest_path) != manifest or dataset.read_bytes() != canonical
                    or review_path.read_bytes() != review_bytes
                    or any(not path.is_file() or path.read_bytes() != content for path, content in planned.items())):
                raise ValueError("frozen dataset/splits changed; use a new cycle")
            return manifest
        if any(path.exists() and path.read_bytes() != content for path, content in planned.items()):
            raise ValueError("split destination already contains different bytes")
        for path, content in planned.items():
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("xb") as stream:
                    stream.write(content)
        temporary = dataset.with_name(dataset.name + ".freeze-" + uuid.uuid4().hex)
        try:
            temporary.write_bytes(canonical)
            os.replace(temporary, dataset)
        finally:
            temporary.unlink(missing_ok=True)
        review_path.write_bytes(review_bytes)
        manifest_path.write_bytes((json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8"))
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path("data/benchmark/human_retrieval.jsonl"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/hybrid-index"))
    parser.add_argument("--output-dir", type=Path, default=Path("evaluation/results"))
    parser.add_argument("--regression-dir", type=Path, default=Path("data/benchmark"))
    parser.add_argument("--owner-identity", help="required when canonical records use project_owner review")
    parser.add_argument("--review-policy", type=Path,
                        help="owner self-review policy; defaults to the dataset directory")
    parser.add_argument("--exposure-registry", type=Path,
                        help="complete source-bound exposure registry required for a release freeze")
    parser.add_argument("--assign-splits", action="store_true", help="deterministically assign reviewed groups before validation")
    args = parser.parse_args(argv)
    from evaluation.benchmarks.human_benchmark_intake import configured_owner_identity
    policy_path = args.review_policy or args.dataset.parent / "phase7_review_policy.json"
    owner_identity = configured_owner_identity(policy_path, args.owner_identity)
    from evaluation.common.release_artifacts import assert_tuning_allowed
    assert_tuning_allowed(args.output_dir, route=True)
    try:
        from evaluation.common.release_artifacts import require_previous_gates
        require_previous_gates("M1", args.output_dir, index_dir=args.index_dir, benchmark_dir=args.dataset.parent)
        rows = [json.loads(line) for line in args.dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
        registry_path = args.exposure_registry or (args.dataset.parent / "phase7_exposure_registry.json")
        exposure_registry = read_json(registry_path)
        source_pool = args.dataset.parent / "human_candidate_pool.jsonl"
        source_lineage = args.dataset.parent / "human_candidate_lineage.json"
        exposure_issues = exposure_registry_errors(rows, exposure_registry, source_pool=source_pool,
                                                    source_lineage=source_lineage,
                                                    index_manifest=args.index_dir / "manifest.json",
                                                    check_splits=False)
        if args.assign_splits and not exposure_issues:
            exposure_records = {entry["qid"]: entry for entry in exposure_registry["records"]}
            rows = assign_grouped_splits(rows, exposure_records)
        regression = [json.loads(line) for path in args.regression_dir.glob("hybrid_retrieval_*.jsonl")
                      for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        from evaluation.benchmarks.owner_generation import load_generation
        authorization, generated = load_generation(args.dataset.parent, args.index_dir)
        report = validate_rows(rows, frozen_evidence(args.index_dir), regression,
                               owner_identity=owner_identity, generated_records=generated)
        if authorization:
            report["generation_authorization_sha256"] = sha256(args.dataset.parent / "phase7_generation_authorization.json")
            dev_auth_path = args.dataset.parent/'phase7_dev_generation_authorization.json'
            if dev_auth_path.is_file():
                report['dev_generation_authorization_sha256'] = sha256(dev_auth_path)
        exposure_issues = exposure_registry_errors(rows, exposure_registry, source_pool=source_pool,
                                                    source_lineage=source_lineage,
                                                    index_manifest=args.index_dir / "manifest.json",
                                                    check_splits=True)
        report["errors"] = sorted(set(report["errors"] + exposure_issues))
        if exposure_issues:
            report["status"] = "conditional"
        report.update(dataset_sha256=sha256(args.dataset), index_sha256=sha256(args.index_dir / "manifest.json"),
                  review_policy_sha256=sha256(policy_path) if policy_path.is_file() else None,
                  grouped_split=grouped_split_report(rows),
                  tag_counts=dict(Counter(tag for row in rows for tag in row.get("tags", []) if isinstance(tag, str)),),
                  reviewer_summary={"reviewed": sum(row.get("review_status") == "approved" for row in rows),
                                    "distinct_reviewers": len({_identity(row.get("reviewer")) for row in rows if _identity(row.get("reviewer"))}),
                                    "author_reviewer_collisions": sum(_identity(row.get("author")) == _identity(row.get("reviewer")) for row in rows)})
    except (OSError, ValueError, KeyError, TypeError) as error:
        report = {"phase": 7, "status": "blocked", "errors": [f"dataset_input:{type(error).__name__}"]}
        rows = []
    if report["status"] == "pass":
        report = freeze_bundle(rows, args.dataset, args.output_dir, report)
    else:
        identity = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()[:16]
        write_json(args.output_dir / f"human_benchmark_attempt_{identity}.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
