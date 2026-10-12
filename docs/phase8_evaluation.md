# Phase 8 evaluation

## Latest live measurement — 2026-10-12, stopped after HTTP 503

The owner explicitly requested real Gemini latency and format measurement after
the completed Chat content regression. The bounded workload reuses previously
approved prompt/schema bodies: 18 answerable cases from 18 connected groups,
119,242 prompt characters maximum, 1,024 output tokens/attempt (18,432 maximum),
15s provider timeout, at least 30s between starts, key_2, no retries/key rotation.
The owner-declared Free Tier restriction remains; no billing or paid fallback was
enabled. Google lists standard Gemini 3.8 Flash input/output as free on Free Tier:
https://ai.google.dev/gemini-api/docs/pricing. Account billing tier is not exposed
by the generation response and is not independently verified by this runner.

Evidence is in `evaluation/results/phase8-live-runtime-20261012/`:
`manifest.json`, bound `preflight.json`, durable `execution.json`,
`measurement.json` and `measurement-review.json`. The independent AI review
checks source facts/citations for all three successful answers, bindings,
strict start spacing (30.250 / 30.179 / 30.315s) and the 19 passing tests.
Actual prompt characters sent: 35,087; known successful output tokens: 1,322.
Usage for the failed request was not supplied and is not silently recorded as zero.
This adds actual API evidence without overwriting or mixing
it into the historical API ledger or the 300-case recorded-Chat replay.

| Measurement | Observed result | Denominator and limits |
|---|---:|---|
| Provider availability | 3 HTTP 200 / 4 POST | Fourth attempt returned HTTP 503; stopped, no retry |
| Original Gemini JSON/schema | 3/3 valid | Only final texts received; no repair or normalization |
| Valid provider schema per attempt | 3/4 | Includes the 503 in denominator; fallback is not Gemini output |
| Model identity and finish reason | gemini-3.8-flash / STOP | All three successful API responses |
| First request, excluding startup | 5,869.477 ms | One observed cold request |
| Startup + first request | 62,477.242 ms | One cold sample, no estimable distribution |
| Warm p50 / p95 / p99 | 8,640.566 / 11,175.703 / 11,175.703 ms | Three warm requests, including one failed request; group-bootstrap CI in report |
| HTTP 503 fallback | 8,640.566 ms | One real application error response, not discarded |
| Application public/internal schema | 4/4 valid | Includes fallback; separate from provider format reliability |
| Process peak working set | 2,531,639,296 bytes | Actual live application process |

Timing is WSGI application-to-provider end-to-end processing, excluding browser/
TCP transit and inter-request quota pacing. This is real generation rather than
instant recorded output. It is nevertheless a small interrupted sample: **3/18
planned requests succeeded (16.67%)**, 4 attempts spent. It cannot establish
production format reliability or robust p95/p99, and HTTP 503 has not disappeared.
The finite workload is closed after its first failure. The generic collector's
`waiting_next_pacific_day` state does not authorize resuming this finite run;
`measure_live_runtime.run` explicitly refuses any previously started workload.

Collector changes retain failed-request latency, raw final output when present,
and process memory. Quota pacing rounds upward by one microsecond to preserve the
strict 30s guard against floating-point roundoff. The related collector and
measurement tests pass **19/19** in `phase8-live-runtime-recheck-20261012.xml`.
The initial failed test report is retained as history; temporary pytest trees
are removed after checking references. No production algorithm, prompt, key,
model or timeout setting was changed for this measurement.

Phase 8 remains 4/5 steps DONE (80% by closed steps), with the live measurement
step in progress. Content/local regression remains complete. The blocker has
changed from absent live observations to an interrupted live workload due to
provider unavailability. No further Chat answers are needed.

To inspect the existing measurement without sending a provider request:

```powershell
Get-Content -Encoding utf8 evaluation/results/phase8-live-runtime-20261012/measurement.json
```

## Latest result — complete Chat content and application regression, 2026-10-12

The two self-contained plan questions containing `it` now resolve their explicit
local subject. This grammar uses no corpus/course allowlist; unspecified pronouns,
explicit context requirements and authorization still apply. Numeric conflict
signatures preserve legal instrument identifiers: references to different
decisions are separate subjects, while contradictory dates/amounts for the same
decision still abstain. Cache identities are now `request-context-v4` and
`grounding-v4`. Fix tests: 259 PASS; application/benchmark regressions: 42 PASS.

`evaluation/results/phase8-post-fix-preflight-20261012.json` exercises all 300
requests with networking disabled. It reaches generation for 145 answerable
cases and locally abstains for all 155 negative cases. The original 142 model
prompts, schemas, requests and evidence are exactly unchanged. Negative public
responses also remain unchanged. These checks are bound in
`evaluation/results/phase8-post-fix-chat-followup-validation-20261012.json`.

All three requested Chat outputs have arrived and passed independent source,
raw JSON and response-schema review without normalization. Chemistry is in
Semester 1 with 3 credits; Algebra is in Semester 1 with 4 credits; Article 2
applies the rewards rule from September 2023. Raw evidence and decisions are in
`evaluation/results/phase8-gemini-chat-followup-3-raw-20261012.jsonl` and
`evaluation/results/phase8-gemini-chat-followup-3-review-20261012.json`.
Collection is **145/145 (100%)**, no missing or duplicate qids. The original
142 response objects are unchanged in
`evaluation/results/phase8-gemini-chat-responses-post-fix-20261012.jsonl`;
its review summary binds all original and supplemental evidence. No further
Chat output is needed for this benchmark.

## Reviewed baseline — 2026-10-12, after all 145 Chat outputs

The current baseline has **300/300 actual WSGI responses**: 155 native local
branches and 145 recorded Chat responses injected at the model boundary.
Network was disabled. Every original prompt/schema was compared byte-for-byte;
no provider requests, key reads, retries or spending were needed.
The execution receipt and predictions are in
`evaluation/results/phase8-chat-replay-complete-20261012/`.
Its `baseline-review.json` is **AUTOMATED_BASELINE_REVIEW_COMPLETE_EXIT_NOT_MET**,
not human approval or a live-provider release pass. `plan.md` records 4/5 steps
DONE (80% by step count), with 6/7 measurement groups covered in the stated scope.
Provider end-to-end latency remains unmeasured. The separately scoped
`content_and_local_regression_pass` is true, with no weak answerable cases.

| Measurement | Result | Scope |
|---|---:|---|
| AI-reviewed semantic answer correctness | 145/145 (100%) | Source-reviewed Chat answers unchanged in public responses; zero false abstentions |
| Negative false-positive rate | 0/155 | All unanswerable requests abstained |
| Internal and public schema validity | 300/300 | Application contracts after disclosed normalization of recorded inputs |
| Source quote and citation-coordinate validity | 145/145 | Independent indexed-source validation |
| Exact-gold citation precision / recall | 144/145 / 144/145 | One correct source quote points to a text chunk instead of the gold table chunk |
| Temporal course-code accuracy | 20/20 | Exact required codes |
| Exact answer substring | 23/30 | Formatting/wording proxy, not semantic correctness |
| Supported published claims | 178/178 | Runtime alignment plus independently AI-reviewed content; not human labels |
| Local replay cold startup + first request | 33,131.608 ms | One cold sample; no estimable cold CI |
| Local replay warm p50 / p95 / p99 | 20.186 / 174.397 / 238.578 ms | 299 warm requests, recorded generation returns instantly |
| Process peak working set / index size | 2,558,656,512 / 33,644,261 bytes | OS peak working set of product replay; hash-bound index tree |

