# Subagent Brief: Adversarial Audit Reconciliation

Last updated: 2026-07-09

## Objective

Adversarially compare the existing Unity 6.5 capability-gap audit and planning
suite with the repository's current source, tests, CLI, and documentation.
Identify what landed, what remains stale, and what the earlier audit failed to
measure.

## Scope

- Read `docs/unity-6.5-capability-gap-audit.md` in full.
- Read the four documents under
  `docs/implementation-plans/unity-6-5-update/` in full.
- Inspect current source/tests for every claimed gap or completed phase.
- Review relevant changes since those documents were last updated using git
  history without modifying history.
- Challenge the meaning of "full coverage," especially claims based on generic
  script execution, menu invocation, or serialized property access.

## Non-Goals

- Do not edit files.
- Do not implement fixes.
- Do not broaden into unrelated Unity project gameplay work.
- Do not accept plan checkboxes as implementation proof.

## Sources

- Root and nested `AGENTS.md` files.
- `docs/unity-6.5-capability-gap-audit.md`.
- `docs/implementation-plans/unity-6-5-update/`.
- Current `README.md`, skill docs, Python/C# source, tests, and git history.

## Required Output

Return a prioritized, source-cited report containing:

1. Prior gaps now implemented with current proof.
2. Prior gaps still open or only partially addressed.
3. New blind spots in the earlier methodology.
4. Contradictions or stale claims across docs, source, help, and tests.
5. Recommended acceptance criteria for an honest full-coverage program.

## Validation

Every implementation-status claim must cite current source or tests, not only a
plan or changelog. Include commands run and relevant git commits when useful.

## Blockers

Report inaccessible history, missing packages, or untestable live-Editor claims
as proof gaps rather than assuming success or failure.
