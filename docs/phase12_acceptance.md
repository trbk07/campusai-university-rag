# Phase 1/2 acceptance

Phase 1/2 now has executable acceptance evidence in
[`evaluation/phase12_acceptance.json`](../evaluation/phase12_acceptance.json).
Regenerate it with:

```powershell
.\.venv\Scripts\python.exe scripts\accept_phase12.py `
  --input-dir data\corpus\university `
  --holdout data\corpus\university\uet_admission_2025.pdf `
  --output evaluation\phase12_acceptance.json
```

The runner uses eight supplied real UET/VNU university PDFs. The minimum is
five real PDFs, at least three document types, multi-page/table coverage, and
an explicit scan/review case. The latest regenerated report has 16/16 exit
criteria true and declares `uet_admission_2025.pdf` as holdout.
Generated fixtures may be enabled with `--allow-fixtures` for deterministic
regression coverage, but they are always labelled `generated_acceptance_fixture`
and can never make the real-corpus gate pass. A 10/10 run must also declare a
real holdout:

```powershell
.\.venv\Scripts\python.exe scripts\accept_phase12.py `
  --input-dir data\corpus\university `
  --holdout data\corpus\university\uet_admission_2025.pdf `
  --output evaluation\phase12_acceptance.json
```

The acceptance contract covers:

- coverage-based real corpus acceptance with document/page/type/citation
  provenance on every text chunk;
- scan ingestion completing as `review_required` with `ocr_required`;
- normalized institution, faculty, program, course/code, version, academic-year,
  issue/effective-date metadata with confidence and source evidence;
- PDF-style heading detection, section inheritance, page ranges, overlap,
  empty-page and heading diagnostics;
- independent table chunks with preserved headers, table IDs, and page ranges;
- golden fixtures for `Điều kiện tốt nghiệp` and `Học phần tiên quyết`.
- atomic registry persistence and full document artifact deletion.
- fail-closed citation validation for document, chunk, page range, table ID,
  source hash, and deleted artifacts.

Confidence note: the current metadata confidence is a binary signal (0.9 when
the field matches a known pattern, 0.0 otherwise), not a calibrated
probability. Future calibration can incorporate source-page position and
pattern specificity.

The document registry uses an in-process `threading.RLock`; it is safe for
threads in one process, but distributed multi-process registry locking remains
out of scope for Phase 1/2.

The golden regression suite is:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_phase12_acceptance.py
```
