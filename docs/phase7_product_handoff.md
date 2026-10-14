# Phase 7 product handoff

## Current completion — owner-amended Chat quality scope, 2026-10-13

**DONE — 100% of the owner's amended quality scope.** The owner explicitly
accepts Chat/file-based answer verification instead of waiting for the API.
All 68 cases pass source review and actual paired application replay: 42 correct
answers, 26 correct negatives, 74 supported claims and 90 supported citation
pairs. Final offline checks pass 1,473 tests with 90.60% coverage; two opt-in
live tests are skipped here, with their earlier genuine integration evidence
retained. All 60 fault cases and the current runtime/evidence bindings pass.

No unchecked content cases remain and no further Chat submission is needed.
The [completion audit](../evaluation/results/phase78-chat-quality-completion-20261013.json)
records the scope amendment and reproducible zero-network checks. C7-05's
original live performance requirement remains **NOT PASSED / RELEASE HARDENING
PENDING**; this closure does not establish production readiness or turn prior
503 failures into successes. Keep reranker off. The following checkpoints
describe the original live contract and remain historical audit evidence.

## Historical live goal — 2026-10-13, provider unavailable

The owner-approved remaining Phase 8 live cohort stopped after its first POST
returned HTTP 503; no retry or key rotation followed. This is a genuine current
product observation, but it does not substitute for C7-05's locked 100-HTTP /
54-provider-call workload. C7-05 and its dependent C7-06 remain incomplete;
the two genuine integrations and quality/fault evidence remain retained.
No new performance run is scheduled while provider recovery is unverified.

The [current execution audit](../evaluation/results/phase8-live-remaining-20261013/exit-review.json)
verifies the exact current source/payload, unchanged product runtime and
300-case regression. The older snapshots below remain historical; their
source hashes are not rewritten after measurement dispatcher/test updates.
Reproduce the current zero-network audit with:

```powershell
.venv\Scripts\python.exe evaluation/results/phase8-live-remaining-20261013/review-execution.py.txt
```

## Latest verification — 2026-10-13

[Continuation review](../evaluation/results/phase7-free-tier-performance-20261013/progress-review.json)
records **2/2 real Gemini integrations PASS**, 1,466 offline tests PASS and
90.60% coverage. The two opt-in tests skipped in the offline suite passed
separately against the provider. Product source/configuration did not change;
the review reconstructs the previous source hash with only the performance
collector and its tests reverted.

The unchanged 100-HTTP/54-provider-call performance workload now supports
Free Tier quota pauses between complete cycles. It counts bound shared history
against 18 starts per Pacific day, permits no immediate retry, rejects modified
or failed checkpoints, and never resends a completed cycle. Its 46 regression
tests and 20-request offline preflight pass. This infrastructure change does
not qualify latency or availability.

The real run stopped after its **first POST returned HTTP 503**. The HTTP
application returned a valid fallback in 1,944.457 ms. No retry or key rotation
followed; provider usage/cost was unavailable. The run is terminal and cannot
resume. Earlier synthetic integrations took 3,616.272 and 2,485.974 ms; their
success does not establish availability for the full workload.

