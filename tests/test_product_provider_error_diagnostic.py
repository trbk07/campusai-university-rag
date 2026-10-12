import hashlib
import io
import json
from pathlib import Path
from urllib.error import HTTPError

from scripts.benchmarks import product_provider_error_diagnostic as diagnostic


def _fixture(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    monkeypatch.setattr(diagnostic, "ROOT", root)
    identity = {"commit": "fixture", "source_sha256": "a" * 64, "runtime_sha256": "b" * 64}
    monkeypatch.setattr(diagnostic, "source_identity", lambda _root: identity)
    body = {"contents": [{"parts": [{"text": "harmless diagnostic"}]}],
            "generationConfig": {"maxOutputTokens": 8}}
    packet = {
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/test:generateContent",
        "llm_config": {"model": "test"},
        "cases": {"current": {"qid": {"provider_body": body}}},
    }
    packet_path = root / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")
    runner_path = root / "runner.py"
    runner_path.write_text("fixture runner", encoding="utf-8")
    manifest = {
        "status": "PREPARED_AWAITING_EXACT_OWNER_AUTHORIZATION",
        "current_source_identity": identity,
        "runner": {"path": "runner.py", "sha256": diagnostic.digest(runner_path)},
        "body_source": {"path": "packet.json", "sha256": diagnostic.digest(packet_path)},
        "qid": "qid",
        "provider_body_sha256": hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest(),
        "wire_body_sha256": hashlib.sha256(json.dumps(body).encode()).hexdigest(),
        "prompt_characters": len("harmless diagnostic"),
        "max_output_tokens_per_request": 8,
        "endpoint": packet["endpoint"],
        "model": "test",
        "max_external_post_requests": 1,
        "max_retries": 0,
        "stop_after_attempt": True,
        "output_path": "result.json",
        "timeout_seconds": 60,
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return root, manifest_path, hashlib.sha256(manifest_path.read_bytes()).hexdigest(), body


def test_diagnostic_captures_redacted_provider_error_and_never_retries(tmp_path, monkeypatch):
    root, manifest, authorized, body = _fixture(tmp_path, monkeypatch)
    key = "secret-test-key"
    prompt = body["contents"][0]["parts"][0]["text"]
    monkeypatch.setenv("GEMINI_API_KEY", key)
    calls = []

    def fail_once(request, timeout):
        calls.append((request, timeout))
        assert request.get_header("X-goog-api-key") == key
        assert json.loads(request.data) == body
        error_body = json.dumps({"error": {
            "status": "INVALID_ARGUMENT",
            "message": f"Bad prompt {prompt}, key {key}",
            "details": [{"reason": "API_KEY_INVALID"}],
        }}).encode()
        raise HTTPError(request.full_url, 400, "bad request", {}, io.BytesIO(error_body))

    monkeypatch.setattr(diagnostic, "urlopen", fail_once)
    report = diagnostic.collect(manifest, authorized)

    assert len(calls) == 1 and calls[0][1] == 60
    assert report["status"] == "HTTP_ERROR_CAPTURED"
    assert report["attempts"] == 1 and report["retries"] == 0
    assert report["provider_error"]["provider_error_status"] == "INVALID_ARGUMENT"
    assert report["provider_error"]["provider_error_reasons"] == ["API_KEY_INVALID"]
    output = (root / "result.json").read_text(encoding="utf-8")
    assert key not in output and prompt not in output


def test_diagnostic_rejects_wrong_manifest_authorization_before_network(tmp_path, monkeypatch):
    _, manifest, _, _ = _fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(diagnostic, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("network")))

    try:
        diagnostic.collect(manifest, "0" * 64)
    except ValueError as error:
        assert "authorization mismatch" in str(error)
    else:
        raise AssertionError("wrong authorization was accepted")
