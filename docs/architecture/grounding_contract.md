# Phase 5 contract

Version: `grounding-public-v2` / `grounding-internal-v2`

## Claim status

- `supported`: the claim is entailed by validated evidence and every material
  marker (number, code, date, unit and polarity) agrees.
- `partial`: only an explicitly bounded part is supported. It is never used
  to publish an unbounded claim; the default policy is to abstain.
- `unsupported`: the evidence does not establish the claim.
- `contradicted`: validated evidence conflicts with the claim.
- `ambiguous`: evidence or source precedence cannot select one interpretation.

Unsupported, contradicted and ambiguous claims are never public. If an answer
contains three claims and one is unsafe, the whole answer abstains unless the
decision policy has explicitly reduced it to a separately cited supported
partial answer. Provider `abstained=false` never overrides verifier output.

An explicit two-part request using both/cả and a no-partial-answer requirement
also checks coverage of both named roles before claim support. Matching a
single course fact cannot satisfy a second unavailable fact, even if the model
omits it from `claims` or appends an unverified absence sentence to `answer`.
This check uses user-request content words and course-code spacing, never
benchmark categories, gold, expected reasons or source filenames. It is a
bounded conservative lexical check for recognized forms, not general semantic
NLU or proof of completeness for every compound question. Ordinary questions
retain their existing path; matching roles must still pass source verification.
Cache versions are `grounding-context-v11` / `grounding-v9`.

## Public response

The public fields are `answer`, `citations`, `claims`, `confidence`,
`abstained`, `abstention_reason`, and `schema_version`. Public payloads never
contain cache keys/hits, local paths, raw provider output, retrieval scores,
debug reasons, source hashes unless explicitly required by the API, or internal
trace data. Every public claim has a stable `claim_id` and citation IDs that
exist in the same response.

`schema_version` is `grounding-public-v2`. An abstained response must provide one
canonical public reason. A citation without a claim mapping is not published.
An abstention publishes no claims or citations. IDs must be nonempty and
unique, pages must be positive integers (booleans are rejected), and every
published claim must map to a published citation. Malformed provider JSON,
conflicting duplicate evidence IDs and non-finite scores fail closed.

Citation quotes allow NFC and whitespace normalization only. Semantic aliases,
case changes and rewritten punctuation do not establish quote fidelity. Page,
range, document and supplied source metadata must agree with the request's
evidence registry.

## Abstention policy

Canonical reasons include `no_evidence_found`, `document_does_not_mention`,
`unsupported_claim`, `contradicted_claim`, `ambiguous_question`,
`conflicting_evidence`, `provider_abstention`, and `invalid_citation`.
Provider reasons are advisory and are reclassified by the verifier. A stale
source is rejected when a newer authoritative source supersedes it; when
precedence cannot be established, the result is `conflicting_evidence`.
An unsuccessful top-k search establishes `no_evidence_found`, including when
the retrieved items fall below the support threshold. A provider assertion of
`document_does_not_mention` cannot prove document-wide absence. That reason
requires a trusted, separately verified document-scope check; the public API
does not accept a caller-supplied proof flag. Otherwise the verifier uses
`unsupported_claim` and a bounded message in the requested language.

The owner-authorized complete-text lane checks registered physical PDF hashes,
page counts, authorized source roots and untruncated text before making at most
one additional inference. Its limits are4 documents,100 pages and96,000 context
characters. Missing, image-bearing, blank, redacted or oversized scope fails
closed. Explicit page requests stay within those pages. Physical-page evidence
IDs bind the PDF hash and original page; citations still pass the same registry,
quote and claim checks. Full-source answers bypass the ordinary answer cache;
bounded page answers retain their content-bound cache. Internal scope flags and
audit evidence are excluded from public/cache serialization. See the
[source-scope mechanism](../grounding/document_scope_integration.md).

An explicit `llm.allow_pdf_scope: true` opts Gemini into a separately authorized
PDF lane. Reader policy `complete-document-source-v3` keeps original bytes for
displayed images/vector graphics or blank pages, with4 documents/100 pages/8MiB
and96,000 extracted-text characters as hard upper bounds. It measures tokens
before the single follow-up inference, requires durable quota and zero retries,
and bypasses model-output cache for the PDF request. Native preflight binds each
exact HTTP body and endpoint; captures retain measurement, PDF hashes and actual
POST ordering. Measurement is not a model prediction. Positive citations still
require source text. The default profile keeps this lane disabled; capability
and model-quality acceptance are separate from passing implementation tests.

Visible course markers normalize legitimate spacing between a code prefix and
its digits, preserving prefixes, dotted namespaces, suffixes, values, units and
negation. For several claims on one table, a quote may contain several complete
original rows as a JSON array, in source order. It never stitches cells or drops
a required row to fit the1200-character quote limit. Oversized quotes fail closed.
Grounding cache policy `grounding-v18` and prompt version `grounding-context-v13` isolate older incomplete quotes and false
abstentions. These are bounded verification rules, not semantic calibration.

Bounded admission-field lookups project a unique value from explicit programme,
discipline-code and admission-quota columns. They exclude foundation allocations,
require physical heading evidence for a requested year and preserve whole-row
citations. Other questions continue through ordinary grounding. A positive answer
about an individual's realized event cannot use only general normative sources
as proof; it fails with `unsupported_claim`. This does not certify document absence
or reject ordinary questions about policy requirements or eligibility.

