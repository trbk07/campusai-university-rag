import hashlib
import json
from pathlib import Path

import pytest

from campusai.rag.schemas import PUBLIC_SCHEMA_VERSION, SCHEMA_VERSION
from evaluation.phase8.build_temporal_review_draft import build
from evaluation.phase8.score_temporal_product_outputs import _index_tree_sha256, score


def _perfect_predictions(rows):
    predictions = []
    for row in rows:
        if not row["answerable"]:
            internal = {
                "answer": "No supporting evidence was found.", "citations": [],
                "confidence": "low", "abstained": True,
                "abstention_reason": "no_evidence_found", "cache_hit": False,
                "claims": [], "evidence_status": "missing", "confidence_score": 0.1,
                "schema_version": SCHEMA_VERSION,
                "confidence_policy_version": "test-policy",
            }
            public = {
                "answer": internal["answer"], "citations": [], "confidence": "low",
                "abstained": True, "abstention_reason": "no_evidence_found", "claims": [],
                "schema_version": PUBLIC_SCHEMA_VERSION,
            }
        else:
            gold = row["gold_claims"][0]
            evidence = gold["evidence"][0]
            chunk = evidence["chunk_id"]
            doc_id = evidence["doc_id"]
            page = evidence["page"]
            page_range = evidence.get("page_range", [page, page])
            citation = {
                "chunk_id": chunk, "doc_id": doc_id, "page": page,
                "page_range": page_range, "quote": evidence["quote"],
                "source_name": "source.pdf",
            }
            answer = row.get("gold_answer")
            if answer is None:
                expected = row["expected_claims"][0]
                answer = (f"{expected['course_name']} is listed in semester {expected['semester']} "
                          f"and carries {expected['credits']} credits." if "multi_hop" in row.get("tags", [])
                          else f"{expected['course_name']} carries {expected['credits']} credits.")
            internal = {
                "answer": answer, "citations": [{**citation, "source_hash": doc_id}],
                "confidence": "high", "abstained": False, "abstention_reason": None,
                "cache_hit": False,
                "claims": [{"claim_id": gold["claim_id"], "text": gold["text"], "type": "fact",
                            "status": "supported", "citation_ids": [chunk],
                            "support_score": 1.0, "numeric_conflict": False}],
                "evidence_status": "found", "confidence_score": 0.9,
                "schema_version": SCHEMA_VERSION,
                "confidence_policy_version": "test-policy",
            }
            public = {
                "answer": internal["answer"], "citations": [citation], "confidence": "high",
                "abstained": False,
                "claims": [{"claim_id": gold["claim_id"], "text": gold["text"],
                            "type": "fact", "citation_ids": [chunk]}],
                "schema_version": PUBLIC_SCHEMA_VERSION,
            }
        predictions.append({
            "qid": row["qid"], "internal_response": internal,
            "public_response": public, "latency_ms": 100.0,
        })
    return predictions


def _write_inputs(tmp_path: Path, rows):
    benchmark_path = tmp_path / "benchmark.jsonl"
    benchmark_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    index_dir = tmp_path / "index"
    docs = {}
    for row in rows:
        for evidence in (row.get("gold_claims") or [{}])[0].get("evidence", []):
            doc_id = evidence["doc_id"]
            existing = docs.get(doc_id, {}).get(evidence['chunk_id'])
            if existing is not None:
                # A source chunk may contain many independently quoted rows.
                # Preserve them all instead of replacing it with the last quote.
                if evidence['quote'] not in existing['content']:
                    existing['content'] += '\n' + evidence['quote']
                continue
            docs.setdefault(doc_id, {})[evidence["chunk_id"]] = {
                "doc_id": doc_id,
                "chunk_id": evidence["chunk_id"],
                "page": evidence["page"],
                "page_range": evidence.get("page_range", [evidence["page"], evidence["page"]]),
                "metadata": {"page_range": evidence.get("page_range", [evidence["page"], evidence["page"]])},
                "content": evidence["quote"],
            }
    index_dir.mkdir(parents=True)
    for doc_id, items in docs.items():
        doc_dir = index_dir / doc_id
        doc_dir.mkdir()
        (doc_dir / "dense.json").write_text(json.dumps({"items": list(items.values())}), encoding="utf-8")
    (index_dir / "manifest.json").write_text(json.dumps({
        "documents": sorted(docs), "model_name": "test", "model_revision": "test"
    }), encoding="utf-8")
    return benchmark_path, index_dir