**Phase 7 remains 4/6 DONE.** C7-05 needs a complete live performance result;
C7-06's test/integration evidence is ready but final closure depends on C7-05.
No further packet or background provider job is scheduled. Keep reranker off.
Historical reproduction (requires that receipt's matching source tree):

```powershell
.venv\Scripts\python.exe evaluation/results/phase7-free-tier-performance-20261013/review-progress.py.txt
```

## Quality acceptance checkpoint — 2026-10-13, before live continuation

The owner returned the active work to Phase 7 and authorized Gemini Chat for
answer-quality verification. **C7-03 is DONE/PASS via owner-mediated Chat**;
the API quota-window workflow below is historical and must not be started.
Phase 7 is now **4/6 items DONE (66.7%)**. The owner supplied all three batches
in one attachment, then a formatting-only resubmission: all 68 unique IDs are
schema-valid and answer/quote/claim contents are unchanged. Original malformed
bytes and the initial application failures remain audit evidence.
The replay exposed false abstentions on institution-prefixed course codes.
Exact column proofs now recognize the full prefix without merging it with bare
codes; cache policy is `grounding-v5`. The corrected product answers 42/42
positive items and abstains correctly on 26/26 negatives, with 74/74 grounded
claims and 90/90 supported claim-citation pairs. Both splits pass the unchanged
numeric gate. See [paired quality review](../evaluation/results/phase7-chat-quality-20261013/paired-quality-review.json)
for source bindings, denominators, strata, grouped intervals and limitations.
168 focused tests and 60/60 fault/restart cases in two processes pass.
The current full offline suite passes **1,457 tests**, with **2 live tests
skipped**, and **90.60% coverage**. See [current offline check bindings](../evaluation/results/phase7-chat-quality-20261013/completion-review.json).

Use [the three batches and shared prompt](../evaluation/phase7/chat-quality-20261013/README.md).
The 24/24/20 inputs cover 42 current and 26 baseline generation calls; the full
experiment still contains 68 question pairs and 136 application responses.
The exact current profile was exercised offline and all 136 prepared cases
match v33's requests, prompts and evidence. No provider request was sent.
No answer key, rubric, arm label or benchmark gold is exported to Chat.

Keep the frozen rubric, comparator and thresholds. Received raw bytes must be
retained without silent escape repair. Schema validity alone is not semantic
acceptance. Review every answer/claim against original sources, run both actual
applications with recorded responses, then score primary splits and regression
against the frozen comparator. These steps are complete for this intake.
Chat UI model/settings remain unverified unless
supplied; do not label recorded application timing as live Gemini latency.

C7-05 is now the active work item; live performance and integrations still need separate runtime evidence. This modality
change does not waive them, promote the reranker or declare 6/6 DONE. The latest
rebind/review is under `evaluation/results/phase7-chat-quality-20261013/`.

## Historical API handoff — superseded for quality collection

Roadmap: [plan.md](../plan.md). Authoritative task state: [completion ledger](../evaluation/results/phase7-completion-20261004/completion_task_ledger.json).

Phase 7 is **3/6 DONE (50%)**, not complete. Keep the local single-process serving profile with `RERANKER_ENABLED=false`. The historic 20-task/19-gate reranker qualification is outside this product-hardening scope.

| Item | State | Current evidence |
|---|---|---|
| C7-01 - serving identity | DONE | [Snapshot v15](../evaluation/results/phase7-completion-20261004/product-serving-snapshot-20261010-v15.json), source `6003f0fc55bcb684fd2c1fe8914d58dfc7b1098b863b5a7184037d0a01b62a0f`, runtime `2ac74741dcc51035c35133a62f8a48e82bfe0a34180520cea05a962f770a5a79`. |
| C7-02 - retrieval/context/scope | DONE | [Rebound audit v2](../evaluation/results/phase7-completion-20261004/product-c7-02-rebind-20261010-v2.json): all 136 baseline/current requests, serialized provider bodies and retrieval evidence byte-match consumed v28. Existing 35 test/33 holdout retrieval metrics remain bound; no fresh-validation claim. |
| C7-03 - answer quality | BLOCKED - Free Tier windows | [V30 shard manifest](../evaluation/results/phase7-completion-20261004/product-primary-retry-manifest-20261010-v30.json), SHA-256 `958ec43d34406abf595aab1d229c129539120299ca656b2f7aa5adc83b6772b7`. Five fixed qid-paired shards plan 68 provider POSTs (14/13/13/14/14), with one shared retry only for HTTP 503 (69 max total). The bundle is offline-validated and has sent zero provider requests. |
| C7-04 - security/failure/restart | DONE | [Current-identity fault/restart v2](../evaluation/results/phase7-completion-20261004/product-runtime-faults-finalprofile-20261010-shards-v2/summary.json): 60/60 cases, 12 categories, two processes, zero provider calls. |
| C7-05 - live performance | BLOCKED by C7-03 | Run the frozen 54-call workload only after full primary source review passes. It will need its own Free Tier-safe execution plan. |
| C7-06 - final checks/handoff | IN PROGRESS | [Full offline suite v4](../evaluation/results/phase7-completion-20261004/product-c7-final-offline-tests-20261010-v4.xml): 1,312 passed, 2 opt-in live integrations skipped; [coverage](../evaluation/results/phase7-completion-20261004/product-c7-final-coverage-20261010-v4.json): 90.60%. Live integrations and final reconciliation remain. |

## Free Tier constraint and primary protocol

The owner requires **Free Tier only and no charges**. Do not link billing, switch to paid quota or rotate keys to evade limits. Google documents that rate limits are per project and requests-per-day quotas reset at midnight Pacific ([rate limits](https://ai.google.dev/gemini-api/docs/rate-limits), [billing](https://ai.google.dev/gemini-api/docs/billing)). The provider reported this project limit as 20 GenerateContent requests. One 68-post run cannot fit.

V27 and v28 are consumed historical runs and cannot resume. V28 produced one complete pair and two valid current answers before HTTP 429 `RESOURCE_EXHAUSTED`. Those responses remain exposed evidence, not fresh validation. V30 preserves the original 68-row population, prompts, source rubric, gold answers, model alias, profile and thresholds. Each shard keeps both arms for each qid together; no partial shard can count as acceptance. The collector permits at most one shard per Pacific date, at most 14 planned POSTs plus the single global retry (15 attempts), and reserves five requests below the observed daily limit. It records Gemini `modelVersion` and stops the whole bundle if that version changes across shards. Any provider/quota error stops the bundle; there is no resume or replacement packet.

V30's source identity is the identity bound by snapshot v15. Its parent packet has SHA-256 `ba1e723d6d82bf941869692a6d75ac3f132db95c8d7b953c26f1062c1994c533`. Shard hashes are:

| Shard | Planned POSTs | SHA-256 |
|---|---:|---|
| 1 of 5 | 14 | `8256ec3f95ba82230c5a20fbdf70577dbfb783c85cb7be54df4add1bb697b69b` |
| 2 of 5 | 13 | `59d36bed8404627e453698249d0df00f10fb195c8a07b76925ed2ec4eb5b47b2` |
| 3 of 5 | 13 | `5da68fa9634a638084005c6c0d515372785f41560a502d47b87883f8ca1eb6b7` |
| 4 of 5 | 14 | `4afad9a32125e5d430361c024e35e2097d3ccdd25301e16b2c94d73d14aac459` |
| 5 of 5 | 14 | `60be9f409b6c766ae225cb013a2b2ca11b6f94bce111e4c8a84bbd67f683ff3f` |

The shared budget is not initialized yet. No provider request has been sent under v30. Offline validation confirms all 68 qids appear once, all 68 planned POSTs are accounted for, each shard is within cap, the maximum is 69 attempts, and no output or rubric was altered.

## Reproduction

From `D:\Project`, initialize the exact one-time budget once after confirming the project is in a new Pacific quota date:

```powershell
.venv\Scripts\python.exe -m scripts.benchmarks.product_retry --manifest evaluation\results\phase7-completion-20261004\product-primary-retry-manifest-20261010-v30.json --authorized-manifest-sha256 958ec43d34406abf595aab1d229c129539120299ca656b2f7aa5adc83b6772b7
```

Collect one shard per Pacific date using the packet path/hash above:

```powershell
.venv\Scripts\python.exe -m scripts.benchmarks.product_primary collect --packet <shard-packet.json> --authorized-packet-sha256 <shard-sha256>
```

After all five shards succeed, validate the full 68-pair union and model-version lock:

```powershell
.venv\Scripts\python.exe -m scripts.benchmarks.product_primary aggregate-quota-shards --manifest evaluation\results\phase7-completion-20261004\product-primary-retry-manifest-20261010-v30.json --authorized-manifest-sha256 958ec43d34406abf595aab1d229c129539120299ca656b2f7aa5adc83b6772b7 --output evaluation\results\phase7-completion-20261004\product-primary-aggregate-20261010-v30.json
```

Aggregation produces a source-review bundle; it does not itself accept answer quality. Review every output against the unchanged rubric and thresholds. Only after C7-03 passes may the frozen performance workload and two integrations run, using only available Free Tier quota. Do not change the source identity, model, index, prompt or thresholds between shards or before performance.

C7-06 remains incomplete because the two live integration tests were skipped and final evidence reconciliation is pending. Secret scan passed; v30 has made zero external calls. Keep the answer key in ignored `configs/key.yaml`; never print, hash or copy it into artifacts.
