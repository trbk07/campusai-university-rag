"""Pinned, local Vietnamese/English OCR assets; never downloaded by a request."""
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, distribution, version
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

RAPIDOCR_SHA256 = {
    'ch_PP-OCRv4_det_infer.onnx':'d2a7720d45a54257208b1e13e36a8479894cb74155a5efe29462512d42f49da9',
    'ch_PP-OCRv4_rec_infer.onnx':'48fc40f24f6d2a207a2b1091d3437eb3cc3eb6b676dc3ef9c37384005483683b',
    'ch_ppocr_mobile_v2.0_cls_infer.onnx':'e47acedf663230f8863ff1ab0e64dd2d82b838fceb5957146dab185a89d6215c',
}


def validate_rapidocr_assets():
    """Validate wheel-bundled models without loading ONNX or downloading."""
    try:
        package=distribution('rapidocr-onnxruntime')
        if package.version != '1.4.4':
            raise ValueError('local release requires rapidocr-onnxruntime1.4.4 from uv.lock')
        for name,expected in RAPIDOCR_SHA256.items():
            path=Path(package.locate_file('rapidocr_onnxruntime/models/'+name))
            if path.is_symlink() or sha256(path.read_bytes()).hexdigest()!=expected:
                raise ValueError('bundled RapidOCR model checksum mismatch')
    except (OSError,PackageNotFoundError) as error:
        raise ValueError('install [ocr] from uv.lock for local RapidOCR') from error
    return {'package':'rapidocr-onnxruntime1.4.4','model_sha256':dict(RAPIDOCR_SHA256)}


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
