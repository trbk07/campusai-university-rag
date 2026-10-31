@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Chua co moi truong Python. Chay: uv sync --frozen --extra feasibility --extra ocr
  pause
  exit /b 1
)
set PYTHONUTF8=1
".venv\Scripts\python.exe" -u -m scripts.operations.local --open-browser
if errorlevel 1 pause
