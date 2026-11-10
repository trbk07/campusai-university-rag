"""Serializable job state/options; no provider credentials are accepted here."""
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
from ..docling_parser import TEXT_COVERAGE_VERSION
from ..table_extractor import TABLE_EXTRACTOR_VERSION
from ..chunker import CHUNKER_VERSION
from ..metadata_detector import METADATA_VERSION

ACTIVE = frozenset({'staging','queued','running'})
TERMINAL = frozenset({'succeeded','failed','cancelled','review_required'})


class JobQueueFull(ValueError):
    pass


class JobStoreUnavailable(RuntimeError):
    pass


DEFAULT_OPTIONS = {'store_dir':'data/store','index_dir':None,
    'dense_model':'fallback-hash-256','dense_model_revision':'1','device':'cpu',
    'batch_size':8,'max_mb':50,'max_pages':218,'enable_ocr':False,
    'ocr_max_pages':50,'ocr_timeout_seconds':120.0,
    'ocr_backend':'rapidocr','ocr_data_dir':None,'progressive_ocr':False}


def normalize_options(options):
    if set(options)-set(DEFAULT_OPTIONS):
        raise ValueError('unsupported ingestion option')
    result = {**DEFAULT_OPTIONS,**options}
    result['store_dir'] = str(Path(result['store_dir']).resolve())
    result['index_dir'] = str(Path(result['index_dir']).resolve()) if result['index_dir'] is not None else None
    if not isinstance(result['ocr_backend'],str) or result['ocr_backend'] not in {'rapidocr','tesseract','vietocr'}:
        raise ValueError('unsupported OCR backend')
    if result['ocr_data_dir'] is not None:
        if not isinstance(result['ocr_data_dir'],(str,Path)) or not str(result['ocr_data_dir']).strip():
            raise ValueError('local OCR language data path required')
        result['ocr_data_dir'] = str(Path(result['ocr_data_dir']).resolve())
    for key in ('batch_size','max_mb','max_pages','ocr_max_pages'):
        if type(result[key]) is not int or result[key] <= 0:
            raise ValueError('positive ingestion limit required')
    if type(result['enable_ocr']) is not bool:
        raise ValueError('OCR flag must be boolean')
    if type(result['progressive_ocr']) is not bool:
        raise ValueError('progressive OCR flag must be boolean')
    timeout = result['ocr_timeout_seconds']
    if (isinstance(timeout,bool) or not isinstance(timeout,(int,float))
            or not math.isfinite(timeout) or timeout <= 0):
        raise ValueError('finite positive OCR timeout required')
    for key in ('dense_model','dense_model_revision','device'):
        if not isinstance(result[key],str) or not result[key]:
            raise ValueError('ingestion model/device identity required')
    return result


def _producer_identity(digest, options, *, current, chunker_version=None, metadata_version=None):
    options = {k:v for k,v in options.items() if k != 'progressive_ocr' or v}
    payload={'source_sha256':digest,'options':options,'text_coverage_version':TEXT_COVERAGE_VERSION,
             'table_extractor_version':TABLE_EXTRACTOR_VERSION}
    if current:
        payload.update(chunker_version=chunker_version or CHUNKER_VERSION,
                       metadata_detector_version=metadata_version or METADATA_VERSION)
    if options.get('ocr_backend')=='vietocr':
        from ..ocr_tables import OCR_TABLE_POLICY
        payload['ocr_table_policy']=OCR_TABLE_POLICY
    if options.get('enable_ocr') and options.get('ocr_backend') in {'rapidocr','vietocr'}:
        from ..ocr_numeric_tables import NUMERIC_TABLE_POLICY
        payload['ocr_numeric_policy'] = NUMERIC_TABLE_POLICY
    if options.get('enable_ocr') and options.get('ocr_backend') == 'tesseract':
        from ..tesseract_worker import RENDER_POLICY
        payload['ocr_render_policy'] = RENDER_POLICY
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def job_identity(digest, options):
    return _producer_identity(digest, options, current=True)


def legacy_job_identity(digest, options):
    """Validate original ledger rows only; new work must use job_identity."""
    return hashlib.sha256(json.dumps({'source_sha256':digest,'options':options},
        sort_keys=True,separators=(',',':')).encode()).hexdigest()


