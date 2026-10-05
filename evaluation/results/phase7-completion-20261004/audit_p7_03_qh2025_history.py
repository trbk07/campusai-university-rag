"""Screen QH-2025 course facts against question-only historical benchmark text."""
from __future__ import annotations

from dataclasses import replace
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from evaluation.common.release_artifacts import sha256, source_identity, write_json
from campusai.retrieval.cross_encoder_provider import (
    ModelIdentity, OfflineCrossEncoderReranker, RerankCandidate, snapshot_sha256,
)
from sklearn.feature_extraction.text import TfidfVectorizer

TASK = ROOT / "evaluation/results/phase7-completion-20261004"
QUEUE = TASK / "p7-03_semantic_review_queue.json"
SOURCE_VALIDATION = TASK / "p7-03_qh2025_source_binding_validation-v3.json"
SMOKE = TASK / "p7-07-cuda-snapshot-smoke.json"
OUT = TASK / "p7-03_qh2025_history_preflight-v2.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-validation", type=Path, default=SOURCE_VALIDATION)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    validation_path, output_path = args.source_validation.resolve(), args.output.resolve()
    if output_path.exists():
        raise FileExistsError(output_path)
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    source = json.loads(validation_path.read_text(encoding="utf-8"))
    if source.get("status") != "PASS" or source.get("release_eligible") is not False:
        raise ValueError("source binding validation must pass while remaining non-release evidence")
    before = source_identity(ROOT)
    historical = []
    source_files = []
    for item in queue["inputs"]["history_datasets"]:
        path = ROOT / item["path"]
        if sha256(path) != item["sha256"]:
            raise ValueError(f"history input hash mismatch: {item['path']}")
        source_files.append({"path": item["path"], "sha256": item["sha256"]})
        for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            question = row.get("question", row.get("query", ""))
            if isinstance(question, str) and question.strip():
                historical.append({"qid": row.get("qid"), "path": item["path"],
                                   "line": line_number, "question": question.strip()})
    expected = queue["inputs"]["history_question_occurrences"]
    if len(historical) != expected:
        raise ValueError(f"history occurrence count mismatch: {len(historical)} != {expected}")
    occurrence_count = len(historical)
    unique = {}
    for item in historical:
        key = re.sub(r"\s+", " ", item["question"]).strip()
        if key not in unique:
            unique[key] = {**item, "occurrence_count": 0}
        unique[key]["occurrence_count"] += 1
    historical = list(unique.values())

    facts = source["facts"]
    target_texts = []
    for fact in facts:
        # Screen subject identity, rather than the shared word "prerequisites".
        target_texts.append(fact["code"] + " " + fact["name"])
    corpus = [item["question"] for item in historical] + target_texts
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2,
                                 sublinear_tf=True, strip_accents=None, max_features=250000)
    matrix = vectorizer.fit_transform(corpus)
    history_matrix = matrix[:len(historical)]
    target_matrix = matrix[len(historical):]

    smoke = json.loads(SMOKE.read_text(encoding="utf-8"))
    identity = replace(ModelIdentity(**smoke["model_identity"]), input_format="body")
    model_dir = ROOT / ".tmp/phase7-models" / identity.model_revision
    if snapshot_sha256(model_dir) != identity.model_sha256:
        raise ValueError("frozen reranker snapshot hash mismatch")
    provider = OfflineCrossEncoderReranker(identity, model_dir, timeout_ms=60000,
                                           candidate_cap=40, score_cache_size=0)
    started = time.perf_counter()
    groups = []
    try:
        provider.warm_up()
        for number, fact in enumerate(facts):
            similarities = (target_matrix[number] @ history_matrix.T).toarray().ravel()
            alias = fact["code"].removeprefix("UET.")
            code_pattern = re.compile(r"(?<![A-Za-z0-9])(?:UET\.)?" + re.escape(alias) + r"(?![A-Za-z0-9])", re.I)
            alias_indexes = [i for i, item in enumerate(historical) if code_pattern.search(item["question"])]
            lexical_indexes = [int(i) for i in similarities.argsort()[::-1]]
            top_indexes = list(dict.fromkeys(alias_indexes + lexical_indexes))[:40]
            candidates = []
            source_rows = {}
            exact_code = []
            for rank, index in enumerate(top_indexes, 1):
                item = historical[int(index)]
                key = hashlib.sha256(f"{item['path']}\0{item['line']}\0{item['question']}".encode()).hexdigest()
                candidate_id = "history-" + key[:24]
                candidate = RerankCandidate(candidate_id, "history-" + key[:16], candidate_id,
                    1, item["question"], rank, float(similarities[index]))
                candidates.append(candidate)
                source_rows[candidate_id] = {**item, "lexical_cosine": float(similarities[index])}
            scored = provider.score(target_texts[number], candidates) if candidates else []
            score_map = {item.candidate_id: item.reranker_score for item in scored}
            ranked = sorted(source_rows, key=lambda key: (-score_map.get(key, float("-inf")), key))
            exact_code = [{"path": item["path"], "line": item["line"], "qid": item["qid"],
                           "question": item["question"]} for item in historical
                          if code_pattern.search(item["question"])]
            groups.append({"connected_group": "qh2025-code-" + hashlib.sha256(fact["code"].encode()).hexdigest()[:16],
                "course_code": fact["code"], "course_name": fact["name"], "credits": fact["credits"],
                "prerequisite_codes": fact.get("prerequisite_codes"), "source_page": fact["page"],
                "source_chunk_id": fact["chunk_id"], "source_row_hash": fact["cells_sha256"],
                "exact_code_history_count": len(exact_code), "exact_code_history": exact_code,
                "code_alias_screened": alias,
                "top_history_questions": [{**source_rows[key], "cross_encoder_score": score_map[key]}
                                          for key in ranked[:12]]})
            if (number + 1) % 10 == 0:
                print(f"QH-2025 similarity groups: {number+1}/{len(facts)}", flush=True)
        provider.drain()
    finally:
        provider.close()
        provider.drain()

    after = source_identity(ROOT)
    report = {
        "schema_version": 1, "task": "P7-03-QH2025-history-screen",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "status": "DIAGNOSTIC_PRE_REVIEW", "release_eligible": False,
        "decision_status": "NO_EXPOSURE_DECISIONS_ASSIGNED",
        "history_occurrences": occurrence_count, "history_unique_questions": len(historical),
        "history_source_files": source_files,
        "history_inventory_sha256": queue["inputs"]["history_audit_sha256"],
        "source_validation_path": validation_path.relative_to(ROOT).as_posix(),
        "source_validation_sha256": sha256(validation_path),
        "source_index_manifest_sha256": source["source_index_manifest_sha256"],
        "source_identity_before": before, "source_identity_after": after,
        "source_stable": before == after, "model_identity": identity.to_dict(),
        "elapsed_seconds": time.perf_counter() - started,
        "method": "All question occurrences are hash-verified, then whitespace-identical questions are deduplicated before character 3-5 gram TF-IDF retrieves 40 distinct identity candidates. Exact code aliases with or without UET prefix have priority. The pinned local BGE reranker reorders candidates, with cache disabled. Only qid, source file/line and question text are retained; no answers, held-out outcomes, split labels or model results are read.",
        "groups": groups,
        "limitations": [
            "Similarity rankings are screening evidence only and do not determine exposure disposition.",
            "Exact course-code mentions are explicit potential exposure candidates for owner-authorized semantic review.",
            "No F0 split or held-out eligibility is assigned by this diagnostic.",
        ],
    }
    write_json(output_path, report)
    print(json.dumps({"status": report["status"], "history_occurrences": occurrence_count,
        "history_unique_questions": len(historical),
        "groups": len(groups), "exact_code_groups": sum(bool(g["exact_code_history_count"]) for g in groups),
        "source_stable": report["source_stable"], "elapsed_seconds": report["elapsed_seconds"],
        "report": output_path.relative_to(ROOT).as_posix()}, indent=2))
    return int(not report["source_stable"])


if __name__ == "__main__":
    raise SystemExit(main())
