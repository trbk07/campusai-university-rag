"""Pin the same verified BGE identity for upload indexing and query encoding."""
from ..config.preflight import verified_model
from ...retrieval.model_runtime import retrieval_runtime
from ...retrieval.hybrid import HybridRetriever


def pinned_retriever(settings):
    snapshot = verified_model(settings)
    retrieval_runtime().register_encoder_snapshot(settings.dense_model,settings.dense_revision,
                                                  snapshot,settings.dense_manifest_sha256)
    return HybridRetriever(settings.indexes,dense_device='cpu',
        dense_model_name=settings.dense_model,dense_model_revision=settings.dense_revision)


def ingestion_settings(settings):
    return {'store_dir':settings.store,'index_dir':settings.indexes,
            'dense_model':settings.dense_model,'dense_model_revision':settings.dense_revision,
            'device':'cpu'}
