"""Freeze and collect one paired primary quality experiment; no fitting or retry."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import zipfile

from evaluation.common.release_artifacts import read_json, sha256, source_identity, write_json
from evaluation.benchmarks.human_benchmark_intake import digest_record
from scripts.benchmarks.product_quality_pilot import ROOT, BASE, PROFILE, CONFIG
from scripts.benchmarks.product_performance import ENDPOINT, available_output, read_json_config
from scripts.benchmarks.product_retry import (Budget, output_token_cap, packet_usage,
                                               validate_retry)

RUBRIC = BASE / "product-primary-source-rubric-20261009.json"
PROTOCOL = BASE / "product-primary-protocol-20261008.json"
BASELINE_TREE = ROOT / ".local_artifacts/experiment_runs/product-prehardening-dfe1c229-20261008"
WORKER = ROOT / "scripts/benchmarks/product_primary_worker.py"


def verify_baseline(archive):
    path = Path(archive["path"])
    if sha256(path) != archive["sha256"]:
        raise ValueError("baseline archive changed")
    with zipfile.ZipFile(path) as z:
        files = [v for v in z.infolist() if not v.is_dir()]
        names = {v.filename for v in files}
        if any(p.relative_to(BASELINE_TREE).as_posix() not in names
               for p in BASELINE_TREE.rglob("*.py") if "__pycache__" not in p.parts):
            raise ValueError("unarchived baseline source file")
        for item in files:
            target = (BASELINE_TREE / item.filename).resolve()
            if not target.is_relative_to(BASELINE_TREE.resolve()) or target.read_bytes() != z.read(item):
                raise ValueError("extracted baseline source changed")
    return len(files)


def paired_schedule(rows):
    rng = random.Random(7)
    result = []
    for row in rows:
        arms = ["baseline", "current"]
        rng.shuffle(arms)
        result.extend({"arm": arm, "qid": row["qid"]} for arm in arms)
    return result


def validate_packet(packet):
    rows = packet["rows"]
    binding = packet["rubric"]
    if sha256(Path(binding["path"])) != binding["sha256"]:
        raise ValueError("source rubric changed")
    rubric = {r["qid"]: r for r in read_json(Path(binding["path"]))["rows"]}
    qids = {r["qid"] for r in rows}
    shard = packet.get("quota_shard")
    if shard:
        parent_path = Path(shard["parent_path"])
        if sha256(parent_path) != shard["parent_sha256"]:
            raise ValueError("quota shard parent changed")
        parent = read_json(parent_path)
        parent_qids = {r["qid"] for r in parent["rows"]}
        if (parent.get("quota_shard") or len(parent_qids) != 68
            or shard.get("qids") != [r["qid"] for r in rows]
            or not qids or not qids <= parent_qids
            or packet["source_identity"] != parent["source_identity"]
            or rows != [r for r in parent["rows"] if r["qid"] in qids]):
            raise ValueError("quota shard differs from its frozen parent population")
        for arm in ("baseline", "current"):
            if packet["cases"][arm] != {qid: parent["cases"][arm][qid] for qid in qids}:
                raise ValueError("quota shard cases differ from the frozen parent")
    elif len(rows) != 68 or len(qids) != 68:
        raise ValueError("paired protocol requires all 68 reviewed rows or a bound shard")
    if (packet["profile"] != PROFILE or packet["endpoint"] != ENDPOINT
        or packet["llm_config"] != read_json_config()
        or packet["minimum_provider_start_interval_seconds"] != 30
        or packet["schedule"] != paired_schedule(rows)):
        raise ValueError("paired protocol changed")
    validate_retry(packet)
    if (not qids <= set(rubric) or (not shard and set(rubric) != qids)) or any(
        any(row[k] != rubric[row["qid"]][k] for k in ("request", "split", "answerable", "source_group", "tags"))
        or digest_record(row["benchmark_row"]) != rubric[row["qid"]]["record_sha256"] for row in rows):
        raise ValueError("paired rows differ from source-reviewed population")
    total_calls = chars = 0
    for arm in ("baseline", "current"):
        if set(packet["cases"][arm]) != {r["qid"] for r in rows}:
            raise ValueError("incomplete paired cases")
        for row in rows:
            case = packet["cases"][arm][row["qid"]]
            body = case["provider_body"]
            if case["request"] != row["request"]:
                raise ValueError("paired request changed")
            if body:
                total_calls += 1
                prompt = body["contents"][0]["parts"][0]["text"]
                chars += len(prompt)
                for key, value in packet["llm_config"]["generation_config"].items():
                    if body["generationConfig"][key] != value:
                        raise ValueError("common generation controls changed")
    if total_calls != packet["max_provider_calls"] or chars != packet["prompt_chars"]:
        raise ValueError("paired egress budget changed")


def verify_inputs(packet):
    if source_identity(ROOT) != packet["source_identity"] or any(
        sha256(Path(p)) != d for p, d in packet["bindings"].items()):
        raise ValueError("paired source or inputs changed")
    verify_baseline(packet["baseline_archive"])


def quota_shard_groups(packet, max_posts=14):
    groups, current, calls = [], [], 0
    for row in packet["rows"]:
        qid = row["qid"]
        row_calls = sum(bool(packet["cases"][arm][qid]["provider_body"])
                        for arm in ("baseline", "current"))
        if row_calls > max_posts:
            raise ValueError("one qid pair exceeds the Free Tier per-shard call cap")
        if current and calls + row_calls > max_posts:
            groups.append(current)
            current, calls = [], 0
        current.append(qid)
        calls += row_calls
    if current:
        groups.append(current)
    if len(groups) < 5 or len(groups) > 8 or len(set(q for group in groups for q in group)) != 68:
        raise ValueError("68-row population cannot be safely partitioned into quota shards")
    return groups


def bind_retry_bundle(packet_path, manifest_path, budget_path, bundle_id):
    """Bind the single-packet retry budget before any live acceptance attempt."""
    return bind_retry_bundle_many([packet_path], manifest_path, budget_path, bundle_id)


def bind_retry_bundle_many(packet_paths, manifest_path, budget_path, bundle_id, *,
                           quota_window_policy=False):
    packet_paths = [Path(path) for path in packet_paths]
    manifest_path, budget_path = map(Path, (manifest_path, budget_path))
    if (not manifest_path.resolve().is_relative_to(ROOT.resolve())
        or any(not path.resolve().is_relative_to(ROOT.resolve()) for path in packet_paths)):
        raise ValueError("retry bundle artifacts must stay inside the project")
    for path in (manifest_path, budget_path):
        if path.exists():
            raise FileExistsError(path)
    if not budget_path.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("retry budget state escapes the project")
    if not isinstance(bundle_id, str) or not bundle_id.strip():
        raise ValueError("retry bundle id is required")
    budget = {"path": str(budget_path.resolve()), "bundle_id": bundle_id,
              "max_extra_attempts": 1}
    packets = [read_json(path) for path in packet_paths]
    if not packets or len({p["source_identity"]["source_sha256"] for p in packets}) != 1:
        raise ValueError("retry bundle requires packets from one frozen source identity")
    calls = chars = 0
    prompt_lengths = []
    output_caps = []
    packet_bindings = []
    for path, packet in zip(packet_paths, packets):
        if path.exists() is False:
            raise FileNotFoundError(path)
        if validate_retry(packet) != 1 or packet.get("retry_budget"):
            raise ValueError("primary retry bundle requires unbound packets with the 503 policy")
        packet["retry_budget"] = budget
        validate_packet(packet)
        packet_calls, packet_chars, packet_lengths = packet_usage(packet)
        calls += packet_calls
        chars += packet_chars
        prompt_lengths.extend(packet_lengths)
        output_caps.append(output_token_cap(packet))
        packet_bindings.append({"path": str(path.resolve()), "sha256": sha256(path)})
    if len(set(output_caps)) != 1:
        raise ValueError("all packets in a shared retry bundle require the same output cap")
    output_cap = output_caps[0]
    max_extra = budget["max_extra_attempts"]
    if quota_window_policy:
        if (len(packets) < 5 or any(not p.get("quota_shard") for p in packets)
            or any(p["max_provider_calls"] > 14 for p in packets)):
            raise ValueError("Free Tier bundle requires bounded qid-paired shards")
    for path, packet in zip(packet_paths, packets):
        write_json(path, packet)
    packet_bindings = [{"path": str(path.resolve()), "sha256": sha256(path)}
                       for path in packet_paths]
    manifest = {
        "schema_version": 1,
        "status": "PREPARED_NOT_AUTHORIZED",
        "source_identity": packets[0]["source_identity"],
        "retry_budget": budget,
        "packets": packet_bindings,
        "max_retries": 1,
        "expected_packet_count": len(packets),
        "planned_provider_posts": calls,
        "maximum_external_post_requests": calls + max_extra,
        "planned_prompt_characters": chars,
        "maximum_new_prompt_characters": chars + sum(sorted(prompt_lengths, reverse=True)[:max_extra]),
        "maximum_output_tokens_per_request": output_cap,
        "maximum_total_output_tokens": (calls + max_extra) * output_cap,
        "minimum_provider_start_interval_seconds": packets[0]["minimum_provider_start_interval_seconds"],
        "stop_on_first_non503_failure_or_failed_retry": True,
    }
    if quota_window_policy:
        manifest["quota_window_policy"] = {
            "provider": "gemini_free_tier", "reset_timezone": "America/Los_Angeles",
            "max_shards_per_pacific_date": 1, "max_planned_posts_per_shard": 14,
            "max_attempts_per_shard_per_day": 15, "model_version_must_remain_constant": True,
        }
    write_json(manifest_path, manifest)
    return {"manifest_sha256": sha256(manifest_path), "packet_shas": [b["sha256"] for b in packet_bindings],
            "planned_provider_posts": calls, "maximum_external_post_requests": calls + max_extra,
            "planned_prompt_characters": chars,
            "maximum_new_prompt_characters": manifest["maximum_new_prompt_characters"],
            "maximum_total_output_tokens": manifest["maximum_total_output_tokens"]}


def prepare(output, out, rubric_path=RUBRIC, retry_manifest=None,
            retry_budget_state=None, bundle_id=None, defer_retry_binding=False):
    available_output(output)
    if read_json_config().get("max_retries") == 1 and not all(
            (retry_manifest, retry_budget_state, bundle_id)) and not defer_retry_binding:
        raise ValueError("configured retry policy requires a bound retry manifest and one-time budget state path")
    if defer_retry_binding and any((retry_manifest, retry_budget_state, bundle_id)):
        raise ValueError("deferred retry binding cannot include retry bundle paths")
    for path in (retry_manifest, retry_budget_state):
        if path is not None and Path(path).exists():
            raise FileExistsError(path)
    out.mkdir(parents=True, exist_ok=False)
    before = source_identity(ROOT)
    rubric = read_json(rubric_path)
    protocol = read_json(PROTOCOL)
    archive = protocol["comparator"]["source_archive"]
    verified = verify_baseline(archive)
    original = {}
    for binding in rubric["primary_files"].values():
        path = Path(binding["path"])
        if sha256(path) != binding["sha256"]:
            raise ValueError("primary population changed")
        original.update({r["qid"]: r for r in (json.loads(line) for line in path.read_text(encoding="utf8").splitlines() if line.strip())})
    rows = []
    for row in rubric["rows"]:
        if digest_record(original[row["qid"]]) != row["record_sha256"]:
            raise ValueError("source rubric population binding changed")
        rows.append({**{k: deepcopy(row[k]) for k in ("qid", "split", "source_group", "request", "answerable", "tags")},
                     "benchmark_row": original[row["qid"]]})
    setup = {"source_identity": before, "profile": PROFILE, "endpoint": ENDPOINT,
        "trees": {"baseline": str(BASELINE_TREE), "current": str(ROOT)}, "rows": rows,
        "llm_config": read_json_config(), "baseline_archive": archive}
    setup_path = out / "setup.json"
    write_json(setup_path, setup)
    cases = {}
    for arm in ("baseline", "current"):
        target = out / f"{arm}.json"
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        env.pop("GEMINI_API_KEY", None)
        run = subprocess.run([sys.executable, str(WORKER), "prepare", arm, str(setup_path), str(target)],
                             capture_output=True, text=True, encoding="utf8", env=env)
        (out / f"{arm}.log").write_text(run.stdout + run.stderr, encoding="utf8")
        raw = read_json(target) if target.is_file() and target.stat().st_size else {}
        if run.returncode or len(raw.get("observations", [])) != 68 or any(
            not o["interface_valid"] for o in raw["observations"]):
            raise RuntimeError("offline paired collector failed; partial evidence retained")
        cases[arm] = {o["qid"]: {"qid": o["qid"], "request": o["request"],
            "provider_body": o["provider_body"], "evidence": o["trace"]["evidence"]} for o in raw["observations"]}
        print(json.dumps({"arm": arm, "http_requests": 68, "external_calls": 0}), flush=True)
    if source_identity(ROOT) != before:
        raise ValueError("source changed during paired preparation")
    bindings = {str(p): sha256(p) for p in [rubric_path, CONFIG, WORKER, Path(__file__),
        Path(PROFILE["CAMPUSAI_INDEX_DIR"]) / "manifest.json", Path(PROFILE["CAMPUSAI_RETRIEVAL_CALIBRATION"]),
        *(Path(b["path"]) for b in rubric["primary_files"].values()),
        out / "baseline.json", out / "current.json"]}
    packet = {**setup, "status": "PREPARED_NOT_AUTHORIZED", "cases": cases,
        "schedule": paired_schedule(rows), "seed": 7, "max_retries": setup["llm_config"]["max_retries"],
        "retry_only_http_status": 503,
        "rubric": {"path": str(rubric_path), "sha256": sha256(rubric_path)},
        "minimum_provider_start_interval_seconds": 30,
        "max_provider_calls": sum(bool(c["provider_body"]) for arm in cases.values() for c in arm.values()),
        "prompt_chars": sum(len(c["provider_body"]["contents"][0]["parts"][0]["text"])
            for arm in cases.values() for c in arm.values() if c["provider_body"]),
        "baseline_files_verified": verified, "bindings": bindings,
        "output_dir": str(BASE / output.stem.replace("egress-packet", "live")),
        "quality_accepted": False, "model_outputs_read": False,
        "limitations": ["Synthetic preparation outputs never qualify answer quality or latency.",
            "Only existing 35 test/33 holdout; not the historical Phase 5 population.",
            "Rubric review is owner-delegated AI, not independent human review.",
            "Baseline prompt/schema retained; only common CUDA/model/generation controls adapted."]}
    validate_packet(packet)
    write_json(output, packet)
    budget_report = None
    if packet["max_retries"] and not defer_retry_binding:
        budget_report = bind_retry_bundle(output, retry_manifest, retry_budget_state, bundle_id)
    print(json.dumps({"packet": str(output), "sha256": sha256(output), "max_provider_calls": packet["max_provider_calls"],
                      "prompt_chars": packet["prompt_chars"], "retry_budget": budget_report,
                      "external_calls": 0}))


def prepare_quota_shards(parent_path, output_dir, retry_manifest, retry_budget_state,
                         bundle_id):
    """Split one frozen 68-row offline packet into quota-window qid pairs."""
    parent_path = Path(parent_path)
    output_dir = Path(output_dir)
    if (not parent_path.resolve().is_relative_to(ROOT.resolve())
        or not output_dir.resolve().is_relative_to(ROOT.resolve())):
        raise ValueError("quota shard artifacts must stay inside the project")
    parent = read_json(parent_path)
    if parent.get("retry_budget") or parent.get("quota_shard"):
        raise ValueError("sharding requires an unbound full-population parent packet")
    validate_packet(parent)
    verify_inputs(parent)
    output_dir.mkdir(parents=True, exist_ok=False)
    groups = quota_shard_groups(parent)
    parent_digest = sha256(parent_path)
    packet_paths = []
    for index, qids in enumerate(groups, 1):
        selected = set(qids)
        child = deepcopy(parent)
        child["rows"] = [r for r in parent["rows"] if r["qid"] in selected]
        child["cases"] = {arm: {qid: parent["cases"][arm][qid] for qid in qids}
                           for arm in ("baseline", "current")}
        child["schedule"] = paired_schedule(child["rows"])
        child["max_provider_calls"] = sum(bool(child["cases"][arm][qid]["provider_body"])
            for arm in ("baseline", "current") for qid in qids)
        child["prompt_chars"] = sum(len(child["cases"][arm][qid]["provider_body"]["contents"][0]["parts"][0]["text"])
            for arm in ("baseline", "current") for qid in qids
            if child["cases"][arm][qid]["provider_body"])
        child["quota_shard"] = {"parent_path": str(parent_path.resolve()),
            "parent_sha256": parent_digest, "index": index, "count": len(groups),
            "qids": qids, "planned_provider_posts": child["max_provider_calls"],
            "maximum_attempts_in_window": child["max_provider_calls"] + 1}
        child["output_dir"] = str(Path(parent["output_dir"]) / f"shard-{index:02d}")
        packet_path = output_dir / f"product-primary-shard-{index:02d}-of-{len(groups):02d}.json"
        if packet_path.exists() or Path(child["output_dir"]).exists():
            raise FileExistsError(packet_path)
        validate_packet(child)
        write_json(packet_path, child)
        packet_paths.append(packet_path)
    bound = bind_retry_bundle_many(packet_paths, retry_manifest, retry_budget_state,
        bundle_id, quota_window_policy=True)
    print(json.dumps({"shards": len(packet_paths), "packet_shas": bound["packet_shas"],
        "retry_manifest_sha256": bound["manifest_sha256"],
        "planned_provider_posts": bound["planned_provider_posts"],
        "maximum_external_post_requests": bound["maximum_external_post_requests"],
        "maximum_attempts_per_quota_window": 15,
        "external_calls": 0}))
    return bound


def receive(process):
    for line in process.stdout:
        if line.startswith("PRIMARY_RESULT "):
            return json.loads(line.removeprefix("PRIMARY_RESULT "))
    raise RuntimeError("paired worker exited before response")


def collect(packet_path, authorized_digest):
    if sha256(packet_path) != authorized_digest:
        raise ValueError("exact paired packet authorization mismatch")
    packet = read_json(packet_path)
    validate_packet(packet)
    verify_inputs(packet)
    budget = Budget(packet_path, authorized_digest) if packet["max_retries"] else None
    out = Path(packet["output_dir"])
    available_output(out / "summary.json")
    if budget and packet.get("quota_shard"):
        budget.claim_quota_window()
    out.mkdir(parents=True, exist_ok=False)
    report = {"status": "STARTED_NO_RESUME", "packet_sha256": authorized_digest,
        "source_identity": packet["source_identity"], "completed_steps": [], "quality_accepted": False,
        "external_provider_calls": 0}
    write_json(out / "summary.json", report)
    processes, logs = {}, []
    provider_counts = {arm: 0 for arm in ("baseline", "current")}
    last_start = 0.0
    try:
        for arm in ("baseline", "current"):
            log = (out / f"{arm}.log").open("w", encoding="utf8")
            logs.append(log)
            processes[arm] = subprocess.Popen([sys.executable, str(WORKER), "live", arm,
                str(packet_path), str(out / f"{arm}.json")], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=log, text=True, encoding="utf8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            if receive(processes[arm]) != {"ready": True, "arm": arm}:
                raise RuntimeError("paired worker not ready")
        for step, case in enumerate(packet["schedule"]):
            verify_inputs(packet)
            report["active_step"] = step
            write_json(out / "summary.json", report)
            expected = packet["cases"][case["arm"]][case["qid"]]
            if expected["provider_body"]:
                time.sleep(max(0, 30.05 - (time.time() - last_start)))
            process = processes[case["arm"]]
            process.stdin.write(json.dumps({**case, "step": step, "digest": authorized_digest,
                "last_provider_start": last_start}) + "\n")
            process.stdin.flush()
            result = receive(process)
            if budget and result.get("model_version"):
                budget.record_model_version(result["model_version"])
            provider_counts[case["arm"]] = result["external_provider_calls"]
            last_start = result["last_provider_start"]
            report["completed_steps"].append({**case, "step": step, "valid": result["valid"]})
            report["external_provider_calls"] = sum(provider_counts.values())
            write_json(out / "summary.json", report)
            if not result["valid"]:
                report["status"] = "PROVIDER_OR_INTERFACE_FAILURE_STOPPED"
                break
        else:
            report["status"] = "PENDING_INDEPENDENT_PAIRED_SOURCE_REVIEW"
    except Exception as error:
        report.update(status="HARNESS_FAILURE_STOPPED", error_type=type(error).__name__)
    finally:
        for process in processes.values():
            if process.poll() is None:
                try:
                    process.stdin.write('{"stop": true}\n')
                    process.stdin.flush()
                    process.wait(timeout=80)
                except (OSError, subprocess.TimeoutExpired):
                    process.terminate()
                    process.wait(timeout=15)
        for log in logs:
            log.close()
        report["arms"] = {arm: {"path": str(out / f"{arm}.json"), "sha256": sha256(out / f"{arm}.json")}
                          for arm in processes if (out / f"{arm}.json").is_file()}
        report["external_provider_calls"] = sum(read_json(Path(v["path"]))["external_provider_calls"]
            for v in report["arms"].values() if Path(v["path"]).stat().st_size)
        report["source_stable"] = source_identity(ROOT) == packet["source_identity"]
        if budget and report["status"] != "PENDING_INDEPENDENT_PAIRED_SOURCE_REVIEW":
            budget.stop(report["status"])
        report.pop("active_step", None)
        write_json(out / "summary.json", report)
    print(json.dumps({k: report[k] for k in ("status", "external_provider_calls", "source_stable")}))
    return report


def aggregate_quota_shards(manifest_path, authorized_digest, output_path):
    """Validate and bind complete shard outputs into one 68-row review bundle."""
    manifest_path, output_path = Path(manifest_path), Path(output_path)
    if (not manifest_path.resolve().is_relative_to(ROOT.resolve())
        or not output_path.resolve().is_relative_to(ROOT.resolve())):
        raise ValueError("aggregate artifacts must stay inside the project")
    if sha256(manifest_path) != authorized_digest:
        raise ValueError("exact shard manifest authorization mismatch")
    manifest = read_json(manifest_path)
    if not manifest.get("quota_window_policy") or output_path.exists():
        raise ValueError("aggregate requires one exact Free Tier shard bundle and a new output path")
    state = read_json(Path(manifest["retry_budget"]["path"]))
    if (state["manifest_sha256"] != authorized_digest or state["stopped"]
        or not isinstance(state.get("provider_model_version"), str)):
        raise ValueError("shared retry budget is stopped or lacks a pinned provider model version")
    aggregate_qids, pair_refs, shard_reports = [], [], []
    model_versions, total_calls, planned_calls = set(), 0, 0
    source_identity_value = manifest["source_identity"]
    parent_path = None
    for binding in manifest["packets"]:
        if sha256(binding["path"]) != binding["sha256"]:
            raise ValueError("shard packet changed before aggregation")
        packet = read_json(binding["path"])
        validate_packet(packet)
        verify_inputs(packet)
        planned_calls += packet["max_provider_calls"]
        if packet["source_identity"] != source_identity_value:
            raise ValueError("shards use different source identities")
        if parent_path is None:
            parent_path = Path(packet["quota_shard"]["parent_path"])
        elif Path(packet["quota_shard"]["parent_path"]) != parent_path:
            raise ValueError("shards do not share one frozen parent")
        qids = [r["qid"] for r in packet["rows"]]
        if set(aggregate_qids).intersection(qids):
            raise ValueError("question appears in multiple quota shards")
        summary_path = Path(packet["output_dir"]) / "summary.json"
        summary = read_json(summary_path)
        if (summary.get("status") != "PENDING_INDEPENDENT_PAIRED_SOURCE_REVIEW"
            or summary.get("packet_sha256") != binding["sha256"]
            or summary.get("source_identity") != source_identity_value
            or not summary.get("source_stable")):
            raise ValueError("shard execution is incomplete, failed, or identity changed")
        step_pairs = {(s["arm"], s["qid"]): s for s in summary["completed_steps"] if s.get("valid")}
        if set(step_pairs) != {(s["arm"], s["qid"]) for s in packet["schedule"]}:
            raise ValueError("shard execution omitted or invalidated a paired step")
        arm_observations = {}
        for arm in ("baseline", "current"):
            arm_binding = summary["arms"][arm]
            arm_path = Path(arm_binding["path"])
            if sha256(arm_path) != arm_binding["sha256"]:
                raise ValueError("shard raw answer file changed")
            raw = read_json(arm_path)
            obs = {row["qid"]: row for row in raw["observations"]}
            if set(obs) != set(qids) or any(not row.get("interface_valid") for row in obs.values()):
                raise ValueError("shard does not contain one valid answer for each paired qid and arm")
            for qid, row in obs.items():
                planned = bool(packet["cases"][arm][qid]["provider_body"])
                version = row.get("provider_model_version")
                if planned and (not isinstance(version, str) or not version):
                    raise ValueError("provider model version missing from a paid output")
                if version:
                    model_versions.add(version)
            total_calls += int(raw["external_provider_calls"])
            arm_observations[arm] = (arm_binding, obs)
        shard_reports.append({"packet": binding, "summary": {"path": str(summary_path.resolve()),
            "sha256": sha256(summary_path)}, "qids": qids})
        for qid in qids:
            pair_refs.append({"qid": qid,
                "baseline": {"path": arm_observations["baseline"][0]["path"],
                    "sha256": arm_observations["baseline"][0]["sha256"], "observation_qid": qid},
                "current": {"path": arm_observations["current"][0]["path"],
                    "sha256": arm_observations["current"][0]["sha256"], "observation_qid": qid}})
        aggregate_qids.extend(qids)
    parent = read_json(parent_path)
    expected_qids = [r["qid"] for r in parent["rows"]]
    claims = state["quota_window_claims"]
    if (aggregate_qids != expected_qids or len(aggregate_qids) != 68
        or len(model_versions) != 1 or next(iter(model_versions)) != state["provider_model_version"]
        or total_calls != len(state["attempts"])
        or total_calls not in (planned_calls, planned_calls + 1)
        or len(state["retry_reservations"]) != total_calls - planned_calls
        or {row["packet_sha256"] for row in claims} != {b["sha256"] for b in manifest["packets"]}
        or len({row["pacific_date"] for row in claims}) != len(claims)):
        raise ValueError("shard union, model version or provider call accounting failed")
    report = {"schema_version": 1, "status": "PENDING_INDEPENDENT_PAIRED_SOURCE_REVIEW",
        "source_identity": source_identity_value,
        "retry_manifest": {"path": str(manifest_path.resolve()), "sha256": authorized_digest},
        "parent_packet": {"path": str(parent_path.resolve()), "sha256": sha256(parent_path)},
        "population": {"rows": 68, "test": sum(r["split"] == "test" for r in parent["rows"]),
            "holdout": sum(r["split"] == "holdout" for r in parent["rows"]),
            "previously_exposed": True, "fresh_validation_claim": False},
        "provider_model_version": next(iter(model_versions)),
        "external_provider_calls": total_calls, "complete_pairs": len(pair_refs),
        "quality_accepted": False, "shards": shard_reports, "paired_observation_refs": pair_refs,
        "rubric": parent["rubric"], "thresholds_unchanged": True,
        "limitations": ["Repeated acceptance on the previously exposed 35/33 population; not fresh validation.",
            "Source review and metric thresholds have not been evaluated by this aggregation step."]}
    write_json(output_path, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    prep = subs.add_parser("prepare")
    prep.add_argument("--output", type=Path, required=True)
    prep.add_argument("--output-dir", type=Path, required=True)
    prep.add_argument("--rubric", type=Path, default=RUBRIC)
    prep.add_argument("--retry-manifest", type=Path)
    prep.add_argument("--retry-budget-state", type=Path)
    prep.add_argument("--bundle-id")
    prep.add_argument("--defer-retry-binding", action="store_true")
    shards = subs.add_parser("prepare-quota-shards")
    shards.add_argument("--parent-packet", type=Path, required=True)
    shards.add_argument("--output-dir", type=Path, required=True)
    shards.add_argument("--retry-manifest", type=Path, required=True)
    shards.add_argument("--retry-budget-state", type=Path, required=True)
    shards.add_argument("--bundle-id", required=True)
    aggregate = subs.add_parser("aggregate-quota-shards")
    aggregate.add_argument("--manifest", type=Path, required=True)
    aggregate.add_argument("--authorized-manifest-sha256", required=True)
    aggregate.add_argument("--output", type=Path, required=True)
    live = subs.add_parser("collect")
    live.add_argument("--packet", type=Path, required=True)
    live.add_argument("--authorized-packet-sha256", required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.output, args.output_dir, args.rubric,
                args.retry_manifest, args.retry_budget_state, args.bundle_id,
                args.defer_retry_binding)
    elif args.command == "prepare-quota-shards":
        prepare_quota_shards(args.parent_packet, args.output_dir, args.retry_manifest,
                             args.retry_budget_state, args.bundle_id)
    elif args.command == "aggregate-quota-shards":
        report = aggregate_quota_shards(args.manifest, args.authorized_manifest_sha256, args.output)
        print(json.dumps({"status": report["status"], "complete_pairs": report["complete_pairs"],
            "external_provider_calls": report["external_provider_calls"], "quality_accepted": False}))
    else:
        collect(args.packet, args.authorized_packet_sha256)


if __name__ == "__main__":
    main()
