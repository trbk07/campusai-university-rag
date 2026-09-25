# UET university corpus

This directory contains public UET/VNU PDF inputs for Phase 1/2 acceptance.
`manifest.json` records each source URL, document category, language, SHA-256,
and holdout assignment. The PDFs are ignored by Git; rebuild them with:

```powershell
.\.venv\Scripts\python.exe scripts\download_uet_corpus.py
```

The acceptance command is:

```powershell
.\.venv\Scripts\python.exe scripts\accept_phase12.py `
  --input-dir data\corpus\university `
  --holdout data\corpus\university\uet_admission_2025.pdf `
  --output evaluation\phase12_acceptance.json
```
