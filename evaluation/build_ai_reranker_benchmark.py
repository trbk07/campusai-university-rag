"""Compile transparent AI research questions against the existing frozen index.

This does not create human approvals or satisfy M1. Splits follow the original
corpus manifest, not a new allocation that could move old holdout sources to dev.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from evaluation.freeze_human_benchmark import normalize_question
from evaluation.release_artifacts import sha256, write_json

DOCUMENTS = {
    "admission": "uet_masters_admission_2022.pdf",
    "rewards": "uet_student_rewards_2023.pdf",
    "electronics": "uet_electronics_program_2023.pdf",
    "cs": "uet_cs_progression.pdf",
    "mechatronics": "uet_mechatronics_curriculum_2023.pdf",
    "mai": "uet_mai_joint_curriculum_2022.pdf",
    "regulation": "uet_training_regulation_2014.pdf",
}


def compile_rows(spec: str, corpus: dict, index_dir: Path) -> list[dict]:
    documents = {item["filename"]: item for item in corpus["documents"]}
    indexed = json.loads((index_dir / "manifest.json").read_text(encoding="utf-8"))["documents"]
    rows, seen = [], set()
    cache = {}
    for number, line in enumerate(spec.splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        fields = line.split("|")
        if len(fields) != 6:
            raise ValueError(f"line {number}: six fields required")
        alias, positions, difficulty, tags, question, answer = fields
        if alias not in DOCUMENTS or difficulty not in {"easy", "medium", "hard"}:
            raise ValueError(f"line {number}: invalid document or difficulty")
        document = documents[DOCUMENTS[alias]]
        doc_id = document["sha256"]
        if doc_id not in indexed or document["benchmark_split"] not in {"dev", "test", "holdout"}:
            raise ValueError(f"line {number}: document not in frozen corpus")
        if doc_id not in cache:
            cache[doc_id] = json.loads((index_dir / doc_id / "bm25.json").read_text(encoding="utf-8"))["items"]
        tag_list = tags.split(",")
        negative = "negative" in tag_list
        if negative != (not positions):
            raise ValueError(f"line {number}: answerability/evidence mismatch")
        normalized = normalize_question(question)
        if not normalized or normalized in seen or not answer.strip():
            raise ValueError(f"line {number}: duplicate question or missing answer")
        seen.add(normalized)
        gold = []
        for position in positions.split(",") if positions else []:
            index = int(position)
            if index < 0 or index >= len(cache[doc_id]):
                raise ValueError(f"line {number}: invalid evidence position")
            item = cache[doc_id][index]
            if item["doc_id"] != doc_id or not isinstance(item["page"], int) or not item["content"]:
                raise ValueError(f"line {number}: invalid frozen evidence")
            gold.append({"doc_id": doc_id, "chunk_id": item["chunk_id"], "page": item["page"],
                         "quote": item["content"], "relevance": 1})
        if len({item["chunk_id"] for item in gold}) != len(gold):
            raise ValueError(f"line {number}: duplicate gold evidence")
        rows.append({"qid": f"phase7-ai-{len(rows)+1:03d}", "split": document["benchmark_split"],
                     "question": question, "expected_answer": answer, "language": "vi",
                     "category": "negative" if negative else tag_list[0], "difficulty": difficulty,
                     "tags": tag_list, "answerable": not negative, "gold_evidence": gold,
                     "doc_ids": [doc_id], "filters": {}, "source_url": document["source_url"],
                     "source_filename": document["filename"], "source_group": doc_id,
                     "paraphrase_group": doc_id, "evidence_source": "frozen_pdf",
                     "author_type": "ai", "review_status": "not_human_reviewed",
                     "release_eligible": False})
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=Path("data/benchmark/phase7_ai_questions.tsv"))
    parser.add_argument("--corpus", type=Path, default=Path("data/corpus/university/manifest.json"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/phase6-index"))
    parser.add_argument("--output-dir", type=Path, default=Path(".release/reranker/studies/ai-benchmark-v1"))
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    output = args.output_dir.resolve()
    if not output.is_relative_to(root / ".release" / "reranker" / "studies"):
        raise ValueError("AI benchmark output must stay in the isolated studies directory")
    corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
    rows = compile_rows(args.spec.read_text(encoding="utf-8"), corpus, args.index_dir)
    # Check actual PDF hashes, not just document names or labels.
    sources = {row["source_filename"] for row in rows}
    for document in corpus["documents"]:
        if document["filename"] in sources and sha256(args.corpus.parent / document["filename"]) != document["sha256"]:
            raise ValueError("source PDF checksum mismatch")
    if len(rows) < 150:
        raise ValueError("research benchmark requires at least 150 questions")
    bindings = {"spec_sha256": sha256(args.spec), "corpus_sha256": sha256(args.corpus),
                "index_sha256": sha256(args.index_dir / "manifest.json"),
                "chunk_sha256": {doc: sha256(args.index_dir / doc / "bm25.json")
                                  for doc in sorted({row["source_group"] for row in rows})}}
    output.mkdir(parents=True, exist_ok=True)
    paths = {}
    for split in ("dev", "test", "holdout"):
        subset = [row for row in rows if row["split"] == split]
        if not any(row["answerable"] for row in subset) or not any(not row["answerable"] for row in subset):
            raise ValueError("each split requires positive and negative cases")
        path = output / f"{split}.jsonl"
        content = "".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in subset)
        if path.exists() and path.read_text(encoding="utf-8") != content:
            raise ValueError("existing study dataset is immutable; choose a new study directory")
        path.write_text(content, encoding="utf-8")
        paths[split] = sha256(path)
    manifest = {"schema_version": 1, "status": "conditional", "release_eligible": False,
                "evidence_type": "ai_authored_pdf_research", "review_status": "not_human_reviewed",
                "split_policy": "original corpus document split; no source crosses splits",
                "records": len(rows), "answerable": sum(row["answerable"] for row in rows),
                "split_counts": dict(Counter(row["split"] for row in rows)),
                "tag_counts": dict(Counter(tag for row in rows for tag in row["tags"])),
                **bindings, "dataset_sha256": paths}
    write_json(output / "dataset_manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
