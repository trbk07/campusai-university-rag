"""Controlled faults on a live isolated service, recorded through the collector."""
from __future__ import annotations

from dataclasses import replace
import time
import uuid

from campusai.rag.service import CampusAIQueryService
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.retrieval.canary_rollout import CanaryController
from campusai.retrieval.hybrid import RetrievalResult
from evaluation.reranker.canary_telemetry import CanaryWindowRecorder

FAULTS = {
    "provenance_error": "corrupt_returned_chunk_content",
    "scope_leakage": "return_frozen_evidence_outside_requested_scope",
    "citation_error": "corrupt_returned_page_range",
    "timeout_budget": "delay_actual_model_prediction_past_request_timeout",
    "negative_fpr_budget": "return_frozen_evidence_for_unanswerable_questions",
    "error_rate_regression": "raise_at_service_response_boundary",
    "memory_budget": "reduce_configured_ram_budget_below_measured_process_rss",
    "latency_budget_three_windows": "delay_service_response_past_latency_budget",
}


def frozen_result(item):
    return RetrievalResult(item["chunk_id"], item["doc_id"], item["page"], item["content"],
                           item.get("content_type", "text"), .5, "controlled_staging_fault", dict(item.get("metadata", {})))


class FaultService:
    """Inject at explicit boundaries while retaining the real service/controller."""
    def __init__(self, service, kind, evidence):
        self.service, self.kind, self.evidence = service, kind, evidence
        self.retriever, self.canary = service.retriever, service.canary
        self.calls = 0
        self.negative_questions = set()

    def seed(self, doc_ids, filters, *, outside=False):
        for (doc_id, _), item in self.evidence.items():
            if (doc_id not in doc_ids if outside else doc_id in doc_ids) and all(
                str(item.get("metadata", {}).get(key, "")).casefold() == str(value).casefold()
                for key, value in (filters or {}).items()):
                return frozen_result(item)
        raise ValueError("frozen evidence unavailable for controlled scope/filter fault")

    def retrieve(self, question, **kwargs):
        self.calls += 1
        if self.kind == "latency_budget_three_windows":
            time.sleep(1.01)
        values = self.service.retrieve(question, **kwargs)
        if self.kind == "error_rate_regression":
            raise RuntimeError("controlled staging response failure")
        if self.kind == "negative_fpr_budget" and question in self.negative_questions:
            return [self.seed(kwargs["doc_ids"], kwargs.get("filters"))]
        if self.kind == "scope_leakage":
            return [self.seed(kwargs["doc_ids"], {}, outside=True)]
        if self.kind in {"provenance_error", "citation_error"}:
            item = values[0] if values else self.seed(kwargs["doc_ids"], kwargs.get("filters"))
            if self.kind == "provenance_error":
                item = replace(item, content=item.content + "\nCONTROLLED_STAGING_CORRUPTION")
            else:
                item = replace(item, metadata={**item.metadata, "page_range": [999, 999]})
            return [item]
        return values


def admitted_id(controller, prefix):
    for counter in range(10000):
        identity = f"{prefix}-{counter}"
        if controller.admits(identity):
            return identity
    raise ValueError("no admitted traffic cohort for fault exercise")


