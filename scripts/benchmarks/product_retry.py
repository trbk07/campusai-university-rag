"""Shared, fail-closed attempt budget for one exact acceptance bundle."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, time as datetime_time, timedelta
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
PACIFIC = ZoneInfo("America/Los_Angeles")


def load_retry503():
    # Both isolated application arms use the same frozen transport policy.
    path = ROOT / "src/campusai/llm/retry.py"
    spec = importlib.util.spec_from_file_location("_product_retry_transport", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.retry503


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf8"))


def validate_retry(packet):
    retries = packet["max_retries"]
    if type(retries) is not int or retries not in (0, 1):
        raise ValueError("invalid product retry limit")
    if retries and (packet.get("retry_only_http_status") != 503
                    or packet["llm_config"].get("retry_only_503") is not True
                    or packet["llm_config"]["max_retries"] != 1):
        raise ValueError("retry requires the narrow product503 policy")
    return retries


def packet_usage(packet):
    """Count exact logical provider payloads and prompt characters in a packet."""
    bodies = []
    if packet.get("schedule") and "cases" in packet:
        for row in packet["schedule"]:
            case = packet["cases"][row["arm"]][row["qid"]]
            if case.get("provider_body"):
                bodies.append(case["provider_body"])
    elif packet.get("workload") and "cases" in packet:
        for row in packet["workload"]:
            if row["planned_provider_call"]:
                body = packet["cases"][row["qid"]].get("provider_body")
                if not body:
                    raise ValueError("planned performance call lacks provider body")
                bodies.append(body)
    elif "provider_bodies" in packet:
        bodies = packet["provider_bodies"]
    else:
        raise ValueError("unknown acceptance packet payload layout")
    lengths = [len(body["contents"][0]["parts"][0]["text"]) for body in bodies]
    if (len(bodies) != packet["max_provider_calls"]
            or sum(lengths) != packet["prompt_chars"]):
        raise ValueError("packet request or prompt budget changed")
    return len(bodies), sum(lengths), lengths


def output_token_cap(packet):
    """Read the per-attempt output ceiling from the exact frozen packet."""
    try:
        value = packet["llm_config"]["generation_config"]["maxOutputTokens"]
    except (KeyError, TypeError):
        raise ValueError("packet output token cap missing") from None
    if type(value) is not int or value < 1:
        raise ValueError("invalid packet output token cap")
    return value


def pacific_date(timestamp=None):
    return datetime.fromtimestamp(time.time() if timestamp is None else timestamp, PACIFIC).date().isoformat()


def initialize(manifest_path, authorized_digest):
    from evaluation.common.release_artifacts import source_identity
    from evaluation.common.artifact_store import entries
    manifest_path = Path(manifest_path)
    if digest(manifest_path) != authorized_digest:
        raise ValueError("exact bundle authorization mismatch")
    manifest = read(manifest_path)
    budget = manifest["retry_budget"]
    path = Path(budget["path"]).resolve()
    expected_packet_count = manifest.get("expected_packet_count", 3)
    max_extra_attempts = budget.get("max_extra_attempts")
    if (not path.is_relative_to(ROOT.resolve()) or path.exists()
        or manifest["source_identity"] != source_identity(ROOT)
        or manifest["max_retries"] != 1 or type(max_extra_attempts) is not int
        or max_extra_attempts not in (1, 3)
        or type(expected_packet_count) is not int or expected_packet_count not in range(1, 9)):
        raise ValueError("bundle source/budget changed or already consumed")
    quota_policy = manifest.get("quota_window_policy")
    if quota_policy is not None and (
        expected_packet_count < 5 or quota_policy != {
            "provider": "gemini_free_tier", "reset_timezone": "America/Los_Angeles",
            "max_shards_per_pacific_date": 1, "max_planned_posts_per_shard": 14,
            "max_attempts_per_shard_per_day": 15, "model_version_must_remain_constant": True,
        }):
        raise ValueError("invalid free-tier shard quota policy")
    catalog = entries()
    if path.relative_to(ROOT.resolve()).as_posix() in catalog:
        raise ValueError("archived budget already consumed")
    packets = {}
    retry_output_caps = []
    for binding in manifest["packets"]:
        if digest(binding["path"]) != binding["sha256"]:
            raise ValueError("bundle packet changed")
        packet = read(binding["path"])
        if validate_retry(packet) != 1 or packet["retry_budget"] != budget:
            raise ValueError("bundle retry policy differs")
        output = Path(packet.get("output_path") or packet.get("output_dir", path.parent / "unused"))
        if "output_dir" in packet:
            output /= "summary.json"
        if output.exists() or (output.resolve().is_relative_to(ROOT.resolve())
                and output.resolve().relative_to(ROOT.resolve()).as_posix() in catalog):
            raise ValueError("bundle packet already consumed")
        calls, chars, prompt_lengths = packet_usage(packet)
        output_cap = output_token_cap(packet)
        packets[binding["sha256"]] = {"max_calls": calls, "prompt_chars": chars,
                                       "prompt_lengths": prompt_lengths,
                                       "output_tokens_per_attempt": output_cap}
        retry_output_caps.extend((length, output_cap) for length in prompt_lengths)
    planned_calls = sum(p["max_calls"] for p in packets.values())
    planned_chars = sum(p["prompt_chars"] for p in packets.values())
    retry_prompt_chars = sum(sorted((n for p in packets.values()
                                     for n in p["prompt_lengths"]), reverse=True)
                             [:budget["max_extra_attempts"]])
    max_calls = planned_calls + budget["max_extra_attempts"]
    max_prompt_total = planned_chars + retry_prompt_chars
    planned_output_tokens = sum(p["max_calls"] * p["output_tokens_per_attempt"]
                                for p in packets.values())
    extra_output_tokens = sum(cap for _, cap in sorted(retry_output_caps, reverse=True)
                              [:budget["max_extra_attempts"]])
    max_output_tokens = planned_output_tokens + extra_output_tokens
    if (len(packets) != expected_packet_count
        or manifest["maximum_external_post_requests"] != max_calls
        or manifest["maximum_new_prompt_characters"] != max_prompt_total
        or manifest["maximum_total_output_tokens"] != max_output_tokens):
        raise ValueError("bundle base request budget changed")
    if quota_policy is not None and any(p["max_calls"] > 14 for p in packets.values()):
        raise ValueError("free-tier shard exceeds its daily planned-post cap")
    state = {"bundle_id": budget["bundle_id"], "manifest_path": str(manifest_path.resolve()),
             "manifest_sha256": authorized_digest, "packets": packets, "attempts": [],
             "retry_reservations": [], "last_provider_start": 0.0, "stopped": False,
             "quota_window_claims": [], "provider_model_version": None,
             "max_calls": max_calls, "max_prompt_chars": max_prompt_total,
             "max_total_output_tokens": max_output_tokens,
             "max_extra_attempts": budget["max_extra_attempts"]}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf8") as stream:
        json.dump(state, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    return path


class Budget:
    def __init__(self, packet_path, authorized_digest):
        self.packet = read(packet_path)
        if digest(packet_path) != authorized_digest or validate_retry(self.packet) != 1:
            raise ValueError("exact retry packet authorization mismatch")
        self.digest = authorized_digest
        self.binding = self.packet["retry_budget"]
        self.path = Path(self.binding["path"]).resolve()
        self.quota_window_policy = bool(read(self.binding_manifest_path()) .get("quota_window_policy"))
        if not self.path.is_relative_to(ROOT.resolve()):
            raise ValueError("budget escapes workspace")
        with self.transaction():
            pass  # Missing/consumed/unapproved state fails before workers start.

    def binding_manifest_path(self):
        state = read(self.path)
        return state["manifest_path"]

    @contextmanager
    def transaction(self):
        lock = self.path.with_suffix(self.path.suffix + ".lock")
        lock.open("x", encoding="utf8").close()
        try:
            state = read(self.path)
            manifest = read(state["manifest_path"])
            if (digest(state["manifest_path"]) != state["manifest_sha256"]
                or manifest["retry_budget"] != self.binding
                or state["bundle_id"] != self.binding["bundle_id"]
                or self.digest not in state["packets"] or state["stopped"]
                or self.digest not in {p["sha256"] for p in manifest["packets"]}
                or state["max_calls"] != manifest["maximum_external_post_requests"]
                or state["max_extra_attempts"] != self.binding["max_extra_attempts"]
                or state["max_prompt_chars"] != manifest["maximum_new_prompt_characters"]):
                raise ValueError("bundle stopped or budget binding changed")
            yield state
            temporary = self.path.with_suffix(self.path.suffix + ".writing")
            with temporary.open("w", encoding="utf8") as stream:
                json.dump(state, stream, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            lock.unlink(missing_ok=True)

    def reserve_retry(self, key):
        with self.transaction() as state:
            identity = [self.digest, key]
            if (identity in state["retry_reservations"]
                or len(state["retry_reservations"]) >= self.binding["max_extra_attempts"]):
                raise RuntimeError("shared503retry budget exhausted")
            state["retry_reservations"].append(identity)

    def claim_quota_window(self):
        """Allow at most one frozen primary shard per Pacific RPD window."""
        if not self.quota_window_policy:
            raise RuntimeError("daily shard policy is not enabled for this bundle")
        now = datetime.now(PACIFIC)
        day = now.date().isoformat()
        reset = datetime.combine(now.date() + timedelta(days=1), datetime_time.min, PACIFIC)
        if (reset - now).total_seconds() < 30 * 60:
            raise RuntimeError("wait for the next Pacific quota window before starting a shard")
        with self.transaction() as state:
            if any(row["pacific_date"] == day for row in state["quota_window_claims"]):
                raise RuntimeError("Free Tier daily request window already used by this acceptance bundle")
            state["quota_window_claims"].append({"packet_sha256": self.digest, "pacific_date": day})

    def record_model_version(self, model_version):
        if not isinstance(model_version, str) or not model_version.strip():
            raise ValueError("provider omitted model version; cross-window acceptance cannot be verified")
        with self.transaction() as state:
            prior = state["provider_model_version"]
            if prior is not None and prior != model_version:
                raise ValueError("provider model version changed across quota-window shards")
            state["provider_model_version"] = model_version

    def before_attempt(self, key, body, retry):
        with self.transaction() as state:
            rows = state["attempts"]
            prior = [r for r in rows if r["packet_sha256"] == self.digest and r["key"] == key]
            if (len(prior) != int(retry) or (retry and [self.digest, key] not in state["retry_reservations"])
                or len(rows) >= state["max_calls"]):
                raise RuntimeError("repeated or unreserved acceptance attempt")
            if not retry and sum(r["packet_sha256"] == self.digest and not r["retry"] for r in rows) >= self.packet["max_provider_calls"]:
                raise RuntimeError("packet call budget exhausted")
            chars = len(body["contents"][0]["parts"][0]["text"])
            if sum(r["prompt_chars"] for r in rows) + chars > state["max_prompt_chars"]:
                raise RuntimeError("bundle prompt budget exhausted")
            time.sleep(max(0, 30.05 - (time.time() - state["last_provider_start"])))
            now = time.time()
            day = pacific_date(now)
            if self.quota_window_policy:
                if not any(row["packet_sha256"] == self.digest and row["pacific_date"] == day
                           for row in state["quota_window_claims"]):
                    raise RuntimeError("attempt is outside its claimed Free Tier daily window")
                attempts_today = sum(pacific_date(row["provider_start"]) == day for row in rows)
                if attempts_today >= 15:
                    raise RuntimeError("per-shard daily provider attempt cap exhausted")
            rows.append({"packet_sha256": self.digest, "key": key, "retry": bool(retry),
                         "provider_start": now, "prompt_chars": chars,
                         "body_sha256": hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()})
            state["last_provider_start"] = now

    def stop(self, reason):
        if read(self.path).get("stopped"):
            return
        with self.transaction() as state:
            state.update(stopped=True, stop_reason=reason)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--authorized-manifest-sha256", required=True)
    args = parser.parse_args()
    print(initialize(args.manifest, args.authorized_manifest_sha256))


if __name__ == "__main__":
    main()