The baseline exposed 71 false application abstentions despite correct recorded
answers. Exact named-course proof now uses the headed Discipline/Credits cells;
it cannot borrow numbers from hours or another course. The percentage minimum
idiom `từ …% … trở lên` is recognized without changing numeric values or support
thresholds. Complete replay has **0/145 false model-branch abstentions**.
The pre-fix baseline, its review and intermediate verification remain audit
evidence. No prompt, model output, split, retrieval setting or threshold changed.
The later context/legal-identity fixes use `request-context-v4` and `grounding-v4`
to avoid stale false abstentions. Timing differences between replay runs do not
establish a provider performance improvement.

All 43 semester annotation corrections were independently verified against
source row hashes and preceding Semester headings in a separate scoring overlay.
Frozen benchmark v5 is unchanged. Exact array quotes with decoded newlines now
compare complete string cells to one original source row. Previously recorded
seven helper discrepancies are covered by the 145/145 source-quote checks.
Historical Chat review files retain their original issue observations.

Citation scoring now counts only public citations, excludes rejected internal
diagnostics and includes every missing gold link in recall. Bilingual lexical
claim matching remains a disclosed proxy: its precision 80/178, recall 80/145
and unmatched/unsupported proxy 97/178 are retained without threshold changes. English/broad gold
versus Vietnamese question-focused claims prevents interpreting these numbers as
independently established semantic error rates. They do not override the separate
AI source review, and the AI review does not pretend to supply human labels.

The three former native false abstentions now publish their source-reviewed
answers and all five claims unchanged. The prior 142-output baseline and its
three weak cases remain in `phase8-chat-replay-final-20261012/` for audit.
Its original reviewer source hash is preserved by `reviewer-source.py.txt` there;
the latest report binds the current reviewer source separately. The alternate
valid citation remains `p8-temporal-2021-adjustment-04a`; gold still names the
table chunk. It is disclosed rather than silently changing frozen gold.

Raw Chat format is **17 valid / 128 invalid**. Escaping-only normalized
copies are separate from raw evidence; application schema success does not erase
the raw failures or establish Gemini API format reliability. The actual Chat
model label/settings were not supplied. This remains exposed regression data.

Reproduce without any provider call (choose a new output directory):

```powershell
$env:PYTHONIOENCODING = 'utf-8'
.\.venv\Scripts\python.exe -m evaluation.phase8.replay_chat_baseline --output-dir evaluation/results/phase8-chat-replay-reproduction --preflight evaluation/results/phase8-post-fix-preflight-20261012.json --chat evaluation/results/phase8-gemini-chat-responses-post-fix-20261012.jsonl --summary evaluation/results/phase8-gemini-chat-content-summary-post-fix-20261012.json
.\.venv\Scripts\python.exe -m evaluation.phase8.score_temporal_product_outputs --benchmark evaluation/results/phase8-chat-replay-reproduction/benchmark-scoring-annotations.jsonl --predictions evaluation/results/phase8-chat-replay-reproduction/predictions.jsonl --execution-manifest evaluation/results/phase8-chat-replay-reproduction/execution.json --output evaluation/results/phase8-chat-replay-reproduction/quality.json
.\.venv\Scripts\python.exe -m evaluation.phase8.review_chat_baseline --output-dir evaluation/results/phase8-chat-replay-reproduction
```

The final command verifies the specified replay and creates its AI
review; it does not overwrite frozen inputs. Quality reports include grouped
bootstrap intervals (2,000 iterations, fixed seed), split/category metrics and
their explicit denominators. Latest integration and relevant regression tests:
`phase8-chat-complete-tests-20261012.xml` (142 passes), including input bindings,
cohort drift, context, numeric grounding, course credits and scorer contracts.
Prior test evidence: `phase8-final-checks-20261012.xml`
(205 passes), `phase8-app-regression-20261012.xml` (61 passes),
`phase8-metric-final-20261012.xml` (10 passes) and
`phase8-benchmark-validation-20261012.xml` (48 passes); suites overlap.

The remaining original exit requirement is a bounded live product measurement
of provider latency and format reliability. The owner-selected Chat workflow
cannot establish that measurement. No automatic API run is authorized by this
report, and none was started. No additional Chat answers are needed for this
completed content regression; no ablation or later phase was opened.

## Historical preparation and collection records

## Current benchmark and execution (2026-10-12)

The current benchmark is `evaluation/phase8/benchmark_candidate_v5.jsonl`,
SHA-256 `0001ed7e3c6ad932434c368eb0bf212110a5d6165a9a4af12a639eb09ce4a93d`.
`evaluation/results/phase8-benchmark-freeze-v5.json` freezes its 300 rows for
regression evaluation: 140 test, 160 holdout, 117 connected groups, zero
cross-split groups. All 20 temporal questions remain in holdout. Historical
exposure and the absence of independent human review remain disclosed.

V4 review is preserved as 28 Accept / 2 Reject. V5 changes only the wording of
`p8-fact-valedictorian-average` and `p8-fact-thesis-excellence-result` to remove
answer leakage. Their gold answers, evidence, qids and splits are unchanged.
The two repaired questions were reviewed again; the final supplemental review
is **30 Accept / 0 Reject / 0 Pending**. Read the saved decisions and evidence in
`evaluation/phase8/benchmark_review_v5.md` and
`evaluation/results/phase8-automated-review-v5.json`.
The 270 historical rows retain their previous review provenance and are not
represented as newly reviewed. Review/successor checks passed 22 tests, saved in
`evaluation/results/phase8-review-successor-tests.xml`.

Status is **AUTOMATED_REVIEW_COMPLETE**, frozen for regression evaluation;
**OFFICIALLY_APPROVED is false** and no human signature is invented. This
closes benchmark preparation/review, not the real-product baseline or Phase 8.
The older v4 measurements below retain their original benchmark/source bindings.

`evaluation.phase8.run_product_baseline` collects the actual WSGI product outputs
under one immutable manifest. It permits at most 18 attempts per Pacific day,
one shard per day, at least 30 seconds between provider starts and a total cap
of planned calls plus 18 failed-attempt allowances. Each attempt has a 15-second
timeout and a 1,024-output-token cap. The runner stops at the first provider or
response failure, persists the completed benchmark prefix, and can continue the
pending question on a later Pacific day. There are no immediate retries,
failure-triggered key rotations, paid fallbacks, billing changes or provider probes. The account's
Free Tier is owner-declared; this runner cannot inspect its billing tier.

