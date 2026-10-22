import pytest
import json

from evaluation.grounding.calibrate_confidence import fit_report, risk_at_coverage
from evaluation.grounding.calibrate_confidence import _score
from campusai.rag.calibration import load_calibration_artifact


def test_calibration_fits_dev_and_keeps_test_holdout_separate():
    rows = []
    for split in ("dev", "test", "holdout"):
        rows.extend([
            {"split": split, "confidence_score": 0.1, "answerable": False, "abstained": True},
            {"split": split, "confidence_score": 0.9, "answerable": True, "abstained": False},
        ])
    result = fit_report({"rows": rows})
    assert result["version"] == "grounding-isotonic-v1"
    assert result["metrics"]["holdout"]["count"] == 2
    assert len(result["artifact_sha256"]) == 64


def test_calibration_requires_dev_split():
    with pytest.raises(ValueError, match="dev split"):
        fit_report({"rows": [{"split": "holdout", "confidence_score": 0.5}]})


def test_calibration_rejects_degenerate_holdout():
    rows = []
    for split in ("dev", "test"):
        rows.extend([
            {"split": split, "confidence_score": 0.1, "answerable": False, "abstained": True},
            {"split": split, "confidence_score": 0.9, "answerable": True, "abstained": False},
        ])
    rows.extend([
        {"split": "holdout", "confidence_score": 0.1, "answerable": False, "abstained": True},
        {"split": "holdout", "confidence_score": 0.2, "answerable": False, "abstained": True},
    ])
    with pytest.raises(ValueError, match="holdout split"):
        fit_report({"rows": rows})


def test_abstention_without_score_calibrates_as_zero_confidence():
    assert _score({"abstained": True, "confidence": "low"}) == 0.0


def test_runtime_calibration_uses_the_exact_raw_score_persisted_for_fitting():
    from campusai.rag.calibration import IsotonicCalibrator
    from campusai.rag.confidence import score_confidence
    calibrator = IsotonicCalibrator((0.9, 1.0), (0.2, 0.9))
    result = score_confidence(retrieval_support=0.666667, claim_entailment=1.0,
        citation_completeness=1.0, calibrator=calibrator)
    assert result.raw_score == 0.9
    assert result.score == calibrator.predict(result.raw_score) == 0.2


@pytest.mark.parametrize("source_pages", [False, True])
def test_answer_cache_separates_calibrators_with_the_same_version(source_pages):
    from campusai.rag.calibration import IsotonicCalibrator
    from campusai.rag.grounding import GroundedAnswerGenerator
    from campusai.rag.service import CampusAIQueryService
    from tests.test_basic_rag import FakeLLM, FakeRetriever, evidence, valid_payload
    llm = FakeLLM(valid_payload())
    generator = GroundedAnswerGenerator(llm, calibrator=IsotonicCalibrator((1.0,), (0.2,)))
    service = CampusAIQueryService(FakeRetriever([evidence()]), generator)
    def ask():
        if source_pages:
            return service.ask_source_pages("Which course is required?", [evidence()])
        return service.ask("Which course is required?", corpus_version="constant-source")
    try:
        first = ask()
        assert first.confidence_score == 0.2
        generator.calibrator = IsotonicCalibrator((1.0,), (0.9,))
        second = ask()
        assert second.confidence_score == 0.9 and not service.last_cache_hit and llm.calls == 2
        cached = ask()
        assert cached.confidence_score == 0.9 and service.last_cache_hit and llm.calls == 2
        assert cached.policy_version == generator.calibrator.version
        generator.calibrator = None
        uncalibrated = ask()
        assert uncalibrated.confidence_score != 0.9 and not service.last_cache_hit and llm.calls == 3
    finally:
        service.close()


@pytest.mark.parametrize("multiple_documents", [False, True])
def test_local_credit_calculations_apply_the_same_pinned_calibrator(multiple_documents):
    from campusai.rag.calibration import IsotonicCalibrator
    from campusai.rag.grounding import GroundedAnswerGenerator
    from tests.test_credit_sum_grounding import NoGeneration, evidence
    calibrator = IsotonicCalibrator((1.0,), (0.7,))
    generator = GroundedAnswerGenerator(NoGeneration(), calibrator=calibrator)
    kwargs = {}
    if multiple_documents:
        from tests.test_multi_hop_evidence import arithmetic, row, Search
        from campusai.rag.multi_hop_evidence import retrieve_composition
        results, trace = retrieve_composition(arithmetic(),
            Search([[row('a', 'CS201', 3), row('b', 'CS202', 4)]]),
            filters=None, mode='hybrid', top_k=5)
        kwargs['multi_hop_context'] = trace
    else:
        results = [evidence(), evidence('CS202', '4', 'b')]
    result = generator.answer('What is the total credits for CS201 and CS202?', results, 'en', **kwargs)
    assert not result.abstained and result.confidence_score == 0.7
    assert result.policy_version == calibrator.version


