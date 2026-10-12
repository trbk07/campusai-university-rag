from scripts.dev import secret_scan
import subprocess


def test_secret_scan_includes_ignored_local_gemini_credential_file(tmp_path, monkeypatch):
    monkeypatch.setattr(secret_scan, "tracked_files", lambda root: [])
    config = tmp_path / "configs" / "gemini.yaml"
    config.parent.mkdir()
    config.write_text("api_key: " + "A" * 32 + "\n", encoding="utf-8")

    assert secret_scan.secret_findings(tmp_path) == ["configs/gemini.yaml:1"]


def test_secret_scan_accepts_environment_only_local_gemini_config(tmp_path, monkeypatch):
    monkeypatch.setattr(secret_scan, "tracked_files", lambda root: [])
    config = tmp_path / "configs" / "gemini.yaml"
    config.parent.mkdir()
    config.write_text(
        "llm:\n  api_key_env: GEMINI_API_KEY\n", encoding="utf-8"
    )

    assert secret_scan.secret_findings(tmp_path) == []


def test_secret_scan_still_scans_tracked_files(tmp_path, monkeypatch):
    tracked = tmp_path / "tracked.yaml"
    tracked.write_text("token: " + "B" * 32 + "\n", encoding="utf-8")
    monkeypatch.setattr(secret_scan, "tracked_files", lambda root: [tracked])

    assert secret_scan.secret_findings(tmp_path) == ["tracked.yaml:1"]


def test_local_key_yaml_must_be_ignored_and_is_not_read_as_source(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / ".gitignore").write_text("/configs/key.yaml\n", encoding="utf-8")
    config = tmp_path / "configs" / "key.yaml"
    config.parent.mkdir()
    config.write_text("A" * 32, encoding="utf-8")
    monkeypatch.setattr(secret_scan, "tracked_files", lambda root: [])

    assert secret_scan.secret_findings(tmp_path) == []


def test_local_key_yaml_without_ignore_rule_fails_closed(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    config = tmp_path / "configs" / "key.yaml"
    config.parent.mkdir()
    config.write_text("A" * 32, encoding="utf-8")
    monkeypatch.setattr(secret_scan, "tracked_files", lambda root: [])

    assert secret_scan.secret_findings(tmp_path) == [
        "configs/key.yaml:must-be-git-ignored"
    ]
