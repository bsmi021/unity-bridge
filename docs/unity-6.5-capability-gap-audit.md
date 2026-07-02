# Unity 6.5 Capability Gap Audit

Last updated: 2026-07-02

## Purpose

Following the Unity 6.5 upgrade compile fixes (`Object.GetInstanceID()` →
`GetEntityId()`, `SerializedProperty.objectReferenceInstanceIDValue` →
`objectReferenceEntityIdValue`, both landed under `#if
UNITY_6000_5_OR_NEWER` guards in `GetSelectionCommandHandler.cs` and
`ValidatePrefabCommandHandler.cs`), this audit asks the broader question:
what else needs updating, upgrading, or adding to the bridge given Unity
6.5 and the current state of comparable Unity automation tooling.

This supersedes nothing in
[`unity-6.4-capability-delta-analysis.md`](unity-6.4-capability-delta-analysis.md)
— that doc's P0/P1/P2 backlog is still valid and several items below
overlap with it (profiler drill-down, `BuildProfile.CreateBuildProfile`,
script CRUD, base64 screenshot, SHA256 precondition,
`StartAssetEditing`/`StopAssetEditing`). Where they overlap, this doc adds
newer evidence (exact file:line, corrected scope) rather than replacing the
prior write-up.

## Methodology

A 27-agent workflow ran in four phases:

1. **Local inventory** (4 parallel agents) — regenerated the CLI command
   surface from `unity-bridge --help` and `src/unity_bridge/commands/`
   against `app.py` registration; swept `ClaudeCodeBridge/*.cs` for other
   Unity-6.5-obsolete API patterns beyond the two already-fixed ones;
   re-verified every gap in the nine existing internal audit/tech-spec docs
   against current source; extracted the full escalate-to-`unity-mcp` list
   and a TODO/FIXME sweep.
