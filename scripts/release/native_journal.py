"""Durable one-attempt QA collection state; contains no gold or provider client."""
from __future__ import annotations

import json
import sqlite3
import unicodedata
import hashlib

from .blind_holdout import commitment, public_request, validate_public_cases, _hash


def question_digest(question):
    text = ' '.join(unicodedata.normalize('NFKC', question).casefold().split())
    return hashlib.sha256(text.rstrip('.!?').strip().encode()).hexdigest()


class NativeJournal:
    """Reserve before HTTP; a crash or provider error never unlocks a question.

    The candidate fingerprint must bind the caller's frozen source/index/profile
    and execution scope. This ledger does not authorize network requests or
    replace checking the central registry and retained attempt journals.
    """

    def __init__(self, path, candidate, cases, *, locked_questions=()):
        if not _hash(candidate):
            raise ValueError('candidate_fingerprint_required')
        validate_public_cases(cases)
        self.cases = {case['id']: json.loads(json.dumps(case)) for case in cases}
        fingerprints = [question_digest(q) for c in cases for q in c['turns']]
        if len(set(fingerprints)) != len(fingerprints):
            raise ValueError('duplicate_public_question')
        locked = list(locked_questions)
        if any(not _hash(digest) for digest in locked):
            raise ValueError('invalid_external_question_lock')
        self.db = sqlite3.connect(path, timeout=30, isolation_level=None)
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS identity (id INTEGER PRIMARY KEY CHECK(id=1), fingerprint TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS locked (digest TEXT PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS attempts (
                digest TEXT PRIMARY KEY, case_id TEXT NOT NULL, turn INTEGER NOT NULL,
                request TEXT NOT NULL, status TEXT NOT NULL, response TEXT, http_status INTEGER,
                execution TEXT,
                UNIQUE(case_id, turn));
        ''')
        if 'execution' not in {row[1] for row in self.db.execute('PRAGMA table_info(attempts)')}:
            self.db.execute('ALTER TABLE attempts ADD COLUMN execution TEXT')
        identity = commitment({'candidate': candidate, 'public_cases': cases})
        try:
            with self.transaction():
                self.db.execute('INSERT OR IGNORE INTO identity VALUES (1,?)', (identity,))
                if self.db.execute('SELECT fingerprint FROM identity').fetchone()[0] != identity:
                    raise ValueError('journal_candidate_or_bank_changed')
                self.db.executemany('INSERT OR IGNORE INTO locked VALUES (?)', ((d,) for d in locked))
        except BaseException:
            self.close()
            raise

    def transaction(self):
        from contextlib import contextmanager

        @contextmanager
        def atomic():
            self.db.execute('BEGIN IMMEDIATE')
            try:
                yield
                self.db.execute('COMMIT')
            except BaseException:
                self.db.execute('ROLLBACK')
                raise
        return atomic()

    def reserve(self, case_id, turn_index):
        """Return a gold-free HTTP body only after the lock is committed."""
        case = self.cases[case_id]
        if type(turn_index) is not int or not 0 <= turn_index < len(case['turns']):
            raise ValueError('invalid_public_turn')
        with self.transaction():
            rows = self.db.execute('SELECT turn,request,status,response FROM attempts WHERE case_id=? ORDER BY turn',
                                   (case_id,)).fetchall()
            if len(rows) != turn_index or any(n != i or status != 'completed'
                                             for i, (n, _req, status, _resp) in enumerate(rows)):
                raise ValueError('attempted_or_incomplete_conversation')
            history = []
            for _n, request, _status, response in rows:
                history.extend([{'role': 'user', 'content': json.loads(request)['question']},
                                {'role': 'assistant', 'content': json.loads(response)['answer']['answer']}])
            body = public_request(case, turn_index, history)
            digest = question_digest(body['question'])
            if (self.db.execute('SELECT 1 FROM locked WHERE digest=?', (digest,)).fetchone()
                    or self.db.execute('SELECT 1 FROM attempts WHERE digest=?', (digest,)).fetchone()):
                raise ValueError('question_already_locked')
            self.db.execute('INSERT INTO attempts(digest,case_id,turn,request,status) VALUES(?,?,?,?,?)',
                            (digest, case_id, turn_index, json.dumps(body, ensure_ascii=False), 'reserved'))
        return digest, body

    def complete(self, digest, http_status, response, *, execution=None):
        """Save the actual raw response; completion is not a quality PASS."""
        raw = json.dumps(response, ensure_ascii=False, allow_nan=False)
        metadata = json.dumps(execution or {}, ensure_ascii=False, allow_nan=False)
        answer = response.get('answer') if isinstance(response, dict) else None
        usable = (isinstance(response, dict) and http_status == 200 and response.get('ok') is True
                  and not response.get('provider_status') and isinstance(answer, dict)
                  and isinstance(answer.get('answer'), str)
                  and answer.get('abstention_reason') != 'provider_abstention')
        with self.transaction():
            changed = self.db.execute('UPDATE attempts SET response=?,http_status=?,status=?,execution=? WHERE digest=? AND status=?',
                                     (raw, http_status, 'completed' if usable else 'failed', metadata, digest, 'reserved')).rowcount
            if changed != 1:
                raise ValueError('attempt_missing_or_already_completed')

    def close(self):
        self.db.close()