def test_saved_product_output_scoring_supports_combined_review_candidate(tmp_path):
    _temporal, _facts, rows, _report = build()
    benchmark_path, index_dir = _write_inputs(tmp_path, rows)
    report = score(rows, _perfect_predictions(rows), benchmark_path=benchmark_path,
                   index_dir=index_dir, bootstrap_iterations=100)

    assert report["status"] == "product_quality_scored_regression_only"
    assert report["gate_eligible"] is False
    assert report["provider_requests_by_scorer"] == 0
    assert report["benchmark"]["rows"] == 300
    assert report["metrics"]["exact_gold_answer_match"]["numerator"] == 30
    assert report["metrics"]["exact_gold_answer_match"]["denominator"] == 30
    assert report["metrics"]["required_code_accuracy"]["numerator"] == 20
    assert report["metrics"]["required_code_accuracy"]["denominator"] == 20
    assert report["metrics"]["grounded_claim_precision"]["value"] == 1.0
    assert report["metrics"]["citation_precision"]["value"] == 1.0
    assert report["metrics"]["citation_recall"]["value"] == 1.0
    assert report["metrics"]["schema_validity"]["numerator"] == 300
    assert report["metrics"]["answerable_false_abstention_rate"]["denominator"] == 145
    assert report["metrics"]["unanswerable_false_positive_rate"]["denominator"] == 155
    assert report["metrics"]["abstention_precision"]["numerator"] == 155
    assert report["metrics"]["abstention_precision"]["denominator"] == 155
    assert report["metrics"]["abstention_recall"]["numerator"] == 155
    assert report["metrics"]["abstention_recall"]["denominator"] == 155
    assert report["metrics"]["abstention_reason_accuracy"]["value"] is None
    assert report["metrics"]["abstention_reason_accuracy"]["status"].startswith("not_measured")
    assert report["grounding_metric_details"]["reason_accuracy"] is None
    assert report["metrics"]["semantic_answer_correctness"]["status"] == "not_measured_human_labels_required"
    assert report["metrics"]["semantic_answer_correctness"]["value"] is None
    assert report["metrics"]["peak_working_set_bytes"]["status"] == "not_measured_execution_manifest_required"
    assert report["metrics"]["index_size_bytes"]["status"] == "measured"
    assert report["runtime"]["index_size_bytes"] == report["metrics"]["index_size_bytes"]["value"]
    assert report["split_metrics"]["test"]["records"] == 140
    assert report["split_metrics"]["test"]["answerable_false_abstention_rate"]["denominator"] == 72
    assert report["split_metrics"]["holdout"]["records"] == 160
    assert report["split_metrics"]["holdout"]["unanswerable_false_positive_rate"]["denominator"] == 87
    assert report["split_metrics"]["test"]["citation_coordinate_validity"]["denominator"] > 0
    assert report["split_metrics"]["holdout"]["grounded_claim_recall"]["ci95"]["status"] == "measured"
    assert report["split_metrics"]["test"]["latency"]["ci95"]["status"] == "measured"
    assert report["latency"]["warm_ci95"]["status"] == "measured"
    assert report["metrics"]["schema_validity"]["ci95"]["status"] == "measured"
    assert report["category_metrics"]["single_hop_fact"]["metrics"]["records"] == 10
    assert report["category_metrics"]["table_or_calculation"]["metrics"]["records"] == 135
    assert report["category_metrics"]["prerequisite_or_multi_hop"]["metrics"]["records"] == 33
    assert report["category_metrics"]["temporal_or_comparison"]["metrics"]["records"] == 20
    assert report["category_metrics"]["unanswerable_or_adversarial"]["metrics"]["records"] == 155
    assert report["category_metrics"]["temporal_or_comparison"]["metrics"]["abstention_reason_accuracy"]["status"].startswith("not_measured")
    assert report["unmeasured"]["semantic_answer_correctness"].startswith("not_measured")
    assert report["unmeasured"]["abstention_reason_accuracy"].startswith("not_measured")


def test_recorded_chat_timings_are_never_labeled_live_provider_latency(tmp_path):
    _temporal, _facts, rows, _report = build()
    benchmark_path, index_dir = _write_inputs(tmp_path, rows)
    predictions = _perfect_predictions(rows)
    for prediction in predictions:
        prediction['mode'] = 'recorded_chat_replay'
    report = score(rows, predictions, benchmark_path=benchmark_path,
                   index_dir=index_dir, bootstrap_iterations=20)
    assert report['status'] == 'recorded_chat_replay_scored_regression_only'
    assert not report['gate_eligible']
    assert not report['latency']['live_provider_latency_measured']
    assert 'live_provider_end_to_end_latency' in report['unmeasured']
    assert 'not_live_provider' in report['split_metrics']['test']['latency']['scope']
    assert 'not_live_provider' in report['category_metrics']['single_hop_fact']['metrics']['latency']['scope']


