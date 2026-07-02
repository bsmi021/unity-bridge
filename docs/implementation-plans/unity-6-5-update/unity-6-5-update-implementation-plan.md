# Unity 6.5 Update Implementation Plan

Last updated: 2026-07-02

## Overview

This plan turns `docs/unity-6.5-capability-gap-audit.md` plus the related handoff
work into an implementation-ready roadmap for Unity Bridge on Unity 6.5.

Branch target: `codex/unity-6-5-update`
Primary spec: `docs/unity-6.5-capability-gap-audit.md`
Related inputs:
- `docs/profiler-frame-drilldown-design.md`
- `.codex/pr16-playmode-reload-trace-brief.md`
- `docs/package-manager-automation-research.html`
- `docs/reload-domain-resilience-research.html`
- `docs/bridge-compile-wait-research.html`
- `docs/unity-6.4-capability-delta-analysis.md`

## Current State Assessment

### Verified in this checkout

- Unity 6.5 EntityId migration branch `origin/fix/unity-6.5-entityid-migration`
  is already an ancestor of `HEAD`.
- `GetSelectionCommandHandler.cs` and `ValidatePrefabCommandHandler.cs` already
  use `#if UNITY_6000_5_OR_NEWER` guards for EntityId APIs.
- `BridgeTestRunReporter.cs`, `CompileCommandHandler.cs`,
  `BridgeOperationLedger.cs`, and `core/bridge.py` already contain reload
  survival and in-flight busy handling work that overlaps the PR #16 handoff.
- The local PR #16 branches are broad historical branches, not clean merge
  sources. They must be reconciled for lessons only.
- `docs/profiler-frame-drilldown-design.md` exists but still has two known
  plan defects from the 6.5 audit: stale `phase7` citation and CLI syntax that
  conflicts with the current command surface.
- Current repo docs and AGENTS text still contain some stale MCP/deprecated
  compatibility language even though current `pyproject.toml` has no `mcp`
  optional dependency and `src/unity_bridge/mcp/` is absent.

### Required before production implementation

- Confirm the live Unity 6.5 editor build and package versions.
- Re-run `unity-bridge --help` and targeted command help before updating CLI
  docs or skills.
- Verify bridge health before compile/test proof.
- Establish a clean work branch. Current checkout contains untracked planning
  docs and a modified `docs/index.md`; do not discard them.

## Handoff Work To Incorporate

### Handoff A: PR #16 PlayMode reload trace

Source: `.codex/pr16-playmode-reload-trace-brief.md`

Plan:
- Treat this as a validation and regression lane, not a merge lane.
- Compare current `BridgeTestRunReporter.cs` and `RunTestsCommandHandler.cs`
  against `codex/fix-pr16-playmode-reload` only to identify missing safeguards.
- Preserve current `RunGuidKey`, cancellation, progress artifacts, test result
  artifacts, selector support, and `SessionState` counters.
- Add or preserve tests for no repeated command execution across reload,
  terminal response writing, progress artifacts, and command-id/run-guid
  persistence.

### Handoff B: Profiler frame drill-down design

Source: `docs/profiler-frame-drilldown-design.md`

Plan:
- Correct the stale phase7 citation.
- Resolve CLI shape before coding. Use either `profiler-control frame ...` or a
  deliberate `profiler` command restructure. Do not ship the current conflicting
  `unity-bridge profiler frame ...` syntax as-is.
- Target Unity 6000.5-safe APIs and avoid obsolete `GetItemInstanceID`.

### Handoff C: Package-manager automation and install handoff

Source: `docs/package-manager-automation-research.html`

Plan:
- Verify current package operations before adding new package features:
  `package batch`, `package pack`, `package clear-cache`, active-operation
  rejection/serialization, manifest/lockfile behavior, and `install` checksum
  drift detection.
- Do not re-open solved package-manager work unless validation finds drift.
- Keep target-project install proof in the final validation chain:
  `unity-bridge install --check`, `unity-bridge install --force` when needed,
  and hash/skill parity checks.

### Handoff D: Unity 6.5 EntityId migration

Source: `origin/fix/unity-6.5-entityid-migration`

Plan:
- No merge needed; branch is already in history.
- Keep a recurring grep gate for removed/obsolete 6.5 APIs:
  `GetInstanceID()`, `InstanceIDToObject`, `Selection.instanceIDs`,
  `objectReferenceInstanceIDValue`, `AddComponent(string)`, legacy component
  accessors, and newer profiler/test APIs that produce 6.5 warnings or errors.

## Priority Roadmap

### Phase 0: Reconcile and Baseline

Goal: make the implementation branch trustworthy before feature work.

Tasks:
1. Create branch `codex/unity-6-5-update`.
2. Record current dirty/untracked docs and preserve ownership.
3. Run current CLI help inventory.
4. Run obsolete API grep sweep across `ClaudeCodeBridge/`.
5. Verify Unity 6.5 bridge status, compile, and current full Python test suite.
6. Update stale docs only after live command surface is confirmed.

Exit criteria:
- Baseline compile and tests recorded, or blockers documented with exact output.
- PR #16 branch assessed as "lessons only" with no wholesale merge planned.
- Handoff docs linked from the implementation plan.

