# Unity 6.4 Capability Delta Analysis

Last updated: 2026-07-01

## Purpose

Cross-reference the bridge's current implementation against (a) what two
prior internal gap reports already flagged, re-verified against HEAD, and
(b) what is genuinely new in Unity 6.4/6.5 relative to the generic Unity 6.x
surface those reports assumed. This is a refresh-and-reconcile pass, not a
from-scratch audit — see Methodology.

Goal stated by the requester: a bridge that can completely control all
exposed features of the Unity Editor.

## Methodology

Two research tracks ran concurrently:

1. **Code-derived inventory** (subagent fork) — regenerated the bridge's
   command/CLI/MCP-tool inventory directly from `src/unity_bridge/commands/`,
   `ClaudeCodeBridge/BridgeCommandRegistry.cs`, `mcp/tools.py`, and
   `mcp/tools_ext.py` as of HEAD, then reconciled every gap item in
   [`phase7-new-gaps-report.md`](phase7-new-gaps-report.md) (2026-04-20) and
   [`unity-bridge-audit-and-gap-analysis.md`](unity-bridge-audit-and-gap-analysis.md)
   (2026-06-09) against current source — classifying each CLOSED / STILL
   OPEN / PARTIAL with file-level evidence.
2. **Web deep-research workflow** (88 sub-agents, 3-vote adversarial
   verification per claim) — resolved what Unity 6.4 actually is and what is
   new in it and the immediately-following 6.5 release, relative to generic
   Unity 6.x, with targeted follow-up on five previously-flagged gap areas
   (script AST editing, APV baking API, per-sample profiler, Memory
   Profiler, Code Coverage package API) and five package-provided Editor
   systems (Shader Graph, VFX Graph, Timeline, Cinemachine, Localization).

Neither prior doc's counts were trusted as current truth — both were stale
(see below) — so the implemented-side list was derived fresh from source,
not from prior documentation.

## 1. Current Bridge Capability Snapshot (corrected counts)

The two prior reports do not reconcile with each other or with HEAD. They
were measuring different things, and both grew since they were written:

| Metric | phase7 (2026-04-20) | audit (2026-06-09) | **Current (HEAD)** |
|---|---|---|---|
| Top-level bridge command-types | 75 | — | **92** |
| C# registered handlers | ~75 | — | **92** (91 unconditional + 1 `#if UNITY_6000_0_OR_NEWER`-gated) |
| CLI subcommands/operations | — | ~240 | **315**, across 68 files |
| CLI command groups | "40+" | — | **~60 sub-app groups + ~25 top-level singular commands** |
| Live MCP tool definitions | ~56 | 94 | **97** (68 in `tools.py` + 29 in `tools_ext.py`) |

The headline finding is that coverage is broad and deep across
hierarchy/scene/prefab, asset/build/package pipelines, all settings
domains, addressables, input system (including authoring), UI Toolkit,
search, cloud project IDs, physics/physics2d, and the Unity-6.4-specific
Phase-0–5 work (object identity, Project Auditor, Entities inspection,
Adaptive Performance, Multiplayer Play Mode, Graph Toolkit). The full
subsystem-by-subsystem inventory is in Appendix A.

**Confirmed absent anywhere in the codebase** (zero grep matches across
`src/unity_bridge/commands/` and `ClaudeCodeBridge/`): Timeline, Cinemachine,
Localization/StringTable, RendererFeature, VolumeProfile, ShaderGraph,
VisualEffectGraph, VisualScripting, ProBuilder, MemoryProfiler/TakeSnapshot/
FrameDataView, SpriteAtlas, per-component-type gizmo/icon toggle
(`AnnotationUtility.SetGizmoEnabled`/`SetIconEnabled`), scoped-registry/
lockfile/outdated package ops, AdaptiveProbeVolume/ProbeReferenceVolume
scripting API, `StartAssetEditing`/`StopAssetEditing` batching, C# script
CRUD/AST-edit handler, base64/multi-angle screenshot return, SHA256
precondition, `externalVersionControl`.

## 2. Phase7 Gap Reconciliation (32 items, 2026-04-20 report)

Of the 6 "Tier 1 — Highest Leverage" items, **5 are now CLOSED**:

