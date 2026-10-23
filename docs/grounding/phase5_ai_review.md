# Phase 5 independent AI review and owner sign-off

Policy: `phase5-ai-owner-v1`, authorized by the project owner on 2026-10-16.
The owner explicitly selected: “Cho phép independent AI review + owner sign-off,
thay yêu cầu human reviewer”. This changes the reviewer requirement for Phase 5;
it leaves numerical thresholds, fresh holdout requirements, real inference,
source bindings and requirements in other phases intact.

The authorization is preserved in
[owner authorization](../../evaluation/results/phase5-owner-ai-review-20261016/owner-authorization.json).
The previous policy and handoff remain available in the
[pre-change archive](../../evaluation/results/phase5-handoff-before-ai-policy-20261016.zip).
Historical reports and the pending historical signoff are not rewritten.

## Required evidence

The existing `independent_human` review path remains valid. The new path uses
`review_type=independent_ai_owner` and `review_policy=phase5-ai-owner-v1`.

1. Record the actual AI reviewer task and available model identity. The reviewer
   must conduct source review independently of the annotation author. A second
   AI task is recorded as AI, including shared-model limitations. It is not a
   human reviewer or proof that the benchmark was never exposed.
2. Review each question and gold against its source, including answerability,
   claim completeness, document/page, abstention reason and temporal scope.
   Quote fidelity alone does not establish that a gold answers its question.
3. Bind every decision to its annotation hash and physical source-audit artifact.
   Retain corrections needed, ambiguity and unresolved findings. They cannot
   appear as approved decisions for the unchanged annotation.
4. Propose corrections in a new benchmark revision, preserving original gold
   and provenance. Have a separate reviewer check the corrected revision.
5. Freeze the reviewed benchmark and review bundle. Obtain a concrete owner
   decision referring to those results. Policy authorization and general
   permission to work are separate from final approval of this frozen bundle.
6. Audit holdout exposure separately. Regrouping existing exposed rows cannot
   make them fresh. Then run the frozen native inference and calibration
   workflow in [operations](../operations/grounding_operations.md).

Source findings must include a rationale, source checksum and inspected pages.
A factual decision must cover the cited gold document/page. A gold abstention
must explain why the available scope supports that reason; claiming whole
document absence requires whole-document review. Temporal review must explicitly
resolve the requested date/cohort or retain the row as unresolved. An abstention
can instead resolve the review by explicitly justifying why the question does
not determine a date/cohort (`effective_date_status=not_determinable_for_question`,
`conclusion=abstention_supported`), without inventing an effective date. Issue dates
and document titles alone do not prove current applicability.

For a question that names a year but whose source does not establish applicability
for that period, an AI reviewer can instead report
`effective_date_status=not_established_for_requested_period` with
`conclusion=abstention_supported`. This path requires an unanswerable annotation,
`source_review.scope=full_documents` and a `requested_period` containing a year
actually present in the question. The reviewer must record either
`source_period_status=established_in_source` with the established source period,
or `source_period_status=undated_in_reviewed_source` with no invented source period.
The temporal decision must still be resolved and include its basis. A fabricated
effective date cannot bypass an invalid period/scope finding. These fields must
come from an actual source review; the author or collector must not fill them in
for an earlier response whose temporal review was missing.

Negative temporal reviews must use one of those two resolved abstention-scope
findings. Supplying a document issue date as `effective_date` does not substitute
for that finding, even when the raw verdict says approved.

For a `no_evidence` case where the user explicitly selected zero documents and
supplied no history or selected text, the source review can use
`scope=retrieval_scope`, `sources=[]` and a physical `request_scope` artifact.
The artifact must exactly contain `{id, request}` using the actual inference
projection; its checksum and request checksum are verified. The review finding
must justify the empty user scope. This path cannot certify a document-wide
absence, a factual claim, an unselected all-document scope or a request with
contextual evidence. The request artifact records an input; it is not a fabricated
reviewer statement or a substitute for independent review/owner approval.

Raw approvals are kept separate from binding validation. Full-document review
must enumerate every physical PDF page. Missing fields, pages or temporal
findings are not filled on behalf of the reviewer. Source review shown gold is
never counted as native CampusAI predictions.

## Validation and scope

The validator checks population, creator/reviewer separation, annotation hashes,
review artifact contents/checksums, source bindings, temporal decisions and owner
approval bindings. It rejects pending or stale evidence. Tests use fictional
attestations; they are never production review evidence.

The owner decision above authorizes this policy and the work. It does not approve
future findings, waive failed quality metrics or turn the original benchmark
into a fresh holdout. The existing 400 records remain available for repair and
reuse. A release PASS still requires every gate in
[release gates](grounding_release_gates.md).

On 2026-10-21 the owner additionally confirmed the existing authored questions
were reviewed and met the standard, and accepted disclosed exposure for Phase 5
acceptance. That concrete content decision is bound to the current source-reviewed
candidate and deterministic 400-record subset in
[owner decisions](../../evaluation/results/phase5-acceptance-20261021/owner-decisions-exposure.json).
This supersedes the freshness requirement only for `phase5_acceptance`; public
release still requires fresh holdout evidence. Exposure is conservatively recorded
as `previously_exposed`, never relabeled fresh. Source findings remain the actual
independent AI decisions; the owner is not presented as an independent AI reviewer.
