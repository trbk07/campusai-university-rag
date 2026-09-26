# Phase 5 annotation guidelines

Annotate claims atomically: split independent facts, numbers, dates, codes,
units and polarity into separate claims. A claim is `supported` only when the
quoted evidence entails the complete proposition. A claim is `partial` only
when the supported boundary is explicit; otherwise use `unsupported`.

Evidence spans must be exact NFC-normalized substrings of the source. Include
the smallest span that establishes the claim, but retain the table header and
row/column context for table facts. Record page, chunk, document and source
hash. Numeric values and units must match exactly; `at least 10` is not
`exactly 10`, and percent is not percentage points.

Use `contradicted` when an authoritative evidence span states the opposite or
an incompatible value. Use `ambiguous` when equally authoritative sources or
interpretations cannot be resolved. A newer official source supersedes an old
one only when publication/effective metadata establishes precedence.

Canonical abstention reasons are `no_evidence_found`,
`document_does_not_mention`, `conflicting_evidence`, `ambiguous_question`,
`provider_abstention`, `unsupported_claim`, and `contradicted_claim`.

Positive example: gold claim “CS201 requires 3 credits” with a quote that
contains `CS201` and `3 credits` is supported. Negative example: a quote for
CS202 or `4 credits` is not support. Borderline example: a paragraph says
“normally 3 credits” while the question asks for an exact mandatory value;
annotate the qualifier and mark the exact claim unsupported unless policy
allows a bounded partial answer.
