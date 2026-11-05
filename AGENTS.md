# Canonical repository

Commit and push this project to `https://github.com/trbk07/campusai-university-rag`.
Use `origin` for that repository. The historical financial-report repository
must not receive project pushes; its legacy remote is fetch-only.

# Project roadmap

Keep `plan.md` at the repository root and tracked in Git throughout the project.
Consult it for the project roadmap and keep references to it current.
Do not move, rename, delete or exclude it during cleanup or restructuring.
The project owner will delete it themselves after the project is complete.

# Cleanup

After each task or phase, delete temporary files, abandoned drafts and generated
outputs that are no longer needed by the project or phase. Check references and
artifact bindings first. Retain source, configuration, tests and evidence needed
to reproduce or audit a result, including historical baseline artifacts.

# Evaluation question reuse

The owner has locked previously attempted evaluation questions, including PASS,
FAIL, provider-error and interrupted attempts. Do not automatically resend them
or start another full Golden100 repetition. Check `question_lock_registry` in
`evaluation/results/campusai_100_remediation_20261103/results.json` and retained
attempt journals before any new live evaluation request. Review saved answers
offline; use genuinely unasked questions for further live checks. Do not combine
predictions from different candidates into a new accuracy score. An existing
question can be sent again only if the owner explicitly changes this instruction.
