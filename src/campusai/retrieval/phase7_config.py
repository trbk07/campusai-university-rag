"""Explicit, fail-closed Phase 7 feature-flag activation."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Mapping

from .calibration import RetrievalPolicy
from .hybrid import HybridRetriever
from .phase7_policy import Phase7Policy, Phase7PolicyError
from .phase7_reranker import ModelIdentity, OfflineCrossEncoderReranker


log = logging.getLogger(__name__)


def build_phase7_retriever(index_root: str | Path, phase6_calibration: str | Path,
                           dev_benchmark: str | Path, *,
                           environ: Mapping[str, str] | None = None) -> HybridRetriever:
    """Return Phase 6 on any activation error, without network model lookup."""
    config = os.environ if environ is None else environ
    phase6 = RetrievalPolicy.from_report(phase6_calibration, expected_mode="hybrid_rrf")
    base_kwargs = {"policies": {"hybrid_rrf": phase6}}
    if config.get("RERANKER_ENABLED", "false").casefold() != "true":
        log.info("phase7_feature_disabled")
        return HybridRetriever(index_root, **base_kwargs)
    try:
        if config.get("RERANKER_MODE", "hard_only") != "hard_only":
            raise ValueError("unsupported_mode")
        identity = ModelIdentity(
            model_name=config.get("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3"),
            model_revision=config["RERANKER_MODEL_REVISION"],
            model_sha256=config["RERANKER_MODEL_SHA256"],
            tokenizer_revision=config["RERANKER_TOKENIZER_REVISION"],
            device=config.get("RERANKER_DEVICE", "cpu"),
            batch_size=int(config.get("RERANKER_BATCH_SIZE", "8")),
            max_length=int(config.get("RERANKER_MAX_LENGTH", "512")),
        )
        policy = Phase7Policy.from_report(
            config["RERANKER_CALIBRATION"], model_identity=identity,
            index_manifest=Path(index_root) / "manifest.json",
            phase6_calibration=phase6_calibration, dev_benchmark=dev_benchmark)
        candidate_cap = int(config.get("RERANKER_CANDIDATE_CAP", "40"))
        if candidate_cap != policy.candidate_cap:
            raise ValueError("candidate_cap_mismatch")
        provider = OfflineCrossEncoderReranker(
            identity, config["RERANKER_MODEL_DIR"],
            timeout_ms=int(config.get("RERANKER_TIMEOUT_MS", "1000")),
            candidate_cap=candidate_cap,
            queue_limit=int(config.get("RERANKER_QUEUE_LIMIT", "2")),
        )
        retriever = HybridRetriever(index_root, phase7_provider=provider,
                                    phase7_policy=policy, phase7_enabled=True, **base_kwargs)
        log.info("phase7_activation_enabled model=%s policy=%s",
                 identity.fingerprint, policy.fingerprint)
        return retriever
    except (KeyError, ValueError, OSError, TypeError, Phase7PolicyError) as error:
        # Deliberately log only the reason type; exception text may contain a
        # local model path or calibration location.
        log.warning("phase7_activation_rejected: %s", type(error).__name__)
        retriever = HybridRetriever(index_root, **base_kwargs)
        retriever.phase7_activation_reason = "activation_rejected"
        return retriever
