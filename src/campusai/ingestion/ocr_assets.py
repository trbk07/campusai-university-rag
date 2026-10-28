"""Pinned, local Vietnamese/English OCR assets; never downloaded by a request."""
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

TESSEROCR_VERSION = '2.12.0'
TESSDATA_SHA256 = {
    'vie': '79df64caf7bcfb2a27df5042ecb6121e196eada34da774956995747636d5bfa1',
    'eng': '7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2',
}

VIETOCR_SHA256 = {
    'vgg_seq2seq.pth': '0921503a41375a0584268e23ef3d414ea478a8fe8777865c7745d38f2d0bc5db',
    'detector.onnx': 'd2a7720d45a54257208b1e13e36a8479894cb74155a5efe29462512d42f49da9',
}
VIETOCR_BYTES = {'vgg_seq2seq.pth':89575371,'detector.onnx':4745517}


def validate_vietocr_assets(directory):
    """Validate only local, pinned inference assets; do not import torch here."""
    if directory is None or Path(directory).is_symlink():
        raise ValueError('pinned local Vietnamese OCR data required')
    root = Path(directory).resolve()
    try:
        if version('rapidocr-onnxruntime') != '1.4.4':
            raise ValueError('Vietnamese OCR requires rapidocr-onnxruntime1.4.4')
        torch_version = version('torch')
        major, minor = map(int,torch_version.split('.')[:2])
        if major != 2 or minor < 2:
            raise ValueError('Vietnamese OCR requires torch2.2 or newer2.x')
        for name, expected in VIETOCR_SHA256.items():
            path = root/name
            if (path.is_symlink() or path.stat().st_size != VIETOCR_BYTES[name]
                    or sha256(path.read_bytes()).hexdigest() != expected):
                raise ValueError('Vietnamese OCR model checksum mismatch')
    except (OSError, PackageNotFoundError) as error:
        raise ValueError('install [ocr,ocr-vietnamese] and pinned Vietnamese OCR models') from error
    return {'engine':'vietocr-vgg-seq2seq-v1','torch':torch_version,
            'detector_package':'rapidocr-onnxruntime1.4.4','model_sha256':dict(VIETOCR_SHA256)}


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
