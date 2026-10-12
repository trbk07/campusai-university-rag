"""Download a public reranker snapshot at a pinned revision and verify LFS bytes.

Never changes an existing model file, historical identity, or release selector.
No Hugging Face token or local benchmark content is sent.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request

from evaluation.common.release_artifacts import sha256, write_json

FILES = ("config.json", "model.safetensors", "sentencepiece.bpe.model",
         "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if len(args.revision) != 40 or any(c not in "0123456789abcdef" for c in args.revision):
        raise ValueError("full pinned revision required")
    model = "BAAI/bge-reranker-v2-m3"
    target = Path(".local_artifacts/models/bge-reranker-v2-m3") / args.revision
    target.mkdir(parents=True, exist_ok=True)
    metadata_url = f"https://huggingface.co/api/models/{model}/revision/{args.revision}?blobs=true"
    with urllib.request.urlopen(metadata_url, timeout=30) as response:
        metadata_bytes = response.read()
    metadata = json.loads(metadata_bytes)
    if metadata["sha"] != args.revision or metadata["id"] != model:
        raise ValueError("upstream returned another model/revision")
    by_name = {item["rfilename"]: item for item in metadata["siblings"]}
    report = {"schema_version": 1, "status": "DOWNLOADING", "recorded_at": datetime.now(timezone.utc).isoformat(),
              "model_name": model, "revision": args.revision, "model_dir": target.as_posix(),
              "metadata_url": metadata_url, "metadata_sha256": hashlib.sha256(metadata_bytes).hexdigest(),
              "credential_sent": False, "benchmark_transmitted": False, "files": {}, "release_eligible": False}
    # The small metadata receipt contains upstream hashes, not downloaded weights.
    receipt_path = args.report.with_name(args.report.stem + "-metadata.json")
    if receipt_path.exists() and receipt_path.read_bytes() != metadata_bytes:
        raise ValueError("metadata receipt changed; preserve old attempt")
    receipt_path.write_bytes(metadata_bytes)
    report["metadata_path"] = receipt_path.as_posix()
    write_json(args.report, report)
    try:
        for name in FILES:
            info = by_name[name]
            destination = target / name
            if not destination.exists():
                temporary = target / (name + ".download")
                if temporary.exists():
                    raise ValueError("partial download exists; inspect failed attempt before retry")
                url = f"https://huggingface.co/{model}/resolve/{args.revision}/{name}"
                count, last = 0, 0
                with urllib.request.urlopen(url, timeout=120) as response, temporary.open("xb") as output:
                    while block := response.read(4 * 1024 * 1024):
                        output.write(block)
                        count += len(block)
                        if count - last >= 128 * 1024 * 1024:
                            print(json.dumps({"file": name, "downloaded_bytes": count, "expected_bytes": info.get("size")}), flush=True)
                            last = count
                if info.get("size") is not None and temporary.stat().st_size != info["size"]:
                    raise ValueError("download size differs from pinned upstream metadata")
                digest = sha256(temporary)
                expected = info.get("lfs", {}).get("sha256")
                if expected and expected != digest:
                    raise ValueError("download LFS SHA256 differs from pinned upstream metadata")
                if not expected:
                    data = temporary.read_bytes()
                    blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
                    if blob != info["blobId"]:
                        raise ValueError("download Git blob hash differs from pinned upstream metadata")
                temporary.rename(destination)
            digest = sha256(destination)
            if destination.stat().st_size != info["size"]:
                raise ValueError("existing snapshot file size mismatch")
            if info.get("lfs", {}).get("sha256"):
                if digest != info["lfs"]["sha256"]:
                    raise ValueError("existing snapshot weight hash mismatch")
            else:
                data = destination.read_bytes()
                if hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest() != info["blobId"]:
                    raise ValueError("existing snapshot config/tokenizer hash mismatch")
            report["files"][name] = {"sha256": digest, "bytes": destination.stat().st_size,
                                     "upstream_blob": info["blobId"], "upstream_lfs": info.get("lfs")}
            write_json(args.report, report)
        config = json.loads((target / "config.json").read_text(encoding="utf8"))
        report["config"] = {k: config.get(k) for k in ("_name_or_path", "model_type", "architectures", "hidden_size", "num_hidden_layers")}
        report["status"] = "PASS_PINNED_PUBLIC_FILE_HASHES"
        write_json(args.report, report)
    except Exception as error:
        report.update(status="FAILED_DOWNLOAD_OR_VERIFICATION", error_type=type(error).__name__)
        write_json(args.report, report)
        raise
    print(json.dumps({"status": report["status"], "model_dir": str(target), "files": len(report["files"])}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
