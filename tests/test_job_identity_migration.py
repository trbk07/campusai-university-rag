"""A coverage policy upgrade must preserve and validate existing job history."""
import hashlib
import json
import sqlite3

import pytest
from campusai.ingestion.jobs import IngestionJobManager, JobStoreUnavailable
from campusai.ingestion.background.state import job_identity, legacy_job_identity, normalize_options


def make_legacy_ledger(tmp_path):
    source = tmp_path/'source.pdf'
    source.write_bytes(b'%PDF-legacy-test-source')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    ledger = tmp_path/'jobs.sqlite3'
    options = normalize_options({'store_dir':tmp_path/'store'})
    manager = IngestionJobManager(journal_path=ledger)
    old_id, _ = manager.prepare_upload(source,digest,**options)
    manager.shutdown()
    with sqlite3.connect(ledger) as db:
        row = json.loads(db.execute('SELECT payload FROM jobs').fetchone()[0])
        row.update(identity=legacy_job_identity(digest,options),state='review_required',
                   stage='review_required',ready=False)
        db.execute('UPDATE jobs SET payload=?',(json.dumps(row),))
    return ledger, source, digest, options, old_id


def test_legacy_rows_load_without_deduplicating_new_policy_work(tmp_path):
    ledger, source, digest, options, old_id = make_legacy_ledger(tmp_path)
    before = source.read_bytes()
    manager = IngestionJobManager(journal_path=ledger)
    try:
        assert manager.get(old_id)['identity'] == legacy_job_identity(digest,options)
        new_id, created = manager.prepare_upload(source,digest,**options)
        assert created and new_id != old_id
        assert manager.get(new_id)['identity'] == job_identity(digest,options)
        assert manager.get(old_id)['state'] == 'review_required'
        assert source.read_bytes() == before
    finally:
        manager.shutdown()


def test_forged_legacy_identity_still_fails_closed(tmp_path):
    ledger, _source, _digest, _options, _old_id = make_legacy_ledger(tmp_path)
    with sqlite3.connect(ledger) as db:
        row = json.loads(db.execute('SELECT payload FROM jobs').fetchone()[0])
        row['identity'] = '0'*64
        db.execute('UPDATE jobs SET payload=?',(json.dumps(row),))
    with pytest.raises(JobStoreUnavailable):
        IngestionJobManager(journal_path=ledger)


@pytest.mark.parametrize('coverage_version', [1, 2])
def test_old_coverage_identity_is_retained_but_never_deduplicates_new_work(tmp_path, coverage_version):
    ledger, source, digest, options, old_id = make_legacy_ledger(tmp_path)
    version_one = hashlib.sha256(json.dumps({'source_sha256': digest, 'options': options,
        'text_coverage_version': coverage_version}, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    with sqlite3.connect(ledger) as db:
        row = json.loads(db.execute('SELECT payload FROM jobs').fetchone()[0])
        row.update(identity=version_one)
        db.execute('UPDATE jobs SET payload=?', (json.dumps(row),))
    manager = IngestionJobManager(journal_path=ledger)
    try:
        assert manager.get(old_id)['identity'] == version_one
        new_id, created = manager.prepare_upload(source, digest, **options)
        assert created and new_id != old_id and manager.get(old_id)['state'] == 'review_required'
    finally:
        manager.shutdown()
