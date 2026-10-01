# CampusAI — Codex Runner Prompt

Paste this with **one task ID at a time**.

```text
Repo: trbk07/campusai-university-rag
Plan: CampusAI_plan_phase3_6_9_5_codex.md
Task: <TASK_ID>

Execute only this task.

Context rules:
1. Read only the task's READ SET first.
2. Use `rg -n` only when a referenced symbol/dependency is unresolved.
3. Do not scan the whole repo.
4. On continuation, inspect `git diff` before reopening full files.
5. Do not modify unrelated phases.
6. Do not change gold labels, test/holdout data, or frozen thresholds to make a gate pass.
7. Do not hand-edit generated evaluation reports.
8. Do not start the next task automatically.

Implementation rules:
- Keep patches minimal and typed/auditable.
- Fail closed on index/provenance/version mismatch.
- Preserve deterministic tie-breaking and reproducibility.
- Add focused tests for every behavior change.
- Run the task TEST SET.
- If a test/gate fails, report the blocker instead of widening scope.

Return only:
TASK: <id>
CHANGED:
- <file>: <change>

TESTS:
- <command>: PASS/FAIL

METRICS:
- <only affected metrics>

OPEN:
- <remaining blocker or NONE>
```

Recommended task order:

```text
P3-A
P3-B
P3-C
P3-D
P3-E
P4-A
P4-B
P4-C
P4-D
P5-A
P5-B
P5-C
P5-D
P5-E
P6-A
P6-B
P6-C
P6-D
P6-E
FINAL-RECERTIFY
```
