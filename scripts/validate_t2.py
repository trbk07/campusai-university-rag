"""Validate a Task 2 feasibility report."""
from __future__ import annotations
import argparse, json
from pathlib import Path
REQUIRED_RESULT = {"path", "file_size_bytes", "sha256", "status"}
VALID_STATUSES = {"success", "failed", "skipped"}
VALID_MODEL_STATUSES = {"not_run", "blocked", "failed", "skipped", "success"}


def _validate_model_metrics(models: dict, errors: list[str]) -> None:
    status = models.get("status")
    if status not in VALID_MODEL_STATUSES:
        errors.append(f"invalid model status: {status!r}")
    if status != "success":
        return
    for name in ("dense", "reranker"):
        metrics = models.get(name)
        if not isinstance(metrics, dict):
            errors.append(f"models.{name} metrics are required when models succeeds")
            continue
        for field in ("cold_seconds", "warm_p50_seconds", "peak_rss_mb"):
            if not isinstance(metrics.get(field), (int, float)):
                errors.append(f"models.{name}.{field} must be numeric")
def validate(report: dict) -> list[str]:
    errors = []
    if report.get("schema_version") not in {1, 2}: errors.append("schema_version must be 1 or 2")
    if not isinstance(report.get("environment"), dict): errors.append("environment is required")
    rows = report.get("parser")
    if not isinstance(rows, list): return ["parser must be a list"]
    seen = set()
    for index, row in enumerate(rows):
        missing = REQUIRED_RESULT - row.keys()
        if missing: errors.append(f"parser[{index}] missing {sorted(missing)}")
        digest = row.get("sha256")
        if digest in seen: errors.append(f"duplicate sha256 at parser[{index}]")
        seen.add(digest)
        if row.get("status") not in VALID_STATUSES: errors.append(f"invalid status at parser[{index}]")
        if row.get("status") == "success":
            elapsed = row.get("cold_parse_seconds", row.get("seconds", -1))
            if row.get("pages", 0) <= 0 or not isinstance(elapsed, (int, float)) or elapsed < 0:
                errors.append(f"invalid success metrics at parser[{index}]")
    summary = report.get("summary", {})
    if summary.get("documents_recorded") != len(rows): errors.append("summary documents_recorded mismatch")
    models = report.get("models")
    if not isinstance(models, dict):
        errors.append("models is required")
    else:
        _validate_model_metrics(models, errors)
    if report.get("schema_version") == 2:
        if not isinstance(report.get("fastembed"), dict): errors.append("fastembed is required in schema 2")
        limits = report.get("limits")
        if not isinstance(limits, dict):
            errors.append("limits is required in schema 2")
        elif limits.get("status") == "measured" and not isinstance(limits.get("limits"), dict):
            errors.append("measured limits require limits.limits")
    return errors
def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("path", type=Path, default=Path("evaluation/t2/results.json"), nargs="?"); args = parser.parse_args()
    errors = validate(json.loads(args.path.read_text(encoding="utf-8")))
    if errors: raise SystemExit("\n".join(errors))
    print("valid Task 2 report")
if __name__ == "__main__": main()
