"""Pinned, local Vietnamese/English OCR assets; never downloaded by a request."""
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

TESSEROCR_VERSION = '2.12.0'
TESSDATA_SHA256 = {
    'vie': '79df64caf7bcfb2a27df5042ecb6121e196eada34da774956995747636d5bfa1',
    'eng': '7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2',
}


def validate_tesseract_assets(directory):
    """Return the exact local asset identity, without loading native OCR DLLs."""
    if directory is None:
        raise ValueError('local OCR language data required')
    root = Path(directory).resolve()
    try:
        if version('tesserocr') != TESSEROCR_VERSION:
            raise ValueError('unsupported tesserocr version')
        for language, expected in TESSDATA_SHA256.items():
            path = root / (language + '.traineddata')
            if path.is_symlink() or sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError('OCR language data checksum mismatch')
    except (OSError, PackageNotFoundError) as error:
        raise ValueError('install the pinned local OCR package and language data') from error
    return {'tesserocr': TESSEROCR_VERSION, 'languages': 'vie+eng',
            'model_sha256': dict(TESSDATA_SHA256)}
