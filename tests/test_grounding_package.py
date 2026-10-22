from evaluation.release.grounding_package import _require_pass, validate_annotation_signoff


def approved_signoff():
    return {
        "status": "approved", "benchmark_sha256": "bench",
        "records_total": 400, "records_reviewed": 400, "records_approved": 400,
        "split_leakage": 0, "missing_gold_evidence": 0, "missing_abstention_reason": 0,
        "creator_ids": ["builder-1"],
        "reviewers": [{"id": "reviewer-2", "independent": True, "records_reviewed": 400,
                       "attestation": "I independently reviewed the frozen benchmark.",
                       "signed_at": "2026-09-30T00:00:00Z"}],
    }


def test_legacy_annotation_summary_accepts_its_summary_fields_only():
    assert validate_annotation_signoff(approved_signoff(), "bench") == []


def test_annotation_signoff_rejects_self_review_and_checksum_change():
    value = approved_signoff()
    value["reviewers"][0]["id"] = "builder-1"
    errors = validate_annotation_signoff(value, "different")
    assert "annotation_creator_reviewer_overlap" in errors
    assert "annotation_benchmark_checksum_mismatch" in errors


def test_boolean_evidence_gate_does_not_treat_false_as_numeric_zero_pass():
    errors = _require_pass({"status": "pass", "safe": False}, "security", ("safe",))
    assert errors == ["security_safe_not_pass"]


def test_package_binds_a_versioned_benchmark_without_overwriting_original(tmp_path, monkeypatch):
    import hashlib
    import json
    from evaluation.release import grounding_package as package
    benchmark_dir = tmp_path / "data/benchmark"
    benchmark_dir.mkdir(parents=True)
    original = benchmark_dir / "grounding_reviewed.jsonl"
    original.write_text('original historical bytes\n', encoding="utf-8")
    original_bytes = original.read_bytes()
    revision = benchmark_dir / "grounding_reviewed_v2.jsonl"
    revision.write_text('reviewed revision bytes\n', encoding="utf-8")
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"policy_version": "grounding-v1", "schema_version": "grounding-public-v2",
                                    "thresholds_frozen": True}), encoding="utf-8")
    calibration = tmp_path / "calibration.json"
    calibration.write_text('{"artifact_sha256":"unit-calibration"}', encoding="utf-8")
    (tmp_path / "uv.lock").write_text('unit lock', encoding="utf-8")
    bundle = tmp_path / "package"
    bundle.mkdir()
    for filename in package.REQUIRED_ARTIFACTS.values():
        (bundle / filename).write_text('{}', encoding="utf-8")
    monkeypatch.setattr(package, "git_fingerprint", lambda _root: ("unit-commit", False))
    manifest = package.build_manifest(bundle, root=tmp_path, release_candidate="phase5-rc-unit",
                                     benchmark=revision, calibration=calibration, config=settings)
    assert manifest["benchmark_path"] == "data/benchmark/grounding_reviewed_v2.jsonl"
    assert manifest["benchmark_sha256"] == hashlib.sha256(revision.read_bytes()).hexdigest()
    (bundle / "release_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    result = package.validate_package(bundle, root=tmp_path, check_repository=False)
    assert "benchmark_source_checksum_mismatch" not in result["errors"]
    assert "benchmark_source_path_invalid" not in result["errors"]
    assert original.read_bytes() == original_bytes
    # Package still fails its other gates; the fixture supplies no real release evidence.
    assert result["status"] == "fail"


def test_package_rejects_benchmark_and_artifact_paths_outside_their_roots(tmp_path):
    import json
    from evaluation.release.grounding_package import validate_package
    bundle = tmp_path / "package"
    bundle.mkdir()
    (tmp_path / "outside.json").write_text('{}', encoding="utf-8")
    (bundle / "release_manifest.json").write_text(json.dumps({"benchmark_path": "../outside.json",
        "artifacts": {"grounding_report": {"path": "../outside.json"}}}), encoding="utf-8")
    result = validate_package(bundle, root=tmp_path, check_repository=False)
    assert "benchmark_source_path_invalid" in result["errors"]
    assert "artifact_grounding_report_path_outside_package" in result["errors"]
