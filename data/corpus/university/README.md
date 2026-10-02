# UET university corpus

This directory contains public UET/VNU PDF inputs for Phase 1/2 acceptance.
`manifest.json` records each source URL, document category, language, SHA-256,
and holdout assignment. The PDFs are ignored by Git; rebuild them with:

```powershell
.\.venv\Scripts\python.exe -m scripts.ingestion.download_uet_corpus
```

The acceptance command is:

```powershell
.\.venv\Scripts\python.exe -m scripts.ingestion.validate_ingestion `
  --input-dir data\corpus\university `
  --holdout data\corpus\university\uet_admission_2025.pdf `
  --output evaluation\results\ingestion_acceptance.json
```