@pytest.mark.parametrize('mutation', ['path-only', 'checksum-only', 'wrong-checksum', 'non-dev-fit', 'invalid-benchmark'])
def test_serving_rejects_invalid_answer_calibration_before_loading_dependencies(tmp_path, monkeypatch, mutation):
    from scripts.operations import serve
    fitted = fit_report({'benchmark_sha256': 'a' * 64, 'rows': [
        {'split': 'dev', 'confidence_score': 0.1, 'answerable': False, 'abstained': True},
        {'split': 'dev', 'confidence_score': 0.9, 'answerable': True, 'abstained': False}]})
    path = tmp_path / 'calibration.json'
    if mutation == 'non-dev-fit':
        fitted['fit_split'] = 'holdout'
    elif mutation == 'invalid-benchmark':
        fitted['benchmark_sha256'] = 'z' * 64
    path.write_text(json.dumps(fitted), encoding='utf-8')
    monkeypatch.setenv('CAMPUSAI_ANSWER_CALIBRATION', str(path))
    monkeypatch.setenv('CAMPUSAI_ANSWER_CALIBRATION_SHA256', fitted['artifact_sha256'])
    if mutation == 'path-only':
        monkeypatch.delenv('CAMPUSAI_ANSWER_CALIBRATION_SHA256')
    elif mutation == 'checksum-only':
        monkeypatch.delenv('CAMPUSAI_ANSWER_CALIBRATION')
    elif mutation == 'wrong-checksum':
        monkeypatch.setenv('CAMPUSAI_ANSWER_CALIBRATION_SHA256', 'wrong')
    monkeypatch.setattr(serve, 'HybridRetriever', lambda *_a, **_k: pytest.fail('retriever loaded before verification'))
    monkeypatch.setattr(serve, 'create_llm', lambda *_a, **_k: pytest.fail('provider loaded before verification'))
    with pytest.raises(ValueError):
        serve.build_application()


def test_serving_passes_the_pinned_answer_calibrator_to_actual_query_service(tmp_path, monkeypatch):
    from scripts.operations import serve
    from tests.test_basic_rag import FakeLLM, FakeRetriever, evidence, valid_payload
    fitted = fit_report({'benchmark_sha256': 'a' * 64, 'rows': [
        {'split': 'dev', 'confidence_score': 0.1, 'answerable': False, 'abstained': True},
        {'split': 'dev', 'confidence_score': 0.9, 'answerable': True, 'abstained': False}]})
    path = tmp_path / 'calibration.json'
    path.write_text(json.dumps(fitted), encoding='utf-8')
    monkeypatch.setenv('CAMPUSAI_ANSWER_CALIBRATION', str(path))
    monkeypatch.setenv('CAMPUSAI_ANSWER_CALIBRATION_SHA256', fitted['artifact_sha256'])
    monkeypatch.setenv('CAMPUSAI_LLM_CONFIG', 'unit-profile')
    monkeypatch.setenv('CAMPUSAI_RETRIEVAL_CALIBRATION', str(tmp_path / 'absent'))
    monkeypatch.setenv('CAMPUSAI_INDEX_DIR', str(tmp_path / 'index'))
    monkeypatch.setenv('CAMPUSAI_STORE_DIR', str(tmp_path / 'store'))
    monkeypatch.setenv('CAMPUSAI_JOB_DB', str(tmp_path / 'jobs.sqlite3'))
    monkeypatch.delenv('CAMPUSAI_RAG_CACHE_PATH', raising=False)
    monkeypatch.setattr(serve, 'HybridRetriever', lambda *_a, **_k: FakeRetriever([evidence()]))
    monkeypatch.setattr(serve, 'create_llm', lambda *_a, **_k: FakeLLM(valid_payload()))
    monkeypatch.setattr(serve, '_read_config', lambda *_a, **_k: {'rag': {}})
    application = serve.build_application()
    try:
        response = application.query_service.ask('Which course is required?', language='en')
        assert not response.abstained and response.confidence_score == 1.0
        assert response.policy_version == 'grounding-isotonic-v1'
        assert application.query_service.answer_generator.calibrator is not None
    finally:
        application.close()


def test_calibration_rejects_non_monotonic_or_non_finite_artifact():
    from campusai.rag.calibration import IsotonicCalibrator
    with pytest.raises(ValueError, match="invalid calibration artifact"):
        IsotonicCalibrator.from_dict({
            "version": "grounding-isotonic-v1",
            "thresholds": [0.2, float("nan")],
            "values": [0.5, 0.4],
        })


def test_calibration_artifact_is_verified_before_runtime_use(tmp_path):
    result = fit_report({"rows": [
        {"split": "dev", "confidence_score": 0.1, "answerable": False, "abstained": True},
        {"split": "dev", "confidence_score": 0.9, "answerable": True, "abstained": False},
    ]})
    path = tmp_path / "calibration.json"
    path.write_text(json.dumps(result), encoding="utf-8")
    calibrator, digest = load_calibration_artifact(path, expected_sha256=result["artifact_sha256"])
    assert calibrator.version == "grounding-isotonic-v1"
    assert digest == result["artifact_sha256"]
    result["artifact"]["values"][0] = 1.0
    path.write_text(json.dumps(result), encoding="utf-8")
    with pytest.raises(ValueError, match="checksum"):
        load_calibration_artifact(path)


def test_risk_at_coverage_isolated_to_holdout_and_tie_deterministic():
    from campusai.rag.calibration import IsotonicCalibrator

    calibrator = IsotonicCalibrator.fit([0.1, 0.9], [False, True])
    rows = [
        {"id": "dev-bad", "split": "dev", "confidence_score": 0.9,
         "answerable": False, "abstained": False},
        {"id": "holdout-a", "split": "holdout", "confidence_score": 0.9,
         "answerable": True, "abstained": False},
        {"id": "holdout-b", "split": "holdout", "confidence_score": 0.9,
         "answerable": True, "abstained": False},
        {"id": "holdout-c", "split": "holdout", "confidence_score": 0.9,
         "answerable": True, "abstained": False},
        {"id": "holdout-d", "split": "holdout", "confidence_score": 0.9,
         "answerable": True, "abstained": False},
        {"id": "holdout-e", "split": "holdout", "confidence_score": 0.1,
         "answerable": False, "abstained": True},
    ]
    assert risk_at_coverage(rows, calibrator, 0.8) == 0.0
