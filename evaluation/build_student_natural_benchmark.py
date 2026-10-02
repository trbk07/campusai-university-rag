"""Build natural user-input fixtures, scoped to uploaded PDFs rather than a school.

Sources are evaluation fixtures only. Runtime does not import this dataset or
assume what a future upload contains. Answerability is fixture-dependent.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from evaluation.build_ai_reranker_benchmark import DOCUMENTS
from evaluation.freeze_human_benchmark import normalize_question
from evaluation.release_artifacts import sha256

CATEGORIES = {
    "paraphrase", "colloquial", "abbreviation", "typo", "slang", "code_switching",
    "lexical_mismatch", "implicit_intent", "conditional", "multi_hop",
    "contextual_followup", "ambiguous", "unanswerable", "long_noisy",
}
SELECTED_INTENTS = {
    "selected_section_plain_language", "selected_section_compare_sanctions",
    "selected_section_extract_percentages", "uploaded_table_semester_lookup",
}


def parse_spec(text: str):
    groups, current = [], None
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("|")
        if line.startswith("@"):
            if len(parts) != 6:
                raise ValueError(f"line {number}: six intent fields required")
            intent, aliases, positions, difficulty, normalized, expected = parts
            current = {"intent": intent[1:], "aliases": aliases.split(","), "positions": positions,
                       "difficulty": difficulty, "normalized": normalized, "expected": expected, "variants": []}
            groups.append(current)
        elif current is None or not 2 <= len(parts) <= 4 or parts[0] not in CATEGORIES:
            raise ValueError(f"line {number}: invalid query variant")
        else:
            current["variants"].append(parts)
    if not groups or len({group["intent"] for group in groups}) != len(groups):
        raise ValueError("missing or duplicate intents")
    for group in groups:
        if len(group["variants"]) != 6:
            raise ValueError(f"{group['intent']}: exactly six authored variants required")
        if group["difficulty"] not in {"easy", "medium", "hard"} or not group["normalized"] or not group["expected"]:
            raise ValueError("invalid intent annotation")
    return groups


def compile_dataset(spec: str, corpus: dict, index_dir: Path):
    groups = parse_spec(spec)
    documents = {document["filename"]: document for document in corpus["documents"]}
    indexed = json.loads((index_dir / "manifest.json").read_text(encoding="utf-8"))["documents"]
    cached, rows, seen = {}, [], set()
    for group in groups:
        supported = group["aliases"] != ["none"]
        if not supported and group["positions"]:
            raise ValueError("unsupported intent cannot have gold evidence")
        scope, gold, source_labels = [], [], []
        selections = []
        if supported:
            position_groups = group["positions"].split(";")
            if len(position_groups) != len(group["aliases"]):
                raise ValueError("one evidence position group per document required")
            for alias, positions in zip(group["aliases"], position_groups):
                if alias not in DOCUMENTS or not positions:
                    raise ValueError("unknown or ungrounded source document")
                document = documents[DOCUMENTS[alias]]
                doc = document["sha256"]
                if doc not in indexed:
                    raise ValueError("source document absent from index")
                scope.append({"document_ref": f"uploaded_{alias}", "fixture_file": document["filename"],
                              "sha256": doc})
                if doc not in cached:
                    cached[doc] = json.loads((index_dir / doc / "bm25.json").read_text(encoding="utf-8"))["items"]
                pages = set()
                for position in positions.split(","):
                    index = int(position)
                    if not 0 <= index < len(cached[doc]):
                        raise ValueError("invalid evidence position")
                    item = cached[doc][index]
                    if item["doc_id"] != doc or not isinstance(item["page"], int):
                        raise ValueError("invalid frozen provenance")
                    pages.add(item["page"])
                    gold.append({"doc_id": doc, "chunk_id": item["chunk_id"], "page": item["page"]})
                    selections.append(item["content"].split("\n\n", 1)[-1])
                source_labels.append(document["filename"] + "#pages=" + ",".join(map(str, sorted(pages))))
        # Preserve old held-out source boundaries. The two-program comparison
        # reserves the mechatronics source for holdout alongside electronics.
        if any(alias in {"electronics", "mechatronics", "cs"} for alias in group["aliases"]):
            split = "holdout"
        elif supported:
            split = documents[DOCUMENTS[group["aliases"][0]]]["benchmark_split"]
        else:
            split = ("dev", "test", "holdout")[int(hashlib.sha256(group["intent"].encode()).hexdigest(), 16) % 3]
        for variant in group["variants"]:
            category, raw_query = variant[:2]
            raw_normalized = variant[2] if len(variant) >= 3 else group["normalized"]
            # Preserve exactly what the fixture author wrote. Do not clean typos,
            # slang, numerical conditions, or entities before benchmarking.
            query, normalized = raw_query, raw_normalized
            key = normalize_question(query)
            if not key or key in seen:
                raise ValueError(f"duplicate/empty natural input: {query}")
            seen.add(key)
            ambiguous = category == "ambiguous"
            context = []
            if category == "contextual_followup":
                if len(variant) != 4 or not variant[3].strip():
                    raise ValueError("contextual follow-up requires explicit prior user turn")
                context = [{"role": "user", "content": variant[3]}]
            elif len(variant) == 4:
                raise ValueError("unexpected context field")
            if category == "unanswerable" and supported or ambiguous and supported:
                raise ValueError("supported intent cannot have unanswerable/ambiguous variants")
            row = {"id": f"q_{len(rows)+1:03d}", "query": query, "normalized_query": normalized,
                   "intent": group["intent"], "category": category,
                   "difficulty": "hard" if category in {"ambiguous", "conditional", "multi_hop", "long_noisy"} else group["difficulty"],
                   "answerable": supported, "ambiguous": ambiguous,
                   "expected_source": "; ".join(source_labels) if supported else None,
                   "expected_behavior": "answer_grounded" if supported else "ask_clarification" if ambiguous else "abstain_no_evidence",
                   "expected_answer": group["expected"], "context": context,
                   "document_context": {"uploaded_documents": scope, "scope": "selected_uploads" if supported else "seed_corpus_upload_fixture",
                                        "fixture_dependent_labels": True},
                   "gold_evidence": gold, "split": split, "paraphrase_group": group["intent"],
                   "author_type": "ai", "review_status": "not_human_reviewed", "release_eligible": False}
            if group["intent"] in SELECTED_INTENTS:
                row["document_context"]["selected_text"] = "\n\n".join(selections)
            rows.append(row)
    return rows


def validate_rows(rows):
    errors, queries, ids, groups = [], set(), set(), {}
    for row in rows:
        if row["id"] in ids or normalize_question(row["query"]) in queries:
            errors.append("duplicate_id_or_query")
        ids.add(row["id"])
        queries.add(normalize_question(row["query"]))
        if row["category"] not in CATEGORIES or not row["normalized_query"]:
            errors.append("invalid_category_or_normalization")
        if row["answerable"] != bool(row["expected_source"] and row["gold_evidence"]):
            errors.append("answerability_source_mismatch")
        if row["category"] == "contextual_followup" and not row["context"]:
            errors.append("contextual_query_without_context")
        if row["ambiguous"] and (row["answerable"] or row["expected_behavior"] != "ask_clarification"):
            errors.append("ambiguous_query_answered_without_clarification")
        if row["author_type"] != "ai" or row["review_status"] != "not_human_reviewed" or row["release_eligible"] is not False:
            errors.append("false_review_provenance")
        group = row["paraphrase_group"]
        if group in groups and groups[group] != row["split"]:
            errors.append("intent_leakage_between_splits")
        groups[group] = row["split"]
    if set(row["category"] for row in rows) != CATEGORIES:
        errors.append("missing_query_categories")
    if not 300 <= len(rows) <= 500:
        errors.append("query_count_outside_300_500")
    return sorted(set(errors))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=Path("data/benchmark/student_natural_queries.spec"))
    parser.add_argument("--corpus", type=Path, default=Path("data/corpus/university/manifest.json"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/phase6-index"))
    parser.add_argument("--output", type=Path, default=Path("data/benchmark/student_natural_queries.jsonl"))
    args = parser.parse_args(argv)
    if args.output.name.startswith("human_retrieval_"):
        raise ValueError("AI fixtures cannot overwrite independently reviewed human benchmarks")
    corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
    for document in corpus["documents"]:
        if document["filename"] in DOCUMENTS.values() and sha256(args.corpus.parent / document["filename"]) != document["sha256"]:
            raise ValueError("fixture PDF checksum mismatch")
    rows = compile_dataset(args.spec.read_text(encoding="utf-8"), corpus, args.index_dir)
    errors = validate_rows(rows)
    if errors:
        raise ValueError(", ".join(errors))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in rows), encoding="utf-8", newline="\n")
    manifest = {"schema_version": 1, "records": len(rows), "intents": len({row["intent"] for row in rows}),
                "categories": dict(Counter(row["category"] for row in rows)),
                "difficulty": dict(Counter(row["difficulty"] for row in rows)),
                "answerable": sum(row["answerable"] for row in rows), "ambiguous": sum(row["ambiguous"] for row in rows),
                "splits": dict(Counter(row["split"] for row in rows)), "validation_errors": errors,
                "dataset_sha256": sha256(args.output), "spec_sha256": sha256(args.spec),
                "corpus_manifest_sha256": sha256(args.corpus), "index_manifest_sha256": sha256(args.index_dir / "manifest.json"),
                "chunk_sha256": {doc: sha256(args.index_dir / doc / "bm25.json") for doc in sorted({item["doc_id"] for row in rows for item in row["gold_evidence"]})},
                "author_type": "ai", "review_status": "not_human_reviewed", "release_eligible": False,
                "runtime_assumption": "none: upload fixture sources live only in evaluation metadata",
                "answerability_scope": "seed corpus only; relabel against each different upload",
                "split_policy": "all six variants of an intent stay together; supported PDF sources do not cross splits",
                "query_policy": "raw authored inputs preserved verbatim; normalized_query is annotation only"}
    args.output.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


def query_input(row: dict, uploads: dict[str, list[str]]) -> dict:
    """Use raw input and explicit current upload bindings, never gold labels."""
    scope = row["document_context"]
    references = [item["document_ref"] for item in scope["uploaded_documents"]] or [scope["scope"]]
    documents = []
    for reference in references:
        binding = uploads.get(reference)
        if not isinstance(binding, list) or not binding or any(not isinstance(doc, str) or not doc.strip() for doc in binding):
            raise ValueError(f"explicit uploaded document binding required: {reference}")
        documents.extend(binding)
    return {"query": row["query"], "doc_ids": list(dict.fromkeys(documents)),
            "context": row["context"], "selected_text": scope.get("selected_text")}


if __name__ == "__main__":
    raise SystemExit(main())