2. **External research** (4 parallel agents, web) — Unity 6.5 new
   Editor-scriptable capabilities; Unity 6.5 deprecations beyond the
   EntityId migration; package-specific 6.5 changes for Timeline,
   Cinemachine, Localization, Memory Profiler, VFX, Addressables, Test
   Framework, Profiler, and Package Manager; a comparative sweep against
   the third-party `unity-mcp` server (confirmed as the specific server
   referenced by name/tool-names in this repo's skill doc) and other Unity
   automation tools.
3. **Synthesis** — one agent cross-referenced all eight reports into 18
   candidate findings, categorized `compile-risk` / `upgrade` /
   `new-capability`, explicitly barred from proposing any MCP server /
   `serve` command / MCP tool schema reintroduction per this repo's own
   `CLAUDE.md`.
4. **Adversarial verification** — each of the 18 candidates was
   independently re-checked against the live codebase by a fresh agent
   instructed to refute it first. **16 confirmed, 2 rejected.** Verification
   also corrected scope/wording on several confirmed findings where the
   synthesis stage's evidence was inaccurate or overstated — those
   corrections are folded into the write-ups below.

## Rejected findings (recorded to prevent re-litigation)

| Claim | Why it's false |
|---|---|
| `ObjectIdentityCommandHandler.cs` has an unguarded EntityId/reflection compile-risk gap | It already resolves `GetInstanceID`/`GetEntityId`/`InstanceIDToObject` via `MethodInfo` reflection with a graceful "EntityId resolution is not available in this Unity version" fallback — not a real risk. This exact risk class (plus `AddComponent(string)` removal, `GameObject.rigidbody`/`.camera`/`Component.renderer` obsolete accessors) is already tracked with a prescribed grep check in [`unity-6.4-capability-delta-analysis.md` §4.1](unity-6.4-capability-delta-analysis.md). |
| Animator/BridgeStatus handlers ship "registered but commented out," non-functional out of the box | False. `BridgeCommandRegistry.cs:26` and `:149` both have live, uncommented `registerHandler(...)` calls reachable from `ClaudeUnityBridge.cs:84`. The claim's source was two stale `*_ACTIVATION.md` companion docs describing a pre-`1d0bee5` architecture; the actual registration bug was already fixed. The activation docs are stale-doc cruft, not a functional gap. |

## Functional bug (not version-specific — fix regardless of 6.5)

**`addressables build` likely never runs a real content build.**
`AddressablesCommandHandler.cs:165-168`'s `ExecuteBuild` calls
`builderType.GetMethod("BuildPlayerContent", BindingFlags.Public |
BindingFlags.Static)` — a name-only lookup. `AddressableAssetSettings` has
had two public static overloads named `BuildPlayerContent` since
Addressables 1.15+ (`BuildPlayerContent()` and `BuildPlayerContent(out
AddressablesPlayerBuildResult result)`). `Type.GetMethod(string,
BindingFlags)` throws `AmbiguousMatchException` whenever multiple methods
share a name under the given flags, regardless of arity (reproduced
locally). The exception is swallowed by the handler's outer
`catch (Exception ex)`, so `addressables build` most likely fails silently
on every currently-supported Addressables version. Separately, even past
that bug, lines 170-177 hardcode `success = true` and never inspect the
`AddressablesPlayerBuildResult.Error` field, so a real content-build
failure that didn't throw would be reported as success anyway.

**Fix:** call the unambiguous overload explicitly —
`GetMethod("BuildPlayerContent", flags, null, new[] {
resultType.MakeByRefType() }, null)` — invoke it, and map `success =
string.IsNullOrEmpty(result.Error)` with the error text surfaced in the
response.

(`build.py`'s separate player-build path, `BuildOperationCommandHandler.cs`,
was checked and does *not* have this problem — it already wraps
`BuildPipeline.BuildPlayer()` in try/catch and checks
`report.summary.result`.)

## High priority

### 1. No line-range/anchor text-patch editing for `.cs` scripts
**Category:** new-capability. **Area:** new `script_edit.py` (or extend
`script_info.py`) + new `ScriptEditCommandHandler.cs`.

Verified absence: `scripting.py`'s only command (`execute-script`) runs an
arbitrary C# expression via `Mono.CSharp.Evaluator` and never persists to a
`.cs` file. `script_info.py`'s three operations (`info`/`list`/
`find-component`) are read-only MonoScript metadata. `AssetExtendedHelpers.cs:166-204`
(`TryCreateFileBasedAsset`, the bridge's only `File.WriteAllText`-based
content writer) handles `textasset`/`shader`/`asmdef`/`asmref` — no `.cs`
case. `.agents/skills/unity-bridge-cli/SKILL.md:70` and
`unity-bridge-audit-and-gap-analysis.md:17` (internally ranked "Top gap 1,
P0") both independently confirm this is the bridge's single largest
capability gap versus `unity-mcp`'s `Unity_ApplyTextEdits`/
`Unity_ScriptApplyEdits`.

**Proposed fix:** `script apply-edit <path> --range <start:end> --content
<text>` (or unified-diff application), writing only the targeted region,
then triggering `AssetDatabase.ImportAsset`/compilation. Native CLI +
file-based protocol command — no MCP tool schema. Note: this closes the
*text-patch* subset only; full AST-aware CRUD (create/delete,
`insert_method`/`replace_method`) is a larger, separate effort tracked in
the existing P0 item.

### 2. Per-sample/per-frame profiler drill-down (`profiler-frame`)
**Category:** new-capability. **Area:** new `profiler_frame.py` + new
`ProfilerFrameCommandHandler.cs`.

There is already an untracked, unimplemented design doc at
`docs/profiler-frame-drilldown-design.md` (181 lines, "Status: Draft —
awaiting approval") proposing exactly this: a `profiler-frame` command type
with `capture-start`/`capture-stop`/`frame-range`/`top-time-samples`/
`self-time-samples`/`sample-time-summary`/`bottom-up-tree`/`gc-alloc`/
`sample-gc-alloc`/`clear` operations over
`ProfilerDriver.GetRawFrameDataView`/`GetHierarchyFrameDataView`. Confirmed
gap: `profiler.py` (CLI group `profiler-control`) only has
start/stop/save/memory; the `profiler` leaf command's `profiler-sample`
handler returns a single-frame aggregate snapshot only; no
`RawFrameDataView`/`HierarchyFrameDataView` usage exists anywhere in the
repo. The `unity-mcp` server's ~9-tool `Unity_Profiler_Get*` family
(visible in this session's tool list) corroborates this as a real
competitive gap.

**Two defects to fix in the design doc before building from it:**
- Its "Tracks: `docs/phase7-new-gaps-report.md` P1 item 12" citation is
  fabricated — that report's P1 tier only has items P1-1 through P1-7, none
  profiler-related.
- Its proposed CLI syntax `unity-bridge profiler frame ...` collides with
  the existing `profiler` leaf command (`diagnostics.py`'s `profiler-sample`
  wrapper) — `profiler` is not a sub-app. Use `unity-bridge profiler-control
  frame ...` instead (or restructure `profiler` first).
- Target non-deprecated overloads: avoid `HierarchyFrameDataView.GetItemInstanceID`
  (obsolete since Unity 6000.3 in favor of `GetItemEntityId`).

The doc's effort estimate (~2 days) and TDD test plan
(`tests/unit/test_profiler_frame.py` + `@pytest.mark.integration`) remain
valid.

### 3. Project-wide text/regex search over `.cs` files — downgraded from the external comparison's "high"
**Category:** new-capability. **Priority:** actually low/medium, not high.

`search.py`/`SearchQueryCommandHandler.cs` wrap `UnityEditor.Search.SearchService`
for asset/scene/menu queries only — no text/regex scan of `.cs` content
exists anywhere in the repo. This matches `unity-mcp`'s `Unity_Grep`/
`Unity_FindInFile`. However, this project's own internal audit
(`unity-bridge-audit-and-gap-analysis.md`) already reviewed this exact
question and did not flag it as a gap — it marked SearchService coverage
as sufficient and ranked script CRUD (item 1 above) as the real P0 instead.
Also, unlike nearly every other bridge command, `.cs` files are plain text
on the same disk the calling agent already has direct filesystem search
access to — routing through the JSON command/response bridge is strictly
slower than a local grep. Worth building as a small addition (and as a
locate-before-patch step for item 1), but not the single highest-value gap.

## Medium priority (upgrades and new capabilities)

### 4. `TestRunnerApi.RegisterCallbacks`/`Execute` — migrate half, watch the other half
`BridgeTestRunReporter.cs:41,68` uses instance `_api.RegisterCallbacks(...)`
and `_api.Execute(...)`. Checked directly against Unity's Test Framework
API docs:
- `RegisterCallbacks` → static `RegisterTestCallback<T>` is available
  **today** in the stable 1.4.x package line — migrate now, no downside.
- `Execute` → static `ExecuteTestRun` and the explicit "non-static methods
  will become obsolete" notice exist **only** in the experimental preview
  package `com.unity.test-framework@2.0.1-exp.2`, not in what Unity 6.4/6.5
  ship by default. Treat as a watch item, not an actionable migration yet.

Separately (own ticket): `TestListCommandHandler.cs`'s header comment
claims it avoids the obsolete `RetrieveTestList` in favor of
`RetrieveTestTree`, but line 77 actually calls `testRunnerApi.RetrieveTestList(...)`
— comment and code disagree, and `RetrieveTestList` has been obsolete since
test-framework 1.1.33.

### 5. Reload-timing code could adopt Unity 6.5's new lifecycle attributes
`AssemblyReloadEvents.beforeAssemblyReload`/`afterAssemblyReload`
(`HeartbeatGenerator.cs:141,147`) and `EditorApplication.playModeStateChanged`
(`ClaudeUnityBridge.cs:45`, `PlayModeControlCommandHandler.cs:45`, the
latter driven by `commands/playmode.py`) could be supplemented with Unity
6.5's new `Unity.Scripting.LifecycleManagement` attributes
(`[OnCodeInitializing]`/`[OnCodeLoaded]`/`[OnCodeDeinitializing]`/
`[OnCodeUnloading]`, `[OnEnteringEditMode]`/`[OnExitingEditMode]`/
`[OnEnteringPlayMode]`/`[OnExitingPlayMode]`, confirmed live at
`docs.unity3d.com/6000.5/.../programming-code-lifecycle.html`). Recommend
additive: add the new hooks under `#if UNITY_6000_5_OR_NEWER` alongside the
existing event-based code kept as the pre-6.5 fallback, not a rip-and-replace.
(`commands/assembly_lock.py`'s `AssemblyReloadLockCommandHandler.cs` uses
`LockReloadAssemblies()`/`UnlockReloadAssemblies()`, not the flagged APIs —
only a secondary beneficiary.)

### 6. Add scripted Build Profile creation
`build_profile.py`'s `VALID_ACTIONS` (list/get-active/set-active/get-info/
get-scenes/set-scenes/get-defines/set-defines/build) and
`BuildProfileCommandHandler.cs`'s matching switch have no `create` action —
new profiles must be created manually in-editor today. Unity 6.5 adds
`BuildProfile.CreateBuildProfile(GUID platformId, string profileName,
UnityAction<BuildProfile> onProfileReady)` (writes to
`Assets/Settings/BuildProfiles/{profileName}.asset`, auto-installs required
platform packages async). Add a `profile create` action, guarded
`#if UNITY_6000_5_OR_NEWER`.

### 7. Inline base64 / multi-angle screenshot return
`CaptureScreenshotCommandHandler.cs:342`'s `SaveScreenshot()` only does
`Texture2D.EncodeToPNG()` → `File.WriteAllBytes` → path (repo-wide grep for
`Base64`/`ToBase64String` returns zero matches). `scene_view.py` exposes
camera-pose control only, no capture, no multi-angle. Add: (a) an optional
`--inline`/base64 flag on the existing `screenshot` command to return image
bytes directly in the JSON response, and (b) a `--multi-angle` mode on
`scene-view` looping N camera poses through the existing capture path.
Both are additive flags on existing commands, not a new subsystem.

### 8. SHA256/content-hash precondition for writes
No `sha256`/`ContentHash`/`IfMatch`/`ComputeHash`-based write precondition
exists anywhere in the bridge (the only `ComputeHash` usage,
`BridgeOperationLedger.cs:335`, hashes command *parameters* for ledger
dedup — unrelated). Real unguarded overwrite surfaces exist today:
`AssetExtendedHelpers.cs:176,183,191,198` (`File.WriteAllText` for
textasset/shader/asmdef/asmref creation) and `material.py`'s `modify`/
`copy_properties` ops. Add `--if-match <sha256>` plus a read command
(`asset-ext hash <path>`) to reject writes when on-disk content has
changed since last read. Becomes more valuable once item 1 (script
text-patch writes) ships — sequence together or immediately after.

### 9. `AssetDatabase.StartAssetEditing`/`StopAssetEditing` batching
Zero matches repo-wide. Important scope correction: there is **no existing
bulk operation to wrap** — `AssetExtendedCommandHandler.cs`'s
delete/copy/move and `AssetOperationCommandHandler.cs`'s import all operate
on exactly one path (or one src+dest pair) per call; the only plural field
(`assetPaths`, on `export`/`reserialize`) already delegates to a single
native batched Unity API call that wouldn't benefit from this wrapper.
Real scope: add a new list-accepting bulk operation (bulk-import is the
cleanest starting case) whose internal per-item loop is bracketed in
`try/finally` with `StartAssetEditing()`/`StopAssetEditing()`. Do not try
to bracket this across separate `batch.py` commands — each is an
independent file-based round-trip on a separate `EditorApplication.update`
tick, and a begin/end pair spanning ticks risks leaving the AssetDatabase
edit-locked on timeout/crash.

### 10. External model (FBX) import automation
`AssetExtendedCommandHandler.cs:233`'s `copy`/`move` use
`AssetDatabase.CopyAsset`, which requires both paths already inside the
AssetDatabase — it cannot ingest a file from an arbitrary OS path.
`import-package` is scoped to `.unitypackage` only.
`ImportSettingsCommandHandler.cs` only configures importers for assets
already in-project. Add `asset-ext import-model <source-path> <dest-path>`:
`File.Copy` from the external path into `Assets/`, then
`AssetDatabase.ImportAsset(destPath, ImportAssetOptions.ForceUpdate)`, then
apply importer settings. **Correction to scope:** this only works for
formats Unity's built-in `ModelImporter` natively supports (FBX, OBJ,
DAE/Collada, 3DS, DXF) — glTF (`.gltf`/`.glb`) has no built-in Unity
importer and requires a third-party `ScriptedImporter` package (UnityGLTF,
glTFast); the command should branch on the resulting `AssetImporter` type
and fail gracefully rather than assume `ModelImporter` unconditionally.

## Low priority

### 11. Dead `ResponseCache` — wire in or delete
`core/cache.py`'s `ResponseCache`/`get_cache()` (re-exported in
`core/__init__.py`) have zero functional callers — `CommandResult.cached`
defaults to `False` and is never set `True` anywhere in `src/`. It was
orphaned by the MCP retirement (PR #17 explicitly called it "the MCP-only
ResponseCache" while deleting `mcp/server.py`'s `_invoke_command`, its only
caller). It also has a pre-existing bug: `invalidate(pattern)` does
`pattern in k` where `k` is a 16-char hex SHA256 digest — a human-readable
command-type string can never match, so only full-clear (`invalidate(None)`)
is reachable. Recommend **deleting** `core/cache.py`,
`core/__init__.py`'s re-export, and `tests/unit/test_cache.py` — simpler
than rehabilitating already-buggy, currently-dead scaffolding. If wired in
instead, key on `is_parallel_safe(command_type, parameters)` or the cache's
own narrower `CACHEABLE_COMMANDS` (4 entries), **not** raw
`PARALLEL_SAFE_COMMANDS` (29 entries, many read-only only for specific
`operation` values post-PR#17's operation-gating — keying on it directly
would cache mutating calls).

