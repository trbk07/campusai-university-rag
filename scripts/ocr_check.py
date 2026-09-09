"""Check Python OCR dependencies, Tesseract, and requested language packs."""
import argparse
import importlib.util
from agentic_rag.ingestion.ocr import available_languages, resolve_tesseract


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", default="eng")
    parser.add_argument("--tesseract-cmd", default=None)
    args = parser.parse_args()
    missing = []
    if not importlib.util.find_spec("pytesseract") or not importlib.util.find_spec("PIL"):
        missing.append("Python OCR packages: uv sync --extra ocr")
    command = resolve_tesseract(args.tesseract_cmd)
    if not command:
        missing.append("Tesseract executable: run scripts\\setup_ocr_windows.ps1")
    languages = available_languages(command)
    requested = set(args.language.split("+"))
    missing_languages = sorted(requested - set(languages))
    if missing_languages:
        missing.append(f"Tesseract language data: {', '.join(missing_languages)}")
    print(f"tesseract: {command or 'NOT FOUND'}")
    print(f"languages: {', '.join(languages) or 'NOT FOUND'}")
    if missing:
        print("OCR CHECK: FAILED")
        for item in missing:
            print(f"- {item}")
        return 1
    print("OCR CHECK: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