Named-course credit claims may omit the word `Course`, but still require an
exact source course name and a unique explicitly headed credit value. Whole
calendar dates and clock times keep their identity across display formats
(`17h00`/`17:00`, numeric day/month/year and full English month names). Reordered
or invalid dates and changed times cannot pass by reusing the same number set.
A credit-count question cannot publish only an empty source heading in place of
its value. These checks preserve source proof and all release thresholds.

Ingestion producer `structure-v6` retains `structure-v5` standalone credit
quantities with their preceding source labels, including emphasized lines.
`table-v4-physical-course-scope` restores continuing course-table columns only
from a prior explicit header with matching physical column widths. It preserves
all original marker, subtotal and spillover rows. Unknown leading rows remain
unscoped; a subtotal is never a semester marker, and a table with several
semesters never receives the last semester as its global scope. Table chunks
repeat actual markers where needed and retain original row indices and header
provenance. A quantity such as
`19 credits` is not a numbered heading. Explicit Markdown and actual structural
headings remain intact. Stored documents are reparsed when their parser,
chunker or table-extractor version is stale; rebuild the retrieval index after
that refresh. Frozen indexes and historical citations retain their original
identities.

## Confidence

Confidence derives from retrieval support, claim entailment and citation
completeness. Without a validated calibrator it is a heuristic score, not a
measured probability. Provider confidence is not trusted. Internal traces keep
`raw_confidence_score` separately from the resulting `confidence_score` so
evaluation does not apply calibration twice; neither score is public.
The calibrator is fit on dev only and evaluated on test and holdout. Runtime
must verify the calibration artifact version and checksum. Finite scores,
equal-score isotonic groups and non-overlapping ECE bins are validated.

Fitting and runtime prediction use the same persisted six-decimal raw score.
Model answers and local source calculations both apply the pinned calibrator
and preserve its version. Ordinary, explicit-page and relation-answer caches
include the calibration payload checksum; two artifacts with the same version
cannot share calibrated answers. Uncalibrated dev training captures stay intact;
test/holdout captures require the pinned artifact. The release validator checks
actual captured scores/labels/version rather than trusting artifact metadata.

## Benchmark policy

The independent benchmark is split by document, question-template, semantic
topic and adversarial-pattern groups. Dev is used for fitting policy artifacts;
test is used for development evaluation; holdout is opened only for final
sign-off. No split may contain duplicate IDs or uncontrolled source leakage.
Repair and release validation share observable source/template/intent families;
gold evidence document IDs are included even when authored group labels differ.
Repartitioning exposed rows does not create a fresh holdout. Release requires
independent decisions bound to every annotation and the benchmark file,
plus a signed holdout exposure audit. Phase 5 accepts independent human review
or the owner-authorized `phase5-ai-owner-v1` independent AI source review with
owner sign-off of the concrete frozen review bundle. AI identities and source
findings remain explicit; this does not change human requirements in other
phases. See [review policy](../grounding/phase5_ai_review.md).
Legacy `reviewed` flags alone are
insufficient. Native predictions and gold scoring run separately; fixtures and
replayed provider responses remain diagnostics.

For the bounded course-credit assertion grammar, a leading course/môn label is
optional when an exact parsed course code identifies a unique headed credit row.
Omitting that label cannot weaken code/namespace/suffix, unit, value or atomicity
checks. Name-only assertions retain their explicit label requirement. Grounding
rejections use the requested language and the actual canonical abstention reason.

Evaluation uses `reviewed-span-coverage-v3` for quoted gold evidence. Location
alone does not earn claim-citation credit. A shared visible quote must cover the
reviewed evidence for every mapped claim, preserving table row boundaries and
code/value identity. Every required evidence link must be covered for claim
grounding/completeness and calibration success. This is a conservative literal
coverage proxy, not general NLI. Alternative valid spans need independent review
and freezing before official held-out inference; they are not guessed from
lexical similarity or added to make observed model outputs pass. Legacy fixture
rows without gold quotes retain a coordinate proxy and cannot satisfy the
official benchmark contract requiring reviewed gold quotes.

A claim that reproduces the complete independently reviewed source quotation
can match its reviewed translated gold fact. Visible evidence must still prove
the full quotation, coordinates, quantities and source heading. This literal
fallback adds no translation model, gold alternatives or unreviewed evidence.

For prose, claim support is checked against the visible citation quote. An
exact source claim selects its actual passage before the general excerpt
window. A requested Article/Điều number selects a unique physical section
heading when available. These operations preserve contiguous source text.
Empty quotes are invalid citations and cannot enter the answer cache.

A source locator in an answer must be proved by its directly cited page or
source heading. It cannot license that number as a factual quantity. Evaluation
can match a longer verbatim contextual quotation to an atomic reviewed gold
span only when the whole claim is present in the actual visible quote and the
reviewed source coordinates/span match. Negating or conditional wrappers do
not earn this match. This remains a bounded literal proxy, not general NLI.

Simple single-course credit requests can use a deterministic headed-column lookup.
The entire request must match the bounded grammar; extra facts, conditions, dates
and instructions fall back to the full pipeline. A unique explicit code/credit
row is required; the original complete row is cited and normal grounding, display
and calibration checks still apply. Document selection alone does not resolve
"this rule" or "that course"; user history, selected text or an explicit local
subject must supply the referent. Request context version is `request-context-v10`.
