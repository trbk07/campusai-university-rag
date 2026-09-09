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

$tessdata = 'C:\Program Files\Tesseract-OCR\tessdata'
$vie = Join-Path $tessdata 'vie.traineddata'
if (-not (Test-Path $vie)) {
    if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Administrator PowerShell is required to install Vietnamese OCR data into Program Files. Re-run PowerShell as Administrator.'
    }
    Invoke-WebRequest -Uri 'https://github.com/tesseract-ocr/tessdata_fast/raw/main/vie.traineddata' -OutFile (Join-Path $env:TEMP 'vie.traineddata')
    Copy-Item (Join-Path $env:TEMP 'vie.traineddata') $vie -Force
    Remove-Item (Join-Path $env:TEMP 'vie.traineddata') -Force
}
uv run python scripts\ocr_check.py --language eng+vie
Write-Host 'OCR setup complete: English and Vietnamese OCR are ready.'