An exclusive worker lock and a durable reservation before network I/O prevent
concurrent workers from spending the same attempt budget. An interrupted worker
requires audit; it is not automatically rerun. Source/config/index drift stops
execution. Quota pacing is outside request latency; startup is included in each
runtime's first cold request and all such requests are excluded from warm
percentiles. Provider final output, usage, finish reason and reported model
version are recorded; provider thought parts and credentials are not recorded.

Prepare once after the collector tests pass, then run at most once per Pacific
day. The key wrapper reads the local file without printing its value:

```powershell
.\.venv\Scripts\python.exe -m evaluation.phase8.prepare_product_run `
  --benchmark evaluation/phase8/benchmark_candidate_v5.jsonl `
  --packet evaluation/results/phase8-product-preflight-v5.json
.\.venv\Scripts\python.exe -m evaluation.phase8.run_product_baseline prepare
.\.venv\Scripts\python.exe -m evaluation.phase8.run_product_baseline run-pool
.\.venv\Scripts\python.exe -m evaluation.phase8.run_product_baseline status
```

Do not rerun preparation when a bound file already exists. Once all 300 outputs
are collected, score the exact frozen benchmark and completed execution:

```powershell
.\.venv\Scripts\python.exe -m evaluation.phase8.score_temporal_product_outputs `
  --predictions evaluation/results/phase8-product-predictions-v5.jsonl `
  --execution-manifest evaluation/results/phase8-product-execution-v5.json `
  --freeze-manifest evaluation/results/phase8-benchmark-freeze-v5.json `
  --output evaluation/results/phase8-product-quality-v5.json
```

The baseline is incomplete until real predictions and the exit review exist.

Actual preparation now exists: `phase8-product-preflight-v5.json` binds 142
planned prompts totaling 1,137,060 characters, SHA-256
`f8f1e1dcca18834da903b992fd91382b2f061f2a185deb7f9a08b450bac7d3ff`.
`phase8-product-run-v5.json` has SHA-256
`bd8ba46ad319ec185cb5c6e2bbc36d5f986bcb5ce4c34a59ed266d1b9ccbaabd`:
160 attempts total, at most 1,320,894 prompt characters and 163,840 output
tokens. The collector/scorer/preflight tests passed **15/15**, saved
in `evaluation/results/phase8-collector-final-tests.xml`; secret scanning passed.

The first live command was rejected by automatic approval review before the
process started. Its reason was that broad Phase 8/Free Tier authorization
does not explicitly authorize sending benchmark prompts and potentially
non-public retrieved project evidence to Google's Gemini API. An exact approval
request for this single manifest, including later daily checkpoint continuation
within its lifetime caps, was explicitly approved by the owner on 2026-10-12.
The earlier rejection is preserved in `phase8-product-egress-review-v5.json`;
it was not bypassed or replaced with another manifest.

The first authorized shard sent one POST at 08:44:43 on 2026-10-12, Bangkok time.
Google returned HTTP 503; no retry POST was sent and no valid prediction was
saved. `phase8-product-execution-v5.json` is `waiting_next_pacific_day`, with
one failed attempt, zero of 300 outputs and 159 lifetime attempts remaining.
The current pending qid is `human-p7r18-curriculum-001-credits-1`.
The same approved manifest permits the next shard from **14:00 on 2026-10-12,
Asia/Bangkok**. This is the runner's approved daily window; no new approval,
model change or additional provider probe is needed. No worker remains running.

Owner amendment on 2026-10-12 authorizes allocation of unfinished questions
across `key_2`, `key_3`, then `key_1`. The collector assigns six attempts to each
within the **same aggregate 18-attempt daily cap** and 160-attempt lifetime cap.
It records the credential name on each attempt; completed qids are never sent
again. It stops the whole shard on the first failure rather than retrying 503
through another key. The original manifest and its spent attempt remain intact;
the reliability addendum is `phase8-product-credential-amendment-v5.json`.

The product profile now disables automatic retries and uses the durable SQLite
overload circuit at `.tmp/gemini-provider-health.sqlite3`. A 503 opens a shared
endpoint/model cooldown of 60 seconds, increasing to 120, 240 and at most 300
seconds after unsuccessful recovery; a longer provider `Retry-After` takes
precedence. Changing keys or restarting a worker does not clear it. During
cooldown, successful cached responses remain usable; uncached requests fail
locally with the existing safe service-unavailable response. After cooldown,
only one real request across workers may test recovery; no separate probe is
sent. An older in-flight success cannot clear a newer overload signal. Queued
rate-limited work is checked again before transport. The first provider call
still has a 15-second timeout; subsequent calls during cooldown do not wait or
consume provider attempts. This bounds local waste, not Google's availability.

Because runtime/config changed, continuation requires the amended offline
preflight and exact comparison of all 300 requests/evidence and all 142 serialized
provider bodies with the approved original. Original benchmark, prompts,
schema, model, gold, rubric, thresholds and egress caps remain fixed. The
addendum binds the updated source/config and equivalent preflight instead of
silently substituting source hashes into the original approval.

Verification completed: **111 tests passed** in
`evaluation/results/phase8-reliability-final-tests.xml`. The amended packet is
`evaluation/results/phase8-product-preflight-v5-reliability.json`, SHA-256
`7cec8cf127d460443058f9a3127eed9aa0a3945c56c339c6a4bf7f329aae45fe`.
Exact comparison passed for 300 request/evidence pairs and 142 serialized
provider bodies. No additional provider request was sent. The original v5
preflight remains historical evidence; the runner now checks the amended
packet's current source/config and its equivalence to the original before any
network I/O.

The one-shot 14:00 dispatcher (PID 13676) was cancelled when the owner requested
checking keys immediately. Its status is now `cancelled_before_run`; no delayed
invocation remains. The owner subsequently approved the exact same-day proposal
`evaluation/results/phase8-now-availability-authorization-v5.json`, SHA-256
`191e34afb22191660cbe7204ac617b5f87d70ffa072590a250487f40e4cdf696`.
It permitted at most 17 new POSTs in the existing day (18 aggregate including
the prior failed attempt), with the existing 160-attempt lifetime limit, model,
payload, Free Tier restriction, 15-second timeout and 30-second spacing intact.
The exception was date-bound to Pacific 2026-10-11. It preferred key_3, key_2,
then key_1 for pending benchmark rows; no separate probe prompt was sent.

The collector-only policy update passed **21 tests** in
`evaluation/results/phase8-availability-final-tests.xml`. The current preflight
is `evaluation/results/phase8-product-preflight-v5-availability.json`, SHA-256
`101e40d47ac8269fc9890b7d69a930af000cdb95ca393b46006c7a0be5495e49`.
All 300 request/evidence pairs and 142 provider bodies still match the original;
the amendment retains the previous source/preflight bindings for audit.

At approximately 09:46 Bangkok, **key_3 returned HTTP 503** on the next pending
approved benchmark request. The worker stopped after one new POST, zero outputs,
zero retries and zero calls through the other keys. Execution now has two total
failed attempts, zero valid rows and 158 lifetime attempts remaining. The same-day
proposal is closed and its continuation flag is disabled. HTTP 503 does not
establish quota exhaustion or authentication validity; key_1 was not tested.
No immediate retry/key failover is authorized after this failure. Original
future daily continuation retains its normal day, source, payload and budget
checks; there is currently no background job.