### Phase 1: Functional Correctness Fixes

Goal: close bugs independent of Unity 6.5 feature scope.

Work items:
1. Fix `addressables build` overload ambiguity and false success reporting.
2. Revalidate PlayMode reload result reporting from the PR #16 handoff.
3. Migrate the safe half of Test Runner callback registration:
   `RegisterCallbacks` to static `RegisterTestCallback<T>` if confirmed
   available in the installed package.
4. Correct `TestListCommandHandler.cs` comment/code drift around
   `RetrieveTestList` versus `RetrieveTestTree`.

TDD gate:
- Write failing tests first for Python command payloads and C# source-contract
  assertions where live C# unit tests are not available.
- Run the failing focused test before implementation and capture the failure.
- Implement source changes only after the red proof exists.

### Phase 2: Script Editing and Write Safety

Goal: add the highest-leverage agent workflow missing from the bridge.

Work items:
1. Add targeted `.cs` text patch support, likely as `script-edit` or an
   extension of `script-info`.
2. Add content hash read/precondition support:
   `asset-ext hash <path>` and `--if-match <sha256>` on write-capable commands.
3. Apply hash preconditions to script edits first, then asset text writers.
4. Trigger `AssetDatabase.ImportAsset` and compile/readiness waits after writes.

Acceptance criteria:
- Range/anchor edit modifies only the intended region.
- Wrong hash rejects the write without changing the file.
- Successful script edit imports and produces compile feedback.
- Direct filesystem changes between read and write are detected.

### Phase 3: Profiler Frame Drill-Down

Goal: make profiler output actionable at frame/sample level.

Work items:
1. Fix `docs/profiler-frame-drilldown-design.md`.
2. Add `profiler-frame` bridge command or a carefully restructured
   `profiler-control frame` surface.
3. Implement frame range, top total/self time samples, sample summary,
   bottom-up tree, GC allocation, and clear operations.
4. Extend profiler controls for area toggles and allocation callstacks.

Acceptance criteria:
- Known slow marker appears in top time samples.
- Known allocation appears in GC allocation query.
- Out-of-range frame indexes fail clearly.
- No obsolete EntityId/InstanceID profiler APIs are used.

### Phase 4: Unity 6.5 Feature Additions

Goal: implement additive Unity 6.5 capabilities from the audit.

Work items:
1. Add Build Profile creation behind `#if UNITY_6000_5_OR_NEWER`.
2. Add Unity 6.5 lifecycle attributes additively, with existing event hooks as
   fallback.
3. Add inline/base64 screenshot return and multi-angle capture workflow.
4. Add external model import for built-in model formats with graceful failure for
   glTF/glb unless a ScriptedImporter package is present.
5. Add bulk import operation bracketed by `AssetDatabase.StartAssetEditing()` and
   `StopAssetEditing()` in `try/finally`.
6. Add serialization analyzer filtering if the saved-console-pattern approach is
   insufficient.
7. Add renderer-feature, volume-profile, and rendering-stats inspections after
   the workflow-blocking items are complete.

### Phase 5: Cleanup and Documentation

Goal: remove dead or stale project surface without mixing cleanup into feature
commits.

Work items:
1. Decide whether to delete or rehabilitate `core/cache.py`.
2. Delete orphaned `commands/reports.py` and `tests/unit/test_reports.py` if
   still unused after current-source verification.
3. Remove stale command-count and MCP compatibility claims from docs/skills.
4. Update `CHANGELOG.md`, `README.md`, `docs/index.md`, and
   `.agents/skills/unity-bridge-cli` after live command help is verified.

## Research Plan

Research must be documented before each feature phase starts. Use official Unity
docs and source/package APIs first; use GitHub and third-party tooling only for
comparative workflow gaps.

Required research briefs:
- `research/unity-6-5-official-api-brief.md`: lifecycle attributes, Build
  Profile creation, serialization analyzer, Test Framework APIs, profiler APIs.
- `research/unity-6-5-package-surface-brief.md`: Addressables, Timeline,
  Cinemachine, Localization, Memory Profiler, VFX, Test Framework, Package
  Manager version-specific notes.
- `research/pr16-reload-reconciliation-brief.md`: current `HEAD` versus PR #16
  branches and live PlayMode proof.
- `research/profiler-frame-design-corrections.md`: corrected command shape,
  deprecation checks, and test fixture design.

If using subagents, write each briefing to a file first and pass only the file
path plus explicit deliverables. Research agents must be read-only unless
assigned a disjoint implementation slice.

## Work Streams

### Stream A: Research and Source Verification

Deliverables:
- Official API research briefs.
- Current-source gap matrix.
- Handoff reconciliation report.

Blocks:
- Any feature implementation that depends on Unity 6.5 API shape.

### Stream B: TDD Implementation

Deliverables:
- Focused failing tests before production changes.
- Small commits by feature slice.
- Updated command modules and C# handlers.

Rules:
- No production code edit before a red test for that behavior.
- Preserve existing CLI command-module pattern.
- Keep C# handler files under 500 LOC and methods under local size limits.
- No MCP reintroduction.

