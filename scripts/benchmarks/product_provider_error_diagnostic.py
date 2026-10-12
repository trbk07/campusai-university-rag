"""Make one explicitly authorized provider request to capture a bounded HTTP diagnostic."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from evaluation.common.release_artifacts import source_identity
from scripts.benchmarks.product_primary_worker import provider_error_diagnostic


ROOT = Path(__file__).resolve().parents[2]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_exclusive(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def collect(manifest_path: Path, authorized_sha256: str) -> dict:
    manifest_path = manifest_path.resolve()
    if not manifest_path.is_relative_to(ROOT) or digest(manifest_path) != authorized_sha256:
        raise ValueError("exact diagnostic manifest authorization mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "PREPARED_AWAITING_EXACT_OWNER_AUTHORIZATION":
        raise ValueError("diagnostic packet is not awaiting authorization")
    runner = (ROOT / manifest["runner"]["path"]).resolve()
    if not runner.is_relative_to(ROOT) or digest(runner) != manifest["runner"]["sha256"]:
        raise ValueError("diagnostic runner binding mismatch")
    if (manifest.get("max_external_post_requests") != 1 or manifest.get("max_retries") != 0
        or manifest.get("stop_after_attempt") is not True):
        raise ValueError("diagnostic call limit changed")
    if source_identity(ROOT) != manifest["current_source_identity"]:
        raise ValueError("source identity changed after diagnostic preparation")

    packet_path = (ROOT / manifest["body_source"]["path"]).resolve()
    if not packet_path.is_relative_to(ROOT) or digest(packet_path) != manifest["body_source"]["sha256"]:
        raise ValueError("diagnostic body source binding mismatch")
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    body = packet["cases"]["current"][manifest["qid"]]["provider_body"]
    body_bytes = json.dumps(body).encode("utf-8")
    prompt = body["contents"][0]["parts"][0]["text"]
    output = (ROOT / manifest["output_path"]).resolve()
    if (not output.is_relative_to(ROOT) or output.exists()
        or hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() != manifest["provider_body_sha256"]
        or hashlib.sha256(body_bytes).hexdigest() != manifest["wire_body_sha256"]
        or len(prompt) != manifest["prompt_characters"]
        or body["generationConfig"]["maxOutputTokens"] != manifest["max_output_tokens_per_request"]
        or packet["endpoint"] != manifest["endpoint"]
        or packet["llm_config"]["model"] != manifest["model"]):
        raise ValueError("diagnostic body, limits, endpoint, or output binding mismatch")
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY is not configured")

    report = {
        "schema_version": 1,
        "status": "ATTEMPT_RESERVED_NO_RESUME",
        "manifest_sha256": authorized_sha256,
        "provider_body_sha256": manifest["provider_body_sha256"],
        "attempts": 0,
        "retries": 0,
        "prompt_characters": len(prompt),
        "diagnostic_only": True,
        "product_acceptance_eligible": False,
    }
    write_exclusive(output, report)
    request = Request(manifest["endpoint"], data=body_bytes, method="POST", headers={
        "Content-Type": "application/json",
        "x-goog-api-key": key,
    })
    started = time.perf_counter()
    report.update(status="REQUEST_SENT_NO_RESUME", attempts=1)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        with urlopen(request, timeout=manifest["timeout_seconds"]) as response:
            result = json.loads(response.read())
        report.update(status="HTTP_RESPONSE_CAPTURED", http_status=200,
                      usage=result.get("usageMetadata"),
                      finish_reason=(result.get("candidates") or [{}])[0].get("finishReason"))
    except HTTPError as error:
        report.update(status="HTTP_ERROR_CAPTURED", http_status=error.code,
                      provider_error=provider_error_diagnostic(error, prompt=prompt, api_key=key))
    except URLError as error:
        report.update(status="TRANSPORT_ERROR_CAPTURED", error_type=type(error).__name__)
    except Exception as error:
        report.update(status="TRANSPORT_OR_CLIENT_ERROR_CAPTURED", error_type=type(error).__name__)
    finally:
        report["latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
        report["credential_value_recorded"] = False
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--authorized-manifest-sha256", required=True)
    args = parser.parse_args()
    report = collect(args.manifest, args.authorized_manifest_sha256)
    print(json.dumps({key: report.get(key) for key in ("status", "http_status", "attempts", "retries")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
