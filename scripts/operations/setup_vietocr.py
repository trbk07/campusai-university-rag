"""Explicitly install pinned local inference assets; requests never download."""
import argparse
from hashlib import sha256
from importlib.metadata import distribution
import os
from pathlib import Path
import tempfile
from urllib.request import urlopen

from campusai.ingestion.ocr_assets import VIETOCR_SHA256,validate_vietocr_assets


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('.cache/ocr/vietocr'))
    parser.add_argument('--source-dir',type=Path,help='Use previously downloaded checkpoint offline')
    args=parser.parse_args()
    if args.output.is_symlink(): parser.error('OCR model directory cannot be a link')
    args.output.mkdir(parents=True,exist_ok=True)
    for name,expected in VIETOCR_SHA256.items():
        target=args.output/name
        if target.is_symlink(): parser.error('OCR model cannot be a link')
        if target.is_file():
            if sha256(target.read_bytes()).hexdigest()!=expected: parser.error('existing OCR asset checksum mismatch')
            continue
        if name=='detector.onnx':
            source=distribution('rapidocr-onnxruntime').locate_file('rapidocr_onnxruntime/models/ch_PP-OCRv4_det_infer.onnx')
            payload=Path(source).read_bytes()
        elif args.source_dir:
            payload=(args.source_dir/name).read_bytes()
        else:
            with urlopen('https://vocr.vn/data/vietocr/vgg_seq2seq.pth',timeout=60) as response:
                payload=response.read(96*1024*1024+1)
        if sha256(payload).hexdigest()!=expected: parser.error('OCR asset checksum mismatch')
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(dir=args.output,delete=False) as output:
                temporary=Path(output.name);output.write(payload);output.flush();os.fsync(output.fileno())
            temporary.replace(target)
        finally:
            if temporary is not None: temporary.unlink(missing_ok=True)
    validate_vietocr_assets(args.output)
    print('Pinned local Vietnamese OCR assets are ready. Select backend explicitly; default is unchanged.')


if __name__=='__main__': main()
