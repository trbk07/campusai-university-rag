"""Publish useful page snapshots, then resume bounded automatic OCR batches."""
import time
from .commit import build_indexes
from ..table_extractor import table_extraction_session


@table_extraction_session()
def ingest_progressively(manager, job_id, options, progress, ingest):
    from ...retrieval.index_builder import build_document_indexes

    job = manager._jobs[job_id]
    common = {key:options[key] for key in ('store_dir', 'max_mb', 'max_pages',
        'ocr_timeout_seconds', 'ocr_backend', 'ocr_data_dir')}
    common.update(progress=progress, allow_partial=True,
        ocr_max_pages=min(4, options['ocr_max_pages']))
    # The first snapshot exposes native pages without waiting for image OCR.
    document = ingest(job.source_path, enable_ocr=False, **common)
    for _ in range(document.page_count + 1):
        manager._checkpoint(job_id)
        if document.chunks and options['index_dir'] is not None:
            build_indexes(manager, job_id, document, options, build_document_indexes)
            manager._update(job_id, ready=True, index_status='ready')
        unread = document.metadata.get('unread_pages', [])
        if not unread or not options['enable_ocr']:
            break
        previous = set(unread)
        started=time.monotonic()
        document = ingest(job.source_path, enable_ocr=True, **common)
        remaining=set(document.metadata.get('unread_pages', []))
        if remaining >= previous:
            # No progress: no automatic retry loop on a broken/unreadable page.
            break
        completed=len(previous-remaining)
        elapsed=max(.001,time.monotonic()-started)
        # Keep the first searchable OCR snapshot small. Later batches amortize
        # parsing/worker/index overhead, while slow pages shrink the next batch
        # to a conservative fraction of the existing hard deadline.
        budget=min(20.,options['ocr_timeout_seconds']*.5)
        common['ocr_max_pages']=max(1,min(options['ocr_max_pages'],
            common['ocr_max_pages']*2,int(budget*completed/elapsed)))
    return document
