"""Run the Gemini connectivity probe using the configured-key wrapper."""
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "evaluation/results/phase7-completion-20261004/probe_gemini_live.py"
runpy.run_path(str(TARGET), run_name="__main__")
