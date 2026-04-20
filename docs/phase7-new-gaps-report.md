# Phase 7 Adversarial Gap Report: New Unity Editor Parity Gaps

**Date:** 2026-04-20
**Reviewer:** Adversarial audit pass
**Baseline:** Phase 5 + Phase 6a-6e (shipped). All gaps in
[`phase4-adversarial-gap-report.md`](phase4-adversarial-gap-report.md) are
considered tracked and excluded from this document.
**Standard:** If a human can do it through the Unity Editor UI (Unity 6.x),
the CLI should be able to do it too.
**Method:** Walk every Editor menu, window, inspector panel, project-settings
page, package-window feature, and built-in tool against the ~75 existing
bridge handlers and the 56 entries in
`TOOL_COMMAND_MAP` + `TOOL_COMMAND_MAP_EXT`. Any capability the Editor
exposes but the CLI cannot reach, and that was not flagged in the
Phase 4 report, is a new gap.

---

## Table of Contents

1. [Summary](#summary)
2. [New Gaps By Subsystem](#new-gaps-by-subsystem)
   1. [Rendering & Graphics Pipeline](#1-rendering--graphics-pipeline)
   2. [UI Toolkit / UXML / UI Builder](#2-ui-toolkit--uxml--ui-builder)
   3. [Visual Scripting, Shader Graph, VFX Graph](#3-visual-scripting-shader-graph-vfx-graph)
   4. [Timeline & Cinemachine](#4-timeline--cinemachine)
   5. [Localization](#5-localization)
   6. [Version Control & Asset Serialization](#6-version-control--asset-serialization)
   7. [Package Manager: Advanced Flows](#7-package-manager-advanced-flows)
   8. [Test Runner: Coverage & Reporting](#8-test-runner-coverage--reporting)
   9. [Input System (Package): Bindings & Control Schemes](#9-input-system-package-bindings--control-schemes)
   10. [Addressables: Profiles, Labels, Analyze](#10-addressables-profiles-labels-analyze)
   11. [Physics 2D & Joint Editors](#11-physics-2d--joint-editors)
   12. [Animation: State Machine Behaviours & Avatar](#12-animation-state-machine-behaviours--avatar)
   13. [Rendering Debugger, Memory Profiler, Frame Debugger](#13-rendering-debugger-memory-profiler-frame-debugger)
   14. [Unity Services & Cloud](#14-unity-services--cloud)
   15. [Editor Preferences & User Settings](#15-editor-preferences--user-settings)
   16. [Build Pipeline: Incremental, Reports, Post-processors](#16-build-pipeline-incremental-reports-post-processors)
   17. [Sprite / 2D Workflows](#17-sprite--2d-workflows)
   18. [Snap, Grid & Alignment](#18-snap-grid--alignment)
   19. [Gizmos & Editor Overlays](#19-gizmos--editor-overlays)
   20. [Search & Quick Search (Unity Search API)](#20-search--quick-search-unity-search-api)
   21. [ProBuilder / Polybrush](#21-probuilder--polybrush)
   22. [Scripting / Code Editor Integration](#22-scripting--code-editor-integration)
3. [Recommended Phase 7 Priorities](#recommended-phase-7-priorities)
4. [Appendix: Cross-Reference of Existing Coverage](#appendix-cross-reference-of-existing-coverage)

---

## Summary

Phases 5-6 closed the high-frequency gaps called out in Phase 4 (primitive
creation, component toggle/remove/reset/copy, PlayerSettings expansion,
platform switching, build options, NavMesh, lightmap settings, reflection
probes, terrain, addressables, tilemap, scene/game view, profiler control,
animation clip, execution order, find references, assembly reload lock,
preset, scene template, input system basics, window management, monoscript,
etc.).

What remains falls into three categories:

1. **Render pipeline configuration** — URP/HDRP assets, Render Graph,
   Volume Framework, SRP Batcher, Render Graph debugger, shader stripping.
2. **Package-provided Editor features** — UI Toolkit, Shader Graph, VFX
   Graph, Visual Scripting, Timeline, Cinemachine, Localization, Memory
   Profiler, Code Coverage, Input System bindings, Addressables profiles.
   Most are accessed through custom Editor windows that the bridge has no
   hooks into.
3. **Specialized workflows** — VCS, build reports, search API, frame
   debugger, gizmo/overlay visibility, snap/grid, physics 2D matrix and
   joint editors, Avatar / Humanoid rig authoring.

This report enumerates **32 new gaps** across 22 subsystems. Each includes
relevance, implementation complexity, and a proposed command type name.

---

## New Gaps By Subsystem

Columns:
- **Freq** = how often a typical Unity developer uses the feature.
- **Value** = automation/agent value (daily scripting > rare one-offs).
- **Complexity** = rough implementation cost on the bridge side
  (`simple` = dictionary/property extension, `medium` = new handler with
  known API, `complex` = requires domain expertise or package-specific API
  reflection).

---

### 1. Rendering & Graphics Pipeline

Phase 6 shipped `graphics-settings` covering `defaultRenderPipeline`,
`transparencySortMode`, and SRP batching. That is a thin slice of the
Graphics project-settings page and nothing from URP/HDRP asset editors.

| # | Gap | Freq | Value | Complexity | Proposed command |
|---|---|---|---|---|---|
| 1.1 | **Shader stripping configuration** (`GraphicsSettings.currentRenderPipeline`, always-included shaders list, preloaded shader variant collections) | weekly | high | medium | `graphics-settings set-stripping` or extend `graphics-settings` |
| 1.2 | **Render pipeline asset editing** (read/write fields on URP `UniversalRenderPipelineAsset` and HDRP `HDRenderPipelineAsset` — MSAA, HDR, shadow distance, SRP features) | weekly | high | medium | `render-pipeline-asset` (new handler, reflection over the active RP asset type) |
| 1.3 | **Renderer Feature list** (URP `ScriptableRendererFeature` — add/remove/reorder/toggle) | weekly | high | complex | `renderer-feature` (new handler) |
| 1.4 | **Volume / Volume Profile authoring** (Global/Local volume GameObjects + VolumeProfile assets with component overrides for bloom, tonemapping, color adjustments, DoF, motion blur) | daily for artists | high | complex | `volume-operation` (bake CRUD on VolumeProfile + override state) |
| 1.5 | **Color Space Validation / Color Gamut** (`PlayerSettings.colorGamuts`, HDR output settings) | rarely | medium | simple | Extend `player-settings-operation` |
| 1.6 | **Preloaded shader variants + ShaderVariantCollection** (save/load .shadervariants assets) | rarely | medium | medium | Extend `shader-inspection` with `variant-collection` ops |
| 1.7 | **Always-included shaders** (`GraphicsSettings.GetGraphicsSettings()` serialized list) | rarely | medium | medium | Extend `graphics-settings` |

**Why it matters:** URP/HDRP are the default pipelines for new Unity 6
projects. An agent cannot tune a project's visual budget (shadow cascades,
MSAA, SRP batcher) without these hooks — it's forced into
`execute-menu-item` and `serialized-property` round-trips that are fragile
because the asset GUIDs and property names change per pipeline version.

---

### 2. UI Toolkit / UXML / UI Builder

UI Toolkit is Unity's forward-looking UI system (both Editor and runtime).
Zero coverage today. The Phase 4 report only mentioned uGUI primitive
creation (`Canvas`, `Button`, `Image`), which is addressed by
`unity_create_primitive`.

| # | Gap | Freq | Value | Complexity | Proposed command |
|---|---|---|---|---|---|
| 2.1 | **Create / edit UXML documents** (read, write, validate `.uxml` markup) | weekly | high | medium | `ui-toolkit` with `get-uxml`/`set-uxml`/`validate` ops |
| 2.2 | **Create / edit USS stylesheets** (CSS-like `.uss` authoring) | weekly | high | simple | `ui-toolkit` with `get-uss`/`set-uss` ops |
| 2.3 | **Create UIDocument GameObject** (ties VisualTreeAsset + PanelSettings into a scene GO) | weekly | high | simple | Extend `create-primitive` or add `ui-document` op |
| 2.4 | **PanelSettings asset CRUD** (scale mode, reference resolution, theme, sort order) | weekly | medium | simple | Extend `asset-extended-operation` or `ui-toolkit` |
| 2.5 | **ThemeStyleSheet + Editor theme** (light/dark theme style sheets) | rarely | low | medium | `ui-toolkit theme` op |
| 2.6 | **Query runtime UI Toolkit hierarchy** (VisualElement tree of a live UIDocument, similar to `query-hierarchy` for GOs) | weekly | high | complex | `query-visual-tree` |

**Why it matters:** Unity 6 defaults to UI Toolkit for all new Editor
windows, and more runtime HUDs are migrating. Agents building or
refactoring UI have no path today other than dropping raw text into asset
files, which bypasses the validation / reimport pipeline and risks
schema-invalid UXML.

---

### 3. Visual Scripting, Shader Graph, VFX Graph

All three are node-graph assets shipped as first-party Unity packages.
Phase 4 flagged "Create Shader Graph file" but only as asset creation.
None of the graph-editing APIs are reachable.

| # | Gap | Freq | Value | Complexity | Proposed command |
|---|---|---|---|---|---|
| 3.1 | **Shader Graph: read / list nodes** (dump node graph as JSON, inspect inputs/outputs, find references to a subgraph) | weekly | medium | complex | `shader-graph` with `get-info`, `list-nodes` |
| 3.2 | **Shader Graph: set exposed property default** | weekly | medium | medium | Extend `shader-graph` |
| 3.3 | **Shader Graph: compile / save** (trigger regeneration, surface compile errors distinct from shader errors) | weekly | medium | medium | `shader-graph compile` (could extend `shader-inspection errors`) |
| 3.4 | **VFX Graph: read effect graph** (list systems, events, attributes, expose properties) | weekly for VFX artists | medium | complex | `vfx-graph` |
| 3.5 | **VFX Graph: set exposed property / trigger event from CLI** (useful for test harnesses) | weekly | medium | complex | Extend `vfx-graph` |
| 3.6 | **Visual Scripting: list ScriptGraphAsset / StateGraphAsset**, validate, regenerate | rarely | low | complex | `visual-scripting` |

**Why it matters:** A large share of Unity projects use Shader Graph for
all materials. Agents doing bulk material refactoring (e.g., swap a shader
property across 200 materials) cannot because neither the source graph
nor its generated variants are introspectable.

**Implementation note:** These all require the `com.unity.shadergraph`,
`com.unity.visualeffectgraph`, `com.unity.visualscripting` packages to
be present. The handlers should detect the package via
`UnityEditor.PackageManager.Client` and return a graceful
`feature_not_installed` response when absent, not a compile error.

---

### 4. Timeline & Cinemachine

Both are packages (`com.unity.timeline`, `com.unity.cinemachine`) shipped
as part of Unity's default authoring workflow for cutscenes and gameplay
cameras. Phase 4 flagged Timeline asset creation only. Phase 5/6 did not
touch these.

| # | Gap | Freq | Value | Complexity | Proposed command |
|---|---|---|---|---|---|
| 4.1 | **Timeline: query tracks and clips** (list tracks, per-clip in/out/asset reference) | weekly | medium | medium | `timeline get-info` |
| 4.2 | **Timeline: add track / clip**, set clip asset / duration, remove | weekly | medium | complex | `timeline` CRUD |
| 4.3 | **Timeline: evaluate at time** (scrub to a given time programmatically for screenshot tests) | weekly | high | medium | `timeline evaluate` (calls `PlayableDirector.Evaluate` after `time = t`) |
| 4.4 | **Cinemachine: list virtual cameras in scene**, read priority/lens/body/aim parameters | weekly | medium | medium | `cinemachine list` / `get-info` |
| 4.5 | **Cinemachine: set virtual camera priority / active** (drive camera blending from tests) | weekly | high | simple | `cinemachine set-priority` |

**Why it matters:** Tests and regression screenshots often need to
"trigger cutscene X, wait 3s, capture frame." Today that requires
`execute-expression` with embedded C# via the scripting handler, which is
far more brittle than a dedicated tool.

---

### 5. Localization

Unity's `com.unity.localization` package is the standard for i18n. Zero
coverage.

| # | Gap | Freq | Value | Complexity | Proposed command |
|---|---|---|---|---|---|
| 5.1 | **List Locales** (`LocalizationSettings.AvailableLocales`) | weekly | medium | simple | `localization list-locales` |
| 5.2 | **Add / remove Locale** | rarely | low | simple | Extend above |
| 5.3 | **List / read String Table entries** (StringTable + SmartFormat metadata) | weekly | medium | medium | `localization string-table` |
| 5.4 | **Set / add String Table entry** (add key, set translation per locale) | weekly | high | medium | Extend above |
| 5.5 | **Export / import CSV or XLIFF** (`LocalizationEditorSettings.*`) | weekly | medium | medium | `localization export-csv` / `import-csv` |
| 5.6 | **Set active Locale at runtime for screenshot pipelines** | weekly | medium | simple | `localization set-locale` |

**Why it matters:** Adding a new language is a multi-step Editor workflow
(create Locale, create String Table for each asset collection, add keys).
Agents doing "add Spanish to this project" have to execute menu items and
then hand-author JSON.

---

### 6. Version Control & Asset Serialization

Phase 4 mentioned VCS settings but none were implemented. Unity 6 has VCS
mode ("Visible Meta Files" vs "Hidden"), Perforce/Plastic integration, and
`ForceSerialization` helpers. Deep serialize exists but VCS is separate.

| # | Gap | Freq | Value | Complexity | Proposed command |
|---|---|---|---|---|---|
| 6.1 | **VCS mode** (`EditorSettings.externalVersionControl` — "Visible Meta Files" / "Hidden Meta Files" / "Perforce") | rarely | medium | simple | Extend `editor-config` |
| 6.2 | **Asset serialization mode** (`EditorSettings.serializationMode` — ForceText/ForceBinary/Mixed). Phase 4 claimed this is in `editor-config`, but current schema only lists it read-only for some paths — verify. | weekly | high | simple | Verify + expose on `editor-config set` |
| 6.3 | **Force-save all assets** (`AssetDatabase.SaveAssets()` + `SaveAssetIfDirty`) after a serialization mode switch | weekly | high | simple | Extend `refresh-assets` with `save-all` op |
| 6.4 | **Line endings enforcement** (`EditorSettings.lineEndingsForNewScripts`). Phase 4 lists this, but only on read; ensure writable. | rarely | low | simple | Verify on `editor-config set` |
| 6.5 | **ForceReserialize subset** (re-save a filtered set of assets, e.g. all `.prefab` to migrate formats) — different from `reimport-all` | rarely | medium | medium | Extend `deep-serialize` |

**Why it matters:** Cross-platform repos need deterministic text
serialization; CI agents that set up a project from a fresh clone must
force-reserialize. Today there's no atomic command for
"change-mode-then-reserialize."

---

### 7. Package Manager: Advanced Flows

`package-operation` covers list/search/add/remove/info/embed/resolve. The
UPM window does more.

| # | Gap | Freq | Value | Complexity | Proposed command |
|---|---|---|---|---|---|
| 7.1 | **List scoped registries / add scoped registry** (`PackageManager.Client.AddScopedRegistry`) — needed for OpenUPM, internal feeds | weekly | high | simple | Extend `package-operation` with `scoped-registry-*` |
| 7.2 | **Enable / disable preview packages** (`PackageManager.Client.PackageListOptions.includePrereleases` + UPM manifest `enableLockFile`) | rarely | medium | simple | Extend `package-operation` |
| 7.3 | **Git URL packages** (add a package from a git URL, with specific branch/ref/subfolder) — current `add` may or may not support this; confirm | weekly | high | simple | Confirm / expose in `package-operation add` |
| 7.4 | **Local / tarball packages** (add from local folder or `.tgz`) | weekly | medium | simple | Confirm / expose |
| 7.5 | **Package lock file inspection** (read `Packages/packages-lock.json` resolved graph) | weekly | medium | simple | Extend `package-operation` with `lockfile` op |
| 7.6 | **UPM update check** (list packages with newer versions available via `PackageInfo.versions.latestCompatible`) | weekly | high | simple | `package-operation outdated` |

---

### 8. Test Runner: Coverage & Reporting

Phase 4 covered run-tests/list-tests and partial test results. Code
coverage package (`com.unity.testtools.codecoverage`) and nunit XML report
handling are missing.

| # | Gap | Freq | Value | Complexity | Proposed command |
|---|---|---|---|---|---|
| 8.1 | **Enable / disable code coverage recording** (Coverage package API: `Coverage.enabled`, `Coverage.StartRecording()`) | weekly | high | medium | `code-coverage` handler |
| 8.2 | **Generate coverage HTML / OpenCover XML report** (`CodeCoverage.GenerateReport()`) | weekly | high | medium | Extend `code-coverage` |
| 8.3 | **Coverage filters** (include/exclude assemblies or paths) | weekly | medium | simple | Extend `code-coverage` |
| 8.4 | **Parse NUnit result XML from last run** (expose it as JSON on `unity_run_tests` return). Phase 4 gap "get test results after a run" was not fully addressed. | daily | high | simple | Extend `run-tests` result payload |
| 8.5 | **Per-test retry on failure** flag (useful for flaky tests in CI) | weekly | medium | medium | Extend `run-tests` params |
| 8.6 | **Run tests in a specific scene** (`PlayMode` tests with scene context) | rarely | medium | medium | Extend `run-tests` |

---

### 9. Input System (Package): Bindings & Control Schemes

`input-system` handler covers list-actions, get-action-map, export,
import. It does not cover creation or binding edits.

| # | Gap | Freq | Value | Complexity | Proposed command |
|---|---|---|---|---|---|
| 9.1 | **Create / rename / delete Action Map** | weekly | high | simple | Extend `input-system` with `action-map-*` |
| 9.2 | **Create / delete Action** inside a map | weekly | high | simple | Extend `input-system` with `action-*` |
| 9.3 | **Add / remove / edit Binding path** (e.g., `<Gamepad>/leftStick`, composite bindings) | weekly | high | medium | `input-system binding-*` |
| 9.4 | **Control Schemes** (add Gamepad/Keyboard&Mouse/Touch scheme, set required devices) | weekly | medium | medium | `input-system scheme-*` |
| 9.5 | **Processors / Interactions** on bindings (Deadzone, Hold, Press, Tap) | weekly | medium | medium | Extend `input-system binding-*` |
| 9.6 | **Legacy Input Manager axes** (`InputManager.asset` — only legacy Input). Phase 4 flagged this; confirm still missing. | rarely | low | medium | `input-legacy` |

---

### 10. Addressables: Profiles, Labels, Analyze

`unity_addressables` covers list-groups/build/clean-cache/mark/set-address.
The Addressables Groups window + Analyze window expose far more.

| # | Gap | Freq | Value | Complexity | Proposed command |
|---|---|---|---|---|---|
| 10.1 | **Profile management** (list profiles, create, set active, set profile variable) | weekly | high | medium | Extend `addressables profile-*` |
| 10.2 | **Labels** (list all labels, add/remove label on entry, rename) | weekly | medium | simple | Extend `addressables label-*` |
| 10.3 | **Group schemas / bundled asset group CRUD** (create new group, change schema, set build path, bundle mode) | weekly | high | medium | Extend `addressables group-*` |
| 10.4 | **Analyze rules** (Fix Duplicate Bundle Dependencies, Check Bundle Size) | weekly | high | complex | `addressables analyze` |
| 10.5 | **Update a Previous Build** / catalog operations (`ContentUpdateScript.BuildContentUpdate`) | weekly | medium | medium | Extend `addressables update-*` |
| 10.6 | **Play Mode Script selection** (Use Asset Database / Simulate Groups / Use Existing Build) | daily when iterating | high | simple | Extend `addressables set-playmode` |

**Why it matters:** Addressables is the de-facto asset delivery system.
Phase 6 landed only the naming/build parts. Profiles and labels are where
the real workflow lives and they're gated behind the Groups window UI.

---

### 11. Physics 2D & Joint Editors

`physics-config` handles 3D gravity, solver, and the 32x32 layer collision
matrix. 2D physics has its own settings and a separate matrix.

| # | Gap | Freq | Value | Complexity | Proposed command |
|---|---|---|---|---|---|
| 11.1 | **Physics2D gravity, sleep threshold, angular/linear drag defaults** (`Physics2D.gravity`, `defaultContactOffset`, `velocityThreshold`) | weekly | high | simple | `physics2d-config` (new) or extend `physics-config` with `dimension: "2d"` |
| 11.2 | **Physics2D layer collision matrix** (separate from 3D) | weekly | high | simple | Same as above |
| 11.3 | **Job system / multi-threaded physics toggles** (`Physics.autoSyncTransforms`, `Physics.autoSimulation`, `Physics2D.simulationMode`) | rarely | medium | simple | Extend `physics-config` |
| 11.4 | **Joint editing** (Configure `HingeJoint`/`SpringJoint`/`ConfigurableJoint` limits, drive, etc. via typed API, not raw SerializedProperty) | weekly | medium | medium | `joint-operation` |

---

### 12. Animation: State Machine Behaviours & Avatar

`animator-operation` covers layers/states/transitions/parameters. Two
gaps remain from the Phase 4 list that weren't actually addressed (the
report mentioned them but they are still not present), plus Avatar which
Phase 4 did not list.

| # | Gap | Freq | Value | Complexity | Proposed command |
|---|---|---|---|---|---|
| 12.1 | **Add / remove StateMachineBehaviour** on an Animator State (e.g., add a custom `StateMachineBehaviour` subclass) | weekly | medium | medium | Extend `animator-operation` with `add-behaviour`/`remove-behaviour` |
| 12.2 | **AnimatorOverrideController** (create, set override pairs) | weekly | medium | medium | `animator-override` |
| 12.3 | **Avatar / Humanoid rig configuration** (set rig type Humanoid/Generic/Legacy on `.fbx`, configure muscles, set avatar definition) | weekly | high | complex | `avatar-rig` |
| 12.4 | **Avatar Mask creation** (include body parts per layer) | weekly | medium | medium | `avatar-mask` |
| 12.5 | **IK settings per layer** (`AnimatorController.layers[i].iKPass`) | rarely | low | simple | Extend `animator-operation` |

---

### 13. Rendering Debugger, Memory Profiler, Frame Debugger

The Memory Profiler *package* (`com.unity.memoryprofiler`) provides
snapshot capture and diff — different from the built-in Profiler's memory
module. Frame Debugger captures a single frame's draw calls.

| # | Gap | Freq | Value | Complexity | Proposed command |
|---|---|---|---|---|---|
| 13.1 | **Memory Profiler snapshot capture** (package API: `MemoryProfiler.TakeSnapshot()`), save to `.snap` | weekly | high | medium | `memory-profiler take-snapshot` |
| 13.2 | **Memory snapshot diff / compare two .snap files** | weekly | high | complex | Extend `memory-profiler diff` |
| 13.3 | **Frame Debugger enable + capture** (`FrameDebuggerUtility.SetEnabled(true)`, step through events, dump current event info) | weekly | medium | complex | `frame-debugger` |
| 13.4 | **Rendering Debugger panels** (URP/HDRP `DebugManager.instance` — set LOD, wireframe, shadow cascade visualization). This is the F10 runtime overlay. | rarely | medium | medium | `rendering-debugger` |

---

### 14. Unity Services & Cloud

Unity offers Cloud Build, Collaborate (deprecated), Cloud Diagnostics,
Analytics, Ads, IAP, Remote Config, Cloud Code, Authentication. All via
`com.unity.services.*` packages.

| # | Gap | Freq | Value | Complexity | Proposed command |
|---|---|---|---|---|---|
| 14.1 | **Get Unity project ID / organization ID / environment ID** (`CloudProjectSettings`) | weekly | high | simple | `services-config get-project-id` |
| 14.2 | **List linked environments and set active environment** (Unity Cloud Dashboard environments) | weekly | high | simple | `services-config environment-*` |
| 14.3 | **Remote Config** (list keys, get value, set value via REST — requires auth token) | weekly | high | complex | `remote-config` |
| 14.4 | **Cloud Diagnostics** (query last N crashes/exceptions from the cloud dashboard) | weekly | medium | complex | `cloud-diagnostics` |
| 14.5 | **Analytics event validation** (dry-run an event payload against its schema) | rarely | medium | medium | `analytics validate-event` |

**Why it matters:** Projects using Unity Gaming Services need to read
their project/org IDs to bootstrap CI/CD, link environments, and inspect
live remote configs. Agents can't do any of this today.

---

### 15. Editor Preferences & User Settings

`editor-prefs` covers generic get/set. The Preferences window (Edit >
Preferences) has structured pages: External Tools, Colors, Keys, GI
Cache, 2D, Diagnostics, Asset Pipeline.

| # | Gap | Freq | Value | Complexity | Proposed command |
|---|---|---|---|---|---|
| 15.1 | **External Tools** (IDE selection, external script editor path, revision control plugin) — `EditorPrefs` keys like `kScriptsDefaultApp` | weekly | medium | simple | Extend `editor-prefs` with named presets |
| 15.2 | **Shortcut profile / custom keybindings** (`ShortcutManager.instance.activeProfileId`, `RegisterShortcutProfile`) | rarely | low | medium | `shortcuts` |
| 15.3 | **Color preferences** (Playmode tint, Scene View background colors, hierarchy selection colors) | rarely | low | simple | Extend `editor-prefs` |
| 15.4 | **GI Cache location and size** | rarely | low | simple | Extend `editor-prefs` |
| 15.5 | **Asset Pipeline mode** (v1 vs v2, parallel import threads) | rarely | medium | simple | Extend `editor-config` |

---

### 16. Build Pipeline: Incremental, Reports, Post-processors

`build-operation` covers trigger/settings/validate/get-target + Phase 5
build options. Missing:

| # | Gap | Freq | Value | Complexity | Proposed command |
|---|---|---|---|---|---|
| 16.1 | **Parse BuildReport from last build** (`BuildReport.summary.totalSize`, asset breakdown, warnings list) | daily | high | medium | Extend `build-operation` result with structured report |
| 16.2 | **Clean build output directory** (explicit cache clean beyond `CleanBuildCache` build option) | weekly | medium | simple | Extend `build-operation clean` |
| 16.3 | **Incremental build** (leverage Unity 6 incremental pipeline when possible — currently always full rebuild) | rarely | medium | medium | Extend `build-operation` flag |
| 16.4 | **Build step dry-run** (list scenes, assets, and size estimate without actually building) | weekly | medium | medium | `build-operation preview` |
| 16.5 | **Platform sub-target / standalone target kind** (Server build for Linux/Windows — `StandaloneBuildSubtarget.Server`) | weekly | medium | simple | Extend `build-operation` |
| 16.6 | **Platform-specific build arguments** (iOS `appendProject`, Android `exportAsGoogleAndroidProject`, WebGL `linkerTarget`) | weekly | high | medium | Extend `build-operation` params |

---

### 17. Sprite / 2D Workflows

Phase 4 flagged sprite editor; Phase 6 added tilemap basics. 2D workflow
still lacks:

| # | Gap | Freq | Value | Complexity | Proposed command |
|---|---|---|---|---|---|
| 17.1 | **Sprite slicing** (Grid-by-cell, grid-by-count, automatic) on an imported texture | weekly | medium | medium | `sprite-editor slice` |
| 17.2 | **Sprite pivot + physics shape** (per-sprite) | weekly | medium | medium | Extend `sprite-editor` |
| 17.3 | **Sprite Atlas v2 CRUD** (create, add folders/sprites, set packing settings, pack) | weekly | medium | medium | `sprite-atlas` |
| 17.4 | **2D Animation package** (skinning editor, bone hierarchy on PSDImporter) | rarely | low | complex | `sprite-skin` |

---

### 18. Snap, Grid & Alignment

Agents building levels need to place objects on a grid. Unity has
`GridSnapping`, `EditorSnapSettings`, and `SceneViewGrid`. None exposed.

| # | Gap | Freq | Value | Complexity | Proposed command |
|---|---|---|---|---|---|
| 18.1 | **Get / set snap increment X/Y/Z + rotation/scale snap** (`EditorSnapSettings.move`, `rotate`, `scale`) | weekly | medium | simple | `snap-settings` |
| 18.2 | **Enable / disable grid snap, vertex snap, surface snap** | weekly | medium | simple | Extend `snap-settings` |
| 18.3 | **Scene View grid axis + size + opacity** (`SceneView.lastActiveSceneView.sceneViewGrids`) | weekly | low | simple | Extend `scene-view` |
| 18.4 | **Snap selection to grid** (menu `Edit > Snap > Snap All Axes`) | weekly | medium | simple | `snap-selection` |

---

### 19. Gizmos & Editor Overlays

Scene View has a gizmo toggle panel (per-component class) and Overlays
(SceneView toolbars). Both are important for automated screenshot tests.

| # | Gap | Freq | Value | Complexity | Proposed command |
|---|---|---|---|---|---|
| 19.1 | **Toggle gizmo visibility per component type** (`AnnotationUtility.SetGizmoEnabled` — internal API) | weekly | medium | medium | `gizmos` |
| 19.2 | **Toggle icon visibility per component type** (`AnnotationUtility.SetIconEnabled`) | weekly | medium | medium | Extend `gizmos` |
| 19.3 | **Set gizmos globally on/off** in Scene / Game view | weekly | medium | simple | Extend `scene-view` / `game-view` |
| 19.4 | **Overlays** (show/hide Scene View overlays by ID; Unity 2022+ overlay system) | rarely | low | complex | Extend `scene-view` |

**Why it matters:** Screenshot regression tests need deterministic
visibility — today agents cannot guarantee whether debug gizmos are on
or off, which leaks into the final image.

---

### 20. Search & Quick Search (Unity Search API)

`com.unity.search` provides the Quick Search window and a powerful
programmatic API (`SearchService.Request`) spanning assets, scenes,
packages, menus, and settings. This is arguably the most powerful single
piece of Editor discovery. Zero coverage.

| # | Gap | Freq | Value | Complexity | Proposed command |
|---|---|---|---|---|---|
| 20.1 | **Execute a Quick Search query** (`SearchService.Request("q:*"," ")`) and return ranked results as JSON | daily | very high | medium | `search-query` |
| 20.2 | **Execute a saved search** (`.searchquery` assets) | weekly | medium | simple | Extend `search-query` |
| 20.3 | **List available search providers** and their filters (`SearchService.Providers`) | rarely | low | simple | Extend `search-query providers` |

**Why it matters:** This is the "grep for Unity" — an agent could use it
to find all scenes referencing asset X, all menu items matching a token,
all animation clips longer than Y. It subsumes and generalizes
`find-references`.

---

### 21. ProBuilder / Polybrush

If the project uses `com.unity.probuilder` (common for greybox levels),
none of its API is bridged.

| # | Gap | Freq | Value | Complexity | Proposed command |
|---|---|---|---|---|---|
| 21.1 | **Create ProBuilder shape** (Cube, Stair, Arch, Torus) with parameters | weekly for level design | medium | medium | `probuilder create` |
| 21.2 | **Extrude / bevel / carve face/edge/vertex** (full mesh editing) | weekly | medium | complex | `probuilder mesh-op` |
| 21.3 | **Convert ProBuilder mesh to asset** (bake to `.asset`) | rarely | low | simple | Extend `probuilder export` |

---

### 22. Scripting / Code Editor Integration

The `scripting.py` command exists for expression execution. Source
authoring workflows are missing:

| # | Gap | Freq | Value | Complexity | Proposed command |
|---|---|---|---|---|---|
| 22.1 | **Create new C# script from template** (MonoBehaviour, ScriptableObject, EditorWindow, Test fixture). `script-info` reads, there is no create-from-template equivalent that runs Unity's `ProjectWindowUtil.CreateScriptAsset` with the right template. | daily | high | simple | Extend `asset-extended-operation create-script` |
| 22.2 | **Regenerate .sln / .csproj** (`AssetDatabase.Refresh()` doesn't always trigger project sync; `UnityEditor.SyncVS.SyncSolution()`) | weekly | high | simple | `compile sync-solution` op |
| 22.3 | **Open file in external IDE** (`EditorUtility.OpenWithDefaultApp`) — useful to surface a line to a human reviewer | rarely | low | simple | `editor open-file` |
| 22.4 | **Project-level script analyzer settings** (Roslyn analyzers via `RoslynAnalyzer` label on DLL assets) | rarely | low | medium | Extend `compilation-pipeline` |

---

## Recommended Phase 7 Priorities

Ranked by combined **daily developer value**, **agent/automation impact**,
and **implementation simplicity**. Items flagged **P0** are the highest
leverage for a single-handler new addition.

### Tier 1 — Highest Leverage

| # | Gap | Why | Complexity |
|---|---|---|---|
| P0-1 | **20.1 Unity Search query** (`SearchService.Request`) | Single handler, subsumes dozens of one-off "find X" workflows. Highest ROI item in this report. | medium |
| P0-2 | **8.4 Parse NUnit XML into `run-tests` response** | Closes the single biggest reporting gap: right now the tool runs tests but the agent must reparse the log. | simple |
| P0-3 | **1.2 Render pipeline asset read/write** | Every URP/HDRP project needs this; agents currently fall back to `serialized-property` with type names that change per RP version. | medium |
| P0-4 | **11.1-11.2 Physics2D settings + matrix** | Symmetric gap with existing `physics-config`; pure dictionary extension. | simple |
| P0-5 | **14.1-14.2 Cloud project/org/environment IDs** | Needed for any UGS bootstrapping; one reflection read. | simple |
| P0-6 | **22.2 Regenerate .sln/.csproj (`SyncSolution`)** | Fixes a recurring "my IDE can't see this script" class of bug in CI. | simple |

### Tier 2 — High-Value Multi-Handler Work

| # | Gap | Why | Complexity |
|---|---|---|---|
| P1-1 | **2.1-2.4 UI Toolkit CRUD** (UXML + USS + PanelSettings + UIDocument) | Unity's default UI system; blocks agent-driven UI work today. | medium |
| P1-2 | **10.1-10.3 Addressables Profiles + Labels + Group Schemas** | Existing `addressables` handler is surface-level; profiles/labels are where the daily workflow lives. | medium |
| P1-3 | **7.1 Scoped registries + 7.3 Git/local packages explicit** | OpenUPM + internal feeds are blocked without scoped registry support. | simple |
| P1-4 | **9.1-9.3 Input System Action/Binding CRUD** | Current handler only reads; no way to author an action from CLI. | medium |
| P1-5 | **16.1 Parse BuildReport** | Agents can trigger builds but can't reason about what shipped or what grew. | medium |
| P1-6 | **4.3 Timeline evaluate at time + 4.4-4.5 Cinemachine priority** | Enables deterministic cutscene screenshot tests. | medium |
| P1-7 | **13.1 Memory Profiler package snapshot** | Distinct from built-in Profiler; blocks any CI memory regression detection. | medium |

### Tier 3 — Medium Leverage / Specialist

| # | Gap | Why | Complexity |
|---|---|---|---|
| P2-1 | **5.1-5.5 Localization minimum set** (locales, string table CRUD, CSV import/export) | High value for multi-lingual projects but only a subset use it. | medium |
| P2-2 | **12.1 StateMachineBehaviour add/remove + 12.3 Avatar rig** | Fills the remaining `animator-operation` gaps. | medium/complex |
| P2-3 | **18.1-18.2 Snap settings + 19.1-19.3 Gizmos** | Small per-gap, but critical for deterministic screenshot pipelines. | simple |
| P2-4 | **17.1-17.3 Sprite slicing + Atlas v2** | 2D games; Tilemap already shipped so sprite-side is the missing half. | medium |
| P2-5 | **1.3 URP Renderer Features** | Complex but unblocks pipeline authoring. | complex |
| P2-6 | **3.1-3.3 Shader Graph introspection** | Large design surface; start with read-only. | complex |

### Tier 4 — Lower Priority / Specialist

- 15.x Editor preferences panels (small value per item)
- 21.x ProBuilder (project-specific)
- 3.4-3.5 VFX Graph (requires specialized API)
- 13.3-13.4 Frame Debugger / Rendering Debugger (rarely automated)
- 14.3-14.5 Remote Config / Cloud Diagnostics (auth complexity)
- 17.4 2D Animation skinning (niche)

### Suggested Phase 7 Milestone Split

Optimal single-cycle scope is **Tier 1 + ~3 items from Tier 2**. A
recommended cut:

- **Phase 7a — "Query & Report"**: 20.1 Search, 8.4 NUnit parse,
  16.1 BuildReport, 14.1-14.2 Services config, 22.2 SyncSolution,
  11.1-11.2 Physics2D.
- **Phase 7b — "Render Config"**: 1.2 RP Asset, 1.1 Shader stripping,
  1.6-1.7 Shader variants, 6.1-6.3 VCS/serialization.
- **Phase 7c — "Author Flows"**: 2.x UI Toolkit core, 9.1-9.3 Input
  System authoring, 10.1-10.2 Addressables profiles + labels.
- **Phase 7d — "Cinematic & Anim"**: 4.3 Timeline evaluate,
  4.4-4.5 Cinemachine, 12.1 StateMachineBehaviour.

---

## Appendix: Cross-Reference of Existing Coverage

This audit accounts for everything currently registered in
`BridgeCommandRegistry.cs` and exposed via `TOOL_COMMAND_MAP` /
`TOOL_COMMAND_MAP_EXT`. The following handlers ship today and are
**not** considered gaps:

```
add-component, addressables, animation-clip, animator-operation,
asset-extended-operation, asset-operation, assembly-reload-lock,
audio-settings, bridge-status, build-operation, build-profile-operation,
build-scenes, capture-screenshot, clear-console, clipboard, compile,
compilation-pipeline, component-copy, component-reset, component-toggle,
console-log, deep-serialize, editor-config, editor-prefs,
environment-settings, execute-menu-item, find-references, focus-object,
game-view, gameobject-operation, gameobject-utility, get-component-data,
get-selection, graphics-settings, import-settings-operation, input-system,
lightmap-operation, list-tests, material-operation, navmesh-operation,
occlusion-culling, package-operation, physics-config,
player-settings-operation, playmode-control, prefab-operation,
prefab-override, preset-operation, profiler-control, profiler-sample,
quality-settings, query-hierarchy, read-console, reflection-probe,
refresh-assets, remove-component, run-tests, scene-operation,
scene-setup-operation, scene-template, scene-view, script-execution-order,
script-info, serialized-property, set-component-data, set-selection,
shader-inspection, tags-layers, terrain-operation, tilemap-operation,
time-settings, transform-operation, undo-operation, validate-prefab,
window-management
```

Total: 75 command types / ~56 MCP tools.

### Deliberately excluded from this report (already tracked elsewhere)

- Any item appearing in
  [`phase4-adversarial-gap-report.md`](phase4-adversarial-gap-report.md)
  sections 1-3 that remains unimplemented (tracked on that report).
- Documented Phase 6e follow-ups (`component-copy`, `component-reset`,
  etc. — these shipped).
- Bugfixes (B1-B8 from the Phase 4 report) — those belong to a
  separate quality backlog, not to capability parity.

### Meta-observations

1. **The biggest class of remaining gaps is package-provided Editor
   tooling** — UI Toolkit, Shader Graph, VFX Graph, Timeline,
   Cinemachine, Memory Profiler, Code Coverage, Localization, Search,
   Addressables Groups. These are the "windows that live inside their
   own assembly" and each requires an optional handler with
   package-presence detection.
2. **Read-only parity is strong; authoring parity is weak.** The bridge
   can query almost anything but can only *write* in the subsystems
   that had Phase 4-6 coverage. E.g., `input-system` reads but cannot
   author actions; `animator` authors but cannot attach behaviours;
   `addressables` marks entries but cannot manage profiles.
3. **Reporting parity is a sleeper gap.** Tests, builds, and
   profiling all produce rich structured output (NUnit XML,
   BuildReport, .raw profiler data, .snap memory snapshots) that the
   bridge does not parse for the caller. A generalized "give me the
   last X result as JSON" pattern would be low-effort, high-value.
4. **The Unity Search API (gap 20.1) is the single highest-ROI
   addition** — one handler + a pass-through of the ranked result set
   subsumes many of the "find" gaps across scenes, assets, menus,
   and settings.

---

*Last updated: 2026-04-20*
