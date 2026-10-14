# Phase 10 — bounded evidence composition

Status: COMPLETE, 14 October 2026. P10-01–05 DONE; T10-01–05 PASS.
All 24 frozen cases pass source review and actual application replay: 12 positive,
12 negative, 32 supported published claims and 24 valid citations. Final offline
suite: 1,550 passed, zero failed, two live opt-in skipped; coverage 91.09%.
See [completion evidence](../evaluation/results/phase10-completion-20261014.json)
and the Phase 10 task/gate table in [plan.md](../plan.md).

The service reuses authorized document selection and the Phase 9 temporal
resolver. Request planning identifies source roles and ordered operands; it
does not infer source facts. Retrieved headed rows prove course identities,
credit values and prerequisite edges. A name-to-code lookup can bridge two
explicitly requested documents without asserting program equivalence.

Bounded composition uses one base retrieval pass of at most 20 returned
candidates. Only a source-proved dependent identifier permits one additional
source-scoped pass, also at most 20. It never uses a reranker or model planner.
Missing sources, ambiguous rows, conflicting values, blank prerequisite cells
and missing dependent rows fail closed. Same course codes or equal credit
values do not establish automatic recognition or a prerequisite relation.

Required rows retain original chunk/page/column values and source-table row
coordinates. Context projections contain exact original headers and cells.
Existing complete native comparisons retain their original application prompt;
both rows must actually be visible within its unchanged context budget.
New composition prompts name the required source roles. Grounding checks every
required credit claim and the actual bridge edge, including after model output.
Two-endpoint lexical overlap cannot certify a prerequisite edge.
Name-to-code claims use the exact headed source row, canonical code spacing and
reviewed bilingual/footnote segments. A name, number or prerequisite cell from
another row cannot certify course identity. This fixes two false contradictions
on spaced master-course codes without changing the submitted Chat payload.

Source-qualified sums and signed differences are calculated locally and then
pass the existing citation/claim validators. Operand order and document identity
are retained even for the same code in two different sources. Context/output
caps remain unchanged. Generation is limited to one boundary per question.

The answer cache binds the composition policy, source-role/operand order and
existing corpus-generation fingerprint. Both source indexes participate in
invalidation. The relation-proof policy also invalidates historical answers
that predate the stricter prerequisite guard. Retrieval caches distinguish
bounded headed-row requests from the historical retrieval path.

## Zero-provider acceptance workflow

Frozen inputs: `evaluation/phase10/benchmark.jsonl`, `source-rubric.json` and
`protocol.json`. Preserve their bytes and all exposed/raw failures. Never feed
the source rubric into the application or Chat packet.

1. Run `python -m evaluation.phase10.run --stage after` with Hugging Face offline
   environment flags. Each run appends a receipt under
   `.local_artifacts/experiment_runs/phase10-20261014` and captures actual prompts.
2. The owner sends `evaluation/phase10/gemini-chat-packet.md` to Gemini Chat and
   returns a UTF-8 JSONL file containing every `qid` and its unchanged `response`.
   The packet contains eight generation cases; local arithmetic/negatives do
   not need Chat. A Phase 9 response file does not satisfy this population.
3. Validate raw parse/schema, preserve original bytes, source-review every
   answer/claim/edge/citation against the frozen rubric, then replay:
   `python -m evaluation.phase10.run --stage after --capture CAPTURE --responses RESPONSES`.
   The final capture is
   `.local_artifacts/experiment_runs/phase10-20261014/after-preflight-rerun-6.json`;
   responses are `normalized-chat-99311cd46f10.jsonl` in the same directory.
   `acceptance-counters.json` proves all eight prompt/schema values and the index
   identical to the historical packet-bound capture. The packet manifest retains
   its immutable send-time identity. Runtime, index, prompt and schema
   compatibility are checked; never attach outputs by qid alone.
   The runner preserves exact input bytes under a SHA-named receipt before
   parsing. It rejects wrong/duplicate qids, incomplete packets, extra envelope
   fields and invalid schemas before rebuilding an index or loading a model.
   Input-format validation alone never grants a source-review PASS.
4. Close tasks/gates only after all 24 cases and the final exit audit pass.

The original owner file (SHA-256
`99311cd46f1077c0b54312d0172bb9a71a4c2f67d3d9bf6638f57c81fb892c3c`)
has 0/8 parseable responses because inner array quotes were not escaped.
`normalize-received.py.txt` and `chat-normalization.json` preserve the original
bytes and document 16 quote escapes plus empty-separator removal: zero semantic
edits, 8/8 normalized schemas valid. The replay runner itself does no repair;
its raw-input receipt is the normalized file, not a native-format PASS.
`quality-review.json` records every accepted case, claim, edge, operand and
physical page/row/column. The first 22/24 replay remains retained as a failure.

Use `.venv/Scripts/python.exe` from the repository root with
`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, and
`HF_HUB_DISABLE_TELEMETRY=1`. Set `torch.set_num_threads(8)` for the recorded local
profile. `evaluation.phase10.prepare.read`/`sha` and
`evaluation.common.artifact_store.resolve_artifact` restore catalogued artifacts
by verified SHA from `.local_artifacts/objects`; the archive must accompany a
checkout to reproduce historical outputs. The runner reconstructs the disposable
Phase 10 index from retained `source-records.json`; source PDFs/original indexes
and the frozen protocol remain available. Do not run `prepare()` to re-freeze.
Restore the normalized response file before passing its physical path to replay.
The preserved `replay-with-counters.py.txt` delegates to the actual encoder/service
and records the final run. New runs append receipts; historical names are reserved
even after their materializations are removed.

Phase 7/8/9 regressions replayed 68/300/24 exact public outputs with compatible
actual payloads. Actual counters: at most two encoder queries/two searches,
eight total generation boundaries; arithmetic and negatives use zero generation.
One local traversal per arm observed median processing 189 ms before versus
696 ms after (excluding first model load), with shared host activity and the
additional dependent search. This is a disclosed cost, not a speedup/SLO claim.
Context cap remains 12,000 characters; candidate caps are 20/search, 40 total.
Cache/fault/truncation/restart/scope controls are covered by the passing suite.
The initial full-suite quota-clock failure is retained; only its test clock was
fixed, and the final suite passed with the production quota guard unchanged.

Chat and recorded replay do not qualify live API latency, availability or native
provider format reliability. R-01/R-02 remain NOT PASSED. No API key, billing or
paid fallback is used by this workflow. Archive required evidence before
removing redundant temporary materializations, and retain root `plan.md`.
