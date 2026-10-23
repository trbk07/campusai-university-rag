"""Compatibility facade for bounded, optionally durable background ingestion."""
from .pipeline import ingest_document
from .background.manager import IngestionJobManager
from .background.state import IngestionJob, JobQueueFull, JobStoreUnavailable

__all__ = ['IngestionJobManager','IngestionJob','JobQueueFull','JobStoreUnavailable']
