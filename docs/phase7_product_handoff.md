# Phase 7 product handoff - in progress

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
