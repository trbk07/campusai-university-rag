"""Explicit, fail-closed Phase 7 feature-flag activation."""

from __future__ import annotations

import logging
import hashlib
import json
import os
from pathlib import Path
from typing import Mapping

from .calibration import RetrievalPolicy
from .hybrid import HybridRetriever
from .rerank_policy import Phase7Policy, Phase7PolicyError
from .cross_encoder_provider import ModelIdentity, OfflineCrossEncoderReranker, RerankerUnavailable
from .runtime_provenance import runtime_sha256


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
    provider = None
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
        if config.get("RERANKER_DEPLOYMENT", "experimental") == "production":
            release = json.loads(Path(config["RERANKER_RELEASE_MANIFEST"]).read_text(encoding="utf-8"))
            if (release.get("status") != "pass" or release.get("score") != 10.0 or release.get("errors") != []
                    or release.get("runtime_sha256") != runtime_sha256()
                    or any(release.get("gates", {}).get(f"M{i}", {}).get("status") != "PASS" for i in range(13))
                    or release.get("model_identity_sha256") != identity.fingerprint
                    or release.get("index_sha256") != policy.index_sha256
                    or release.get("device") != identity.device
                    or release.get("candidate_cap") != policy.candidate_cap
                    or release.get("rerank_cap") != policy.rerank_candidate_cap
                    or release.get("phase6_calibration_sha256") != policy.phase6_calibration_sha256
                    or release.get("phase7_calibration_sha256") != hashlib.sha256(Path(config["RERANKER_CALIBRATION"]).read_bytes()).hexdigest()):
                raise Phase7PolicyError("production release gate rejected")
        elif config.get("RERANKER_DEPLOYMENT", "experimental") != "experimental":
            raise ValueError("unsupported_deployment")
        candidate_cap = int(config.get("RERANKER_CANDIDATE_CAP", "40"))
        if candidate_cap != policy.candidate_cap:
            raise ValueError("candidate_cap_mismatch")
        provider = OfflineCrossEncoderReranker(
            identity, config["RERANKER_MODEL_DIR"],
            timeout_ms=int(config.get("RERANKER_TIMEOUT_MS", "1000")),
            candidate_cap=candidate_cap,
            queue_limit=int(config.get("RERANKER_QUEUE_LIMIT", "2")),
        )
        provider.verify_snapshot()
        if config.get("RERANKER_WARMUP", "false").casefold() == "true":
            provider.warm_up()
        retriever = HybridRetriever(index_root, phase7_provider=provider,
                                    phase7_policy=policy, phase7_enabled=True, **base_kwargs)
        log.info("phase7_activation_enabled model=%s policy=%s",
                 identity.fingerprint, policy.fingerprint)
        return retriever
    except (KeyError, ValueError, OSError, TypeError, AttributeError, Phase7PolicyError, RerankerUnavailable) as error:
        if provider is not None:
            provider.close()
        # Deliberately log only the reason type; exception text may contain a
        # local model path or calibration location.
        log.warning("phase7_activation_rejected: %s", type(error).__name__)
        retriever = HybridRetriever(index_root, **base_kwargs)
        retriever.phase7_activation_reason = "activation_rejected"
        return retriever
