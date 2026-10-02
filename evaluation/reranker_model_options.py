"""Shared explicit inference settings for calibration and release commands."""
from __future__ import annotations


def add_inference_options(parser):
    from campusai.retrieval.reranker_inputs import FORMATS
    parser.add_argument("--input-format", choices=FORMATS, default="full_chunk")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--batch-window-ms", type=float, default=0.0)
    parser.add_argument("--max-batch-pairs", type=int, default=200)


def inference_settings(args):
    return {key: getattr(args, key, default) for key, default in (
        ("batch_size", 8), ("max_length", 512), ("input_format", "full_chunk"),
        ("batch_window_ms", 0.0), ("max_batch_pairs", 200))}


def inference_cli(args):
    return [value for key, setting in inference_settings(args).items()
            for value in ("--" + key.replace("_", "-"), str(setting))]