An optional content-review sample is available at
`evaluation/phase8/gemini_chat_pending_case_v5.md`: the missing qid's exact prompt,
retrieved evidence and output schema, with no gold answer attached. An owner-
supplied Gemini Chat response can be evaluated for content under a separate
manual-review provenance. It does not enter the API baseline prediction file
or establish product execution, provider latency/usage/reliability or a gate PASS.

The local `key.yaml` originally contained two assignment lines that YAML parsed
as one scalar. It was normalized to a YAML mapping while preserving both key
values; the existing wrapper now reads the separate `key_2`. Credentials were
not printed, and the frozen source/profile bindings remained unchanged.
With 142 planned calls and 18 attempts per day, complete collection needs at
least eight productive Pacific days; failed shards can extend that duration.

The current preflight's saved retrieval outputs have now been scored in
`evaluation/results/phase8-product-preflight-retrieval-v5.json` (SHA-256
`12a81df2aabfd9a5f370daae7cc59b06a41eb84b245a2cec3b5df412de1c9486`).
This computation makes zero provider calls and performs no new retrieval:
Recall@1 is 120/145, Recall@3 141/145, Recall@5 142/145, answerable MRR
0.899080, and unanswerable retrieval FPR 0/155. Each metric has its denominator,
population, aggregation and connected-group bootstrap interval; split counts
are 140 test / 160 holdout. Independent matching on exact doc/chunk pairs agrees
with the shared scorer for all 300 rows, and the saved report reproduced exactly.
This measures the product WSGI/profile captured by preflight, with its deliberately
absent retrieval-calibration file. Request scope also matters: 115 historical
questions supply one document through their existing `doc_ids` input; the other
185 search all 10 indexed documents. The adapter reads these request fields,
not gold evidence. Thus the aggregate is a mixture of document-scoped and
corpus-wide queries. The older standalone calibrated retrieval runner searched
the full corpus and measured a different path; score differences do not prove
an improvement.

The three answerable misses at rank five are
`human-p7r18-curriculum-004-combined-2`,
`human-p7r18-curriculum-001-combined-2`, and
`p8-temporal-2021-adjustment-04a`. The first two use local branches; the temporal
case plans a provider call. Keep these as weak-segment evidence for baseline
review, without tuning the frozen product before the complete baseline.
Synthetic provider-failure responses and preflight timing are excluded from
product answer-quality and end-to-end performance claims.

The exact offline computation recipe is retained inside the JSON report with
its own SHA-256. Reproduce it from the project root without changing collector
source or the approved manifest:

```powershell
@'
import contextlib, hashlib, io, json, runpy
from pathlib import Path
report = json.loads(Path('evaluation/results/phase8-product-preflight-retrieval-v5.json').read_text(encoding='utf-8'))
assert hashlib.sha256(report['recipe_source'].encode()).hexdigest() == report['recipe_sha256']
recipe = Path('.tmp/phase8-preflight-retrieval-recipe.py')
recipe.write_text(report['recipe_source'], encoding='utf-8', newline='\n')
try:
    with contextlib.redirect_stdout(io.StringIO()):
        runpy.run_path(str(recipe), run_name='__main__')
    print('Saved retrieval report reproduced exactly.')
finally:
    recipe.unlink()
'@ | .\.venv\Scripts\python.exe -
```

## Scope and order

Phase 8 owns an independent measurement layer for retrieval and answer quality.
It does not change Phase 7's release decision and must not delay its completion.
The project owner explicitly authorized Phase 8 preparation while Phase 7 is
still open. This authorization permits evaluation preparation only; it does not
override Phase 7's status or satisfy Phase 8's exit criteria.

## Historical benchmark candidate v1

`evaluation.phase8.benchmark_candidate` derives a 280-row historical candidate from the
existing `data/benchmark/grounding_reviewed.jsonl` test and holdout splits. It
keeps source bytes unchanged and records the exact source hash, selected IDs,
category counts, split counts, connected-group counts, annotator labels, prior
exposure, and review status. Recreate the audit packet with:

```powershell
.\.venv\Scripts\python.exe -m evaluation.phase8.benchmark_candidate `
  --output evaluation/results/phase8-benchmark-candidate-v1.json
```

The candidate is **not eligible, not frozen, and not gate eligible**. The rows were already
used in Phase 5 evaluation, and `engineering-review-1` is not evidence of
independent human signoff. Do not describe this cohort as fresh validation.
Freeze only after an actual reviewer examines the exact bound rows and signs
the resulting benchmark hash. A human review and an owner-delegated AI review
must be reported as different review modes; never call AI review independent
human review. The existing delegated-review helper is opt-in and the current
policy is Phase 7-specific, so it does not authorize a Phase 8 review packet.
On 2026-10-11 the owner explicitly delegated the 30-row Phase 8 v4 review to
Codex. That instruction authorizes an automated AI review in its own scope;
it does not reuse the Phase 7 policy or create a human signature. The v4 review
below records this authorization separately from official benchmark approval.
If the reviewer rejects the candidate or prior exposure makes it unsuitable,
collect a new benchmark instead of relabeling it.
The current audit also finds one connected component across all 280 selected
rows. That leaves no defensible independent-group resampling unit for confidence
intervals, so this dataset cannot qualify as the Phase 8 benchmark as-is.
Even without near-duplicate linking, only two groups remain and the largest
contains 168/280 rows. The candidate's generic page-question templates explain
the collapse; disabling that link would not make the sample adequately
independent.
Only three of the 13 documents in the supplied university corpus appear in
these test/holdout rows. Ten documents remain candidate source material, but
their historical exposure has not been audited and cannot yet be treated as
fresh.

The strongest existing replacement source is the Phase 7 r18 human benchmark.
Its test/holdout rows have owner-review signoff but were already used in Phase
7 and have no temporal/comparison tags. A deterministic 280-row selection is
measured for retrieval in
`evaluation/results/phase8-r18-retrieval-baseline-v1.json`. Reproduce it offline with:

```powershell
.\.venv\Scripts\python.exe -m evaluation.phase8.run_retrieval_baseline `
  --output evaluation/results/phase8-r18-retrieval-baseline-v1.json
```

It reports answerable Recall@5 109/122 (0.893; connected-group bootstrap 95% CI
0.717 to 1.000 over 10 answerable groups), answerable MRR 109/122, unanswerable
false-positive rate 0/158, and retrieval abstention 158/158. Warm latency is
p50 21.64 ms, p95 352.70 ms, and p99 366.57 ms; cold start is 24.57 s and peak
working set is 2.52 GB. Every value and its denominator are recorded in the
JSON, alongside benchmark, model, index, and calibration hashes. This is
historical regression evidence, not fresh validation. The prior r18 release
report uses different 130-row benchmark hashes and is not combined with this
result.

## Combined benchmark candidate v4

Candidate v4 corrects only the question wording for temporal qids ending
`-04`, `-09`, `-14`, and `-19`: each now asks for the adjusted code, matching
the unchanged gold answer. All 300 qids, gold fields, evidence and splits are
identical to v3. The v3 candidate and owner packet remain historical evidence;
review the v4 packet linked below. No approval is transferred or invented.

