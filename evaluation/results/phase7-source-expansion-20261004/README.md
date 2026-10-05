# Phase 7 source expansion — 2026-10-04

This is source preparation, not release acceptance. Active r18 remains M0/M1/S1
PASS, M2 FAIL, 3/19 gates PASS, score unavailable. No new heldout/model scores
were measured and no existing benchmark, source index or consumed lock changed.

Original public UET PDFs are retained in
[`data/corpus/phase7_source_expansion/20261004`](../../../data/corpus/phase7_source_expansion/20261004/source_manifest.json).
Document years come from the PDFs: Robotics 2020 and Electronics masters 2022.
They are not represented as current 2026 curricula. The Nano biology scan-only
PDF is archived but excluded from indexing; the Physics download failed TLS
hostname verification, recorded without disabling verification.

Actual offline CUDA BGE-M3 indexing added 158 chunks from two readable PDFs to a
separate copy of the original index. All original document bytes were preserved.
The expanded index has 12 documents, 26 files, embedding dimension 1024 and
manifest SHA-256 `f944f088bc01f173c340f92b94b8f3f89b0f61af9fabec84a38a51440d91ac3d`.
The physical cached model commit is
`5617a9f61b028005a4858fdac845db406aefb181`; the existing serialization field `1`
is a provider version, not that commit. Exact source/runtime bindings are in
the historical GPU build receipt and source ZIP; this is not a clean release.

Explicit header/row extraction binds 95 course rows (61 Robot, 34 Electronics)
to the physical index. Source rendering corroborates column roles and merged
credit cells. Blank prerequisite cells remain unknown. The Robot page-13 table
split omits some rows, so the extractor does not claim complete course coverage.

The final automatic history screen includes 27,957 question occurrences from
all JSONL files under `data/benchmark` and `evaluation/results`, including owner
inputs. Exact course codes with spacing, Vietnamese/English aliases and wrapped
name spans exclude historical mentions. It proposes 43 connected source groups;
semantic exposure approval, question generation and successor freeze are pending.
The preliminary 53/44-group screens are preserved as historical diagnostics.

Final offline regression: **786 passed, 2 opt-in live LLM tests skipped**, coverage
**89.51%**. Final spaced-code history audit is
`source_history_screen_spaced_codes.json`; the restored-index replay is
`restored_index_history_screen.json` and yields the same proposals and exclusions.
The audit source snapshot is distinct from the earlier GPU-build snapshot; neither
is used to reinterpret the old r18 release measurements.

`expanded_index.zip` restores every index file byte-for-byte. The raw ingestion
JSONs are exact-byte gzip archives. Archive/member SHA-256s, PDF receipts,
source table PNGs and source snapshots provide reproduction evidence.

```powershell
$env:PYTHONPATH='.;src'
$env:PYTHONUTF8='1'
Copy-Item evaluation/results/phase7-source-expansion-20261004/reproduction/restore_and_verify_index.py.txt .tmp/restore_and_verify_index.py
.venv/Scripts/python.exe .tmp/restore_and_verify_index.py .tmp/phase7-expanded-restored-review
.venv/Scripts/python.exe -m scripts.benchmarks.audit_phase7_source_proposals --index-dir .tmp/phase7-expanded-restored-review --source-manifest data/corpus/phase7_source_expansion/20261004/source_manifest.json --history-dir data/benchmark --history-dir evaluation/results --output .tmp/phase7-expanded-restored-audit.json
```

Use absent restore/audit destinations. Do not rebind old measurements to this
index. Next: reconstruct all consumed r18 rows and the 13 exposed r12 absence
rows as strictly dev-only, prove old source provenance under the expanded index,
audit semantic aliases and connected groups, then freeze a successor benchmark
before measuring M0–M12 and S1–S6 in order.
