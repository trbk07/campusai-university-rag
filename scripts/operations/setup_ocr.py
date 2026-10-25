"""Install pinned language data explicitly; app requests never download models."""
import argparse
from hashlib import sha256
from importlib.metadata import version
import os
from pathlib import Path
import tempfile
from urllib.request import urlopen

from campusai.ingestion.ocr_assets import TESSDATA_SHA256, TESSEROCR_VERSION, validate_tesseract_assets


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('.cache/ocr/tessdata_fast'))
    parser.add_argument('--source-dir',type=Path,help='Use already downloaded official models offline')
    args=parser.parse_args()
    if version('tesserocr') != TESSEROCR_VERSION:
        parser.error('Install the project [ocr] extra first')
    args.output.mkdir(parents=True,exist_ok=True)
    for language,expected in TESSDATA_SHA256.items():
        name=language+'.traineddata';target=args.output/name
        if target.is_file():
            if sha256(target.read_bytes()).hexdigest()!=expected:
                parser.error('Existing language model has a different checksum; keep it outside the pinned directory')
            continue
        if args.source_dir:
            payload=(args.source_dir/name).read_bytes()
        else:
            url='https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/4.1.0/'+name
            with urlopen(url,timeout=60) as source:payload=source.read(8*1024*1024+1)
        if sha256(payload).hexdigest()!=expected:
            parser.error('Language model checksum mismatch; nothing installed for this language')
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(dir=args.output,delete=False) as handle:
                temporary=Path(handle.name);handle.write(payload);handle.flush();os.fsync(handle.fileno())
            temporary.replace(target)
        finally:
            if temporary is not None:temporary.unlink(missing_ok=True)
    validate_tesseract_assets(args.output)
    print('Pinned local Vietnamese/English OCR language models are ready.')


if __name__=='__main__':main()
