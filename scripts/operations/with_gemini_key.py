"""Run a Python module with an owner-supplied local key, without echoing it."""
from __future__ import annotations

import argparse
import ast
import os
from pathlib import Path
import runpy
import re
import sys

KEY_NAMES = {
    "key", "key_1", "key_2", "api_key", "gemini_key", "gemini_api_key",
    "google_api_key",
}


def read_key(path: Path, key_name: str | None = None) -> str:
    import yaml
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError):
        raise ValueError("cannot read local Gemini credential file") from None
    if isinstance(value, dict):
        normalized = {str(name).strip().lower(): candidate for name, candidate in value.items()}
        selected = key_name.strip().lower() if key_name else None
        if selected:
            value = normalized.get(selected)
        else:
            value = next((normalized[name] for name in
                          ("api_key", "gemini_api_key", "google_api_key", "key", "key_1", "key_2")
                          if normalized.get(name)), None)
    if isinstance(value, str) and "=" in value:
        name, candidate = value.split("=", 1)
        normalized_name = name.strip().lower()
        selected = key_name.strip().lower() if key_name else None
        if normalized_name in KEY_NAMES and (selected is None or normalized_name == selected):
            candidate = candidate.strip()
            if candidate.startswith(("'", '"')):
                try:
                    candidate = ast.literal_eval(candidate)
                except (ValueError, SyntaxError):
                    raise ValueError("invalid quoted local Gemini credential") from None
            value = candidate
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{16,}", value.strip()):
        raise ValueError("local Gemini credential must be a single key string or api_key mapping")
    return value.strip()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key-file", type=Path, default=Path("configs/key.yaml"))
    parser.add_argument("--key-name", help="select key_1/key_2 when the local file has multiple credentials")
    parser.add_argument("--live-tests", action="store_true")
    parser.add_argument("module")
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    try:
        key = read_key(args.key_file, args.key_name)
    except ValueError as error:
        parser.error(str(error))
    previous_key = os.environ.get("GEMINI_API_KEY")
    previous_live = os.environ.get("RUN_LLM_INTEGRATION")
    previous_argv = sys.argv
    previous_path = sys.path[:]
    try:
        project_root = str(Path(__file__).resolve().parents[2])
        # A shared editable environment may point to a different checkout.
        # Resolve this runner's source before importing the target module.
        source_root = str(Path(project_root) / 'src')
        sys.path[:] = [source_root, project_root, *(
            entry for entry in sys.path if entry not in {source_root, project_root})]
        os.environ["GEMINI_API_KEY"] = key
        if args.live_tests:
            os.environ["RUN_LLM_INTEGRATION"] = "1"
        sys.argv = [args.module, *args.arguments]
        runpy.run_module(args.module, run_name="__main__", alter_sys=True)
    finally:
        sys.argv = previous_argv
        sys.path[:] = previous_path
        for name, previous in (("GEMINI_API_KEY", previous_key), ("RUN_LLM_INTEGRATION", previous_live)):
            if previous is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = previous
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