The earlier 280-row r18-only cohort was useful for historical retrieval checks,
but it lacked a direct factual lookup type and temporal/comparison coverage. The
current unapproved candidate is source-bound in
`evaluation/results/phase8-benchmark-review-candidate-v4.json` and serialized at
`evaluation/phase8/benchmark_candidate_v4.jsonl`. Rebuild the candidate and both
supplemental review drafts with:

```powershell
.\.venv\Scripts\python.exe -m evaluation.phase8.build_temporal_review_draft
```

The candidate contains 270 rows from the previously owner-reviewed r18 cohort,
20 temporal/comparison rows from the 2021 correction table, and 10 single-hop
facts from the 2023 awards regulation and 2014 training-regulation excerpt. Ten
historical rows are deterministically omitted (five per split, selected only
from multi-row groups) to keep the complete benchmark at 300. Split counts are
140 test / 160 holdout. The combined qid-set SHA-256 is
`2e36cfdb7f605b8f57a99d20ea33a619b95e977dcff69e4d35d5f0a2deac2796`; the exact
JSONL SHA-256 is
`9309fb0eb1defd15da946cba9cd657dd82bf0bd98c924adb0d3012193aa1166c`.
There are 117 connected groups, largest size 22, and zero cross-split groups.
The manifest reports query-type counts (categories may overlap): 10 single-hop
facts, 135 table/calculation, 33 prerequisite/multi-hop, 20 temporal/comparison,
and 155 unanswerable/adversarial.

The 115 answerable historical r18 rows now have deterministic claim annotations
derived from their owner-reviewed structured gold and source-validation table
rows. The builder checks each source-cell hash and indexed page/chunk before
emitting claims. The other 30 supplemental rows carry explicit gold claims and
source quotes. The owner review packet at
`evaluation/phase8/benchmark_owner_review_v4.md` binds both supplemental JSONLs
and the exact combined candidate hash. Its 30 row decisions are now complete
under the owner's explicit AI-review delegation: 28 Accept and 2 Reject. The
local integrity check confirms all 30 review qids are present, all 30 evidence
links resolve to the cited indexed chunk/page, every source quote matches its
indexed passage/table row, and the three source PDFs match the corpus manifest
hashes. This proves source binding, not question naturalness or owner approval.
Source documents were indexed previously, and 13/20 temporal facts overlap
retained benchmark content. The historical v3-wording artifact-scope exposure audit scanned 115
Phase 7 product egress/execution JSON artifacts: no Phase 8 candidate qid or
exact question appeared in stored text. A broader exact-text scan of 1,685 text artifacts (427,205,208 bytes) under `data/benchmark` and `evaluation/results/phase7*` also found zero qid/question matches for the 30 supplemental rows. The actual Phase 7 dev-quality live
record (`product-dev-quality-live-20261009-v6.json`, SHA-256
`aacaed70bd566706b9a3074173f2ff869d7c970700bce1a41d74f42043603db4`) contains
6 recorded LLM call contexts; 3 of the candidate's 10 source document IDs occur
in those contexts, while no candidate qid or exact question appears. Fourteen
Phase 7 performance egress manifests reference all 10 source document IDs, but
no corresponding performance execution artifact exists in the scanned results;
these manifests alone do not prove that requests were sent. A separate scan of
75 saved Phase 7 primary-output files also found no candidate qid or exact
question, so those outputs cannot be scored as Phase 8 product results. These
artifact scans establish known source overlap but cannot rule out semantic or
provider-side exposure; keep the candidate regression-only, not fresh validation or a frozen benchmark.

### Automated review disposition (2026-10-11)

`evaluation/results/phase8-automated-review-v4.json` records all 30 per-row
decisions, six review criteria with reasons, original PDF page/section locators,
benchmark/row/source/index hashes, the authorization scope and the AI identity.
The reviewer read all eight pages of the three original PDFs, including the
table columns visually. This is a source-based AI review, not independent human
review or a second independently deployed model. It made no provider calls.

The status is **AUTOMATED_REVIEW_COMPLETE**, with **OFFICIALLY_APPROVED=false**.
The generated draft manifest retains its original creation-time review status;
the new AI review report supersedes pending decisions for these 30 rows only.
It does not rewrite the benchmark's source-review fields or freeze state.
The four revised temporal questions (`-04`, `-09`, `-14`, `-19`) are Accept:
original PDF rows independently support the unchanged adjusted codes, and only
the question field changed from v3. The two Reject decisions are:

- `p8-fact-valedictorian-average`: the award title already supplies the answer's
  scope, "ngành học". The fact is supported, but the question leaks its answer.
- `p8-fact-thesis-excellence-result`: the question contains "Xuất sắc", the very
  result it asks the model to return. Source correctness does not cure leakage.

Keep the v4 benchmark bytes unchanged as the reviewed object. Repair or replace
these two questions in a subsequent candidate and review the changes before
freezing; do not silently remove them or relabel their decisions. The Markdown
packet is updated in place as requested, while its original hash is recorded.
The builder's overwrite guard protects that completed review from regeneration.

Recheck the saved decisions and mechanical provenance offline with:

```powershell
.\.venv\Scripts\python.exe -m evaluation.phase8.validate_automated_review
```

The validator checks all 30 decisions, Markdown agreement, source hashes,
PDF/chunk page coordinates, exact indexed quotes, PDF quote presence, temporal
table columns and the four-question v3/v4 diff. It does not infer semantic
correctness from a passing hash check. The saved validation report is
`evaluation/results/phase8-automated-review-v4-validation.json`; focused test
results are in `evaluation/results/phase8-automated-review-v4-tests.xml`.
The focused review, draft-generation and saved-output scorer suite passed
21 tests, including missing/duplicate decisions, forged human signoff,
unreviewed v4 changes and incorrect physical PDF pages within a valid chunk range.

No unconditional human-signature requirement is specified for this delegated
automated review. Human endorsement remains unprovided; any separate gate that
requires a human signature must remain `PENDING_HUMAN_APPROVAL`. This review does
not freeze or officially approve the 300-row benchmark, whose two rejected rows
still need repair, nor does it pass the product baseline or the Phase 8 exit.

An offline retrieval baseline was measured on this exact 300-row JSONL and is
recorded in `evaluation/results/phase8-benchmark-retrieval-candidate-v5.json`; earlier reports remain historical.
The v5 report evaluates candidate v4 and was captured by a source-stability measurement receipt. Reproduce it with:

```powershell
.\.venv\Scripts\python.exe -m evaluation.phase8.run_retrieval_baseline `
  --benchmark evaluation/phase8/benchmark_candidate_v4.jsonl `
  --output evaluation/results/phase8-benchmark-retrieval-candidate-v5.json
```