def test_citation_recall_counts_missing_gold_and_excludes_hidden_diagnostics(tmp_path):
    _temporal, _facts, rows, _report = build()
    benchmark_path, index_dir = _write_inputs(tmp_path, rows)
    predictions = _perfect_predictions(rows)
    index = next(i for i, row in enumerate(rows) if row['answerable'])
    predictions[index]['internal_response']['abstained'] = True
    predictions[index]['public_response'].update(abstained=True, citations=[], claims=[],
                                                abstention_reason='unsupported_claim')
    # Internal rejected claims/citations remain for diagnosis; cannot raise recall.
    report = score(rows, predictions, benchmark_path=benchmark_path,
                   index_dir=index_dir, bootstrap_iterations=20)
    links = sum(len(c['evidence']) for row in rows for c in row.get('gold_claims', []))
    missing = sum(len(c['evidence']) for c in rows[index]['gold_claims'])
    assert report['metrics']['citation_recall']['denominator'] == links
    assert report['metrics']['citation_recall']['numerator'] == links - missing
    assert report['metrics']['citation_recall']['value'] < 1
    assert report['metrics']['citation_precision']['value'] == 1


def test_citation_identity_is_not_bilingual_lexical_claim_matching(tmp_path):
    _temporal, _facts, rows, _report = build()
    benchmark_path, index_dir = _write_inputs(tmp_path, rows)
    predictions = _perfect_predictions(rows)
    for pred in predictions:
        for contract in ('internal_response', 'public_response'):
            for claim in pred[contract]['claims']:
                claim.update(claim_id='model-id', text='Một cách diễn đạt khác ngôn ngữ.')
    report = score(rows, predictions, benchmark_path=benchmark_path,
                   index_dir=index_dir, bootstrap_iterations=20)
    assert report['metrics']['citation_precision']['value'] == 1
    assert report['metrics']['citation_recall']['value'] == 1
    assert report['metrics']['grounded_claim_precision']['value'] < 1


def test_abstention_precision_and_recall_use_prediction_populations(tmp_path):
    _temporal, _facts, rows, _report = build()
    benchmark_path, index_dir = _write_inputs(tmp_path, rows)
    predictions = _perfect_predictions(rows)
    answerable_qid = next(row["qid"] for row in rows if row["answerable"])
    unanswerable_qid = next(row["qid"] for row in rows if not row["answerable"])
    for prediction in predictions:
        if prediction["qid"] == answerable_qid:
            prediction["internal_response"].update({
                "abstained": True, "abstention_reason": "unsupported_claim", "claims": [], "citations": [],
            })
            prediction["public_response"].update({
                "abstained": True, "abstention_reason": "unsupported_claim", "claims": [], "citations": [],
            })
        elif prediction["qid"] == unanswerable_qid:
            prediction["internal_response"].update({
                "abstained": False, "abstention_reason": None,
                "answer": "unsupported", "claims": [], "citations": [],
            })
            prediction["public_response"].update({
                "abstained": False, "answer": "unsupported", "claims": [], "citations": [],
            })
    report = score(rows, predictions, benchmark_path=benchmark_path,
                   index_dir=index_dir, bootstrap_iterations=100)

    precision = report["metrics"]["abstention_precision"]
    recall = report["metrics"]["abstention_recall"]
    assert precision["numerator"] == 154 and precision["denominator"] == 155
    assert recall["numerator"] == 154 and recall["denominator"] == 155
    assert report["metrics"]["answerable_false_abstention_rate"]["numerator"] == 1
    assert report["metrics"]["unanswerable_false_positive_rate"]["numerator"] == 1


def test_abstention_reason_accuracy_is_scored_only_with_gold_labels(tmp_path):
    _temporal, _facts, rows, _report = build()
    benchmark_path, index_dir = _write_inputs(tmp_path, rows)
    labeled_qid = next(row["qid"] for row in rows if not row["answerable"])
    for row in rows:
        if row["qid"] == labeled_qid:
            row["gold_abstention_reason"] = "no_evidence_found"
    benchmark_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    report = score(rows, _perfect_predictions(rows), benchmark_path=benchmark_path,
                   index_dir=index_dir, bootstrap_iterations=100)

    metric = report["metrics"]["abstention_reason_accuracy"]
    assert metric["status"] == "measured"
    assert metric["numerator"] == 1 and metric["denominator"] == 1
    assert metric["value"] == 1.0


