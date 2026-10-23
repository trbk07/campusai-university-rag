# Whole-document source-scope integration proposal

Status: owner authorized implementation on2026-10-20 with the explicit reply
“Cho phép triển khai cơ chế này” (question call
`call_0748f8cc2bc54d31a62319c00393e137`). The reader and bounded runtime path are
implemented;268 focused and2132 full offline tests pass (2 live skips). The later
native dev8 run exercised2 conditional full-source calls with the correct
absence reasons on one1-page textual PDF. Official population acceptance on the
latest runtime remains pending. See the
[authorization record](../../evaluation/results/phase5-source-scope-local-20261020-v6/owner-authorization.json).
This is not benchmark approval, completed P5-05 or an exact acceptance payload permission.

The existing generator accepts `document_does_not_mention` only with a trusted
scope flag. The service now supplies it only after complete local checks. A top-k response can say
that evidence is insufficient; it cannot establish absence throughout a PDF.

## Implemented local checks

`RegisteredDocumentScopeReader` reads registered SHA256 source identities from
an operator-configured store. Serving roots default to server-managed uploads;
an offline corpus root requires explicit operator configuration. It checks source
hashes, registered page counts, complete extracted text and full prompt coverage.
Links, junctions, unowned paths, missing/failed sources, blank pages, image content,
redacted text and any truncation reject the complete-scope finding. There is no
model call or network operation in this reader. Serving injects it into the query service.

Default bounds are four documents,100 total pages,20MiB total source bytes and
96,000 context characters. A successful result describes complete textual
coverage only. It does not decide whether a semantic fact is absent, resolve
temporal applicability, certify graphical content or approve benchmark gold.

## Authorized inference behavior

1. Preserve the existing ordinary retrieval/inference path. When that model
   explicitly proposes document-wide absence, keep its result provisional.
2. Resolve only the request's authorized document scope. Read all selected source
   pages using the local checks above. Missing, filtered or oversized scope stays
   an unsupported/insufficient-evidence response; never infer absence from top-k.
3. If and only if the complete textual scope is established and full-text egress
   is authorized, make at most one additional call using the existing Free model
   and key. The payload contains the question, all checked source text, original
   document/page identities and the usual answer schema. It contains no benchmark
   labels, expected answers, private API keys or guessed source data.
4. That inference may return a supported cited answer, an explicit ambiguity, or
   an abstention. Only its checked full-source absence can retain
   `document_does_not_mention`; all existing citation/claim guards still apply.
5. Preserve provider failure/overload semantics and shared quota admission. Do
   not retry, rotate keys, increase quality thresholds or call a paid fallback.
6. Keep source-coverage diagnostics internal. Bind cache behavior to the source
   policy and physical identities; avoid ordinary-cache reuse for full-source
   results unless those source bindings are reverified. Keep request isolation.
7. Extend native preflight to list both initial and potential follow-up prompt
   hashes before sending anything. Existing packet permissions do not authorize
   a new follow-up payload. Preserve both raw captures and real transport counts.

The full-text payload can contain more sensitive content than retrieved spans,
and a qualifying request can consume two provider calls. Source checks do not
remove that egress/privacy or latency tradeoff. The owner authorized this runtime
behavior; native acceptance collection still requires an exact preflight packet.

## Integration acceptance

- Full-source identity/page/coverage checks and local limits fail closed.
- A relevant fact at the end of a document prevents a false absence outcome.
- A missing page, changed PDF, scan/image, sanitized or truncated scope cannot
  enable document-wide absence.
- No cross-request authorization, prompt, evidence, cache or internal-field leak.
- Provider failures remain operational failures, not correct negative gold.
- Native collector preflights every possible emitted prompt and reconciles
  multiple captures/POSTs for a case without generating outputs from gold.
- Existing phase regressions pass; source/config/cache/exposure bindings are
  refreshed before official inference. Numerical release thresholds stay fixed.

Automatic approval rejected the previous runtime patch because it could send
complete selected-document text to the LLM and change shared service behavior
beyond the specifically approved payloads. The owner subsequently explicitly
authorized the described mechanism. That resolves implementation authorization;
the limits and per-payload acceptance permissions remain in force.

Current native dev8 acceptance recorded10 successful model outputs for8 questions,
including2 conditional complete-source calls. Both absence cases returned the
reviewed reason with checked full-source traces;2 ambiguity cases also matched.
This covers one1-page textual PDF only. A positive false abstention exposed a
bare-code parsing gap, now fixed together with reason/language messages and
grounding-v8 cache policy. Recorded-JSON replay passes all8; replay is not new
inference. The latest runtime still needs native acceptance/calibration on the
official population. See [current handoff](phase5_completion.md).