Answerable Recall@5 is 132/145 (0.910; group-bootstrap 95% CI 0.774 to 1.000 over
40 answerable groups), answerable MRR is 121.533/145 (0.838; CI 0.693 to 0.937),
and unanswerable false-positive rate is 0/155. Multi-hop Recall@5 is 27/33
(0.818). The v5 retrieval-only report measured warm p95 366.573 ms, cold start 24.914 s, peak working set 2,510,516,224 bytes, and index size 33,644,261 bytes. The 300-row measurements vary between reruns and do not include LLM generation. Report SHA-256: `b136f8abc3255e56e0af30cecc484db5312dea9919a1e5f1bf2e40ad27de3207`; source-stability receipt: `evaluation/results/raw/measurement_receipts/phase8_retrieval_candidate_v4_8d4a0d915f9843e48759ded3cb462cfa.json` (SHA-256 `3db04d66bbf479a6d4a9d4b6fb94d482cf6aebd17184f0822a68ec2fab946409`). It binds the benchmark and calibration inputs; the report records the index manifest hash. Full product-run resource acceptance remains open. Split metrics are now
bound in the report: test has Recall@5 60/72 (0.833; group-bootstrap CI95
0.588 to 1.000 over 10 groups), MRR 0.826 and FPR 0/68; holdout has Recall@5
72/73 (0.986; CI95 0.946 to 1.000 over 30 groups), MRR 0.850 and FPR 0/87.
All 20 temporal cases are in holdout, so the test split does not measure that
category. These are offline retrieval-only measurements, not a product
answer-quality gate.

Separate supplemental retrieval diagnostics, with zero provider calls, are
recorded in `evaluation/results/phase8-temporal-retrieval-diagnostic-v2.json`
and `evaluation/results/phase8-factual-retrieval-diagnostic-v1.json`. Temporal
Recall@1/3/5 is 0/20, 18/20, and 19/20. Factual Recall@1/3/5 is 9/10, 10/10,
and 10/10. The temporal v2 diagnostic uses candidate-v4 wording; factual v1 remains historical with unchanged factual rows. Both remain regression diagnostics pending review.

The saved-output scorer in
`evaluation/phase8/score_temporal_product_outputs.py` accepts predictions for
the exact 300-qid candidate and checks schema, exact gold-answer text, temporal
code accuracy, citation coordinates, grounded claims, answerability and abstention
precision/recall, plus test/holdout metric denominators. It has no provider client.
Abstention reason accuracy is emitted as `not_measured` until owner-labeled gold
reason fields exist; the grounding summary no longer reports an unlabeled reason
metric as zero. Exact text matching is not semantic review, so semantic answer
correctness is explicitly `not_measured` until human labels are bound. The scorer
measures index size in bytes and binds it to the index-manifest hash; peak product
working set is explicitly `not_measured` until a product execution manifest is
bound. The scorer accepts `--execution-manifest` only when its recorded benchmark,
prediction, and index-manifest hashes match the exact files being scored and its
index tree hash covers every indexed file; its peak working-set measurement is a
positive byte count with a declared method. The scorer also verifies that the
in-memory rows came from the exact benchmark and prediction files in that manifest.
Category/split tables carry independent denominators. These accounting
changes are covered by the Phase 8 scorer tests, but do not substitute for real
product outputs. No complete live product baseline has been measured on v4.

### Product-run preflight (zero egress)

`evaluation/phase8/prepare_product_run.py` runs the exact benchmark through the
local WSGI/query-service path with an offline LLM recorder and blocks
`urllib.request.urlopen`. Reproduce the prepared packet with:

```powershell
.\.venv\Scripts\python.exe -m evaluation.phase8.prepare_product_run `
  --packet evaluation/results/phase8-product-preflight-v4.json
