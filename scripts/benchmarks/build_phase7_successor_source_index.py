"""Build a separate BGE source index while preserving the historical baseline.

The new index is source construction evidence, not a release measurement.
Metadata for the four added PDFs is curated from their physical cover pages.
No legacy document, measured report, split or approval is rewritten.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import time

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

from campusai.ingestion.chunker import make_chunks
from campusai.ingestion.docling_parser import parse_pdf
from campusai.retrieval.dense_index import DenseIndex
from campusai.retrieval.index_builder import build_document_indexes
from campusai.retrieval.model_runtime import retrieval_runtime
from campusai.schemas import Document, Table
from evaluation.benchmarks.dev_inheritance import file_bindings, preserved_index
from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence
from evaluation.benchmarks.source_course_rows import source_course_rows
from evaluation.common.release_artifacts import sha256, verify_index_files


INSTITUTION = "University of Engineering and Technology, Vietnam National University Hanoi"
CURATION = {
    "uet_robotics_curriculum_2020.pdf": {
        "program": "Robotics Engineering", "degree_level": "undergraduate",
        "version": "1120/QD-DT (2020-12-11)", "issue_date": "2020-12-11",
        "proof_pages": [1], "required_text": ["1120", "11 tháng 12 năm 2020", "Robotics Engineering"],
        "applicability_note": "Issue date is explicit; a student cohort is not inferred.",
    },
    "uet_electronics_masters_curriculum_2022.pdf": {
        "program": "Electronics and Communications Engineering — Electronics Engineering",
        "degree_level": "masters", "version": "2022-11 curriculum decision",
        "issue_year": 2022, "issue_month": 11,
        "proof_pages": [1, 3], "required_text": ["tháng 11 năm 2022", "Electronics Engineering", "Thạc sĩ"],
        "applicability_note": "Decision year/month only; no cohort or exact day is inferred.",
    },
    "uet_telecommunications_masters_curriculum_2022.pdf": {
        "program": "Electronics and Communications Engineering — Communications Engineering",
        "degree_level": "masters", "version": "2022-11 curriculum decision",
        "issue_year": 2022, "issue_month": 11,
        "proof_pages": [1, 3], "required_text": ["tháng 11 năm 2022", "+ Tiếng Anh: Communications Engineering", "Thạc sĩ"],
        "applicability_note": "Decision year/month only; no cohort or exact day is inferred.",
    },
    "uet_engineering_mechanics_masters_schedule_2019_publication.pdf": {
        "program": "Engineering Mechanics", "degree_level": "masters",
        "proof_pages": [1], "required_text": ["chương trình đào tạo Cơ kỹ thuật", "luận văn Thạc sĩ", "4 kỳ"],
        "applicability_note": "PDF has no issue date/cohort. URL directory 2019 is publication provenance only.",
    },
}


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ValueError(f"refusing to overwrite evidence: {path}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def identity(fact: dict) -> tuple:
    # Header/context hashes and batch-relative row numbers legitimately change.
    # These source coordinates and the complete cell hash must remain equal.
    return fact["doc_id"], fact["page"], fact["code"], fact["cells_sha256"]


def restored_tables(doc_id: str, evidence: dict) -> list[Table]:
    """Recover lossless table cells from the physically verified parent index."""
    grouped = {}
    for (doc, _chunk), record in evidence.items():
        if doc == doc_id and record["content_type"] == "table":
            grouped.setdefault(record["metadata"]["table_id"], []).append(record)
    tables = []
    for table_id, records in sorted(grouped.items()):
        records.sort(key=lambda record: record["metadata"]["table_part"])
        payloads = [json.loads(record["content"][record["content"].index('{"headers"'):])
                    for record in records]
        if any(payload["headers"] != payloads[0]["headers"] for payload in payloads):
            raise ValueError("parent table parts disagree on headers")
        tables.append(Table(table_id, doc_id, records[0]["metadata"]["pages"],
                            payloads[0]["headers"], [row for part in payloads for row in part["rows"]]))
    return tables


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-index", type=Path, required=True)
    parser.add_argument("--expanded-index", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--qh-index", type=Path, required=True)
    parser.add_argument("--qh-store", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("output directory already exists; use a new evidence version")
    started = time.perf_counter()
    baseline_binding = file_bindings(args.baseline_index)
    expanded_binding = file_bindings(args.expanded_index)
    qh_binding = file_bindings(args.qh_index)
    preserved_index(args.baseline_index, args.expanded_index, baseline_binding)
    old_evidence = frozen_evidence(args.expanded_index)
    old_facts = source_course_rows(old_evidence)
    source = json.loads((args.source_dir / "source_manifest.json").read_text(encoding="utf8"))
    by_name = {item["filename"]: item for item in source["documents"]}
    index = args.output_dir / "index"
    store = args.output_dir / "store"
    shutil.copytree(args.baseline_index, index)
    store.mkdir()
    receipts = []
    for name, fields in CURATION.items():
        item = by_name[name]
        pdf = args.source_dir / name
        if sha256(pdf) != item["doc_id"]:
            raise ValueError(f"source PDF digest changed: {name}")
        pages = parse_pdf(pdf)
        proof = [{"page": number, "text": pages[number - 1]["text"]}
                 for number in fields["proof_pages"]]
        proof_text = " ".join(" ".join(row["text"].split()) for row in proof)
        if not all(text in proof_text for text in fields["required_text"]):
            raise ValueError(f"curated metadata is not supported by physical PDF: {name}")
        original_metadata = next(record["metadata"] for (doc_id, _), record in old_evidence.items()
                                 if doc_id == item["doc_id"])
        doc = Document(item["doc_id"], str(pdf.resolve()), len(pages), language="vi",
                       tables=restored_tables(item["doc_id"], old_evidence))
        # Do not retain guessed currency, code-derived years, label-as-program,
        # guessed academic-year filters or document-wide semester filters.
        doc.metadata = {"document_type": "curriculum", "domain": "academic", "language": "vi",
                        "source_url": item["source_url"], "source_pdf_sha256": doc.doc_id,
                        "source_name": name, "metadata_curation": "physical_source_review_v1",
                        **{key: value for key, value in fields.items()
                           if key not in {"proof_pages", "required_text"}}}
        if "mechanics" not in name:
            doc.metadata["institution"] = INSTITUTION
        doc.language = "vi"
        diagnostics = {}
        doc.chunks = make_chunks(pages, doc.doc_id, doc.metadata, doc.tables, diagnostics=diagnostics)
        if diagnostics["chunks_over_limit"] or diagnostics.get("oversized_table_cells"):
            raise ValueError(f"truncated or oversized source evidence: {name}")
        dump(store / doc.doc_id / "meta.json", doc.to_dict())
        build_document_indexes(doc, index, dense_model="BAAI/bge-m3", device="cuda", batch_size=8)
        receipts.append({"filename": name, "doc_id": doc.doc_id, "chunks": len(doc.chunks),
                         "metadata_before": original_metadata, "metadata_after": doc.metadata,
                         "table_provenance": "lossless table cells restored from verified parent BM25 records",
                         "physical_metadata_proof": proof, "chunk_diagnostics": diagnostics})
        print(json.dumps({"built_document": name, "chunks": len(doc.chunks)}, ensure_ascii=True), flush=True)
    qh_manifest = json.loads((args.qh_index / "manifest.json").read_text(encoding="utf8"))
    if len(qh_manifest["documents"]) != 1:
        raise ValueError("expected exactly one QH-2025 source document")
    qh_id = qh_manifest["documents"][0]
    qh_doc = Document.from_dict(json.loads((args.qh_store / qh_id / "meta.json").read_text(encoding="utf8")))
    # Re-encode the exact reviewed QH-2025 records; no hash embedding is copied.
    dump(store / qh_id / "meta.json", qh_doc.to_dict())
    build_document_indexes(qh_doc, index, dense_model="BAAI/bge-m3", device="cuda", batch_size=8)
    before_qh = frozen_evidence(args.qh_index)
    evidence = frozen_evidence(index)
    if any(evidence[key] != value for key, value in before_qh.items()):
        raise ValueError("reviewed QH-2025 chunk bytes changed")
    facts = source_course_rows(evidence)
    for doc_id in [entry["doc_id"] for entry in receipts]:
        old = Counter(identity(f) for f in old_facts if f["doc_id"] == doc_id)
        new = Counter(identity(f) for f in facts if f["doc_id"] == doc_id)
        if old != new:
            raise ValueError(f"curation changed physical course cells/pages: {doc_id}")
    migration = []
    for fact in old_facts:
        matches = [candidate for candidate in facts if identity(candidate) == identity(fact)]
        if len(matches) != 1:
            raise ValueError("source fact migration must be one-to-one")
        migration.append({"before": fact, "after": matches[0], "physical_cells_unchanged": True})
    preserved_index(args.baseline_index, index, baseline_binding)
    if file_bindings(args.expanded_index) != expanded_binding or file_bindings(args.qh_index) != qh_binding:
        raise ValueError("source evidence index was modified")
    if not verify_index_files(index):
        raise ValueError("new physical index binding failed")
    for doc_id in json.loads((index / "manifest.json").read_text(encoding="utf8"))["documents"]:
        dense = DenseIndex.load(index / doc_id / "dense.json")
        if dense.model_name != "BAAI/bge-m3" or dense.manifest["embedding_dimension"] != 1024:
            raise ValueError("successor index contains a fallback or mismatched dense provider")
    encoder = retrieval_runtime().get_encoder("BAAI/bge-m3", device="cuda")
    revision = encoder._first_module().auto_model.config._commit_hash
    weights = Path.home() / ".cache/huggingface/hub/models--BAAI--bge-m3/snapshots" / revision / "pytorch_model.bin"
    if not weights.is_file():
        raise ValueError("loaded physical model weights cannot be identified")
    dump(args.output_dir / "source_course_facts.json", facts)
    dump(args.output_dir / "source_fact_migration.json", migration)
    receipt = {"schema_version": 1, "status": "PASS_SOURCE_INDEX_CONSTRUCTION",
               "recorded_at": datetime.now(timezone.utc).isoformat(), "release_eligible": False,
               "benchmark_f0_frozen": False, "baseline_documents_unchanged": True,
               "baseline_index_sha256": sha256(args.baseline_index / "manifest.json"),
               "expanded_parent_sha256": sha256(args.expanded_index / "manifest.json"),
               "qh_source_index_sha256": sha256(args.qh_index / "manifest.json"),
               "index_sha256": sha256(index / "manifest.json"), "index_files": file_bindings(index),
               "model_name": "BAAI/bge-m3", "model_hf_commit": revision,
               "model_weights_sha256": sha256(weights), "provider_manifest_revision": "1",
               "provider_revision_note": "Provider format version 1 is distinct from the actual HF commit.",
               "device": "cuda", "batch_size": 8, "network_access": "HF offline cache only",
               "documents": len(json.loads((index / "manifest.json").read_text(encoding="utf8"))["documents"]),
               "source_course_facts": len(facts), "migrated_facts": len(migration),
               "source_fact_migration_sha256": sha256(args.output_dir / "source_fact_migration.json"),
               "source_course_facts_sha256": sha256(args.output_dir / "source_course_facts.json"),
               "curation": receipts, "builder_sha256": sha256(Path(__file__)),
               "elapsed_seconds": time.perf_counter() - started}
    dump(args.output_dir / "index_build_receipt.json", receipt)
    print(json.dumps({key: receipt[key] for key in ("status", "documents", "source_course_facts", "index_sha256", "model_hf_commit")}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