## 22/10 coverage finding and authorized PDF lane

Owner reply to `call_4d835485c64e44d39cbb8be45b9d1390`: “Đồng ý triển khai và tối đa2 POSTs probe”.
The actual decision is recorded in `native-authorizations.json:pdf_vision` in the
acceptance study. It authorizes this bounded extension and the exact probe only;
it is not source review, model-quality approval or a new native qualification budget.

The native baseline has67 complete-scope failures with
`source_text_coverage_incomplete`. The HUST PDF contains rendered images on
physical pages1,2,5 and34. Resource enumeration missed inline images on the
first three of those pages. Reader policyv2 now checks displayed images,
including inline content; unused resource entries alone do not block text.
The new image tests PASS. This fixes coverage integrity; it does not authorize
ignoring images or certify document absence from incomplete text.

Implemented method: an explicitly enabled Gemini PDF/vision follow-up for
image-bearing selected documents, retaining the original public/private source
bytes instead of dropping their graphical content. Bounds:4 selected/authorized
PDFs,100 pages,8MiB total original PDF bytes and96,000 extracted-text characters;
at most1 additional inference and1 token-measurement request. Keep Free/key/model,
physical hashes, page identities, temporal scope, no retries, existing claim/
citation checks and fail-closed budget admission. Unreadable/unsupported images
cannot certify absence. Positive image-only facts still require verifiable
citation text; no new trusted quote is fabricated from a model response.

The text-only mechanism remains the default. The opt-in path binds complete request
body/PDF hashes in native preflight, preserves raw responses and request journals,
and keeps token measurement separate from model predictions. The reader checks
displayed inline images and vector graphics, physical identity and all bounds.
Focused scope/native/integrity tests PASS95; combined PDF/retrieval tests PASS131.
The actual34-page HUST source passes local coverage with78,420 text characters
and its exact original PDF bytes, using0 provider requests. Default remains disabled;
the text-only and other-provider paths keep their current behavior. Never send
unselected source files or infer permission from a filename. Full PDF bytes may
include signatures, seals, QR images and metadata not present in extracted text.

Provider capability still requires the separately authorized bounded probe.
[Prepared packet](../../evaluation/results/phase5-acceptance-20261021/pdf-vision-probe-egress.json)
contains the full original public HUST34-page PDF and a generic request to
describe visible image elements on pages1,2,5 and34. No benchmark questions,
labels, expected answers, review approval or CampusAI predictions are included.
It permits at most2 POSTs:1 `countTokens`, then1
`generateContent` if measurement/admission succeed after quota/cooldown clears.
Both target `gemini-3.5-flash-lite` at `generativelanguage.googleapis.com/v1beta/models/`.
Stop at the first provider error including429/503; no retry/key rotation/reset.
Owner authorization is recorded;0 requests have been sent. Quota/cooldown must open first.
This diagnostic cannot be counted as a CampusAI prediction or independent review.

Google documents [native PDF vision](https://ai.google.dev/gemini-api/docs/document-processing)
and [request token measurement](https://ai.google.dev/api/tokens). Its
[media-resolution guidance](https://ai.google.dev/gemini-api/docs/media-resolution)
varies PDF token allocation with the model/resolution, so the old text byte
estimate must not be blindly reused for binary PDFs. Support on the pinned
model/endpoint must be established by the bounded probe, not assumed from
examples using a newer model. If it fails, retain the failure and change method.

## 23/10 compact PDF follow-up

The original full PDF is still sent, with all physical pages and graphical
content. Its prompt now contains exact page/chunk locators instead of a second
full transcription; the complete extracted index stays local for source hashes,
coverage checks and claim/citation verification. Text-only scope is unchanged.
PDF-coverage metadata without actual PDF attachments fails before inference.
On the13-page UET source the textual prompt shrinks30,772→7,082 characters
(76.99%); original PDF bytes are identical.819 affected tests PASS. The separately
approved compact native probe then completed5/5 POSTs without provider failure;
both absence cases match reviewed gold after complete source inspection. For
test-007, countTokens measured10,132 input tokens versus20,121 in the previous
request. This is a bounded capability/quality result, not a reliability or
latency guarantee. [Actual probe and bindings](../../evaluation/results/phase5-reason-qualification-compact-1d3b5a10-20261023/checkpoint.json).
Exact native egress approval and all previous bounds still apply.
