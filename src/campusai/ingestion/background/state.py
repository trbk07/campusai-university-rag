"""Serializable job state/options; no provider credentials are accepted here."""
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
from ..docling_parser import TEXT_COVERAGE_VERSION

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
    'ocr_backend':'rapidocr','ocr_data_dir':None}


def normalize_options(options):
    if set(options)-set(DEFAULT_OPTIONS):
        raise ValueError('unsupported ingestion option')
    result = {**DEFAULT_OPTIONS,**options}
    result['store_dir'] = str(Path(result['store_dir']).resolve())
    result['index_dir'] = str(Path(result['index_dir']).resolve()) if result['index_dir'] is not None else None
    if not isinstance(result['ocr_backend'],str) or result['ocr_backend'] not in {'rapidocr','tesseract'}:
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
    timeout = result['ocr_timeout_seconds']
    if (isinstance(timeout,bool) or not isinstance(timeout,(int,float))
            or not math.isfinite(timeout) or timeout <= 0):
        raise ValueError('finite positive OCR timeout required')
    for key in ('dense_model','dense_model_revision','device'):
        if not isinstance(result[key],str) or not result[key]:
            raise ValueError('ingestion model/device identity required')
    return result


def job_identity(digest,options):
    return hashlib.sha256(json.dumps({'source_sha256':digest,'options':options,'text_coverage_version':TEXT_COVERAGE_VERSION},
        sort_keys=True,separators=(',',':')).encode()).hexdigest()


def legacy_job_identity(digest, options):
    """Validate original ledger rows only; new work must use job_identity."""
    return hashlib.sha256(json.dumps({'source_sha256':digest,'options':options},
        sort_keys=True,separators=(',',':')).encode()).hexdigest()


def accepted_job_identities(digest, options):
    """Accept exact historical formats only; new work uses full current options."""
    variants = [options]
    if options.get('ocr_backend') == 'rapidocr' and options.get('ocr_data_dir') is None:
        variants.append({k:v for k,v in options.items() if k not in {'ocr_backend','ocr_data_dir'}})
    identities = {function(digest,variant) for variant in variants
                  for function in (job_identity,legacy_job_identity)}
    identities.update(hashlib.sha256(json.dumps({'source_sha256':digest,'options':variant,
        'text_coverage_version':1},sort_keys=True,separators=(',',':')).encode()).hexdigest()
        for variant in variants)
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
