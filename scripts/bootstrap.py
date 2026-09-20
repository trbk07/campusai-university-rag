"""Create an isolated .venv and install this repository (cross-platform)."""
from __future__ import annotations
import os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"
python = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
if not python.exists():
    subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])
subprocess.check_call([str(python), "-m", "pip", "install", "--upgrade", "pip"])
subprocess.check_call([str(python), "-m", "pip", "install", "-e", f"{ROOT}[dev]"])
print(f"Ready: {python}")
