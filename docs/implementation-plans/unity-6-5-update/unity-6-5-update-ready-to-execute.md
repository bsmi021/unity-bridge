# Unity 6.5 Update Ready To Execute

Last updated: 2026-07-02

Status: implementation executed on `codex/unity-6-5-update`; full live Unity
validation is still pending a target Unity project.

## Planning Deliverables

- [x] Detailed plan:
      `docs/implementation-plans/unity-6-5-update/unity-6-5-update-implementation-plan.md`
- [x] Summary:
      `docs/implementation-plans/unity-6-5-update/unity-6-5-update-summary.md`
- [x] Execution guide:
      `docs/implementation-plans/unity-6-5-update/unity-6-5-update-execution-guide.md`
- [x] Readiness checklist:
      `docs/implementation-plans/unity-6-5-update/unity-6-5-update-ready-to-execute.md`

## Must Do Before Code

- [x] Create branch `codex/unity-6-5-update`.
- [x] Confirm current dirty files with `git status --short --branch`.
- [ ] Confirm live Unity 6.5 editor status with `unity-bridge --pretty status`.
- [ ] Run baseline full suite and coverage.
- [x] Write official API research briefs.
- [x] State acceptance criteria and failing tests for the first behavior change.

## Handoff Incorporation Status

- [x] Unity 6.5 EntityId branch: already ancestor of `HEAD`.
- [x] PR #16 reload brief: included as validation/reconciliation lane.
- [x] Profiler frame design: included with correction gate.
- [x] Package-manager research/install handoff: included as validation-first
      lane.
- [ ] Live PR #16 PlayMode proof: still required during implementation.
- [ ] Target-project install parity: still required before release/push.

## Implementation Launch Checklist

- [ ] Research brief for Phase 1 completed.
- [x] First red test named and written.
- [x] Red failure output recorded.
- [x] Production files edited only after red proof.
- [x] Focused test green.
- [x] Refactor under green.
- [ ] Full suite and coverage gate run before push.

## Phase Gates

### Gate 0: Baseline

- [x] Help surface verified.
- [ ] Unity 6.5 compile baseline recorded.
- [ ] Handoff branches/docs reconciled.

### Gate 1: Correctness

- [x] Addressables build fixed.
- [ ] PlayMode reload terminal behavior verified or fixed.
- [x] Test Runner migration decision documented.

### Gate 2: Safe Writes

- [x] Script edits implemented.
- [x] SHA256 preconditions implemented.
- [ ] Compile/import feedback verified.

### Gate 3: Profiler

- [x] Profiler design corrected.
- [x] Profiler frame commands implemented.
- [ ] Slow marker and GC allocation acceptance tests pass.

### Gate 4: Unity 6.5 Additions

- [x] Build Profile create implemented.
- [x] Lifecycle hooks implemented additively.
- [x] Screenshot/model/import additions selected and validated with source/unit tests.

### Gate 5: Release

- [x] README, CHANGELOG, docs index, and skill docs updated.
- [ ] Full tests pass with coverage above 90 percent.
- [ ] Unity 6.5 compile/test proof recorded.
- [ ] Install parity checked.
- [ ] Branch ready to commit and push.

## Definition of Done

The Unity 6.5 update is done only when all selected gaps have source-backed
tests, Unity 6.5 compile/test proof is green, full coverage remains above 90
percent, handoff work has been reconciled, and docs/skills match the live CLI.
