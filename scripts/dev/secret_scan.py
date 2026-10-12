"""Fail on common committed API-key shapes without printing their values."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


PATTERNS = (
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(
        r"(?i)\b(?:api[_-]?key|secret|token)\b\s*[:=]\s*['\"]?[A-Za-z0-9_-]{24,}"
    ),
)


def tracked_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return [root / item for item in result.stdout.decode().split("\0") if item]


def secret_findings(root: Path) -> list[str]:
    """Scan tracked files and require the local key file to remain Git-ignored."""
    files = tracked_files(root)
    local_credential = root / "configs" / "gemini.yaml"
    if local_credential.is_file() and local_credential not in files:
        files.append(local_credential)

    local_key = root / "configs" / "key.yaml"
    local_key_relative = local_key.relative_to(root).as_posix()
    if local_key.is_file() and local_key not in files:
        ignored = subprocess.run(
            ["git", "check-ignore", "--quiet", "--no-index", "--", local_key_relative],
            cwd=root,
            check=False,
            capture_output=True,
        )
        if ignored.returncode != 0:
            return [f"{local_key_relative}:must-be-git-ignored"]

    findings: list[str] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if any(pattern.search(line) for pattern in PATTERNS):
                findings.append(f"{path.relative_to(root).as_posix()}:{line_number}")
    return findings


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    findings = secret_findings(root)
    if findings:
        print("Potential secret material found at:")
        print("\n".join(findings))
        return 1
    print("Secret scan passed: no common API-key patterns found in tracked files or the ignored local Gemini credential file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
