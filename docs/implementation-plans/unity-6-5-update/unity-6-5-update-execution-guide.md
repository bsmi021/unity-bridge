# Unity 6.5 Update Execution Guide

Last updated: 2026-07-02

## Execution Flow

```
Phase 0: Baseline and handoff reconciliation
  |
  +-- Verify branch, dirty files, live help, Unity 6.5 status
  +-- Reconcile PR #16, profiler, package-manager, EntityId handoffs
  \-- Gate 0: baseline proof recorded

Phase 1: Correctness fixes
  |
  +-- Addressables build red test -> fix -> green
  +-- PlayMode reload proof red/green if needed
  \-- Gate 1: functional bugs closed

Phase 2: Script editing and write safety
  |
  +-- Hash/read tests
  +-- Script edit tests
  +-- Import/compile feedback tests
  \-- Gate 2: safe writes shipped

Phase 3: Profiler frame drill-down
  |
  +-- Correct design doc
  +-- Profiler-frame tests
  +-- Handler/module implementation
  \-- Gate 3: slow-frame and GC acceptance proof

Phase 4: Unity 6.5 additive features
  |
  +-- Build Profile create
  +-- Lifecycle hooks
  +-- Screenshot/model/import/rendering additions
  \-- Gate 4: selected additions proven

Phase 5: Cleanup and release docs
  |
  +-- Dead code decisions
  +-- README/CHANGELOG/skill sync
  \-- Gate 5: full suite, coverage, install parity, push-ready
```

## Phase 0 Checklist

- [ ] Create `codex/unity-6-5-update`.
- [ ] Record `git status --short --branch`.
- [ ] Verify `origin/fix/unity-6.5-entityid-migration` remains ancestor of
      `HEAD`.
- [ ] Run current `unity-bridge --help` and targeted help for changed groups.
- [ ] Run obsolete API grep sweep.
- [ ] Run `unity-bridge --pretty status`.
- [ ] Run current compile/test baseline.
- [ ] Write research briefs before feature coding.

## Phase 1 TDD Cycles

### Addressables build

Red tests:
- `addressables build` maps failed `AddressablesPlayerBuildResult.Error` to
  `success: false`.
- C# source contract calls the out-parameter overload of
  `BuildPlayerContent`.
- No name-only `GetMethod("BuildPlayerContent", flags)` remains.

Green implementation:
- Resolve the unambiguous overload.
- Invoke with a by-ref result.
- Set success from the result error field.

### PR #16 reload behavior

Red tests or live repro:
- Run-tests command is not reprocessed after domain reload.
- Run GUID survives until cancel or terminal response.
- Terminal response writes before SessionState cleanup.
- Progress/result artifacts are written.

Green implementation:
- Patch only the missing gap found in current `HEAD`.
- Preserve current selector and progress behavior.

## Phase 2 TDD Cycles

### Hash preconditions

Red tests:
- Hash command sends `asset-extended-operation` or chosen command type with
  path and hash operation.
- Write command with wrong `ifMatch` returns failure and preserves file.
- Write command with correct `ifMatch` proceeds.

Green implementation:
- Add C# hash helper using SHA256 over normalized project file path.
- Add Python CLI flags and payload marshalling.
- Reuse helper for script-edit and text asset writers.

### Script edits

Red tests:
- Range edit validates path is under `Assets/` and ends in `.cs`.
- Invalid range fails.
- Anchor not found fails.
- Successful range edit writes only the selected span.
- Successful edit imports asset and returns compile/readiness guidance.

Green implementation:
- Add script edit command module and C# handler/models.
- Register command and timeout.
- Keep edits line-oriented and bounded for first iteration.

## Phase 3 TDD Cycles

### Profiler frame

Red tests:
- Every CLI subcommand sends expected command type and camelCase params.
- Frame-index validation is represented in source.
- C# source uses `GetRawFrameDataView` / `GetHierarchyFrameDataView`.
- C# source does not use obsolete `GetItemInstanceID`.

Green implementation:
- Add profiler frame handler and models.
- Add Python command module and app registration.
- Add profiler-control area toggle support.
- Add integration test scene or fixture for slow marker and allocation.

## Phase 4 TDD Cycles

- Build Profile create: unit payload tests, C# version guard source test, live
  creation proof.
- Lifecycle hooks: source-contract tests for additive 6.5 attributes plus legacy
  fallback events.
- Screenshot inline/multi-angle: payload tests, base64 field test, multi-angle
  command shape, live file/inline proof.
- External model import: path validation tests, built-in model format success,
  glTF/glb graceful failure without ScriptedImporter.
- Bulk import: list payload tests and source-contract test for
  `StartAssetEditing`/`StopAssetEditing` in `try/finally`.

## Final Validation Commands

Use PowerShell from `C:\Projects\unity-bridge`.

```powershell
uv run ruff check src tests
uv run pytest --cov=unity_bridge --cov-fail-under=90
unity-bridge --pretty status
unity-bridge --timeout 600 --pretty test compile
unity-bridge install --check --project <TargetUnityProject>
```

Add focused Unity test commands for each live bridge behavior changed in the
phase. Do not push until the full project suite has passed.

## Rollback Rules

- Revert only the current phase's own branch changes.
- Do not revert pre-existing dirty files or handoff docs.
- If a Unity 6.5 API is unavailable in the installed editor/package version,
  stop that feature, update the research brief, and keep earlier green phases.

## Commit Slices

Recommended commit order:
1. `docs: plan Unity 6.5 bridge update`
2. `fix(addressables): report content build failures`
3. `fix(test): harden PlayMode reload reporting`
4. `feat(script): add safe text edits`
5. `feat(asset): add hash preconditions`
6. `feat(profiler): add frame drilldown`
7. `feat(profile): create Unity 6.5 build profiles`
8. `docs: refresh Unity 6.5 bridge surface`
