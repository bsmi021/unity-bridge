# Unity 6.5 Update Summary

Last updated: 2026-07-02

## Objective

Implement the Unity 6.5 update for Unity Bridge without losing current CLI-only
work or the PR #16/package/profiler handoff context.

## Key Inputs

- `docs/unity-6.5-capability-gap-audit.md`: source backlog and sequencing.
- `.codex/pr16-playmode-reload-trace-brief.md`: reload-result validation
  handoff.
- `docs/profiler-frame-drilldown-design.md`: draft profiler-frame design that
  needs correction before implementation.
- `docs/package-manager-automation-research.html`: package-manager and install
  handoff context.
- `origin/fix/unity-6.5-entityid-migration`: already merged into current history.

## Current Conclusions

- Do not merge PR #16 branches wholesale. They contain useful reload/package
  history but also broad old surface churn.
- Keep current `BridgeTestRunReporter` improvements, including run GUID,
  cancellation, progress artifacts, result artifacts, selectors, and
  SessionState counters.
- Treat package-manager handoff as validation-first because many recommended
  package operations already exist.
- Fix the profiler design doc before coding the profiler frame feature.
- Keep all implementation behind TDD and full coverage gates.

## Priority Order

1. Reconcile handoffs and establish Unity 6.5 baseline.
2. Fix `addressables build` overload/error reporting.
3. Revalidate PR #16 PlayMode reload terminal-result behavior.
4. Add script text editing plus SHA256 write preconditions.
5. Implement profiler frame drill-down.
6. Add Unity 6.5 features: Build Profile create, lifecycle hooks, screenshot
   inline/multi-angle, external model import, asset editing batch, analyzer
   filtering, rendering inspection.
7. Clean stale docs/dead code after feature work.

## Required Validation

- `uv run ruff check src tests`
- `uv run pytest --cov=unity_bridge --cov-fail-under=90`
- `unity-bridge --pretty status`
- `unity-bridge --timeout 600 --pretty test compile`
- Focused EditMode/PlayMode runs for changed live bridge behavior.
- `unity-bridge install --check` and target-project parity when deploying.

## Definition of Done

Unity Bridge is considered updated for Unity 6.5 when compile/test proof is
green on Unity 6.5, the selected capability gaps are implemented and documented,
handoff work is reconciled with source evidence, and the full coverage gate
stays above 90 percent.
