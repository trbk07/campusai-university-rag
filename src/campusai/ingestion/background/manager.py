"""One bounded ingestion executor with optional durable, single-owner state."""
from .executor import BoundedExecutor
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
import threading
import time
import uuid

from .journal import JobJournal
from .state import (ACTIVE, TERMINAL, IngestionJob, JobQueueFull, recoverable_source,
                    JobStoreUnavailable, job_identity, normalize_options)


class IngestionJobManager:
    def __init__(self,max_workers=1,*,max_pending=2,journal_path=None):
        if type(max_workers) is not int or not 1 <= max_workers <= 32:
            raise ValueError('ingestion worker limit invalid')
        if type(max_pending) is not int or not 0 <= max_pending <= 32:
            raise ValueError('ingestion queue limit invalid')
        self.max_workers,self.max_pending = max_workers,max_pending
        self._lock = threading.RLock()
        self._jobs,self._options,self._futures,self._cancel_events,self._by_identity = {},{},{},{},{}
        self._closed,self._healthy = False,True
        self._journal = JobJournal(journal_path) if journal_path is not None else None
        try:
            rows = self._journal.load_and_recover() if self._journal else []
            for job,options in sorted(rows,key=lambda row:(row[0].created_at,row[0].retry_count)):
                self._jobs[job.job_id],self._options[job.job_id] = job,options
                self._by_identity[job.identity] = job.job_id
                self._cancel_events[job.job_id] = threading.Event()
            self._executor = BoundedExecutor(max_workers,max_pending)
        except Exception:
            if self._journal: self._journal.close()
            raise

    @staticmethod
    def _sha256(path):
        digest = hashlib.sha256()
        with Path(path).open('rb') as handle:
            for block in iter(lambda:handle.read(1024*1024),b''):
                digest.update(block)
        return digest.hexdigest()

    def _persist(self,job,options):
        try:
            if self._journal: self._journal.save(job,options)
        except JobStoreUnavailable:
            self._healthy = False
            raise

    def _admit(self):
        if self._closed or not self._healthy:
            raise JobStoreUnavailable('ingestion worker unavailable')
        if sum(job.state in ACTIVE for job in self._jobs.values()) >= self.max_workers+self.max_pending:
            raise JobQueueFull('ingestion queue full')

    def _existing_is_live(self,job,options):
        if job.state in ACTIVE: return True
        if job.state not in {'succeeded','review_required'}: return False
        # A crash during managed deletion must not make a later re-upload
        # deduplicate against an already removed document/index.
        if not Path(job.source_path).is_file(): return False
        if not (Path(options['store_dir'])/job.source_sha256/'meta.json').is_file(): return False
        if options['index_dir'] is not None and job.state == 'succeeded':
            return all((Path(options['index_dir'])/job.source_sha256/name).is_file()
                       for name in ('bm25.json','dense.json'))
        return True

    def _create(self,path,digest,options,*,staging=False,reprocess_review=False):
        if not re.fullmatch('[0-9a-f]{64}',digest):
            raise ValueError('source SHA256 required')
        identity = job_identity(digest,options)
        existing = self._jobs.get(self._by_identity.get(identity))
        if existing and self._existing_is_live(existing,options) and not (
                reprocess_review and existing.state == 'review_required'):
            return existing.job_id,False
        self._admit()  # Before a job, temporary file or upload directory exists.
        job_id,now = uuid.uuid4().hex,time.time()
        job = IngestionJob(job_id,str(Path(path).resolve()),state='staging' if staging else 'queued',
            stage='receiving' if staging else 'queued',created_at=now,updated_at=now,
            source_sha256=digest,identity=identity,document_id=digest,
            retry_count=existing.retry_count+1 if existing else 0,
            upload_temporary_path=str(Path(path).parent/('.uploading-'+job_id+'.pdf')) if staging else None)
        self._persist(job,options)
        self._jobs[job_id],self._options[job_id] = job,options
        self._by_identity[identity] = job_id
        self._cancel_events[job_id] = threading.Event()
        return job_id,True

    def prepare_upload(self,source_path,digest,**options):
        normalized = normalize_options(options)
        with self._lock:
            return self._create(Path(source_path).resolve(),digest,normalized,staging=True)

    def activate(self,job_id):
        with self._lock:
            job = self._jobs[job_id]
            if job.state != 'staging': raise ValueError('upload is not staged')
            # The worker verifies the staged source before parsing. Re-hashing
            # here repeats a full disk read on the HTTP upload's critical path.
            self._update(job_id,state='queued',stage='queued')
            self._schedule(job_id)
        return job_id

    def reject_upload(self,job_id,*,code='invalid_pdf',retryable=False):
        with self._lock:
            self._update(job_id,state='failed',stage='failed',ready=False,retryable=retryable,
                error_code=code,action='retry' if retryable else 'reupload',
                ingestion_status='failed',completed_at=time.time())

    def submit(self,source_path,*,expected_sha256=None,reprocess_review=False,**options):
        path = Path(source_path).resolve()
        digest,normalized = self._sha256(path),normalize_options(options)
        if expected_sha256 is not None and digest != expected_sha256:
            raise ValueError('job source changed')
        if type(reprocess_review) is not bool:
            raise ValueError('review reprocessing flag must be boolean')
        with self._lock:
            job_id,created = self._create(path,digest,normalized,reprocess_review=reprocess_review)
            if created: self._schedule(job_id)
            return job_id

    def _schedule(self,job_id):
        try:
            self._futures[job_id] = self._executor.submit(self._run,job_id)
        except RuntimeError:
            self._update(job_id,state='failed',stage='failed',ready=False,retryable=True,
                error_code='worker_unavailable',action='retry',ingestion_status='failed',
                completed_at=time.time())
            raise JobStoreUnavailable('ingestion executor unavailable') from None

    def _update(self,job_id,**values):
        with self._lock:
            job = replace(self._jobs[job_id],updated_at=time.time(),**values)
            self._persist(job,self._options[job_id])
            self._jobs[job_id] = job

    def retry(self,job_id):
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.state != 'failed' or not job.retryable:
                raise ValueError('job retry unavailable')
            self._admit()
            if not recoverable_source(job,self._options[job_id]):
                raise ValueError('job source incomplete or changed; re-upload required')
            source = Path(job.source_path)
            if not source.is_file() and job.upload_temporary_path:
                temporary = Path(job.upload_temporary_path)
                if temporary.is_file() and self._sha256(temporary) == job.source_sha256:
                    temporary.replace(source)
            if not source.is_file() or self._sha256(source) != job.source_sha256:
                raise ValueError('job source incomplete or changed; re-upload required')
            from .commit import cleanup_stage
            cleanup_stage(self._options[job_id],job_id,job.source_sha256,restore=True)
            return self.submit(source,**self._options[job_id])

    def _run(self,job_id):
        from .. import jobs as compatibility
        options = self._options[job_id]
        job = self._jobs[job_id]
        try:
            self._checkpoint(job_id)
            self._update(job_id,state='running',stage='validating',progress=0.05,
                         started_at=time.time(),ingestion_status='running')
            if self._sha256(job.source_path) != job.source_sha256:
                raise ValueError('job source changed')
            stages = {'validating':(0,.08),'parsing':(.08,.45),'ocr':(.45,.75),
                'detecting_metadata':(.45,.55),'extracting_tables':(.55,.65),'chunking':(.65,.76),
                'persisting':(.76,.90),'indexing':(.90,.98),'review_required':(.90,1),'done':(1,1)}
            def progress(stage,value):
                self._checkpoint(job_id)
                start,end = stages.get(stage,(.05,.90))
                value=round(start+(end-start)*max(0,min(1,value)),4)
                with self._lock:
                    self._update(job_id,stage=stage,
                                 progress=max(self._jobs[job_id].progress,value))
            document = compatibility.ingest_document(job.source_path,store_dir=options['store_dir'],
                max_mb=options['max_mb'],max_pages=options['max_pages'],progress=progress,
                enable_ocr=options['enable_ocr'],ocr_max_pages=options['ocr_max_pages'],
                ocr_timeout_seconds=options['ocr_timeout_seconds'])
            self._checkpoint(job_id)
            if document.doc_id != job.source_sha256: raise ValueError('parsed source identity changed')
            if options['index_dir'] is not None and document.status != 'review_required':
                self._update(job_id,index_status='running',stage='indexing',progress=.90)
                from ...retrieval.index_builder import build_document_indexes
                from .commit import build_indexes
                build_indexes(self,job_id,document,options,build_document_indexes)
            with self._lock:
                self._checkpoint(job_id)
                review = document.status == 'review_required'
                self._update(job_id,state='review_required' if review else 'succeeded',
                    stage='review_required' if review else 'done',progress=1.0,
                    ingestion_status='review_required' if review else 'succeeded',
                    index_status='ready' if options['index_dir'] is not None and not review else 'not_requested',
                    ready=options['index_dir'] is not None and not review,completed_at=time.time(),
                    error=document.review_reason if review else None,
                    error_code=document.review_reason if review else None)
        except JobStoreUnavailable:
            # No unjournaled success/admission after a disk/ledger failure.
            self._healthy = False
        except Exception as error:
            cancelled = str(error) == 'job_cancelled'
            retryable = not cancelled and isinstance(error,(TimeoutError,OSError,ConnectionError))
            self._update(job_id,state='cancelled' if cancelled else 'failed',
                stage='cancelled' if cancelled else 'failed',ready=False,
                error=None if cancelled else type(error).__name__,
                error_code=None if cancelled else type(error).__name__.lower(),
                retryable=retryable,action='retry' if retryable else 'review_input',
                ingestion_status='cancelled' if cancelled else 'failed',completed_at=time.time())

    def _checkpoint(self,job_id):
        if self._cancel_events[job_id].is_set(): raise RuntimeError('job_cancelled')

    def get(self,job_id):
        with self._lock:
            job = self._jobs.get(job_id)
            return job.to_dict() if job else None

    def list(self):
        with self._lock: return [job.to_dict() for job in self._jobs.values()]

    def stats(self):
        with self._lock:
            counts = {state:sum(job.state==state for job in self._jobs.values())
                      for state in {job.state for job in self._jobs.values()}}
            counts.update(active_workers=counts.get('running',0),queue_limit=self.max_pending,
                          worker_limit=self.max_workers,store_available=self._healthy,
                          pending_work_items=self._executor.pending_count)
            return counts

    def cancel(self,job_id):
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.state in TERMINAL: return False
            self._cancel_events[job_id].set()
            self._update(job_id,cancel_requested=True)
            future = self._futures.get(job_id)
            if job.state == 'staging' or (future is not None and self._executor.cancel(future)):
                self._update(job_id,state='cancelled',stage='cancelled',progress=1,
                    ingestion_status='cancelled',ready=False,completed_at=time.time())
            return True

    def forget_document(self,doc_id):
        with self._lock:
            remove = [job_id for job_id,job in self._jobs.items() if
                (job.document_id==doc_id or Path(job.source_path).parent.name==doc_id)
                and job.state not in ACTIVE]
            if self._journal:
                try: self._journal.forget(remove)
                except JobStoreUnavailable:
                    self._healthy = False
                    raise
            for job_id in remove:
                job = self._jobs.pop(job_id)
                self._options.pop(job_id,None)
                self._futures.pop(job_id,None)
                self._cancel_events.pop(job_id,None)
                if self._by_identity.get(job.identity)==job_id: self._by_identity.pop(job.identity,None)

    def shutdown(self,wait=True):
        with self._lock:
            self._closed = True
            for job_id,job in list(self._jobs.items()):
                if job.state in {'staging','queued'}:
                    try: self.cancel(job_id)
                    except JobStoreUnavailable: self._healthy = False
        self._executor.shutdown(wait=wait,cancel_futures=True)
        if wait:
            if self._journal: self._journal.close()
        elif self._journal:
            def close_after_workers():
                self._executor.shutdown(wait=True)
                self._journal.close()
            threading.Thread(target=close_after_workers,daemon=True).start()