### 12. Rendering-internals inspection gaps
`render_pipeline.py`/`RenderPipelineCommandHandler.cs` cover
list-assets/get-current/set-default/set-quality/inspect on the
`RenderPipelineAsset` itself, but never descend into a renderer data
asset's `m_RendererFeatures` list. Zero matches for `VolumeProfile`,
`SRP.?Batcher`, `GPU.?Resident`, `BatchRendererGroup` anywhere in the repo.
`ProfilerSampleCommandHandler.cs` exposes only legacy
`UnityStats.triangles/drawCalls/vertices`. Add three read-only operations:
`list-renderer-features`, `inspect-volume-profile`, and a `rendering-stats`
op surfacing SRP Batcher/GPU Resident Drawer/BatchRendererGroup counters.
Inspection-only, explicitly deferred behind the workflow-blocking items
above.

### 13. Delete orphaned `commands/reports.py`
`extract_test_report()`/`extract_build_report()` are not imported by
`app.py`, `testing.py`, `build.py`, or anywhere else in `src/` — only their
own test file imports them. Also functionally redundant:
`core/output.py`'s generic `_to_snake_case_keys()` already normalizes every
`CommandResult` payload (including `run-tests`/`build-operation`) the same
way. Delete both `reports.py` and `tests/unit/test_reports.py`.

