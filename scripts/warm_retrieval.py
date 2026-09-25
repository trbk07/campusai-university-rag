"""Warm retrieval models once at application startup."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from campusai.retrieval.model_runtime import warm_retrieval_models


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dense-model")
    parser.add_argument("--reranker-model")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    args = parser.parse_args()
    loaded = warm_retrieval_models(
        dense_model=args.dense_model,
        reranker_model=args.reranker_model,
        device=args.device,
    )
    print(json.dumps({"status": "ready", "loaded_models": loaded}))


if __name__ == "__main__":
    main()
