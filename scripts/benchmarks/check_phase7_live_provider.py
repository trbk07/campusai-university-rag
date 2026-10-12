"""Run the two existing synthetic live-provider contracts with redacted evidence.

This command sends only the fixed test prompts, not benchmark questions or corpus
excerpts. The local config credential is passed only to the configured Gemini
authentication client; it is never printed or persisted in evidence.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

from evaluation.common.release_artifacts import sha256, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    import yaml
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    key = os.environ.get("GEMINI_API_KEY") or config.get("api_key")
    if not key:
        raise ValueError("Gemini credential is not configured")
    model = config["llm"]["model"]
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=False)
    tests = ["tests/integration/test_gemini.py", "tests/integration/test_basic_rag_provider.py"]
    xml = output / "tests.xml"
    command = [sys.executable, "-m", "pytest", *tests, "-q", "--tb=short", f"--junitxml={xml}"]
    env = dict(os.environ, GEMINI_API_KEY=key, RUN_LLM_INTEGRATION="1", PHASE7_LLM_MODEL=model,
               PHASE4_LLM_MODEL=model, PYTHONIOENCODING="utf-8")
    try:
        result = subprocess.run(command, env=env, text=True, encoding="utf-8", errors="replace",
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
        log, code = result.stdout, result.returncode
    except subprocess.TimeoutExpired as error:
        log = error.stdout or ""
        if isinstance(log, bytes):
            log = log.decode("utf-8", errors="replace")
        log += "\nLive contract invocation exceeded 300 seconds.\n"
        code = 124
    log = log.replace(key, "[REDACTED]")
    (output / "pytest.log").write_text(log, encoding="utf-8")
    counts = None
    if xml.exists():
        xml.write_text(xml.read_text(encoding="utf-8").replace(key, "[REDACTED]"), encoding="utf-8")
        root = ET.parse(xml).getroot()
        suites = list(root.iter("testsuite"))
        counts = {field: sum(int(suite.get(field, "0")) for suite in suites)
                  for field in ("tests", "failures", "errors", "skipped")}
    report = {"schema_version": 1, "task": "P7-06.5", "recorded_at": datetime.now(timezone.utc).isoformat(),
              "status": "PASS" if code == 0 and counts == {"tests": 2, "failures": 0, "errors": 0, "skipped": 0} else "FAIL",
              "exit_code": code, "counts": counts, "provider": "Gemini", "model": model,
              "endpoint_host": "generativelanguage.googleapis.com", "benchmark_transmitted": False,
              "payload_scope": "Two fixed synthetic test contracts: OK response and 130-credit internship fixture.",
              "release_eligible": False, "paid_tier_or_billing_changed": False,
              "runner_sha256": sha256(__file__), "tests": {path: sha256(path) for path in tests},
              "artifacts": {path.name: sha256(path) for path in output.iterdir() if path.is_file()},
              "limitations": ["Does not measure benchmark answer quality, paired reranking, quota capacity, or S4/S5.",
                              "Live calls may incur ordinary configured-provider usage; cost is not reported by these tests."]}
    write_json(output / "report.json", report)
    print(json.dumps({key: report[key] for key in ("status", "exit_code", "counts", "model", "benchmark_transmitted")}))
    print(log)
    return code or (0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    raise SystemExit(main())
