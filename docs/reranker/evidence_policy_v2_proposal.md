# Proposed Phase 7 evidence schema v2

Status: proposal only; automatic approval review rejected applying this change.
The serving module remains `src/campusai/retrieval/evidence_policy.py`, version
`evidence-softmax-v1`, with twelve feature columns.

## Requested change

Append three observable features to the shared fitting/serving extractor:

| Feature | Meaning |
|---|---|
| `query_anchor_coverage` | Fraction of complete numeric values, course identifiers and explicit uppercase acronyms in the request that occur in the actual top-five source bodies. |
| `requested_field_count` | Number of requested field types explicitly named in the question. |
| `requested_field_coverage` | Fraction of those requested field types present in the actual top-five source bodies. |

Use accent-normalized Vietnamese/English field names for GPA, teaching staff,
credits, prerequisites, tuition, registration fees, examination schedules,
teaching rooms and email. Decode table cells, strip generated provenance
prefixes, and never use gold labels, benchmark identifiers or document IDs as
serving inputs. An unspecified anchor or field has neutral coverage of one.
These are probability-model features, not unconditional abstention rules.

Bump the serialized schema version from `evidence-softmax-v1` to
`evidence-softmax-v2`, with fifteen columns. Old probability artifacts will be
incompatible and require new calibration. This can change answer/abstain and
reranking decisions wherever the optional reranker is enabled. The default
disabled setting, evidence domain guard and mandatory release gates remain.

## Measurement sequence after authorization

1. Implement the shared extractor and version change; check fitting/serving
   feature parity, whole-value anchor matching, decoded table fields, absence
   signals, malformed observations and rejection of stale artifacts.
2. Use dev-only fitting and grouped out-of-fold measurement. Preserve failed
   experiments and AI/owner provenance; auxiliary experiments cannot qualify
   the release benchmark automatically.
3. Create a successor source freeze. Measure M3–M5 with matching model, runtime,
   index and source identities, preserving previously consumed heldout studies.
4. Continue M6–M12 and S1–S6 only as their prerequisites pass.

This document does not apply the change or claim that it passes M5.
