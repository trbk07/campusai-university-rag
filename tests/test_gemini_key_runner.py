import os
from pathlib import Path
import sys

import pytest

from scripts.operations.with_gemini_key import main, read_key


@pytest.mark.parametrize("content", ["local-example-key", "api_key: local-example-key", "GEMINI_API_KEY = 'local-example-key'", 'api_key = "local-example-key"'])
def test_supported_local_key_formats(tmp_path, content):
    path = tmp_path / "key.yaml"
    path.write_text(content, encoding="utf-8")
    assert read_key(path) == "local-example-key"


@pytest.mark.parametrize("key_name", ["key_1", "key_2"])
def test_selects_named_key_from_assignment_or_mapping(tmp_path, key_name):
    path = tmp_path / "key.yaml"
    other = "key_2" if key_name == "key_1" else "key_1"
    path.write_text(f'{other}: other-example-key\n{key_name}: selected-example-key\n', encoding="utf-8")
    assert read_key(path, key_name) == "selected-example-key"


def test_accepts_named_key_assignment_without_printing_credential(tmp_path):
    path = tmp_path / "key.yaml"
    path.write_text("key_2='selected-example-key'", encoding="utf-8")
    assert read_key(path, "key_2") == "selected-example-key"


def test_default_key_selection_accepts_key1_assignment(tmp_path):
    path = tmp_path / "key.yaml"
    path.write_text("key_1='selected-example-key'", encoding="utf-8")
    assert read_key(path) == "selected-example-key"


@pytest.mark.parametrize("content", ["", "{}", "[one,two]", "key with spaces", "api_key = __import__('os')"])
def test_invalid_key_format_never_echoes_local_content(tmp_path, content):
    path = tmp_path / "key.yaml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError) as error:
        read_key(path)
    assert not content or content not in str(error.value)


def test_module_key_environment_is_scoped_and_restored(tmp_path, monkeypatch):
    path = tmp_path / "key.yaml"
    path.write_text("key_2='local-example-key'", encoding="utf-8")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("RUN_LLM_INTEGRATION", raising=False)
    observed = []
    previous_path = sys.path[:]
    def run_module(*args, **kwargs):
        assert sys.path[0] == str(Path(__file__).resolve().parents[1] / 'src')
        observed.append((os.environ["GEMINI_API_KEY"], os.environ["RUN_LLM_INTEGRATION"]))
    monkeypatch.setattr("scripts.operations.with_gemini_key.runpy.run_module", run_module)
    assert main(["--key-file", str(path), "--key-name", "key_2",
                 "--live-tests", "pytest", "-q"]) == 0
    assert observed == [("local-example-key", "1")]
    assert sys.path == previous_path
    assert "GEMINI_API_KEY" not in os.environ and "RUN_LLM_INTEGRATION" not in os.environ