| # | Gap | Status |
|---|---|---|
| 20.1 | Unity Search query | **CLOSED** — `search-query` (`search.py:18-77`) |
| 8.4 | Parse NUnit/test results into response | **CLOSED** — `testing.py:465-499` |
| 11.1-11.2 | Physics2D gravity + collision matrix | **CLOSED** — `physics2d.py` |
| 14.1-14.2 | Cloud project/org/environment IDs | **CLOSED** — `cloud_services.py:21-85` |
| 22.2 | Regenerate .sln/.csproj | **CLOSED** — `sync_solution.py:23` |
| 1.2 | Render pipeline asset read/write | **PARTIAL** — list/inspect/assign shipped; deep URP/HDRP field-level editing not separately confirmed |

Tier 2 items also closed since the report: **2.1-2.4 UI Toolkit CRUD**
(UXML/USS/PanelSettings/UIDocument), **9.1-9.3 Input System authoring**
(action-map/binding/control-scheme CRUD), **10.1-10.4 Addressables
profiles/labels/analyze**. **6.2/6.4 asset serialization mode + line
endings** are closed; **6.1 VCS mode** (`externalVersionControl`) remains
open.

**Still firmly open** (verified absent against current source): render
pipeline internals — shader stripping, Renderer Feature list, Volume/
VolumeProfile authoring, shader variant collections (1.1, 1.3-1.7); Shader
Graph / VFX Graph / Visual Scripting (3.x); Timeline & Cinemachine (4.x);
Localization (5.x); scoped registries / package lockfile / outdated check
(7.1, 7.5, 7.6); StateMachineBehaviour / AnimatorOverrideController / Avatar
rig authoring (12.x); Memory Profiler / Frame Debugger / Rendering Debugger
(13.x); Remote Config / Cloud Diagnostics (14.3-14.5); per-component-type
gizmo/icon toggle (19.1-19.2); Sprite slicing / Atlas v2 (17.x); ProBuilder
(21.x); create-script-from-template (22.1).

## 3. Audit-Report Reconciliation (2026-06-09 report)

| HIGH-severity item | Status |
|---|---|
| `CompileCommandHandler` busy-waits on main thread | **CLOSED** — converted to `EditorApplication.update`-driven polling, returns "running" immediately (`CompileCommandHandler.cs:84-217`) |
| Parallel batch mutates concurrently (`transform-operation`/`serialized-property` misclassified) | **CLOSED** — `protocol.py:164-180,210-232` now gates parallel-safety on `parameters.operation`, not just command-type |
| Global `--timeout`/`UNITY_BRIDGE_TIMEOUT` dead for CLI | **PARTIAL** — bridge-level default now honors it (`app.py:59-61`); per-command CLI wrappers still don't thread it through `get_timeout(global_override=...)` |
| Cache `invalidate(pattern)` cannot match command types | **STILL OPEN** — bug reproduced verbatim in current code (`cache.py:76-80,149-169`) |

All five **"Top gap"** capability items from the audit remain open and are
the most material distance from "controls everything the Editor UI can do":
**C# script CRUD + AST edits** (competitor `unity-mcp`'s
`Unity_ApplyTextEdits`/`Unity_ScriptApplyEdits` does this; our bridge's
`MonoScriptCommandHandler.cs` is confirmed read-only), **inline base64 /
multi-angle screenshot return** (renderer exists, only writes to disk),
**per-sample profiler drill-down + Adaptive Probe Volume baking**,
**`execute-script` not exposed as an MCP tool**, **SHA256 concurrent-edit
precondition + `StartAssetEditing` batching**.

## 4. Unity 6.4 / 6.5 Findings (the genuinely new delta)

Unity 6.4 (build `6000.4`) is a confirmed, real, shipped release — launched
March 2026 as an "Update/Supported" release (LTS-equivalent support, not
LTS-branded), immediately following Unity 6.3 LTS and immediately preceding
**Unity 6.5 (`6000.5`, shipped ~June 2026)**. As of today (2026-06-30), 6.4
itself is reportedly reaching end-of-life with users directed to 6.5+ — so
compatibility work should be anchored against **6.5**, not 6.4, going
forward.

