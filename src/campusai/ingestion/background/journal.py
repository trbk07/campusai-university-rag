"""Single-owner SQLite ledger; lifetime OS lock prevents false crash recovery."""
import json
from contextlib import contextmanager
import math
from pathlib import Path
import re
import sqlite3
import time

from .state import (ACTIVE, TERMINAL, IngestionJob, JobStoreUnavailable, normalize_options,
                    accepted_job_identities, recoverable_source)


class JobJournal:
    def __init__(self,path):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self._lock_handle = None
        try:
            self._acquire_owner()
            with self._connect() as db:
                schema = db.execute('PRAGMA user_version').fetchone()[0]
                if schema not in (0,1):
                    raise JobStoreUnavailable('unsupported job ledger schema')
                db.execute('CREATE TABLE IF NOT EXISTS jobs '
                           '(job_id TEXT PRIMARY KEY, payload TEXT NOT NULL, options TEXT NOT NULL)')
                db.execute('PRAGMA user_version=1')
        except (OSError,sqlite3.Error):
            self.close()
            raise JobStoreUnavailable('job ledger unavailable') from None
        except Exception:
            self.close()
            raise

    def _acquire_owner(self):
        import os
        handle = self.path.with_suffix(self.path.suffix+'.lock').open('a+b')
        try:
            if os.name == 'nt':
                import msvcrt
                handle.seek(0)
                if not handle.read(1):
                    handle.write(b'0')
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            handle.close()
            raise JobStoreUnavailable('job ledger already has an owner') from None
        self._lock_handle = handle

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path,timeout=1)
        try:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('PRAGMA synchronous=FULL')
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def load_and_recover(self):
        rows = []
        try:
            with self._connect() as db:
                for payload,options in db.execute('SELECT payload, options FROM jobs'):
                    job = IngestionJob(**json.loads(payload))
                    saved_options = json.loads(options)
                    normalized = normalize_options(saved_options)
                    legacy_options = {k:v for k,v in normalized.items() if k not in {'ocr_backend','ocr_data_dir'}}
                    valid_options = saved_options == normalized or saved_options == legacy_options
                    if (not valid_options or not Path(job.source_path).is_absolute()
                            or not re.fullmatch('[0-9a-f]{32}',job.job_id)
                            or not re.fullmatch('[0-9a-f]{64}',job.source_sha256)
                            or job.identity not in accepted_job_identities(job.source_sha256,normalized)
                            or job.state not in ACTIVE|TERMINAL
                            or not math.isfinite(job.progress) or not 0 <= job.progress <= 1):
                        raise ValueError('invalid job ledger state')
                    if job.state in ACTIVE:
                        # Never automatically re-run a crashed job. The owner
                        # retries explicitly using its persisted source/options.
                        job.state,job.stage = 'failed','interrupted'
                        job.ready,job.retryable = False,recoverable_source(job,normalized)
                        job.error_code = 'processing_interrupted'
                        job.action,job.ingestion_status = ('retry' if job.retryable else 'reupload'),'failed'
                        job.index_status = 'not_ready'
                        job.updated_at = job.completed_at = time.time()
                        db.execute('UPDATE jobs SET payload=? WHERE job_id=?',
                                   (json.dumps(job.to_dict()),job.job_id))
                    rows.append((job,normalized))
        except (ValueError,TypeError,sqlite3.Error):
            raise JobStoreUnavailable('job ledger unreadable') from None
        return rows

    def save(self,job,options):
        try:
            with self._connect() as db:
                db.execute('INSERT OR REPLACE INTO jobs VALUES (?,?,?)',
                    (job.job_id,json.dumps(job.to_dict(),allow_nan=False),
                     json.dumps(options,allow_nan=False)))
        except (ValueError,TypeError,sqlite3.Error):
            raise JobStoreUnavailable('job ledger write failed') from None

    def forget(self,job_ids):
        try:
            with self._connect() as db:
                db.executemany('DELETE FROM jobs WHERE job_id=?',((job_id,) for job_id in job_ids))
        except sqlite3.Error:
            raise JobStoreUnavailable('job ledger write failed') from None

    def close(self):
        if self._lock_handle is not None:
            self._lock_handle.close()  # Closing releases the lifetime OS lock.
            self._lock_handle = None
