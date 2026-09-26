# Phase 5 release gates

The release validator is authoritative; reports cannot contain a manually
supplied pass flag. A release candidate must use runtime mode and include the
benchmark checksum, code fingerprint, schema/policy versions and calibration
artifact checksum.

Required dataset gates:

- at least 400 records;
- dev >= 120, test >= 130, holdout >= 150;
- all Phase 5 categories present;
- unique IDs, evidence for every answerable gold claim, and a reason for every
  gold abstention;
- no uncontrolled cross-split source/template leakage.

Required safety gates:

- unsupported and contradicted public-claim leakage: 0;
- citation coordinate validity: 100%;
- citation precision >= 0.99, recall/completeness >= 0.98;
- grounded claim precision >= 0.99 and recall >= 0.95;
- abstention precision >= 0.99, recall >= 0.98, reason accuracy >= 0.95;
- schema/internal-field leakage: 0.

Required calibration gates:

- fit split is dev only;
- holdout ECE <= 0.05 and Brier <= 0.08;
- calibration count >= 400;
- risk at 80% coverage <= 1% and at 90% coverage <= 2%.

If any gate fails, status is `pre-release` or `release_candidate`, never
production-ready. Thresholds, annotations and policy are frozen before the
final holdout run; fixes produce a new release candidate.