### Stream C: Validation and Documentation

Deliverables:
- Full Python test suite with coverage over 90 percent.
- Unity 6.5 compile/test proof through `unity-bridge`.
- Install parity proof for at least one target Unity project if deployment is in
  scope.
- README, CHANGELOG, docs index, and skill updates.

## File Ownership Map

Likely create:
- `src/unity_bridge/commands/script_edit.py`
- `src/unity_bridge/commands/profiler_frame.py`
- `ClaudeCodeBridge/ScriptEditCommandHandler.cs`
- `ClaudeCodeBridge/ScriptEditModels.cs`
- `ClaudeCodeBridge/ProfilerFrameCommandHandler.cs`
- `ClaudeCodeBridge/ProfilerFrameModels.cs`
- `tests/unit/test_script_edit.py`
- `tests/unit/test_profiler_frame.py`
- `docs/implementation-plans/unity-6-5-update/research/*.md`

Likely modify:
- `src/unity_bridge/app.py`
- `src/unity_bridge/core/protocol.py`
- `src/unity_bridge/commands/addressables.py`
- `src/unity_bridge/commands/asset_extended.py`
- `src/unity_bridge/commands/build_profile.py`
- `src/unity_bridge/commands/editor.py`
- `src/unity_bridge/commands/profiler.py`
- `src/unity_bridge/commands/scene_view.py`
- `src/unity_bridge/commands/testing.py`
- `ClaudeCodeBridge/AddressablesCommandHandler.cs`
- `ClaudeCodeBridge/AssetExtendedCommandHandler.cs`
- `ClaudeCodeBridge/AssetExtendedHelpers.cs`
- `ClaudeCodeBridge/BuildProfileCommandHandler.cs`
- `ClaudeCodeBridge/CaptureScreenshotCommandHandler.cs`
- `ClaudeCodeBridge/ProfilerControlCommandHandler.cs`
- `ClaudeCodeBridge/TestListCommandHandler.cs`
- `ClaudeCodeBridge/BridgeTestRunReporter.cs`
- `ClaudeCodeBridge/HeartbeatGenerator.cs`
- `ClaudeCodeBridge/ClaudeUnityBridge.cs`
- `BridgeCommandRegistry.cs`
- `README.md`
- `CHANGELOG.md`
- `docs/index.md`
- `.agents/skills/unity-bridge-cli/SKILL.md`

## Testing Matrix

Required focused tests by phase:
- Addressables build overload and error propagation.
- Test runner callback registration/source contract.
- Script edit range/anchor validation, hash mismatch, successful write payload.
- Asset hash read and `--if-match` rejection.
- Profiler frame command payloads and C# source-contract checks.
- Build Profile create payload and Unity 6.5 guard.
- Screenshot inline/multi-angle payload behavior.
- External model import validation.
- Bulk import parameters and `StartAssetEditing` source-contract check.

Required full gates before push:
- `uv run ruff check src tests`
- `uv run pytest --cov=unity_bridge --cov-fail-under=90`
- `unity-bridge --pretty status`
- `unity-bridge --timeout 600 --pretty test compile`
- Unity EditMode and PlayMode focused runs for changed bridge behavior.
- `unity-bridge install --check` against the target Unity project.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Handoff branch is merged wholesale | Regresses CLI-only work and may reintroduce MCP churn | Extract findings only; cherry-pick only after file-level review |
| Unity 6.5 APIs differ from audit notes | Compile break or wrong design | Official docs/source research brief before each feature |
| Script editing overwrites concurrent edits | Data loss | Ship hash preconditions with script edits |
| Profiler APIs are editor-only or retention-limited | Flaky feature | Live-editor acceptance tests and documented non-goals |
| Package Manager request concurrency returns | Nondeterministic package state | Validate single-operation gate before package additions |
| Coverage drops under 90 percent | Fails project rule | Add focused unit tests with each feature |

## Acceptance Criteria

The plan is complete when:
- Handoff artifacts are explicitly reconciled.
- The Unity 6.5 audit is mapped to phases and test gates.
- Research briefs are identified before feature work.
- TDD cycles and validation commands are named.
- No production code has been changed by this planning step.

The implementation is complete when:
1. Unity 6.5 compile is clean with no 6.5 obsolete-as-error API use.
2. Full Python suite passes with coverage above 90 percent.
3. Live bridge status, compile, and relevant EditMode/PlayMode validations pass.
4. Addressables build reports true success/failure.
5. Script edit and hash precondition workflows are implemented and documented.
6. Profiler frame drill-down passes unit and live acceptance tests.
7. Selected Unity 6.5 additions are implemented behind safe version guards.
8. README, CHANGELOG, docs index, and skill docs match live CLI behavior.
9. Bridge install parity is proven for the target Unity project.

## Definition of Done

Done means the branch can be pushed without caveats:
- All acceptance criteria are met.
- The full project test suite and coverage gate pass.
- Unity 6.5 live compile/test proof is recorded.
- Handoff work is either integrated, superseded, or explicitly rejected with
  source evidence.
- Documentation and changelog are updated.
- No unrelated dirty files are staged.
