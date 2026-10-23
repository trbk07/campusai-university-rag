"""Durable deletion intents; running ingestion must stop before files disappear."""
import re
import threading

from .ingestion.background.commit import atomic_text


class DocumentDeletions:
    def __init__(self, documents):
        self.documents = documents
        self.pending, self.failed = set(), set()
        self.thread = None
        self.file_locks = [threading.RLock() for _ in range(64)]
        root = self.root()
        if root.is_dir():
            self.pending.update(path.name for path in root.iterdir()
                                if re.fullmatch('[0-9a-f]{64}', path.name)
                                and not path.is_symlink() and path.is_file())
        if self.pending:
            self.start()

    def root(self):
        from .web_documents import contained
        return contained(self.documents.store, self.documents.store / '.deletions')

    def file_lock(self, doc_id):
        return self.file_locks[int(doc_id[:2], 16) % len(self.file_locks)]

    def mark(self, doc_id):
        from .web_documents import contained
        root = self.root()
        root.mkdir(parents=True, exist_ok=True)
        atomic_text(contained(self.documents.store, root / doc_id), '')
        self.pending.add(doc_id)
        self.failed.discard(doc_id)

    def finish(self, doc_id):
        from .web_documents import contained
        contained(self.documents.store, self.root() / doc_id).unlink(missing_ok=True)
        self.pending.discard(doc_id)
        self.failed.discard(doc_id)

    def start(self):
        # Caller holds the document lock, except during single-threaded startup.
        if self.thread is None:
            self.thread = threading.Thread(target=self._run, name='campusai-delete', daemon=True)
            self.thread.start()

    def _run(self):
        documents = self.documents
        while True:
            with documents.lock:
                pending = self.pending - self.failed
                if not pending:
                    self.thread = None
                    return
            for doc_id in pending:
                lock = self.file_lock(doc_id)
                if not lock.acquire(blocking=False):
                    continue
                try:
                    if documents.cancel_document_jobs(doc_id):
                        continue
                    # Never hold the UI metadata lock while an existing answer
                    # finishes using its source. New requests already see the intent.
                    with documents.corpus_lock.write(), documents.lock:
                        documents._delete_artifacts(doc_id)
                        self.finish(doc_id)
                except Exception:
                    # Keep the durable intent and expose a retry button; do not
                    # silently claim deletion or spin on a filesystem failure.
                    with documents.lock:
                        self.failed.add(doc_id)
                finally:
                    lock.release()
            threading.Event().wait(.1)
