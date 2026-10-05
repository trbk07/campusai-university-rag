import os

import pytest

from scripts.operations.with_gemini_key import main, read_key


@pytest.mark.parametrize("content", ["local-example-key", "api_key: local-example-key", "GEMINI_API_KEY = 'local-example-key'", 'api_key = "local-example-key"'])
def test_supported_local_key_formats(tmp_path, content):
    path = tmp_path / "key.yaml"
    path.write_text(content, encoding="utf-8")
    assert read_key(path) == "local-example-key"


@pytest.mark.parametrize("content", ["", "{}", "[one,two]", "key with spaces", "api_key = __import__('os')"])
def test_invalid_key_format_never_echoes_local_content(tmp_path, content):
    path = tmp_path / "key.yaml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError) as error:
        read_key(path)
    assert not content or content not in str(error.value)


def test_module_key_environment_is_scoped_and_restored(tmp_path, monkeypatch):
    path = tmp_path / "key.yaml"
    path.write_text("local-example-key", encoding="utf-8")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("RUN_LLM_INTEGRATION", raising=False)
    observed = []
    def run_module(*args, **kwargs):
        observed.append((os.environ["GEMINI_API_KEY"], os.environ["RUN_LLM_INTEGRATION"]))
    monkeypatch.setattr("scripts.operations.with_gemini_key.runpy.run_module", run_module)
    assert main(["--key-file", str(path), "--live-tests", "pytest", "-q"]) == 0
    assert observed == [("local-example-key", "1")]
    assert "GEMINI_API_KEY" not in os.environ and "RUN_LLM_INTEGRATION" not in os.environ