### 4.1 Breaking changes to verify against (Unity 6.5)

These are the highest-priority items — not new capabilities, but
compatibility risks that could silently break the bridge on a Unity
upgrade:

| Change | Detail | Action needed |
|---|---|---|
| **InstanceID → EntityId (hard break)** | The `EntityId` type and the deprecation of `InstanceID`-based APIs (warnings only) land in **Unity 6.4**. Unity 6.5 escalates this: obsolete integer-based APIs (`Object.GetInstanceID`, `Resources.InstanceIDToObject`, `Selection.instanceIDs`) become **compilation errors**, not warnings. | The bridge already has an `object-identity` CLI group built specifically for "EntityId/legacy instance ID normalization" (Phase 1 of the 6.4 roadmap), so 6.4 itself should already be warning-clean. **Verify this handler and every other handler that touches `GetInstanceID`/`InstanceIDToObject`/`Selection.instanceIDs` compiles clean against 6.5's hard-error behavior** — this is a real compile-break risk across `ClaudeCodeBridge/*.cs`, not just the dedicated handler. |
| **`AddComponent(string)` removed** | Unity 6.5 removes the legacy string-based `GameObject.AddComponent(string)` overload and obsolete accessors (`GameObject.rigidbody`, `GameObject.camera`, `Component.renderer`). | Grep `ClaudeCodeBridge/` for these patterns before any 6.5 upgrade; `add-component` handler should already use generic `AddComponent(Type)`/reflection, but confirm. |
| **Built-In Render Pipeline deprecated** | Supported through 6.7 LTS lifecycle, but flagged obsolete starting 6.5. | No bridge action required now; informational for any render-pipeline work prioritization. |
| **URP Compatibility Mode fully removed** (6.4) | `URP_COMPATIBILITY_MODE` scripting define removed; Render Graph is now the only path for custom render passes. | Confirm `render-pipeline`/`graphics-state` handlers don't branch on the removed define. |

### 4.2 New capabilities not yet bridged

| Capability | Source | Bridge status |
|---|---|---|
| **Redesigned Rendering Statistics window** — SRP Batcher / GPU Resident Drawer / BatchRendererGroup / GPU instancing metrics (Unity 6.4) | `WhatsNewUnity64.html` | **New gap.** Not covered by `profiler-sample`/`profiler-control` (those wrap `ProfilerDriver` counters, not this window). Candidate new handler or extension. |
| **Scene View Grid Transform** — custom (non-orthogonal) grid position + rotation, "Copy from Active Object" (Unity 6.4) | `WhatsNewUnity64.html`, `CustomizeGrid.html` | **Extends an already-closed gap.** `scene-state` covers move/rotate/scale snap increments (phase7 18.1-18.3, closed) but not full Grid Transform (position+rotation) — verify and extend if absent. |
| **`BuildProfile.CreateBuildProfile`** — new scripting method for programmatic Build Profile creation (Unity 6.5) | `WhatsNewUnity65.html`, ScriptReference | **New gap.** `build-profile-operation` covers existing-profile build/scenes/defines; profile *creation* via this new API is not confirmed present — extend if the handler only operates on pre-existing profiles. |
| **Project Auditor now built-in by default** (no package install required), with rule logic split into a separate `com.unity.project-auditor-rules` package (Unity 6.4) | `WhatsNewUnity64.html`, Project Auditor intro page | **Verify, don't rebuild.** `ProjectAuditorCommandHandler` already exists with "reflection-safe optional API handling for ... com.unity.project-auditor." Confirm it also detects/handles the separate rules package gracefully now that the base feature ships in-Editor. |
| **Adaptive Performance redesigned scaler UI** — add/remove/configure ScriptableObject-based scalers directly in a profile (Unity 6.4) | `WhatsNewUnity64.html` | Bridge's `adaptive-performance` handler is read-only (scaler profile listing). This is primarily an Editor-UI change; underlying scripting API change not confirmed — low priority unless scripting surface is independently verified to have changed. |
| **ECS Core packages** (Entities/Collections/Mathematics/Entities Graphics ship with Editor by default, Unity 6.4) | `WhatsNewUnity64.html` | Packaging change only — bridge's `entities` handler already covers world/system/entity-count inspection with reflection-safe optional handling. No action required. |

