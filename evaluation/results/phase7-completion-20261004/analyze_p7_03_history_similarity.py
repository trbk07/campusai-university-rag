"""Build a dev-safe, history-wide lexical/cross-encoder similarity audit."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import time

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "evaluation/results/phase7-completion-20261004"
QUEUE = TASK / "p7-03_semantic_review_queue.json"
SMOKE = TASK / "p7-07-cuda-snapshot-smoke.json"
OUT = TASK / "p7-03-history-similarity-preflight.json"


def main() -> int:
    from campusai.retrieval.cross_encoder_provider import (
        ModelIdentity, OfflineCrossEncoderReranker, RerankCandidate, snapshot_sha256,
    )
    from evaluation.common.release_artifacts import sha256, source_identity, write_json
    from sklearn.feature_extraction.text import TfidfVectorizer

    if OUT.exists():
        raise FileExistsError(OUT)
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
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

    groups = queue["groups"]
    target_texts = []
    for group in groups:
        facts = group["facts"]
        fields = []
        for fact in facts:
            fields.extend([fact.get("code", ""), fact.get("name", ""),
                           "credits " + str(fact.get("credits", "")),
                           "prerequisites " + str(fact.get("prerequisite_codes", ""))])
        target_texts.append(" ".join(value for value in fields if value))
    corpus = [item["question"] for item in historical] + target_texts
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2,
                                 sublinear_tf=True, strip_accents=None, max_features=250000)
    matrix = vectorizer.fit_transform(corpus)
    history_matrix = matrix[:len(historical)]
    target_matrix = matrix[len(historical):]

    smoke = json.loads(SMOKE.read_text(encoding="utf-8"))
    base_identity = ModelIdentity(**smoke["model_identity"])
    from dataclasses import replace
    identity = replace(base_identity, input_format="body")
    model_dir = ROOT / ".tmp/phase7-models" / identity.model_revision
    if snapshot_sha256(model_dir) != identity.model_sha256:
        raise ValueError("frozen reranker snapshot hash mismatch")
    provider = OfflineCrossEncoderReranker(identity, model_dir, timeout_ms=60000,
                                           candidate_cap=40, score_cache_size=0)
    started = time.perf_counter()
    results = []
    try:
        provider.warm_up()
        for number, group in enumerate(groups):
            similarities = (target_matrix[number] @ history_matrix.T).toarray().ravel()
            top_indexes = similarities.argsort()[::-1][:40]
            candidates = []
            source_rows = {}
            for rank, index in enumerate(top_indexes, 1):
                item = historical[int(index)]
                key = hashlib.sha256(f"{item['path']}\0{item['line']}\0{item['question']}".encode()).hexdigest()
                candidate_id = "history-" + key[:24]
                candidate = RerankCandidate(candidate_id, "history-" + key[:16], candidate_id,
                    1, item["question"], rank, float(similarities[index]))
                candidates.append(candidate)
                source_rows[candidate_id] = {**item, "lexical_cosine": float(similarities[index])}
            target_query = target_texts[number]
            scores = provider.score(target_query, candidates) if candidates else []
            score_map = {item.candidate_id: item.reranker_score for item in scores}
            ranked = sorted(source_rows, key=lambda key: (-score_map.get(key, float("-inf")), key))
            results.append({
                "connected_group": group["connected_group"],
                "course_codes": sorted({fact["code"] for fact in group["facts"]}),
                "source_fact_hashes": sorted({fact["source_content_sha256"] for fact in group["facts"]}),
                "target_text": target_query,
                "review_flags": group.get("manual_review_flags", []),
                "top_history_questions": [{**source_rows[key], "cross_encoder_score": score_map[key]}
                                          for key in ranked[:12]],
            })
            if (number + 1) % 10 == 0:
                print(f"similarity groups: {number+1}/{len(groups)}", flush=True)
        provider.drain()
    finally:
        provider.close()
        provider.drain()

    after = source_identity(ROOT)
    report = {
        "schema_version": 1, "task": "P7-03", "status": "DIAGNOSTIC_PRE_REVIEW",
        "release_eligible": False, "decision_status": "NO_EXPOSURE_DECISIONS_ASSIGNED",
        "history_occurrences": len(historical), "history_source_files": source_files,
        "history_inventory_sha256": queue["inputs"]["history_audit_sha256"],
        "candidate_queue_sha256": sha256(QUEUE), "candidate_groups": len(groups),
        "index_manifest_sha256": queue["inputs"]["index_manifest_sha256"],
        "dev_packet_sha256": queue["inputs"]["dev_packet_sha256"],
        "model_identity": identity.to_dict(), "source_identity_before": before,
        "source_identity_after": after, "source_stable": before == after,
        "elapsed_seconds": time.perf_counter() - started,
        "method": "Character 3-5 gram TF-IDF retrieves top 40 from complete question-only history; pinned BGE cross-encoder reranks each candidate group. No answers, held-out outputs, split labels, or retrieval/model outcomes are used.",
        "groups": results,
        "limitations": [
            "Similarity rankings are screening evidence only. They do not establish independence or exposure disposition.",
            "Every proposed group still receives an explicit project-owner-authorized semantic decision with source/history rationale before F0.",
            "This output contains history question text only and is not a frozen split or human benchmark export.",
        ],
    }
    write_json(OUT, report)
    print(json.dumps({"status": report["status"], "history_occurrences": len(historical),
                      "groups": len(results), "source_stable": report["source_stable"],
                      "elapsed_seconds": report["elapsed_seconds"], "report": OUT.as_posix()}, indent=2))
    return int(not report["source_stable"])


if __name__ == "__main__":
    raise SystemExit(main())