def run_fault_exercises(factory, baseline, evidence, rows, healthy_windows, *, ram_limit_bytes, requests=100, checkpoint=None):
    """No synthetic window metrics: every exercise executes >=100 real requests.

The memory exercise changes the configured alert budget, not the measured RSS.
It verifies the alert/rollback path without allocating most of the host RAM.
"""
    if requests < 100 or not rows:
        raise ValueError("at least 100 requests and a reviewed workload required")
    workload = rows * max(1, (requests + len(rows) - 1) // len(rows))
    # A known frozen document remains available outside a restricted
    # scope, so this exercise isolates scope from provenance failure.
    known_docs = {doc for doc, _ in evidence}
    scoped = [row for row in rows if set(row["doc_ids"]) < known_docs]
    if not scoped:
        raise ValueError("reviewed scope-restricted workloads required for scope exercise")
    cohorts = [next((row for row in scoped if predicate(row)), None) for predicate in (
        lambda r: not r["answerable"], lambda r: r["answerable"] and r["difficulty"] == "easy",
        lambda r: r["answerable"] and r["difficulty"] == "hard")]
    if any(row is None for row in cohorts):
        raise ValueError("scope exercise needs reviewed easy/hard/negative restricted queries")
    scoped_workload = cohorts * ((requests + 2) // 3)
    exercises = []
    for kind, injection in FAULTS.items():
        controller = CanaryController()
        for window in healthy_windows:
            if controller.observe(window):
                raise ValueError("healthy promotion history contains rollback")
        if controller.traffic_percent != 25:
            raise ValueError("fault exercises require completed live 25% rollout")
        retriever = factory()
        if not retriever.phase7_enabled:
            raise ValueError("live fault activation rejected")
        provider = retriever.phase7_provider
        service = CampusAIQueryService(retriever, GroundedAnswerGenerator(), canary=controller)
        fault = FaultService(service, kind, evidence)
        fault.negative_questions = {row["question"] for row in rows if not row["answerable"]}
        fault_rows = scoped_workload if kind == "scope_leakage" else workload
        budget = ram_limit_bytes
        if kind == "memory_budget":
            import psutil
            budget = max(1, psutil.Process().memory_info().rss // 2)
        recorder = CanaryWindowRecorder(fault, baseline, evidence, ram_limit_bytes=budget)
        windows = []
        run_id = uuid.uuid4().hex
        try:
            if kind == "timeout_budget":
                provider.warm_up()
                model = provider._model
                delay = provider.timeout_ms / 1000 + .1
                class DelayedModel:
                    def predict(self, *args, **kwargs):
                        time.sleep(delay)
                        return model.predict(*args, **kwargs)
                provider._model = DelayedModel()
            for number in range(3 if kind == "latency_budget_three_windows" else 1):
                recorder.start()
                for i, row in enumerate(fault_rows):
                    request_id = admitted_id(controller, f"{run_id}-{number}-{i}")
                    recorder.retrieve(row, request_id=request_id)
                window = recorder.finish()
                observed_reason = service.observe_canary_window(window)
                window["observed_rollback_reason"] = observed_reason
                windows.append(window)
                if observed_reason:
                    break
            before = provider.metrics_snapshot()["submitted_requests"]
            probes = []
            for row in rows[:3]:
                kwargs = {"doc_ids": row["doc_ids"], "filters": row.get("filters"), "top_k": 5}
                expected = [r.to_dict() for r in baseline.search(row["question"], mode="auto", **kwargs)]
                # Direct mode exercises disabled runtime admission independently
                # of the controller returning to zero-percent traffic.
                output = [r.to_dict() for r in retriever.search(row["question"], mode="phase7", **kwargs)]
                probes.append({"qid": row["qid"], "output": output, "baseline": expected})
            after = provider.metrics_snapshot()["submitted_requests"]
            metrics = provider.metrics_snapshot()
            exercise = {"expected_reason": kind, "observed_reason": observed_reason, "injection": injection,
                        "cohort": "admitted_only_for_controlled_faults", "windows": windows,
                        "injected_service_calls": fault.calls, "service_phase7_enabled_after": retriever.phase7_enabled,
                        "provider_closed_after": metrics["closed"], "provider_calls_before_followup": before,
                        "provider_calls_after_followup": after, "new_reranker_calls_after": after - before,
                        "followup_probes": probes}
            exercises.append(exercise)
            if checkpoint:
                checkpoint(exercises)
            if (observed_reason != kind or retriever.phase7_enabled or not metrics["closed"] or before != after
                    or any(probe["output"] != probe["baseline"] for probe in probes)):
                raise ValueError("live rollback exercise failed: " + kind)
        finally:
            recorder.close()
            service.close()
            provider.close()
            provider.drain()
    return exercises