### 14. Stale documentation
- `README.md:660` states "92 top-level entries: 67 command groups and 25
  top-level commands." Live `unity-bridge --help` (verified empirically,
  2026-07-01) has **97**. Fix: stop hard-coding the count — point solely to
  `unity-bridge --help`, consistent with the drift note already at
  `CLAUDE.md:163-165`.
- `CLAUDE.md:153`'s `**Core:**` bullet lists `diagnostics, editor, lifecycle,
  workflow` as if they were invocable group names. None are —
  `unity-bridge workflow --help` returns "No such command 'workflow'"
  (exit 2). They're module names whose commands surface differently:
  `diagnostics.py` → `doctor`/`status`; `editor.py` → `selection`/`menu`/
  `refresh`/`focus`/`screenshot`; `lifecycle.py` → `install`/`init`/
  `clean`/`version`; `workflow.py` → `snapshot` (group) + `tdd` (standalone
  command). Same false claim repeats at `CLAUDE.md:79`'s Project Structure
  comment (`workflow.py # workflow + snapshot groups`). (`CLAUDE.md:151`'s
  "40+ CLI groups" header itself is accurate — only the line-153 name list
  is wrong.)

### 15. Serialization Roslyn analyzer diagnostics
Unity 6.5 ships `com.unity.serialization` as a core package with a bundled
Roslyn "serialization rules analyzer" (codes UAC1000–UAC1018 — missing
`[Serializable]`, bad `[SerializeReference]` usage, unsupported collection
types), surfaced as Console warnings like any Roslyn diagnostic — confirmed
live at `docs.unity3d.com/6000.5/.../script-serialization-analyzer.html`.
These warnings already flow through `CompileCommandHandler.cs`'s
`GetCompilationMessages()` (backing `testing.py`'s `compile` command, *not*
`compile_extended.py` which only handles assemblies/defines/which/
optimization) and through `console.py`'s existing `console read --pattern`.
A minimal version of this could ship as a documented saved pattern
(`console read --pattern "UAC1[0-9]{3}"`) rather than new code; a dedicated
`--serialization-only`/`--code-filter UAC` flag on `test compile` would be
the low-effort code option if a dedicated surface is still wanted.

## Recommended sequencing

1. Fix the `addressables build` `AmbiguousMatchException`/hardcoded-success
   bug (functional bug, unrelated to 6.5, cheap fix).
2. Script text-patch editing (#1) — highest-leverage capability gap,
   independently confirmed by internal escalation list and external
   comparison.
3. Profiler frame drill-down (#2) — design already drafted, just needs the
   two doc corrections applied before implementation.
4. SHA256 write precondition (#8) — sequence with/after #1 since script
   writes are the highest-value target for it.
5. Everything else in Medium, by convenience/ROI — several are single-flag
   additions to already-existing commands (Build Profile create, inline
   screenshot, external model import).
6. Low-priority cleanup (dead cache, orphaned `reports.py`, stale docs) —
   any time, low risk, low effort.
