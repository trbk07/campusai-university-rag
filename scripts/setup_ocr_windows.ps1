$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'uv is required. Install it from https://docs.astral.sh/uv/'
}
uv sync --extra dev --extra ocr

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw 'winget is required, or install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki'
}
winget install --id UB-Mannheim.TesseractOCR -e --accept-package-agreements --accept-source-agreements
uv run python scripts\ocr_check.py --language eng
Write-Host 'OCR setup complete. Add vie language data separately for Vietnamese OCR.'
