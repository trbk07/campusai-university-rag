# Phase 7 successor source preparation — 2026-10-04, batch b

This archive is source preparation, not release acceptance. The active r18
release still has M0/M1/S1 PASS and M2 FAIL: 3/19 gates, null score and
`all_release_gates_pass=false`. No new benchmark questions, heldout eligibility,
reranker measurements or release freeze are claimed here.

Original public PDFs are in
[`data/corpus/phase7_source_expansion/20261004b`](../../../data/corpus/phase7_source_expansion/20261004b/source_manifest.json).
The combined manifest retains Robot 2020 and Electronics masters 2022, adds
Telecommunications masters 2022 and the Engineering Mechanics study guide, and
keeps the scan-only Nano biology document excluded. The Mechanics URL was
published in 2019; the PDF does not state an academic cohort, so its indexed
`academic_year` is `unspecified`. These documents are not called current 2026
curricula. The original batch and consumed benchmark artifacts remain intact.

Actual offline CUDA BGE-M3 indexing added **47 chunks** (35 Telecommunications,
12 Mechanics) to a separate copy of the 12-document index. The result has
**14 documents**, 30 physical files and manifest SHA-256
`40a3e711298fdb66cdd906b19ad84ab9565dd43badfed7caed4eef81a671bec6`.
All previous document files are byte-identical; only the copied root manifest
changes. `expanded_index.zip` restores all 30 file hashes and reproduces the
history screen. The physical model revision is
`5617a9f61b028005a4858fdac845db406aefb181`; the existing provider version field
`1` is not a Hugging Face commit.

PDF table renders corroborate **43 new explicit course rows**, making 138 rows
across four readable sources. Mechanics has eight named coursework rows plus
EMA7205 thesis, 18 credits. Uncoded elective placeholders are excluded. Blank
prerequisites remain unknown. Source spelling and translations are retained,
including duplicates across Electronics and Telecommunications; they are not
counted as independent subjects.

The final `source_history_screen_ancestor.json` checks **28,774 historical
question occurrences in 177 JSONL files**. It forms connected course-code and
bilingual/wrapped-alias families across all indexed curriculum tables before
excluding history mentions. Exposure in one source propagates through the
whole family, including old indexed ancestors. The preliminary independent
row screen proposed 51 groups; transitive screening leaves **59 rows in 47
groups**. These are automatic proposals. Semantic exposure review and complete
successor split/group preflight remain pending; no heldout approval is inferred.
`restored_index_history_screen_ancestor.json` reproduces the final proposals,
exclusions and historical inventory. Earlier screens are retained as dated
diagnostics, without rebinding their source snapshots.

Final offline regression: **812 passed, 2 opt-in live LLM tests skipped**,
coverage **89.51%**. The skips are not live-provider acceptance.
`index_build_source_manifest.json` binds the GPU build to its actual original
source/runtime. `final_ancestor_audit_source_manifest.json` separately binds
the final screening/tests to their CPU source/runtime. Both retain the existing
dirty source helper explicitly and are not clean release manifests.

Reproduction uses an absent destination:

```powershell
$env:PYTHONPATH='.;src'
$env:PYTHONUTF8='1'
Copy-Item evaluation/results/phase7-successor-source-20261004b/reproduction/restore_and_verify_index.py.txt .tmp/restore_phase7_source_b.py
.venv/Scripts/python.exe .tmp/restore_phase7_source_b.py .tmp/phase7-source-b-restored
.venv/Scripts/python.exe -m scripts.benchmarks.audit_phase7_source_proposals --index-dir .tmp/phase7-source-b-restored --source-manifest data/corpus/phase7_source_expansion/20261004b/source_manifest.json --history-dir data/benchmark --history-dir evaluation/results --output .tmp/phase7-source-b-restored-audit.json
```

Next: finish semantic exposure review, implement strict question/source validation
for these explicit column-role facts, reconstruct all 817 inherited rows as dev
under this index, verify independent heldout and novel dev coverage, then freeze
and measure release gates in order. Roadmap: [plan.md](../../../plan.md).