def test_scoring_fails_closed_on_missing_prediction_rows(tmp_path):
    _temporal, _facts, rows, _report = build()
    benchmark_path, index_dir = _write_inputs(tmp_path, rows)

    with pytest.raises(ValueError, match="one record per benchmark qid"):
        score(rows, _perfect_predictions(rows)[:-1], benchmark_path=benchmark_path,
              index_dir=index_dir, bootstrap_iterations=100)


def test_execution_manifest_binds_peak_memory_to_the_exact_scored_run(tmp_path):
    _temporal, _facts, rows, _report = build()
    benchmark_path, index_dir = _write_inputs(tmp_path, rows)
    predictions_path = tmp_path / "predictions.jsonl"
    predictions_path.write_text("".join(
        json.dumps(row, ensure_ascii=False) + "\n" for row in _perfect_predictions(rows)), encoding="utf-8")
    index_manifest_path = index_dir / "manifest.json"
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {
        "schema_version": 1, "status": "completed", "peak_working_set_bytes": 123456789,
        "measurement_method": "psutil.Process.memory_info().peak_wset",
        "bindings": {
            "benchmark_sha256": digest(benchmark_path),
            "predictions_sha256": digest(predictions_path),
            "index_manifest_sha256": digest(index_manifest_path),
            "index_tree_sha256": _index_tree_sha256(index_dir),
        },
    }
    manifest_path = tmp_path / "execution-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = score(rows, _perfect_predictions(rows), benchmark_path=benchmark_path,
                   index_dir=index_dir, execution_manifest_path=manifest_path,
                   predictions_path=predictions_path, bootstrap_iterations=100)

    metric = report["metrics"]["peak_working_set_bytes"]
    assert metric["status"] == "measured"
    assert metric["value"] == 123456789
    assert metric["execution_manifest_sha256"] == digest(manifest_path)
    assert "peak_working_set_bytes" not in report["unmeasured"]

    predictions_path.write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="bindings do not match"):
        score(rows, _perfect_predictions(rows), benchmark_path=benchmark_path,
              index_dir=index_dir, execution_manifest_path=manifest_path,
              predictions_path=predictions_path, bootstrap_iterations=100)


def test_daily_worker_cold_starts_are_excluded_from_warm_latency(tmp_path):
    _temporal, _facts, rows, _report = build()
    benchmark_path, index_dir = _write_inputs(tmp_path, rows)
    predictions = _perfect_predictions(rows)
    for i, prediction in enumerate(predictions):
        prediction.update(runtime_id="day-one" if i < 150 else "day-two", cold_start=i in {0, 150})
        prediction["latency_ms"] = 50000.0 if prediction["cold_start"] else 100.0
    report = score(rows, predictions, benchmark_path=benchmark_path, index_dir=index_dir,
                   bootstrap_iterations=100)
    assert report["latency"]["cold_start_values_ms"] == [50000.0, 50000.0]
    assert report["latency"]["warm_requests"] == 298
    assert report["latency"]["warm_p99_ms"] == 100.0
    predictions[150]["cold_start"] = False
    with pytest.raises(ValueError, match="first request of each runtime"):
        score(rows, predictions, benchmark_path=benchmark_path, index_dir=index_dir,
              bootstrap_iterations=100)


def test_freeze_review_is_bound_to_exact_scored_benchmark(tmp_path):
    from evaluation.phase8.repair_reviewed_benchmark import FREEZE, OUT, ROOT
    rows = [json.loads(line) for line in (ROOT / OUT).read_text(encoding="utf-8").splitlines()]
    benchmark_path, index_dir = _write_inputs(tmp_path, rows)
    benchmark_path.write_bytes((ROOT / OUT).read_bytes())
    benchmark_path.write_bytes((ROOT / OUT).read_bytes())
    report = score(rows, _perfect_predictions(rows), benchmark_path=benchmark_path, index_dir=index_dir,
                   freeze_manifest_path=ROOT / FREEZE, bootstrap_iterations=100)
    assert report["benchmark"]["owner_review"] == "owner_delegated_ai_complete"
    assert report["benchmark"]["officially_approved"] is False
    rows[0]["question"] += " changed"
    benchmark_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    with pytest.raises(ValueError, match="freeze does not bind"):
        score(rows, _perfect_predictions(rows), benchmark_path=benchmark_path, index_dir=index_dir,
              freeze_manifest_path=ROOT / FREEZE, bootstrap_iterations=100)
