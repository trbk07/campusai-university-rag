from copy import deepcopy

from evaluation.reranker.collect_context_lifecycle import lifecycle_summary, coordinates
from evaluation.reranker.supplemental_gates import context_errors


def proof():
    cold = dict(model_loads=0, inference_calls=0)
    warm = dict(model_loads=1, inference_calls=1)
    requests = dict(model_loads=1, inference_calls=4)
    return dict(before=cold, after_warm=warm, after_requests=requests,
                before_closed_request=requests, after_closed_request=requests,
                before_failed_request=cold, after_failed_request=cold,
                after_drain=dict(submitted_requests=4, completed_requests=4,
                                 cancelled_requests=0, active_requests=0),
                baseline_phase6=[dict(chunk_id="source")], warm_failure_phase6=[dict(chunk_id="source")])


def test_summary_uses_actual_counter_differences():
    summary = lifecycle_summary(proof())
    assert summary["startup_loads"] == 1
    assert summary["request_loads"] == 0
    assert summary["request_inference_calls"] == 3
    assert summary["pending_after_drain"] == 0
    changed = deepcopy(proof())
    changed["after_closed_request"] = dict(model_loads=1, inference_calls=5)
    assert lifecycle_summary(changed)["closed_new_inference"] == 1


def test_context_gate_rejects_counter_summary_forgery_and_source_mismatch():
    observations = dict(schema_version=2, evidence_type="physical_dev_context_lifecycle",
                        lifecycle_proof=proof(), lifecycle=lifecycle_summary(proof()))
    fields = ("source_sha256", "runtime_sha256", "model_identity_sha256", "index_sha256")
    observations.update({key: "a" * 64 for key in fields})
    report = {"observations": observations, **{key: "a" * 64 for key in fields}}
    observations["lifecycle"]["request_inference_calls"] = 100
    assert context_errors(report) == ["lifecycle_counter_replay"]
    observations["lifecycle"] = lifecycle_summary(proof())
    observations["source_sha256"] = "b" * 64
    assert context_errors(report) == ["context_measurement_binding:source_sha256"]
