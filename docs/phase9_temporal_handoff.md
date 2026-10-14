# Phase 9 temporal handoff — complete

Updated: 2026-10-14, Asia/Bangkok. P9-01–06 DONE; T9-01–05 PASS.
All 24 frozen quality cases pass actual application replay. Bindings, handoff,
offline checks and cleanup are complete. No native API performance claim is made.

The product resolves source eligibility before retrieval/generation, separates
version labels/cohort periods from effective dates, and binds temporal decisions
to answer/retrieval scope and metadata generation. Unknown applicability and
unproven latest/current precedence stop before the model. Comparisons require
both selected versions in the same source-reviewed family, with bounded evidence
for each side. Reranker stays off; no provider calls or paid fallback were used.

Native ingest retains exact date clauses and precision. Signing dates cannot
become effective dates without an explicit same-day clause. Missing/invalid
dates remain unknown. Optional curated family/replacement annotations require
source proof and review; they are not inferred from filenames or publication
order. Cross-document grouping cannot rely only on a program name when degree
and document type are unknown. Partial amendments never silently repeal a whole
parent. Complex partial-amendment applicability currently abstains safely.

Frozen inputs: `evaluation/phase9/protocol.json`, `benchmark.jsonl`,
`source-rubric.json` and `source-audit.json`. There are two real-source families,
12 dev and 12 acceptance cases, plus the unchanged Phase 8 temporal regression.
The 2023 electronics PDF has blank signature day/month/number and explicitly
applies from intake 2022. QH-2025 is a cohort designation. Neither justifies
inventing an effective day or global current validity. The newly preserved HTML
source uses a declared logical snapshot page, not a physical PDF page.

Verification completed:

- 24/24 source eligibility decisions; 16/16 real negative cases stop before LLM.
- Original 116 focused controls plus the repaired split-fact/version control;
  current full suite 1,502 PASS / 2 opt-in live SKIP, coverage 91.05%.
  Initial full-suite failure is retained: the old historical
  receipt correctly rejects a changed runtime. Its guard remains enforced.
- Current-runtime regressions: Phase 7 all 68 public outputs/provider bodies
  match their reviewed baseline; Phase 8 145 reviewed answers and 155 local
  negatives remain correct, with 300 valid schemas and 178 supported claims.
- Local alternating warm measurements with an instant synthetic model show no
  observed processing regression. These are neither model quality nor API SLOs.

All eight original outputs were received and individually source-reviewed:
eight raw schemas valid, seven content answers accepted and one false abstention.
Original application replay passed 21/24 cases. The electronics degree comparison
omitted a short fact block from its bounded context. Two correct duration answers
were also falsely rejected because grounding did not receive the source-verified
version from a separate title block. Both application defects are repaired;
gold and raw failures remain unchanged. Version propagation uses independently
verified source annotations, never filenames or unproven dates. Comparison fact
preference operates only within the existing bounded candidates, with no extra
retrieval/model pass.

Six original payloads remain byte-identical. Two comparison payloads changed
(`p9-robotics-07`, `p9-electronics-07`) and received new actual owner-mediated
Chat outputs. Both were independently source-reviewed and replayed with those
exact captured prompts/schemas. All 24 cases now pass: 8 positive answers,
16 safe local negatives, 12 supported claims/citations and 24 valid public
schemas; no missing outputs, false abstentions or scope leaks. Dev and acceptance
are each 12/12. These are exposed reruns, not fresh validation. The original
failed raw output and replay are preserved, not overwritten by the successful run.
The current per-case review and complete raw replay are hash-bound by
`evaluation/results/phase9-completion-20261014.json`.

No further Chat output or provider call is required. The original and repair
packets remain evidence of the submitted model inputs. Raw responses retain the
owner-mediated provenance; Chat UI model/settings were not independently verified.

Zero-network commands from the repository root:

```powershell
.venv\Scripts\python.exe -m evaluation.phase9.prepare
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
# Replay all eight actual model outputs and all sixteen local negatives.
.venv\Scripts\python.exe -m evaluation.phase9.run --capture-file .local_artifacts/experiment_runs/phase9-20261014/repair-preflight.json --responses .local_artifacts/experiment_runs/phase9-20261014/complete-chat-responses.jsonl
```

Do not regenerate or replace the packet after sending it. The runner rejects
overwriting a frozen capture, checks captures before writing a replay receipt,
and records missing model cases explicitly. Repeating a replay writes a new
`-rerun-N` receipt; prior raw receipts remain unchanged. The evaluator-only
receipt guard was checked by another full 24-case replay with identical prompts,
public answers and runtime hash; the previous source digest was reconstructed
using the retained evaluator snapshot. Production code and full-suite coverage
did not change. Replay checks the
captured runtime, index, prompt and schema. A runtime or payload change requires
an explicit compatibility review; never silently attach responses to new inputs.
If source metadata changes, persist the BM25/index generation and invalidate
both caches. Reference day/timezone and resolver policy are part of answer reuse.
Clear any experimental answer cache when upgrading from an unqualified development
runtime; the temporal policy remains an unreleased implementation until phase exit.

All raw source/index/observations/tests are retained in the hash-verified local
artifact store. The compact [progress report](../evaluation/results/phase9-progress-20261014.json)
provides current bindings and pending work. Phase 7/8 historical reports/gold stay
unchanged; live R-01/R-02 are not qualified by this temporal workflow.

Cleanup removed 18 task-temporary paths, including all Phase 9 pytest roots,
the exported coverage database and the final helper. The owner separately approved
root-only ACL changes on two inaccessible pytest directories after initial
automatic review rejection. A same-account Administrator/UAC helper inspected
4,779 entries per root, found no reparse points, removed both and verified absence.
No recursive ACL change or outside-project action occurred. The helper's exact
bytes and cleanup receipt are retained in the artifact catalog. Source, baseline,
frozen inputs, failure evidence and successful raw responses remain retained.
