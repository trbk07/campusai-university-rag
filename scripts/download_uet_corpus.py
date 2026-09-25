"""Download and verify the public UET corpus declared in manifest.json."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("data/corpus/university"))
    parser.add_argument("--refresh", action="store_true", help="Redownload files even when the checksum matches.")
    args = parser.parse_args()

    manifest_path = args.output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for item in manifest.get("documents", []):
        destination = args.output_dir / item["filename"]
        expected = item["sha256"]
        if destination.exists() and not args.refresh and sha256(destination) == expected:
            print(f"verified {destination.name}")
            continue
        request = Request(item["source_url"], headers={"User-Agent": "CampusAI corpus fetcher/1.0"})
        with urlopen(request, timeout=60) as response, destination.open("wb") as handle:
            while block := response.read(1024 * 1024):
                handle.write(block)
        if sha256(destination) != expected:
            destination.unlink(missing_ok=True)
            raise SystemExit(f"checksum mismatch: {destination.name}")
        print(f"downloaded {destination.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