```

The 300-row run completed with 140 test / 160 holdout qids, 300 unique rows,
142 planned model prompts, 1,136,771 prompt characters, zero provider requests,
and no prompt-hash or request/response omissions. Packet SHA-256:
`acbdcb482d0825f9ed2900e09aaca63faf3c01577fe4dd88ec438744cdf5a774`.
The packet binds the exact benchmark, product LLM config, index manifest/tree,
and current source identity. Preflight fallback responses for those 142 prompted
rows are explicitly synthetic and are not scored; locally completed no-prompt
rows are diagnostic only and are not mixed into a future live latency run. This
packet is preparation evidence, not a request authorization or quality result.
The v1-v3 packets remain historical evidence. V4 binds candidate v4 after
four question-wording corrections; gold, source, qids, split and rubric are
unchanged. The 158 local-only internal and public responses are identical to
v3. Only the four corrected questions change their prepared prompts. All
preflight runs sent zero provider requests.

The draft builder hashes the exact encoded output bytes, preserves each existing
file's newline convention, and checks every generated output before writing any
of them. If an artifact differs, regeneration stops before writing any file. A
regression test verifies that changed owner-review content and companion files
remain untouched. The Phase 8 test suite passes 16 tests.

### No-prompt local branch diagnostic

The rows that did not plan a provider call were separately scored from their
captured real local product responses in
`evaluation/results/phase8-local-branch-preflight-diagnostic-v3.json` (SHA-256
`e47cd816626e80fb4464c6f20bcd6478ba1a5cd025e71840a7591a4357b84a39`). This
current diagnostic binds preflight v4 and its source identity. The slice has
158 rows: 155 unanswerable and only 3 answerable. Its latency describes only
those selected local requests; it does not classify cold/warm starts and is
not an end-to-end product performance measurement. Schema validity
was 158/158 and unanswerable false-positive rate was 0/155; all 3 answerable
rows falsely abstained (3/3). This small slice is a diagnostic, not a quality
gate or representative estimate. It shows the answerable no-prompt path is a
weak segment to review after the complete baseline; no tuning or ablation is
opened by this finding.

The three answerable false-abstentions were triaged without changing product
code. `human-p7r18-curriculum-004-combined-2` and
`human-p7r18-curriculum-001-combined-2` are complete, one-document-scoped course
questions, but `resolve_query` treats the word “it” as a follow-up and asks for
clarification despite there being no prior turn. `p8-fact-awards-effective-date`
has a retrieved 2023 regulation passage that states the requested effective
month, but the local branch abstains with `conflicting_evidence` after retrieval
also returns unrelated curriculum/regulation passages. These are concrete
regression targets for review after the full baseline; they do not authorize
tuning, and the small local-only slice remains ineligible for a Phase 8 gate.

The product report emits connected-group-bootstrap intervals at the split and
query-category levels for estimable quality ratios and warm-latency percentiles.
The first request is reported separately as cold start; it has no interval from
a single observation. Category definitions are
bound in the report and may overlap; current candidate-v4 denominator checks
cover 10 single-hop facts, 135 table/calculation cases, 33 prerequisite/multi-hop
cases, 20 temporal/comparison cases, and 155 unanswerable/adversarial cases.
The existing split allocation still places all temporal/comparison cases in
holdout, which is reported as a limitation rather than repaired by splitting a
connected group.

## Metric contract

The baseline report must include, for every metric, its numerator, denominator,
population, and aggregation rule. Report retrieval Recall@1/3/5 and answerable
MRR over answerable queries; report negative-query false-positive and abstention
rates over unanswerable queries. Report grounded-claim precision/recall,
unsupported and contradicted claim leakage, citation precision/recall and
coordinate validity, abstention precision/recall and reason accuracy. Report
latency with cold-start separated from warm p50/p95/p99, and resource use with
peak resident memory and index size. Use connected source/template/question
groups as the resampling unit for 95% confidence intervals; never treat
paraphrases from one group as independent observations. Category and split
tables must show their own denominators. An unmeasured value is reported as
`not_measured` with a reason, never silently omitted or represented as zero.

Phase 5's 400-row report uses `FixtureLLM`, which emits gold-derived answers;
its perfect answer/citation/grounding scores are a fixture ceiling, not product
quality evidence. The Phase 3 retrieval report covers 100 queries but only two
documents and five chunks, so it is a historical smoke baseline, not a
representative current-product baseline. These reports can validate metric
plumbing and supply historical context only.

## Owner-selected Gemini Chat content verification

On 2026-10-12 the owner selected Gemini Chat for subsequent content verification.
For each needed case, Codex supplies a Markdown file with the saved project
prompt, retrieved evidence and output schema, plus a copyable instruction prompt.
No benchmark gold or credentials belong in the supplied file. Owner-pasted
outputs are retained and reviewed with separate Gemini Chat provenance; model
identity and generation time remain unknown unless actually supplied.

The first review is recorded in
`evaluation/results/phase8-gemini-chat-case-001-review.json`, bound to the
original pasted text, a separately normalized JSON, benchmark and preflight.
The Algebra answer and citation are supported by the page 1 table: 4 credits.
The pasted JSON fails parsing because the quote string contains unescaped
double quotes. Escaping only those quotes produces schema-valid JSON; this
does not turn the original output into a format PASS. Whether the formatting
loss occurred in Gemini or during copying is unknown.

The owner reaffirmed Gemini Chat 3.8 Flash as the requested content-verification
route and authorized grouping multiple cases per attachment. API collection is
paused for this content task; no key probe, automatic provider call or quota
reset wait is required to prepare Chat cases. This changes the collection
workflow, not gold answers, rubric or thresholds. The actual Chat model label
must be recorded from the UI when supplied; it has not been independently
verified. Batch execution differs from an isolated API request and is disclosed.

The owner requested approximately 60 cases per attachment for faster progress.
All 141 unreviewed generation cases are now prepared as batch 002 (60), batch
003 (60), and batch 004 (21), under `evaluation/phase8/gemini_chat_batch_*_v5.md`.
Batch 002 replaces its earlier five-case preparation; its 60 outputs have now
been received and reviewed (see update below). Use a new conversation for each attachment.

Each file stores the shared prompt instructions, response schema and identical
evidence blocks once. Each qid retains its original question section and an
ordered evidence-block allowlist. Reconstructing shared instructions, QUESTION,
question section, EVIDENCE and the referenced blocks reproduces every original
prompt exactly, including whitespace. Gemini must use only listed evidence for
that qid. Deduplication changes storage, not available evidence or the question.
The output envelope is JSONL: one complete `{qid, response}` object per line,
without fences or commentary; each response satisfies the original schema.
Missing, duplicate, unknown qids, invalid JSON/schema, wrong page/chunk,
unsupported quotes, cross-case leakage and semantic errors are checked per case.
Preserve all raw output. Retain complete lines if output is truncated; request
only missing/malformed qids afterward. A 60-case input is not a guarantee of a
complete response or a quality PASS. Exporting files is not completed review.

`evaluation/results/phase8-gemini-chat-progress-v5.json` binds the benchmark,
original preflight, completed reviews and current batch. Current generation
review coverage is 142/142 (100%): 142 content acceptances, 14 raw JSON format
passes and 128 complete raw format failures. The previously truncated case is
now resolved by a complete final response, not by inference. The other 158 benchmark cases take local application branches and need
their own evaluation; they are not automatically accepted. The 300-row full
benchmark and API baseline denominators remain distinct from the 142-case
manual generation coverage. `evaluation/results/phase8-gemini-chat-batches-validation-v5.json`
binds all three files and verifies exact text/hash reconstruction for 141/141
prompts, unchanged schemas, unique qids, no reviewed qid re-export and no gold
fields/credential export. No provider requests were made. The total original
prompt text is 1,127,001 characters; the three deduplicated JSON packages total
228,894 characters (about 80% fewer characters, not a measured token count).

Initial pilot content progress was one reviewed case, one content acceptance,
zero originally valid JSON outputs. This did not establish benchmark-wide
quality. No API calls were made for this review, and no rows were added to the
API baseline predictions. Application integration, latency, resource usage and
provider reliability still require their own measurements. Gemini Chat content
review alone does not satisfy the existing Phase 8 exit gates below.

## Phase 8 exit

### Batch 002 review update (2026-10-12)

The owner returned file 1 as a 60-line pasted attachment. Exact original bytes
are retained in `evaluation/results/phase8-gemini-chat-batch-002-raw.txt`.
`evaluation/results/phase8-gemini-chat-batch-002-review.json` records all 60
decisions with question-specific requested fields and source proof; the readable
table is `evaluation/phase8/gemini_chat_batch_002_review_v5.md`.
All 60 expected qids are present exactly once. Content review accepts all 60
answers and their claim texts against QUESTION, structured expected_claims and
supplied source. Ten original lines parse as JSON; 50 fail due to unescaped
quotes inside quote strings. Only those escapes were repaired in a separate
normalized JSONL, which passes all 60 original response schemas. The origin of
the escaping loss is unknown; original format failures remain recorded.

Two evaluator issues are explicitly open. Six quotes represent exact source
table rows with newline-containing cells but fail the existing quote helper;
decoded-cell equality establishes manual provenance, not a helper PASS. Eight
semester questions have derived gold_claims about credits. Their unchanged
structured expected_claims and preceding source table semester headings support
the responses. The derivation function currently distinguishes only multi_hop
versus other curriculum queries, causing the semester annotation discrepancy.
The frozen benchmark and thresholds were not changed to accommodate outputs.
These issues require resolution before an automated benchmark gate can pass.

At the batch-002 checkpoint, Chat review progress was 61/142 (42.96%), 61 content acceptances, 10 raw
JSON format passes and 51 raw format failures (including the initial pilot).
There are 81 unreviewed generation qids: batch 003 (60) and batch 004 (21).
Do not regenerate the 60 correct answers merely to repair copying/escaping.
No API calls were made and API baseline predictions remain unchanged.

### Batch 003 review update (2026-10-12)

File 2 contained 56 complete records, one truncated final record and three
absent qids. The exact input is retained in
`evaluation/results/phase8-gemini-chat-batch-003-raw.txt`; complete records alone
were normalized for quote escaping and reviewed. All 56 complete answers and
claim texts are supported by the question-specific evidence and structured
expected_claims. All 56 original lines have quote-escaping errors; normalized
copies pass the unchanged schema. The truncated response is not completed by
inference and does not count as reviewed or accepted.

`evaluation/results/phase8-gemini-chat-batch-003-review.json` records decisions
for all 60 expected qids: 56 ACCEPT_CONTENT and four PENDING_OUTPUT, with the
original line numbers, parser errors, evidence proof and missing-qid list.
The readable table is `evaluation/phase8/gemini_chat_batch_003_review_v5.md`.
This batch adds 20 semester gold-annotation mismatches and one newline table
quote-helper discrepancy. Totals are 28 annotation mismatches and seven helper
discrepancies, explicitly unresolved; frozen gold and thresholds are unchanged.

At the batch-003 checkpoint, there were 117/142 reviewed (82.39%), 117 content acceptances,
ten original format passes and 107 complete original format failures. There
are 25 remaining generation cases. `evaluation/phase8/gemini_chat_remaining_v5.md`
combines exactly the four unfinished batch-003 qids and the 21 original
batch-004 qids. Each of its 25 prompts reconstructs exactly to the saved
preflight and uses the unchanged response schema. The file contains no already
reviewed qid, gold answer or credential. Use this file instead of the original
batch 004; do not send both. Existing prepared batch files are retained as
hash-bound audit evidence. No API call or end-to-end acceptance is claimed.

### Batch 004 review update (2026-10-12)

The owner supplied original file 3, not the consolidated 25-case followup.
All 21 expected batch-004 qids are present exactly once and were still pending.
The exact attachment is retained in
`evaluation/results/phase8-gemini-chat-batch-004-raw.txt`; detailed decisions
are in `evaluation/results/phase8-gemini-chat-batch-004-review.json` and
`evaluation/phase8/gemini_chat_batch_004_review_v5.md`.
All 21 answers and claim texts correctly state the requested credits or
semester, verified against the source table row and its preceding semester
heading and unchanged structured expected_claims. All citations pass the
existing quote helper. All 21 original lines fail JSON parsing due to unescaped
quotes; escaping-only copies pass schema, without converting raw failures to
passes. Twelve additional semester annotations incorrectly describe credits.
Open issue totals: 40 annotation mismatches and seven prior quote-helper
discrepancies; frozen gold, rubric and thresholds remain unchanged.

At the batch-004 checkpoint, generation review coverage was 138/142 (97.18%), with 138 content
acceptances, ten raw format passes and 128 complete raw format failures.
The four incomplete/absent batch-003 qids are the only missing model cases.
`evaluation/phase8/gemini_chat_final_4_v5.md` exports exactly those four with
lossless prompt reconstruction and the original schema; it replaces the
25-case followup for further collection. Do not resend file 3 or completed
cases. Bound earlier files are retained for audit. No API calls were made;
full Phase 8 still requires resolution of evaluator issues, the 158 local
application cases, runtime/resource evidence and baseline review.

### Final four and collection completion (2026-10-12)

The owner returned four complete JSONL objects for exactly the four remaining
qids. All four original objects pass JSON parsing, the unchanged response
schema, citation coordinates/quotes and semantic content review without any
normalization. Source table rows and preceding semester headings independently
establish the requested three semesters and one credit value. Original input
is `evaluation/results/phase8-gemini-chat-final-4-raw.jsonl`; per-case review is
`evaluation/results/phase8-gemini-chat-final-4-review.json`.

`evaluation/results/phase8-gemini-chat-content-summary-v5.json` binds every
review and the 142-case combined response file
`evaluation/results/phase8-gemini-chat-responses-v5.jsonl`. That file is an
offline Chat artifact with per-row provenance and normalization flags; it must
not enter the API prediction file. All 142 qids exactly match the planned model
generation cohort, with no missing/duplicate qid. All 142 normalized responses
pass their original schemas. Raw format totals are 14 pass / 128 fail; formatting
loss origin remains unknown and original failures remain failures.

Status: **CHAT_CONTENT_COLLECTION_AND_REVIEW_COMPLETE — 142/142, 100%**.
All 142 content decisions are ACCEPT_CONTENT under question-aligned structured
gold and supplied source review. No further owner Chat outputs are currently
needed. This is regression evaluation with batched, owner-mediated Chat
provenance; the actual model identity and generation settings were not verified.
It does not establish abstention/FPR on unanswerable questions because all 142
model-generation cases are answerable.

Open issues remain: 43 derived semester/credits gold annotation mismatches,
seven newline quote-helper discrepancies, 158 local application cases and
runtime/resource evidence. Frozen gold/rubric/thresholds were not changed.
Raw format, automated frozen-gold scoring, end-to-end baseline and Phase 8
gates are not passed by completing Chat collection. No API calls were made.

Phase 8 passes only when all of the following are bound to a reproducible run:

1. A 100–300-query benchmark version is frozen after review, includes all
   required query types, and has zero unresolved group leakage or review status.
2. Product baseline outputs are measured on that exact version. Fixture-only
   answers do not qualify. Every metric has the denominator, connected groups,
   and a group-aware confidence interval where applicable.
3. Latency and resource measurements are present, with source/runtime/index/
   benchmark hashes and enough metadata to reproduce the run.
4. The baseline report identifies weak segments. Ablations remain closed until
   that report passes review; each later change needs a hypothesis and must not
   regress citation or grounding.

Current state: the repaired 300-row v5 benchmark is reviewed and frozen for
regression evaluation. The corpus is historically exposed, so this benchmark is
regression-only. Real product answer/citation/groundedness/abstention outputs
and end-to-end product latency/resource measurements are still missing. The
retrieval-only run now has source-stability receipt evidence; ablations remain
closed. No Phase 8 PASS is claimed.

Exit audit (2026-10-12):

| Exit item | Status | Remaining evidence |
|---|---|---|
| Reviewed, frozen benchmark with required types and no group leakage | Complete for regression | V5: 30 Accept / 0 Reject / 0 Pending after two wording repairs; 300 rows, 117 groups, zero cross-split groups. Delegated AI and historical review modes are disclosed; no human signature is claimed. |
| Product quality baseline on the exact benchmark | Chat content collection/review complete; full baseline in progress | Generation cohort: 142/142 reviewed, 142 content accepted, no missing/duplicate qid. Raw format 14 valid/128 invalid; disclosed normalized schemas 142 valid. Seven quote-helper discrepancies and 43 derived gold-annotation mismatches remain recorded. The 158 local cases and runtime/resource evidence need separate evaluation. API history remains unchanged. |
| Reproducible latency and resource measurements | Partial | Receipt-bound retrieval-only latency, working set, and index size are measured on candidate v4, but end-to-end product latency/resource tied to real product predictions is missing. |
| Weak-segment report reviewed before ablations | Partial | Retrieval and local-only diagnostics identify risks, including three local false-abstentions, but the complete product baseline has not been reviewed. |

Before adding the automated-review validator, the preflight packet was checked
against benchmark, product LLM configuration, index manifest/tree and source
identity; all five matched. The saved v4 packet retains that earlier source
identity. Do not call it source-current after evaluation-code additions; rebind
the final repaired candidate before any future live API execution. The current
sequence is owner-mediated Gemini Chat batch collection, per-case content review,
separate local application/resource measurement, then baseline review. No product
tuning starts before that baseline review. The historical API manifest is retained
for audit and does not schedule new calls under the Chat workflow.