def accepted_job_identities(digest, options):
    """Accept exact historical formats only; new work uses full current options."""
    variants = [options]
    if not options.get('progressive_ocr'):
        variants.append({k:v for k,v in options.items() if k != 'progressive_ocr'})
    if options.get('ocr_backend') == 'rapidocr' and options.get('ocr_data_dir') is None:
        variants.append({k:v for k,v in options.items() if k not in {'ocr_backend','ocr_data_dir'}})
    identities = {function(digest,variant) for variant in variants
                  for function in (job_identity,legacy_job_identity)}
    identities.update(_producer_identity(digest, variant, current=False) for variant in variants)
    # Read historical producer-bound ledgers without reusing their identity for
    # new uploads. The owner restored the v7 code after v8/v9 had produced jobs.
    identities.update(_producer_identity(digest,variant,current=True,
        chunker_version=version,metadata_version='source-labelled-v2')
        for variant in variants for version in ('structure-v7-diagram-semester-scope',
            'structure-v8-embedded-table-headers','structure-v9-article-boundaries'))
    identities.update(_producer_identity(digest,variant,current=True,
        chunker_version=version,metadata_version='source-labelled-v3-field-provenance')
        for variant in variants for version in ('structure-v7-diagram-semester-scope',
            'structure-v8-piece-page-provenance','structure-v9-source-body-syntax'))
    identities.update(hashlib.sha256(json.dumps({'source_sha256':digest,'options':variant,
        'text_coverage_version':version},sort_keys=True,separators=(',',':')).encode()).hexdigest()
        for variant in variants for version in (1,2,3,4))
    if options.get('ocr_backend') == 'vietocr':
        from ..ocr_tables import OCR_TABLE_POLICY
        identities.update(hashlib.sha256(json.dumps({'source_sha256':digest,'options':options,
            'text_coverage_version':version,'ocr_table_policy':OCR_TABLE_POLICY},
            sort_keys=True,separators=(',',':')).encode()).hexdigest() for version in (3,4))
    # v5 introduced the table producer in the durable identity. Keep exact
    # historical formats readable; new uploads use the current producer.
    for variant in variants:
        for producer in ('table-v5-partial-numeric-grid', 'table-v6-leader-text-grid', TABLE_EXTRACTOR_VERSION):
            previous = {'source_sha256':digest, 'options':variant, 'text_coverage_version':4,
                        'table_extractor_version':producer}
            if options.get('ocr_backend') == 'vietocr':
                from ..ocr_tables import OCR_TABLE_POLICY
                previous['ocr_table_policy'] = OCR_TABLE_POLICY
            identities.add(hashlib.sha256(json.dumps(previous,sort_keys=True,separators=(',',':')).encode()).hexdigest())
            if options.get('enable_ocr') and options.get('ocr_backend')=='tesseract':
                # The v3 producer remains a valid historical ledger identity.
                # New v4 work gets a different key and reparses stale OCR text.
                previous['ocr_render_policy']='gray-small-print-v3'
                identities.add(hashlib.sha256(json.dumps(previous,sort_keys=True,separators=(',',':')).encode()).hexdigest())
    return identities




def recoverable_source(job,options):
    def matches(path):
        try:
            digest = hashlib.sha256()
            with path.open('rb') as handle:
                for block in iter(lambda:handle.read(1024*1024),b''): digest.update(block)
            return digest.hexdigest()==job.source_sha256
        except OSError:
            return False
    source = Path(job.source_path)
    if job.upload_temporary_path:
        root = Path(options['store_dir']).resolve()
        temporary = Path(job.upload_temporary_path)
        if (source.parent != root/'uploads'/job.source_sha256 or temporary.parent != source.parent
                or temporary.name != '.uploading-'+job.job_id+'.pdf'):
            raise ValueError('upload recovery path invalid')
        for path in (source,temporary):
            if not path.resolve().is_relative_to(root): raise ValueError('upload recovery redirected')
        if temporary.is_symlink() or source.is_symlink(): raise ValueError('upload recovery redirected')
        if temporary.is_file() and not matches(temporary):
            temporary.unlink()  # Incomplete generated upload, never the original canonical PDF.
        if source.is_file() and matches(source): return True
        return temporary.is_file() and matches(temporary)
    return source.is_file() and matches(source)


@dataclass
class IngestionJob:
    job_id: str
    source_path: str
    state: str = 'queued'
    stage: str = 'queued'
    progress: float = 0.0
    document_id: str | None = None
    error: str | None = None
    error_message: str | None = None
    error_code: str | None = None
    retryable: bool = False
    action: str | None = None
    created_at: float = 0.0
    updated_at: float = 0.0
    started_at: float | None = None
    completed_at: float | None = None
    retry_count: int = 0
    ingestion_status: str = 'queued'
    index_status: str = 'not_requested'
    ready: bool = False
    source_sha256: str = ''
    identity: str = ''
    upload_temporary_path: str | None = None
    cancel_requested: bool = False

    def to_dict(self):
        return asdict(self)
