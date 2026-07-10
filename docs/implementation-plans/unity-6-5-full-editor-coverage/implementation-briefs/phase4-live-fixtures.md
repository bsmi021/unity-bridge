# Phase 4 Live Fixture Brief

Last updated: 2026-07-10

## Scope

Create a durable pytest integration fixture layer for the Unity 6.5 live
scenarios in the parent plan. Own new files under `tests/integration/` plus
focused fixture helpers under `tests/fixtures/` if needed. Do not modify bridge
production code; report any discovered production defect to the main agent.

## Required behavior

- Select the target project only from `UNITY_BRIDGE_PROJECT`; skip with an
  explicit reason if it is unset, not Unity 6000.5.x, or the heartbeat is not
  healthy.
- Use the supported CLI/Python command cores for end-to-end file-protocol
  checks. Never read installed handler source as behavior proof.
- Add safe, isolated tests for: truthful inner failures/non-zero exit, menu
  validation with a detectable non-execution assertion, screenshot camera
  selection/base64/multi-angle plus exact Scene View restoration, Build Profile
  callback terminal delivery (guarded by a platform GUID environment variable),
  and profiler frame-budget behavior.
- Add path-safety/model-import scenarios only when they can be contained under
  `Assets/UnityBridgeFixtures/` with `try/finally` cleanup and without deleting
  pre-existing content.
- Mark all cases `integration`; use bounded timeouts and actionable skips.

## Tests and proof

Use Arrange/Act/Assert. Run collection and unit-level helper tests without Unity.
Do not install/deploy into a target project and do not mutate an external Unity
project in this lane. The main agent owns the first live run after source
installation.

## Non-goals

- Do not commit/push, edit production bridge files, or change the plan/audit.
- Do not assume `C:/Projects/builder`; the fixture contract is environment based.