### 4.3 Package-provided Editor systems — resolved (follow-up research, 2026-07-01)

Section 4.3 originally left Shader Graph, VFX Graph, Timeline, Cinemachine,
Localization, and Memory Profiler as an open "absence-of-evidence, not a
confirmed negative" finding, because the first research pass only checked
the Editor's generic "What's New" pages, which don't cover package-scoped
API changes. A dedicated follow-up ran primary-source searches directly
against each package's Scripting API reference and changelog
(`docs.unity3d.com/Packages/<id>@<version>/api/...`), with 3-vote
adversarial verification on every central claim. All nine open items are
now resolved with direct evidence:

| Subsystem | Verdict | Evidence |
|---|---|---|
| **Timeline** (`com.unity.timeline`) | **Buildable now — full authoring** | `TimelineAsset.CreateTrack<T>()` (4 overloads incl. parented tracks), `TrackAsset.CreateClip<T>()`/`CreateDefaultClip()`/`GetClips()`/`DeleteClip()`, `PlayableDirector.time` + `.Evaluate()` for scrubbing — all public, stable since package 1.6, present in 1.8.12 (the version bundled with Unity 6.4). Zero claims refuted. |
| **Cinemachine** (`com.unity.cinemachine` 3.x) | **Buildable now — full authoring** | `Unity.Cinemachine.CinemachineCamera` (renamed from `CinemachineVirtualCamera` in 3.x), `Priority`/`PrioritySettings`, `Lens`/`LensSettings`, `Follow`/`LookAt`/`Target`, `GetCinemachineComponent`, `CinemachineBrain` for active-camera/blend introspection. Zero claims refuted (3/3 confirmed each). Full scene enumeration needs a standard hierarchy walk (existing bridge pattern) since `CinemachineCore.GetVirtualCamera` only tracks currently-active cameras. |
| **Localization** (`com.unity.localization`) | **Buildable now — full authoring** | `LocalizationEditorSettings` for Locale/StringTableCollection CRUD, `StringTable.AddEntry`, static `Csv`/`Xliff` classes for import/export. Zero claims refuted. Editor-assembly-only (`UnityEditor.Localization.*`), which is fine for a bridge handler. |
| **Memory Profiler** (core `Unity.Profiling.Memory.MemoryProfiler`, no package needed) | **Buildable now — capture only** | `MemoryProfiler.TakeSnapshot(string path, Action<string,bool> finishCallback, CaptureFlags captureFlags)` confirmed exact (the repo's own speculative citation matched verbatim) — ships with Unity core since at least 6000.0, present through 6.4/6.5. Async/callback-based, writes a `.snap` file. The `com.unity.memoryprofiler` package's *own* namespace was checked and confirmed to contain no capture/load/diff API (only a metadata-tagging helper) — load/diff/compare of existing snapshots remains a genuine capability gap. Batch-mode support is undocumented either way (not confirmed, not denied). |
| **VFX Graph** (`com.unity.visualeffectgraph`) | **Read-only only** | `VisualEffectAsset.GetEvents()`/`GetExposedProperties()` are public and asset-only (no scene/play mode needed) — confirmed against `UnityCsReference` source and ScriptReference, zero claims refuted. True graph authoring (add/remove nodes, systems, blocks) and even system-name enumeration are internal-only or require instantiating a live `VisualEffect` component in a scene. |
| **Shader Graph** (`com.unity.shadergraph`) | **Not implementable** | No public API for node enumeration, property get/set, or compile/save exists across six independent fetches spanning package versions 3.3–17.5. `ShaderGraphImporter` covers only the asset-import pipeline. This is a genuine Unity-side capability gap, not a research shortfall. |
| **Code Coverage** (`com.unity.testtools.codecoverage`) 6.4/6.5 delta | **No bridge changes needed** | The only package release in the 6.4/6.5 window (1.3.0, 2026-01-22) was fixes/behavior-only (removed an unused `CoverageFormat` class, changed `pathFilters` inclusion/exclusion ordering semantics, bug fixes) — zero new flags/formats/hooks. The existing `CodeCoverageCommandHandler.cs`/`code_coverage.py` already cover the stable surface. One follow-up: review whether the bridge's `pathFilters` handling assumes exclusions apply before inclusions, since 1.3.0 changed that ordering. |
| **`Unity.Hierarchy` namespace** (Unity 6.5 core) | **Real, but marginal value for this bridge** | The namespace is real: `Unity.Hierarchy.Editor.HierarchyWindow` (the class behind Unity 6.5's actual shipped Hierarchy window) exposes `SetSearchText()`, `UpdateEditorSelection()`, a `View` property, and customization events. A separate, unrelated generic tree data structure (`Hierarchy`/`HierarchyFlattened`/`HierarchyViewModel`) also exists but is not tied to the real window. `HierarchyWindow` inherits `EditorWindow`, so it needs a live Editor GUI session (consistent with how this bridge already runs, via `EditorApplication.update` — not literal `-batchmode`). Practical verdict: this offers narrow value (search-box/selection-sync on the real window) that the bridge's existing `query-hierarchy`/`get-selection` commands already substantially cover — low priority. |

**What changed from the original (incorrect) assumption**: three subsystems
previously assumed to be permanent "zero coverage" gaps — Timeline,
Cinemachine, Localization — turn out to have full, stable, public authoring
APIs and are genuinely buildable today. Memory Profiler snapshot *capture*
is also buildable (the repo's own speculative API citation was confirmed
exact). Shader Graph is now a **confirmed** dead end rather than an open
question, which matters because it stops future research/build effort
being spent re-litigating it.

## 5. Recommended Priorities

Merging the reconciled phase7/audit backlogs with the new 6.4/6.5 findings,
ranked by leverage:

### P0 — Compatibility risk (do before any Unity version bump)
1. Audit every `GetInstanceID`/`InstanceIDToObject`/`Selection.instanceIDs`
   call site in `ClaudeCodeBridge/*.cs` against the Unity 6.5 hard-error
   change; confirm the `object-identity` handler is the sole/correct
   abstraction point.
2. Grep for `AddComponent(string)` and the removed `GameObject.rigidbody`/
   `GameObject.camera`/`Component.renderer` accessors.

### P0 — Capability (carried over from audit, unchanged by 6.4/6.5)
3. C# script CRUD + AST-aware edits (single largest competitive gap).
4. Inline base64 / multi-angle screenshot return (closes agent visual
   feedback loop; renderer already exists).
5. Fix `cache.py` `invalidate(pattern)` (real bug, reproduced verbatim).

### P1 — New-since-last-audit capability
6. Rendering Statistics window metrics (SRP Batcher/GPU Resident Drawer/
   BatchRendererGroup/GPU instancing) — net-new in 6.4, currently unbridged.
7. `BuildProfile.CreateBuildProfile` — extend `build-profile-operation` to
   create profiles, not just operate on existing ones (6.5 API).
8. Scene View Grid Transform (position+rotation) — extend `scene-state` if
   it doesn't already cover full grid transform, not just snap increments.
9. Harden + MCP-expose `execute-script` as a structured `RunCommand`
   escape hatch (cheapest way to eliminate "not implemented" dead-ends for
   any future Unity API the bridge hasn't dedicated a handler to yet).

### P2 — Package-provided Editor systems (resolved by follow-up research, §4.3)
10. **Buildable now — build these**: `timeline-operation` (create-track,
    create-clip, get-clips, delete-clip, director time/evaluate),
    `cinemachine-operation` (camera CRUD, priority, lens, follow/lookat,
    brain/blend introspection via existing hierarchy-walk pattern for full
    scene enumeration since `CinemachineCore` only tracks active cameras),
    `localization-operation` (locale CRUD, string-table-collection CRUD,
    string entry add/update, CSV/XLIFF import-export), and a
    `memory-profiler` command wrapping the confirmed-exact
    `Unity.Profiling.Memory.MemoryProfiler.TakeSnapshot` (capture only —
    load/diff of existing `.snap` files has no public API and stays a gap).
11. **Buildable now, narrow scope**: `vfx-asset-info` — read-only, exposing
    only `VisualEffectAsset.GetEvents()`/`GetExposedProperties()`. Do not
    attempt VFX graph authoring or system-name enumeration (would require
    instantiating a scene GameObject — a heavier pattern needing separate
    design sign-off).
12. **Confirmed not implementable — stop researching**: Shader Graph. No
    public node/property/compile API exists at any checked version
    (3.3–17.5). Documented here so future passes don't re-spend budget.
13. **Low priority / marginal value**: `Unity.Hierarchy` namespace
    (`HierarchyWindow.SetSearchText`/`UpdateEditorSelection`) — real API,
    but duplicates value the bridge's existing `query-hierarchy`/
    `get-selection` commands already provide; only worth building if a
    concrete need for hierarchy-window search-box/selection-sync surfaces.
14. **No action**: Code Coverage — the only 6.4/6.5-window package release
    (1.3.0) was fixes-only; existing handler already covers the stable
    surface. One follow-up code-review item: verify the bridge's
    `pathFilters` handling against 1.3.0's inclusion/exclusion ordering
    change.
15. Per-sample Profiler drill-down (`HierarchyFrameDataView`/
    `RawFrameDataView`) and Adaptive Probe Volume baking scripting API —
    still confirmed absent from Unity itself as of 6.4/6.5 (unchanged from
    §4.1); revisit only if/when Unity ships first-party APIs for these.

## Appendix A: Current Bridge Capability Inventory (source-derived)

Subsystem → CLI group(s) → bridge command-type(s) → C# handler → Unity API.
Produced by reading `src/unity_bridge/commands/*.py`,
`ClaudeCodeBridge/BridgeCommandRegistry.cs`, and every
`*CommandHandler.cs` against HEAD (`83f6b1c`, branch
`codex/improve-unity-bridge-skill`).

| Subsystem | CLI group(s) | Bridge command-type | C# handler | Operations (sample) | Unity API |
|---|---|---|---|---|---|
| Hierarchy/GameObject | hierarchy, component, select, prefs (gameobject-utility) | query-hierarchy, get/set-component-data, add/remove-component, component-toggle/copy/reset, gameobject-utility, get/set-selection | `QueryHierarchyCommandHandler`, `*ComponentData*Handler`, `AddComponentCommandHandler`, `RemoveComponentCommandHandler`, `ComponentToggle/Copy/ResetCommandHandler`, `GameObjectUtilityCommandHandler`, `SelectionCommandHandler` | full CRUD + missing-script find, static flags | `GameObject`, `Component`, `Selection` |
| Scene | scene, scene-ext, scene-template, scene-view, scene-state | scene-operation, scene-setup-operation, scene-template, scene-view, scene-state | `SceneOperationCommandHandler`, `SceneSetupCommandHandler`, `SceneTemplateCommandHandler`, `SceneViewCommandHandler`, `SceneStateCommandHandler` | load/save/create/additive, multi-scene layouts, snap/grid/gizmo/overlay state | `EditorSceneManager`, `SceneView`, `EditorSnapSettings` |
| Prefab | prefab, undo (prefab-override) | prefab-operation, validate-prefab, prefab-override | `PrefabOperationCommandHandler`, `ValidatePrefabCommandHandler`, `PrefabOverrideCommandHandler` | instantiate, validate, list/apply/revert overrides, unpack | `PrefabUtility` |
| Transform/Property | transform, property | transform-operation, serialized-property | `TransformCommandHandler`, `SerializedPropertyCommandHandler` | get/set position/rotation/scale/parent/sibling, generic SerializedProperty get/set | `Transform`, `SerializedObject` |
| Materials/Shaders | material, shader | material-operation, shader-inspection | `MaterialOperationCommandHandler`, `ShaderInspectionCommandHandler` | set properties/keywords, list keywords/errors/properties | `Material`, `Shader` |
| Animation | animator, animation-clip | animator-operation, animation-clip | `AnimatorOperationCommandHandler` (+layer/state/transition/parameter partials), `AnimationClipCommandHandler` | layers/states/transitions/params CRUD; clip CRUD | `AnimatorController`, `AnimationClip` — no StateMachineBehaviour add/remove, no AnimatorOverrideController, no Avatar/Humanoid rig |
| Assets | asset, asset-ext | asset-operation, asset-extended-operation | `AssetOperationCommandHandler`, `AssetExtendedCommandHandler`/Helpers | find/query, create/delete/copy/move, deps, guid, folder mgmt, export/import package | `AssetDatabase` — no C# script-file create/edit (`MonoScriptCommandHandler.cs` confirmed read-only) |
| Import pipeline | import-settings, compile | import-settings-operation, compilation-pipeline, compile | `ImportSettingsCommandHandler`/Helpers, `CompilationPipelineCommandHandler`, `CompileCommandHandler` | reimport, bulk import, templates; assemblies/defines query; trigger+wait compile | `AssetImporter`, `CompilationPipeline` |
| Build | build, profile | build-operation, build-profile-operation | `BuildOperationCommandHandler`/Helpers, `BuildPlatformOperations`, `BuildProfileBuildHelpers` | trigger/settings/validate/get-target, subtarget (Server/Player), Build Profile build-by-profile | `BuildPipeline`, `BuildProfile` |
| Package management | package | package-operation | `PackageManagerCommandHandler` | list/search/add/remove/info/embed/resolve, tarball pack | `PackageManager.Client` — no scoped-registry add/list, no lockfile/outdated check |
| Testing | test, coverage | run-tests, cancel-tests, list-tests, code-coverage | `RunTestsCommandHandler`, `CancelTestsCommandHandler`, `TestListCommandHandler`, `CodeCoverageCommandHandler` | run/cancel/list tests; durable result-artifact read; coverage availability/install/start/pause/resume/stop/find-reports/summarize | `TestRunnerApi`, `com.unity.testtools.codecoverage` |
| Console/Diagnostics | console, status/doctor | read-console, clear-console, console-log, health-check | `ReadConsoleCommandHandler`, `ClearConsoleCommandHandler`, `ConsoleLogCommandHandler`, `BridgeStatusCommandHandler` | read/clear/log, health/doctor | `Debug`, `LogEntries` |
| Profiler | profiler-control | profiler-sample, profiler-control | `ProfilerSampleCommandHandler`, `ProfilerControlCommandHandler` | aggregate counters; save/load/`ProfilerDriver` control | `ProfilerDriver` — no `HierarchyFrameDataView`/`RawFrameDataView`, no Memory Profiler `TakeSnapshot` |
| Lighting | lightmap | lightmap-operation | `LightmapOperationCommandHandler`/Models/Helpers | bake/cancel/clear/status/settings | `Lightmapping` (legacy bake only) — no Adaptive Probe Volume API |
| Rendering | render-pipeline, graphics-state, graphics-settings | render-pipeline, graphics-state, graphics-settings | `RenderPipelineCommandHandler`, `GraphicsStateCommandHandler`, `GraphicsSettingsCommandHandler` | list/inspect/assign RP assets; GraphicsStateCollection create/load/trace/save/warmup; SRP-batcher/transparency sort | `RenderPipelineAsset`, `GraphicsStateCollection`, `GraphicsSettings` — no RendererFeature/VolumeProfile/shader-stripping-list exposure |
| Physics | physics, physics2d | physics-config, physics2d-config | `PhysicsConfigCommandHandler`, `Physics2DConfigCommandHandler` | 3D gravity/solver/layer matrix; 2D gravity + collision matrix | `Physics`, `Physics2D` — joint editing still absent |
| Quality/Settings | quality, settings, time-settings, audio-settings, environment-settings, editor-config, prefs | quality-settings, player-settings-operation, time-settings, audio-settings, environment-settings, editor-config, editor-prefs | `QualitySettingsCommandHandler`, `PlayerSettingsCommandHandler`/Helpers, `TimeSettingsCommandHandler`, `AudioSettingsCommandHandler`, `EnvironmentSettingsCommandHandler`, `EditorConfigCommandHandler`, `EditorPrefsCommandHandler` | full settings read/write incl. `serializationMode`, `lineEndingsForNewScripts` — no `externalVersionControl` exposure | various |
| Tags/Layers | tags, layers, sorting-layers | tags-layers | `TagsLayersCommandHandler` | CRUD on tags/layers/sorting layers | `TagManager` |
| NavMesh/Terrain/Occlusion/Reflection | navmesh, terrain, occlusion, reflection-probe | navmesh-operation, terrain-operation, occlusion-culling, reflection-probe | `NavMeshCommandHandler`, `TerrainCommandHandler`, `OcclusionCullingCommandHandler`, `ReflectionProbeCommandHandler` | bake/query, terrain ops, occlusion bake, probe CRUD | `NavMeshBuilder`, `TerrainData`, `StaticOcclusionCulling`, `ReflectionProbe` |
| Addressables/Tilemap | addressables, tilemap | addressables, tilemap-operation | `AddressablesCommandHandler`/AdvancedHelpers, `TilemapCommandHandler` | groups/build/clean-cache/mark/set-address plus profiles, labels, analyze | `AddressableAssetSettings` — group-schema CRUD and content-update/catalog ops still open |
| Input System | input-system | input-system | `InputSystemCommandHandler` | list-actions/get-action-map/export/import plus add-action-map, add-binding (interactions/processors), add-control-scheme | `InputActionAsset` |
| UI Toolkit | ui-toolkit | ui-toolkit | `UIToolkitCommandHandler` | create-panel-settings, UXML/USS/UIDocument ops | `VisualElement`, `PanelSettings`, `UIDocument` |
| Search | search | search-query | `SearchQueryCommandHandler` | query, providers | `SearchService` |
| Cloud/Services | cloud | cloud-services | `CloudServicesCommandHandler` | project-id, environments, active-environment | `CloudProjectSettings` — Remote Config/Cloud Diagnostics still open |
| Sync/Scripting tools | sync-solution, scripting | sync-solution, execute-script | `SyncSolutionCommandHandler`, `ExecuteScriptCommandHandler` | regenerate .sln/.csproj; arbitrary C# expression eval | `SyncVS.SyncSolution`, `Mono.CSharp.Evaluator` — `execute-script` confirmed CLI-only, no MCP tool |
| Unity 6.4 packages | object-identity, project-auditor, entities, adaptive-performance, multiplayer-playmode, graph-toolkit | object-identity, project-auditor, entities, adaptive-performance, multiplayer-playmode, graph-toolkit | `ObjectIdentityCommandHandler`, `ProjectAuditorCommandHandler`, `EntitiesCommandHandler`, `AdaptivePerformanceCommandHandler`, `MultiplayerPlayModeCommandHandler`, `GraphToolkitCommandHandler` | EntityId/instance-id normalization, Project Auditor run/export/diff/fix, Entities world/system/entity inspection, Adaptive Performance scaler profiles, MPPM read-only, graph asset inspect/export | reflection-safe optional-package handling confirmed for Entities/Adaptive Performance |
| Window/Clipboard/Preset/Deep-serialize | window, clipboard, preset, deep-serialize, script-info | window-management, clipboard, preset-operation, deep-serialize, script-info | `WindowCommandHandler`, `ClipboardCommandHandler`, `PresetCommandHandler`, `DeepSerializeCommandHandler`, `MonoScriptCommandHandler` | list/open/focus/close windows; read/write clipboard; preset CRUD; full EditorJsonUtility serialize; MonoScript info (read-only) | — |

**Confirmed absent anywhere in source** (grep-verified zero matches across
`src/unity_bridge/commands/` and `ClaudeCodeBridge/`): `Timeline`,
`Cinemachine`, `Localization`/`StringTable`, `RendererFeature`,
`VolumeProfile`, `ShaderGraph`, `VisualEffectGraph`, `VisualScripting`,
`ProBuilder`, `MemoryProfiler`/`TakeSnapshot`/`FrameDataView`,
`SpriteAtlas`, per-component-type gizmo/icon toggle, scoped-registry/
lockfile/outdated package ops, `AdaptiveProbeVolume`/`ProbeReferenceVolume`,
`StartAssetEditing`/`StopAssetEditing` batching, script-CRUD/AST-edit
handler, base64/multi-angle screenshot return, SHA256 precondition,
`externalVersionControl`.
