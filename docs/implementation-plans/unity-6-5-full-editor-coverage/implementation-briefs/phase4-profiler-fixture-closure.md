# Phase 4 Profiler Fixture Closure Brief

Last updated: 2026-07-10

## Objective

Find a deterministic way to produce and retain Unity 6000.5 profiler frames in
the disposable fixture so the known slow-marker and known allocation scenarios
can pass live rather than skip.

## Scope

- Inspect profiler control/frame handlers, CLI wrappers, tests, live fixture
  code, prior logs, and the disposable project's current configuration.
- Determine whether frames require play mode, an interactive Editor, explicit
  profiler enablement/areas, frame selection, or fixture-side marker code.
- Propose the smallest live marker/allocation producer and exact command order.

## Non-goals

- Do not edit source, tests, or Unity projects.
- Do not count source contracts, mocked data, or a skip as live profiler proof.
- Do not rely on private Unity APIs for the claimed supported path.

## Sources

- `ClaudeCodeBridge/ProfilerFrameCommandHandler.cs`
- `ClaudeCodeBridge/ProfilerSampleCommandHandler.cs`
- `src/unity_bridge/commands/profiler_frame.py`
- `tests/integration/test_unity65_live_matrix.py`
- `tests/integration/live_unity.py`
- disposable fixture logs under the current user's Temp directory

## Required Output

Provide a source-cited root cause, a deterministic fixture recipe, exact CLI or
pytest commands, expected evidence fields, and the smallest AAA test change if
needed. State whether batchmode/headless proof is possible.

## Validation And Blockers

Read-only investigation only. You may inspect current process/log/project
state, but do not start or mutate Unity. Report exact blockers and alternatives.
