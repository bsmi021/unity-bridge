# Phase 4 Live Matrix Expansion Brief

Last updated: 2026-07-10

## Scope

Extend the environment-gated live Unity 6000.5 integration layer under
`tests/integration/` and its unit helpers. Do not edit production bridge code or
deploy an external project.

## Required scenarios

- Screenshot multi-angle failure after state mutation still restores the exact
  Scene View state; create only a unique disposable directory/file conflict.
- Profiler known marker/allocation evidence when an explicitly configured
  fixture scene or command is available; otherwise give an actionable skip.
- PlayMode enter/stop terminal delivery and reload recovery using bounded waits
  and cleanup.
- Addressables true success/failure guarded behind explicit fixture environment
  variables so ordinary projects are never mutated accidentally.
- Parameterized optional-adapter availability/package-missing behavior for
  every existing optional adapter command group. Package absence is an expected
  structured outcome, not a test failure or mutation.
- Add a fixture-matrix manifest/validator that records core-clean,
  package-rich, and playback/build-target roles through environment variables;
  collection must show exactly which required roles are unavailable.

Use only registered CLI paths verified from live `--help`. Keep every mutation
inside unique test-owned paths with `try/finally` cleanup. Add Arrange/Act/Assert
unit tests for selection, guard, and command construction.

## Non-goals

- Do not commit/push, install source into a project, assume Builder paths, or
  modify production code. The main agent owns live execution and any defect fix.
