# Phase 5 contract

Version: `phase5-public-v2` / `phase5-internal-v2`

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

## Public response

The public fields are `answer`, `citations`, `claims`, `confidence`,
`abstained`, `abstention_reason`, and `schema_version`. Public payloads never
contain cache keys/hits, local paths, raw provider output, retrieval scores,
debug reasons, source hashes unless explicitly required by the API, or internal
trace data. Every public claim has a stable `claim_id` and citation IDs that
exist in the same response.

`schema_version` is `phase5-public-v2`. An abstained response must provide one
canonical public reason. A citation without a claim mapping is not published.

## Abstention policy

Canonical reasons include `no_evidence_found`, `document_does_not_mention`,
`unsupported_claim`, `contradicted_claim`, `ambiguous_question`,
`conflicting_evidence`, `provider_abstention`, and `invalid_citation`.
Provider reasons are advisory and are reclassified by the verifier. A stale
source is rejected when a newer authoritative source supersedes it; when
precedence cannot be established, the result is `conflicting_evidence`.

## Confidence

Confidence is a calibrated probability-like score derived from retrieval
support, claim entailment and citation completeness. Provider confidence is
not trusted. The calibrator is fit on dev only and evaluated on test and
holdout. Runtime must verify the calibration artifact version and checksum.

## Benchmark policy

The independent benchmark is split by document, question-template, semantic
topic and adversarial-pattern groups. Dev is used for fitting policy artifacts;
test is used for development evaluation; holdout is opened only for final
sign-off. No split may contain duplicate IDs or uncontrolled source leakage.
