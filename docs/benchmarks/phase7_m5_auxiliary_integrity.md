# M5 auxiliary integrity task — 2026-10-03

This task completes source and evaluation integrity fixes. M5 is still failing.
See [plan.md](../../plan.md#phase-7--reranker) for the active roadmap and
[the archived summary](../../evaluation/results/phase7-source-context-20261003-r17/dev_auxiliary_integrity_task/task_summary.json)
for hashes, physical source identity and compressed raw observations.

## Repairs

- Inspect every decoded body in the scoped curriculum, including table cells.
  The initial eight-record experiment inspected only course-code occurrences.
  Four records use a document mentioning instructors elsewhere; they cannot
  establish the conservative whole-document absence proof.
- Reconstruct course names/codes from frozen source tables and verify the
  original owner-authorized dev generation bank. Bind policy, confirmation,
  generation authorization, source bank, history, index and primary dev hashes.
- Keep AI origin, owner identity and actual recording time explicit. There is
  no independent human review or new heldout claim.
- Declare one common template group. Four distinct course pairs therefore
  constitute one connected auxiliary group, with their primary family links.
- Allow `--evidence-dev` only alongside `--exploratory`. No automatic discovery
  in the release workflow or unconditional auxiliary requirement in M5.
  Existing gate thresholds remain unchanged. Report primary metrics separately.

## Actual corrected cap-8 measurement

| Observation | Result |
|---|---:|
| Primary / auxiliary rows | 212 / 4 |
| Primary / auxiliary scored requests | 81 / 4 |
| No / partial / sufficient evidence examples | 6 / 14 / 65 |
| Connected auxiliary groups | 1 |
| Grouped folds | 5 |
| Primary selected Recall@5 | 96.23% |
| Primary selected negative FPR | 3.77% |
| Combined fitted / OOF negative FPR | 10.53% / 10.53% |
| Rerank p95 | 146.38 ms |
| Inference errors | 0 |
| Calibration feasible | false |
| Related verification | 80 passed |

Both failed experiments are retained, with their original source identities.
The archive's source delta preserves the exact measured files; its inventory
recomputes the measured source SHA. One unused test import was removed after
inference. These observations remain exploratory and are not rebound to the
later source. Gzip entries preserve exact uncompressed bytes and both checksums.

No heldout rows were opened for this task and no Gemini calls were made.
M3/M4 receipts belong to the earlier 618a6ef snapshot; their immutable study
locks remain intact. The previous r15 M6 failure remains consumed, including
its unchanged machine test/holdout bytes.

## Remaining dependency

The current v1 probability features did not distinguish missing requested
information reliably in these grouped dev measurements. A proposal to change
the shared runtime feature schema/version was rejected by automatic approval
review because of its persistent serving impact. Specific permission is
pending. A successor source freeze and valid benchmark procedure are needed
before official M3–M5 measurements and subsequent release gates.
