# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Deprecated
- The MCP server interface (`mcp/`, `unity-bridge serve`, the `[mcp]` extra, and the MCP-only `ResponseCache`) is deprecated and no longer actively maintained. The supported interface is the `unity-bridge` CLI; `serve` now emits a deprecation notice but still starts.

### Changed
- Refreshed `README.md` to describe the current CLI-first support model, deprecated MCP compatibility surface, Codex skill/agent metadata, live command counts, and material subcommands.
- Parallel batch execution now classifies command safety by `parameters.operation`, not just command type, so operation-gated commands (`transform-operation`/`serialized-property`/`clipboard`/etc.) only run concurrently for their read-only operations.
- The global `--timeout` flag and `UNITY_BRIDGE_TIMEOUT` now apply across the whole CLI (previously ignored by every command); a global override is treated as a blanket per-command timeout.
- Settings command modules (physics2d, audio, time, graphics, environment, lightmap) now build their `set` parameters via a shared `core/settings_params.py` helper, removing ~140 lines of duplicated flag/value boilerplate (bridge payloads unchanged).
- Shared datetime/int parsing helpers consolidated into `core/timeutil.py` (previously duplicated in `core/health.py` and `core/operation.py`).
- CLI command/group registration failures are now logged as warnings instead of being silently swallowed.
- Editor readiness waits now run off the async event loop so MCP/control-plane calls can keep responding while Unity is compiling, importing, or reloading.

### Fixed
- **C# bridge: PlayMode test runs and compiles now survive the domain reload they trigger (C5).** A new reload-surviving `BridgeTestRunReporter` (`[InitializeOnLoad]`, re-registers `TestRunnerApi` callbacks each domain load, persists the originating command id in `SessionState`) reports the final result back even though entering play mode reloads the domain and wipes in-memory state — previously PlayMode runs were unreportable and the caller timed out. `CompileCommandHandler` likewise persists the in-flight compile in `SessionState` and completes it on the next domain load (`CompletePendingCompileAfterReload`, run before ledger recovery), and `BridgeOperationLedger.RecoverAfterReload` now skips commands explicitly deferred across a reload instead of force-writing a spurious "interrupted" response. Assembly-reload-lock depth is `SessionState`-backed so a lock taken before a reload survives it. *(Needs in-Editor PlayMode verification.)*
- **C# bridge: the `compile` handler no longer freezes the Unity Editor.** The blocking `Thread.Sleep` busy-wait on `EditorApplication.isCompiling` (which ran on the main thread Unity needs to drive compilation) was replaced with a non-blocking `EditorApplication.update` poll that returns `running` immediately and writes the terminal response when compilation finishes, never started (nothing to compile), or times out. A compile-triggered domain reload is handled by the existing operation-ledger recovery. *(Needs in-Editor compile verification — no Unity available at change time.)*
- **C# bridge: `HeartbeatGenerator` now writes atomically** via the shared `WriteAtomic` (temp + fsync + replace) instead of delete-then-move, removing the window where a health check could observe a missing heartbeat file.
- **C# bridge:** command files are now processed in submission (creation-time) order rather than the unspecified filesystem order; `_processedCommandFiles` is bounded to currently-present files instead of growing for the whole session; `isHealthy` no longer depends on the no-op file watcher; and `bridge-log.jsonl` is size-rotated at 5 MB.
- A plain command timeout now reports exit code 4 (Timeout) instead of 1.
- The operation ledger guards against the cross-process (Python/C#) write race: illegal transitions are rejected gracefully instead of raising, and a concurrently-written terminal state is no longer clobbered by a later non-terminal write.
- Non-idempotent commands that Unity has already accepted are no longer re-sent on retry (preventing duplicate side effects) unless an `idempotencyKey` is supplied.
- `unity-bridge clean` now reaps response files orphaned by timed-out/terminal operations.
- The retry layer treats unrecognized result shapes as failures rather than silently as success; busy-accounting can no longer produce a negative active-elapsed; `UNITY_BRIDGE_TIMEOUT` parsing tolerates surrounding whitespace and rejects non-positive/garbage values.

### Added
- Optional `coverage` CLI group, `code-coverage` bridge command, and `unity_code_coverage`
  MCP tool for Code Coverage package availability/install, recording control, and report
  discovery/summarization without requiring `com.unity.testtools.codecoverage` at compile time.
- Python-side queued command dispatch now persists queued command payloads outside Unity's command directory and dispatches them only after editor readiness returns; `unity_submit_command` returns an operation ID immediately for MCP clients that need a responsive control plane while Unity is busy.
- Package Manager automation now exposes `package batch`, `package pack`, and
  `package clear-cache --yes`, with MCP schema fields for `packagesToAdd`,
  `packagesToRemove`, `packageFolder`, `targetFolder`, and `confirmClearCache`.
- Editor readiness health state distinguishes bridge liveness from command readiness and waits before writing command files.
- Durable bridge operation state machine with per-command JSON snapshots, JSONL transition logs, Unity domain-generation tracking, atomic C# response writes, reload recovery, stale terminal ledger cleanup, and `operation status` / `unity_operation_status` inspection surfaces.
- **Unity 6.4 Phase 5: Built-in core packages** — 3 command groups + MCP tools:
  - `entities` command group + `unity_entities` MCP tool for reflection-safe Unity Entities availability, loaded world listing, default/named world summaries, entity counts, managed system inspection, and bounded archetype/component-type inspection.
  - `adaptive-performance` command group + `unity_adaptive_performance` MCP tool for Adaptive Performance availability, project settings, loader state, scaler profile discovery, and scaler setting inspection.
  - `multiplayer-playmode` command group + `unity_multiplayer_playmode` MCP tool for read-only Multiplayer Play Mode package/module availability, current player role, and current player tags.
- **Unity 6.4 Phase 4: Graphs and deterministic editor state** — 2 new command groups + MCP tools:
  - `graph-toolkit` command group + `unity_graph_toolkit` MCP tool for Graph Toolkit availability, graph asset discovery, graph inspection, and JSON-friendly graph export using reflection over the built-in Unity 6.4 module.
  - `scene-state` command group + `unity_scene_state` MCP tool for deterministic Scene View/editor state: snap settings, grid state, gizmo state, active transform tool, pivot settings, visible/locked layer masks, and overlay listing/toggle.
- **Unity 6.4 Phase 3: Rendering and build** — 2 new command groups + 1 expanded build surface:
  - `render-pipeline` command group + `unity_render_pipeline` MCP tool for render pipeline asset listing, current/default/quality state inspection, default assignment, quality override assignment, and asset inspection.
  - `graphics-state` command group + `unity_graphics_state` MCP tool for `GraphicsStateCollection` creation, load info, begin/end trace, trace save, warmup, progressive warmup, and variant clearing.
  - Extended `build-profile-operation` with `get-scenes`, `set-scenes`, `get-defines`, `set-defines`, and `build`, including structured build report summary, slowest build steps, largest packed assets, and warning/error counts.
- **Unity 6.4 Phase 2: Authoring systems** — 3 expanded bridge surfaces:
  - `ui-toolkit` command group + `unity_ui_toolkit` MCP tool for `UIDocument` discovery, UXML/USS inspection, UXML asset creation, `PanelSettings` asset creation, and adding/configuring `UIDocument` components.
  - Extended `input-system` with authoring operations: create `.inputactions` assets, add action maps, add actions, add bindings, add control schemes, and list control schemes.
  - Extended `addressables` with profile listing/activation, label listing/mutation, group schema listing, and best-effort Analyze rule discovery/execution with graceful unsupported results.
- **Unity 6.4 Phase 1: Identity and audit** — 2 new command groups + MCP tools:
  - `object-identity` resolves selected objects and explicit targets across `EntityId`, `GlobalObjectId`, asset paths, scene hierarchy paths, and legacy instance IDs.
  - `project-auditor` checks Project Auditor availability, runs audits, saves reports, and summarizes saved reports through reflection so projects without `com.unity.project-auditor` still compile.
- **Phase 0 surface hardening** — exposes existing late-phase bridge capabilities consistently:
  - Registered Phase 4 expansion, Phase 6, Phase 6b, and Phase 7 CLI groups in `app.py`.
  - Exposed Phase 4 extension, Phase 4 misc, Phase 6 settings, Phase 6b, and Phase 7 tools through MCP, bringing the active MCP surface to 83 tool definitions.
  - Added inventory and surface tests for CLI registration, MCP mapping/timeout coverage, and C# `.meta` file completeness.
  - Added missing Unity `.meta` files for Phase 7 C# bridge files.
- **Phase 7a-2: Structured test + build reports** — closes the "we ran it but the agent has to re-parse the log" gap:
  - `run-tests` response now includes `inconclusive`, `resultState`, `testSuite`, plus a `testCases` array (full name, status, duration, assembly, categories) alongside the existing `failures` array. NUnit semantics, no log scraping required.
  - `build-operation` response now includes a structured `summary` (result, platform, total size bytes/MB, total time, start/end timestamps, output path, build GUID), the top 50 slowest `buildSteps` with duration and depth, the top 25 `largestAssets` (path, size, kind), and aggregated `errorCount`/`warningCount`.
  - `unity_bridge.commands.reports` with `extract_test_report()` and `extract_build_report()` helpers that normalize the C# payload into snake_case Python dicts.
  - New `BuildReportHelpers.cs` (C#) populates the structured fields from `UnityEditor.Build.Reporting.BuildReport` — packed-asset breakdown uses a try/catch so platforms that don't support `report.packedAssets` degrade gracefully.
  - 10 new unit tests (`tests/unit/test_reports.py`).
- **Phase 7a: Query & Report** — 4 new command groups + MCP tools:
  - `sync-solution` — regenerate `.sln`/`.csproj` via modern `Unity.CodeEditor.CodeEditor.CurrentEditor.SyncAll()` with a legacy `UnityEditor.SyncVS.SyncSolution` fallback. Fixes "IDE doesn't see my new script" in CI.
  - `cloud` — Unity Gaming Services lookups: `cloud project-id`, `cloud environments`, `cloud active-environment`. Reads `CloudProjectSettings` plus the Services Core package (via reflection so the bridge compiles without the package).
  - `physics2d` — Physics2D settings and 32x32 2D layer collision matrix: `physics2d get`, `physics2d set`, `physics2d matrix`, `physics2d set-collision`. Symmetric with the existing 3D `physics` group.
  - `search` — Unity Search (Quick Search) integration: `search query "t:Material"`, `search providers`. Reflection-based wrapper around `UnityEditor.Search.SearchService.Request`; single handler subsumes a large class of "find X" workflows.
- `schemas_phase7.py` with MCP input schemas for the Phase 7a tools
- 4 new C# handlers (`SyncSolutionCommandHandler`, `CloudServicesCommandHandler`, `Physics2DConfigCommandHandler`, `SearchQueryCommandHandler`), all registered in `BridgeCommandRegistry.cs`
- `cloud-services` and `search-query` declared parallel-safe (read-only)
- 17 new unit tests (`tests/unit/test_phase7_query_report.py`)

### Fixed
- Package Manager client requests are now serialized in the C# bridge so a
  second UPM request is rejected while one is pending, matching Unity's
  sequential `PackageManager.Client` requirement.
- Unity bridge response and operation JSON parsing now tolerates UTF-8 BOM-prefixed files, and the C# atomic writer now emits UTF-8 without BOM for bridge JSON files.
- Hardened bridge operation ledger writes with unique temp files, bounded retry/backoff, and clearer response-vs-ledger failure logging so transient Bridge state file locks do not masquerade as Unity compile/build failures.
- `unity-bridge clean` now prunes stale bridge `*.tmp` files from command, response, and operation state directories while still preserving active operation records.
- Packaged command-line installs now bundle `ClaudeCodeBridge/`, so `unity-bridge install` deploys the current C# bridge scripts from normal wheel installs as well as editable source installs.
- Restored `unity-bridge playmode stop` by sending canonical `operation` payloads and accepting legacy `action` aliases in the C# bridge handler.
- Applied the advertised `package list --source` filter in the C# Package Manager handler, including source validation and filtered list responses.
- Wired Input System authoring overwrite flags through the Python CLI/core helpers and allowed control schemes to be created without optional binding-group/device details, matching the MCP schema.
- Added and registered the missing `execute-script` C# handler so the existing `unity-bridge script` command reaches live Unity instead of failing as an unknown command type.
- Updated `unity-bridge install` to deploy the bundled `unity-bridge-cli` Codex skill into the target project's `.agents/skills/` directory and report its status in `--check`.
- Replaced stale MCP compatibility tests that inspected deleted `unity_bridge_mcp_server.py` with tests against the current modular MCP tool registry.
- Modernized legacy root-level bridge/WSL health tests so the full `tests/` suite collects against the current package layout.
- Added explicit timeout defaults for late-phase command types that were previously relying on the protocol fallback.
- **Registered 29 orphaned C# command handlers in `BridgeCommandRegistry.cs`** — Phase 4 expansion (`script-execution-order`, `assembly-reload-lock`, `find-references`, `navmesh-operation`, `animation-clip`, `terrain-operation`, `reflection-probe`, `occlusion-culling`), Phase 6a-6e (`time-settings`, `graphics-settings`, `environment-settings`, `audio-settings`, `component-copy`, `component-reset`, `scene-view`, `game-view`, `profiler-control`, `addressables`, `tilemap-operation`, `input-system`, `clipboard`, `preset-operation`, `scene-template`, `script-info`, `deep-serialize`, `window-management`), and the previously-disabled `capture-screenshot`, `playmode-control`, `asset-operation`. The C# handler files and the Python/MCP layers already existed; the registry had never been updated to wire them in. Unit tests pass because they mock the bridge — live Unity previously returned "Unknown command type" for every Phase 4-ext / Phase 6 command.
- Added `timeout` property to 21 core MCP schemas in `schemas.py` (previously only `run_tests`, `build_operation`, `compile_scripts` declared it) so LLM clients can discover per-tool timeout overrides
- Cleared all ruff lint errors across `src/` and `tests/` (unused imports, dead variables, lambda-to-def)
- Deleted stale root-level tests `tests/test_response_cache.py` and `tests/test_retry_handler.py` — superseded by `tests/unit/test_cache.py` and `tests/unit/test_retry.py` with correct module imports
- Added missing fields to `AssetExtendedOperationParams` model (`renderTextureWidth`, `renderTextureHeight`, `renderTextureDepth`, `initialContent`, `reserializeMode`)
- Added missing `using System.Collections.Generic` to `AssetExtendedHelpers.cs`
- Added 16 missing fields to `PlayerSettingsData` model to match `PlayerSettingsHelpers.BuildSettingsSnapshot()`
- Added missing `using UnityEditor.Build` to `PlayerSettingsHelpers.cs` for `NamedBuildTarget`
- Replaced non-existent `SceneView.GetBuiltinCameraModes()` with `SceneView.GetBuiltinCameraMode(DrawCameraMode)` in `SceneViewCommandHandler.cs`

### Changed
- Gitignored per-session artifacts (`.summaries/`, `logs/`, `.claude/settings.local.json`) so local state no longer shows up as untracked in `git status`
- Refreshed `CLAUDE.md` and `README.md` with current module counts, Phase 4-6 command groups, and the expanded MCP schema file layout
- Restructured `unity-bridge-cli` skill from 611-line monolith to progressive disclosure pattern (301-line SKILL.md + 7 domain reference files)
- Added `allowed-tools` frontmatter to restrict skill to CLI commands and file reading
- Added decision tree and quick-scan sections to SKILL.md for faster command discovery
- Updated skill description with Phase 6 trigger words (navmesh, terrain, tilemap, addressables, etc.)
- Created domain reference files: scene-commands, component-commands, asset-commands, build-commands, settings-commands, specialized-commands, tools-commands
- Added Phase 6 commands (not yet registered in CLI) to reference files: navmesh, animation, terrain, tilemap, addressables, reflection-probes, occlusion, time, graphics, environment, audio, scene-view, game-view, profiler controls, clipboard, presets, scene-templates, script-info, deep-serialize, window, input-system, execution-order, assembly-lock, find-references, component copy/paste/reset, material keywords

### Added
- Phase 4 Misc: 8 expanded capabilities covering remaining miscellaneous gaps
- Expanded `CreateAssetByType`: PhysicsMaterial, PhysicsMaterial2D, AnimationClip, RenderTexture, TextAsset, Shader, asmdef, asmref, custom ScriptableObject subtypes
- `clipboard` command: read/write system clipboard via `EditorGUIUtility.systemCopyBuffer`
- `preset-operation` command: create, apply, can-apply presets, list defaults
- `scene-template` command: list, create-from-scene, instantiate scene templates
- `script-info` command: MonoScript inspection — class info, list all scripts, find component source
- `deep-serialize` command: EditorJsonUtility deep serialization including private fields
- `--deep` flag on `component get` CLI for full Editor serialization
- `window-management` command: list, open, focus, close Editor windows
- `input-system` command: list/export/import InputActionAssets (requires com.unity.inputsystem)
- 7 new MCP tools: `unity_clipboard`, `unity_preset`, `unity_scene_template`, `unity_script_info`, `unity_deep_serialize`, `unity_window_management`, `unity_input_system`
- `schemas_phase4_misc.py` with MCP input schemas for Phase 4 Misc tools
- Phase 6b: Scene, material, component, and inspector gap closures (7 capabilities)
- Material keyword operations: `enable-keyword`, `disable-keyword`, `get-keywords` on material-operation
- Material `set-render-queue` and `copy-properties` operations on material-operation
- `component-copy` command: copy/paste component values via EditorJsonUtility serialization
- `component-reset` command: reset component to defaults via SmartReset or temp-object fallback
- `move-object` operation on `scene-operation`: move root GameObjects between loaded scenes
- `scene-view` command: get/set Scene View camera (pivot, rotation, size, ortho, 2D, draw mode)
- `game-view` command: get Game View state, set resolution, set zoom scale
- `profiler-control` command: start/stop profiler, save data to file, get detailed memory stats
- 5 new C# handlers: ComponentCopyCommandHandler, ComponentResetCommandHandler, SceneViewCommandHandler, GameViewCommandHandler, ProfilerControlCommandHandler
- MaterialKeywordHelpers.cs: partial class for keyword/queue/copy operations
- 5 new MCP tools: `unity_component_copy`, `unity_component_reset`, `unity_scene_view`, `unity_game_view`, `unity_profiler_control`
- `schemas_phase6b.py` with MCP input schemas for Phase 6b tools
- `material` CLI group with subcommands: enable-keyword, disable-keyword, get-keywords, set-render-queue, copy-properties
- `component copy`, `component paste`, `component reset` CLI commands
- `scene move-object` CLI command
- `scene-view` CLI group: get, set, toggle-2d, set-draw-mode
- `game-view` CLI group: get, set-resolution, set-scale
- `profiler` CLI group: start, stop, save, memory
- Phase 6b timeout defaults in `protocol.py` for 5 new command types
- Unit tests for all Phase 6b core functions (38 tests)
- Build, platform, and pipeline gap closures: 6 capabilities across build, scripting, and asset systems
- `switch-platform` operation on `build-operation`: switch active build target with deferred response (domain reload)
- `list-platforms` operation on `build-operation`: enumerate all BuildTargets with support status
- Extended build options: `autoRunPlayer`, `connectProfiler`, `allowDebugging`, `compress` (lz4/lz4hc), `cleanBuildCache`, `detailedBuildReport`, `buildScriptsOnly`, `--scenes` override, `--subtarget` (Server/Player)
- `script-execution-order` command: get/set MonoScript execution order via MonoImporter API
- `assembly-reload-lock` command: lock/unlock/status for EditorApplication assembly reload control
- `find-references` command: find all ObjectReference properties pointing at a given asset across loaded scenes
- `reserialize` operation on `asset-extended-operation`: force reserialize all or specific assets with mode control
- `build switch-platform`, `build list-platforms` CLI commands
- `execution-order get`, `execution-order set` CLI commands
- `assembly-lock`, `assembly-unlock`, `assembly-status` CLI commands
- `find-references` CLI command
- `asset-ext reserialize` CLI command with `--paths` and `--mode` options
- 3 new MCP tools: `unity_script_execution_order`, `unity_assembly_reload_lock`, `unity_find_references`
- `schemas_pipeline.py` with MCP input schemas for pipeline tools
- 3 new C# handlers: ScriptExecutionOrderCommandHandler, AssemblyReloadLockCommandHandler, FindReferencesCommandHandler
- `BuildPlatformOperations.cs` partial class with switch-platform, list-platforms, and extended build option helpers
- Pipeline timeout defaults in `protocol.py` for 3 new command types
- `script-execution-order` and `find-references` added to `PARALLEL_SAFE_COMMANDS` (read-only)
- Unit tests for all 6 new capabilities (57 tests)
- Phase 5 Quick Wins: 6 new capabilities covering daily-use gaps from adversarial review
- `create-primitive` operation on `gameobject-operation`: create cubes, spheres, lights, cameras, particle systems
- `set-active` operation on `gameobject-operation`: activate/deactivate GameObjects with Undo
- `remove-component` command: remove components from GameObjects (undo-aware, blocks Transform removal)
- `component-toggle` command: enable/disable Behaviour, Renderer, and Collider components
- Additive scene loading: `mode` parameter on `scene-operation load` (single, additive, additive-without-loading)
- `unload` and `set-active` operations on `scene-operation` for multi-scene editing workflows
- `console-log` command: log custom messages to Unity Console (log, warning, error)
- `--additive` flag on `scene load` CLI command
- `hierarchy create-primitive`, `hierarchy set-active` CLI commands
- `component remove`, `component enable`, `component disable` CLI commands
- `scene load-additive`, `scene unload`, `scene set-active` CLI commands
- `console log` CLI command with `--type` flag
- 5 new MCP tools: `unity_create_primitive`, `unity_remove_component`, `unity_component_toggle`, `unity_gameobject_set_active`, `unity_console_log`
- `schemas_phase5.py` with MCP input schemas for Phase 5 tools
- 3 new C# handlers: RemoveComponentCommandHandler, ComponentToggleCommandHandler, ConsoleLogCommandHandler
- Phase 5 timeout defaults in `protocol.py` for new command types
- Unit tests for all Phase 5 core functions
- Phase 4 Critical Gaps: 9 new command types with C#, Python, and MCP support
- `set-selection`: programmatically set or clear Unity Editor selection by GameObject paths
- `editor-prefs`: read/write EditorPrefs and SessionState (string, int, float, bool)
- `build-scenes`: manage Build Settings scene list (list, add, remove, enable, disable, reorder)
- `duplicate` operation added to `gameobject-utility` for duplicating GameObjects with Undo support
- 3 new MCP tools (`unity_set_selection`, `unity_editor_prefs`, `unity_build_scenes`)
- 3 new C# command handlers (SelectionCommandHandler, EditorPrefsCommandHandler, BuildScenesCommandHandler)
- Phase 4 timeout defaults in `protocol.py` for all 3 new command types
- `select` CLI command group for selection management
- `prefs` CLI command group for editor preferences
- `build-scenes` CLI command group for build scene list management
- `hierarchy duplicate` CLI command for duplicating GameObjects
- Unit tests for select, prefs, build-scenes, and duplicate commands
- `transform-operation`: dedicated transform control (get/set position, rotation, scale, reparent, sibling index) with Undo support
- `serialized-property`: access ALL serialized fields including `[SerializeField]` private fields via Unity SerializedObject API (list, get, set)
- `physics-config`: read/set gravity, solver settings, read/modify 32x32 layer collision matrix
- `quality-settings`: list quality levels, get current settings (shadows, AA, LOD, vsync), switch active level
- `tags-layers`: list/add tags, list/add layers (user slots 8-31), list/add sorting layers via TagManager
- `editor-config`: read/set enter play mode options, serialization mode, async shader compilation, line endings, root namespace
- 6 new MCP tools (`unity_transform`, `unity_serialized_property`, `unity_physics_config`, `unity_quality_settings`, `unity_tags_layers`, `unity_editor_config`)
- 6 new C# command handlers (Transform, SerializedProperty, PhysicsConfig, QualitySettings, TagsLayers, EditorConfig)
- `schemas_phase4.py` extended with 6 additional Phase 4 MCP schema definitions
- Phase 4 timeout defaults in `protocol.py` for 6 new command types
- `transform` CLI command group for transform manipulation
- `property` CLI command group for SerializedProperty access
- `physics` CLI command group with `collision` subgroup for physics configuration
- `quality` CLI command group for quality settings
- `tags`, `layers`, `sorting-layers` CLI command groups for tags/layers management
- `editor-config` CLI command group for editor settings
- Unit tests for all 6 new Phase 4 command modules (96 tests)

### Fixed
- `SetComponentDataCommandHandler.cs`: rewritten to use SerializedObject/SerializedProperty as primary approach (fixes `[SerializeField] private` field access), with reflection fallback for runtime-only fields
- `GameObjectOperationCommandHandler.cs`: replaced `Object.DestroyImmediate()` with `Undo.DestroyObjectImmediate()` for undo-aware destruction
- `GameObjectOperationCommandHandler.cs`: replaced `new GameObject()` with `ObjectFactory.CreateGameObject()` for auto Undo registration and Preset application

### Added (previous)
- Phase 1 Core Platform APIs: 4 new command groups with C#, Python, and MCP support
- `player-settings-operation`: read/write PlayerSettings and manage scripting define symbols
- `asset-extended-operation`: create, delete, copy, move, deps, guid, folder management, export/import
- `build-profile-operation`: list, get/set active, inspect Unity 6 Build Profiles
- `package-operation`: list, search, add, remove, info, embed, resolve UPM packages
- 4 new MCP tools (`unity_player_settings`, `unity_asset_extended`, `unity_build_profile`, `unity_package_operation`)
- `schemas_ext.py` for Phase 1 MCP schema definitions
- Unit tests for all 4 new command modules
- Phase 2 Developer Workflow APIs: 5 new command types with C#, Python, and MCP support
- `undo-operation`: perform, redo, history, clear, group-name, collapse undo groups
- `compilation-pipeline`: list assemblies, query defines, script-to-assembly lookup, optimization mode
- `prefab-override`: list, apply, revert overrides; status, find-instances, unpack prefabs
- `list-tests`: discover tests, categories, and assemblies without running them (uses TestRunnerApi.RetrieveTestTree)
- `gameobject-utility`: find missing scripts, manage static flags, set layer/tag
- 5 new MCP tools (`unity_compilation_pipeline`, `unity_undo_operation`, `unity_prefab_overrides`, `unity_list_tests`, `unity_gameobject_utility`)
- 5 new C# command handlers with separate model files (CompilationPipeline, TestList, PrefabOverride, Undo, GameObjectUtility)
- Phase 2 timeout defaults in `protocol.py` for all 5 new command types
- `list-tests` added to `PARALLEL_SAFE_COMMANDS` (read-only)
- `compile` CLI command group for compilation pipeline queries
- `undo` CLI command group for undo/redo management
- Prefab override CLI subcommands under `prefab overrides`
- Hierarchy utility CLI subcommands: `missing-scripts`, `static-flags`, `set-static-flags`, `set-layer`, `set-tag`
- `test list` CLI command for test discovery
- Unit tests for compilation pipeline, test listing, and all Phase 2 modules
- Phase 3 Specialized APIs: 4 new command types with C#, Python, and MCP support
- `shader-inspection`: list all shaders, get info, check errors, enumerate properties, find by property, list keywords (read-only, parallel-safe)
- `lightmap-operation`: bake (async/sync), cancel, clear, status, read settings
- `import-settings-operation`: get/set import settings, reimport, bulk-set, save/apply templates for textures, models, audio
- `scene-setup-operation`: save/restore multi-scene setups, play mode start scene, cross-scene refs, preview scenes
- 4 new MCP tools (`unity_shader_inspection`, `unity_lightmap_operation`, `unity_import_settings`, `unity_scene_extended`)
- `schemas_phase3.py` for Phase 3 MCP schema definitions
- 4 new C# command handlers with separate model files (ShaderInspection, LightmapOperation, ImportSettings, SceneSetup)
- Phase 3 timeout defaults in `protocol.py` (15s shader, 30s lightmap/scene-setup, 60s import-settings)
- `shader-inspection` added to `PARALLEL_SAFE_COMMANDS` (read-only)
- `shader` CLI command group for shader inspection
- `lightmap` CLI command group for lightmap operations
- `import-settings` CLI command group for asset import settings
- `scene-ext` CLI command group for extended scene management
- Unit tests for all 4 Phase 3 command modules
- `app.py` Typer entry point with global flags (`--project`, `--pretty`, `--human`, `--verbose`, `--quiet`, `--timeout`, `--no-color`)
- `mcp/server.py` migrated from monolithic `unity_bridge_mcp_server.py`, uses shared core async functions
- `mcp/tools.py` tool definitions and command map for MCP tool dispatch
- `mcp/schemas.py` JSON Schema definitions for all 26 MCP tools
- Lazy DirectBridge initialization in `AppState.get_bridge()`
- Signal handler for clean Ctrl+C exit (code 130)
- Graceful degradation for optional command modules via `_try_register_command`

### Changed
- Split all source files over 500 LOC into partial classes or companion files to meet architecture limit
- `AnimatorOperationCommandHandler.cs` (2081 LOC) split into 5 partial class files by operation category
- `ClaudeUnityBridge.cs` (864 LOC) split: command registry to `BridgeCommandRegistry.cs`, menu items to `BridgeMenuItems.cs`
- `BridgeModels.cs` (778 LOC) split: late-phase models moved to `BridgeModelsPhase3.cs`
- `ImportSettingsCommandHandler.cs` (707 LOC) split: per-importer helpers to `ImportSettingsHelpers.cs`
- `PrefabOperationCommandHandler.cs` (621 LOC) split: helpers to `PrefabOperationHelpers.cs`, trimmed doc comment
- `AssetExtendedCommandHandler.cs` (572 LOC) split: export/import/utility to `AssetExtendedHelpers.cs`
- `BuildOperationCommandHandler.cs` (542 LOC) split: validation to `BuildOperationHelpers.cs`
- `MaterialOperationCommandHandler.cs` (527 LOC) split: property helpers to `MaterialOperationHelpers.cs`
- `schemas.py` (518 LOC): moved `batch()` and `help_topic()` schemas to `schemas_ext.py`
- `tools.py` updated to reference `schemas_ext.batch()` and `schemas_ext.help_topic()`
- Phase 3 tech spec revised (v0.2.0): consolidated 22 MCP tools to 4, fixed obsolete API references, added edge case handling
- MCP tool count increased from 35 to 39 (26 core + 4 Phase 1 + 5 Phase 2 + 4 Phase 3)
- `schemas_ext.py` extended with Phase 2 schemas (undo, compilation pipeline, prefab overrides, list tests, gameobject utility)
- `hierarchy_app` registered as Typer group to expose Phase 2 utility subcommands

### Fixed
- `install` command: replaced missing `install_bridge` module with native install logic in `lifecycle.py`
- `version` command: bridge version no longer shows "unknown"
- MCP server auto-install now uses shared `lifecycle.install()` instead of missing legacy module
- Broken unit test imports: `test_cache.py` and `test_retry.py` updated from stale `response_cache`/`retry_handler` imports to `unity_bridge.core.cache`/`unity_bridge.core.retry`
- `test_cache.py` `CacheEntry` tests: fixed offset-naive `datetime.now()` to `datetime.now(timezone.utc)` to match `cache.py` implementation
- CHANGELOG duplicate `### Added` section merged into one under `[Unreleased]`

## [3.0.0] - 2026-02-21

### BREAKING CHANGES
- Removed all PowerShell dependencies; MCP server now requires DirectBridge (aiofiles)
- `mcp.json` command changed from `python` to `python3` (Ubuntu/WSL default)
- Removed `psutil` dependency from `bridge_utils.py`

### Removed
- Removed PowerShell fallback from `invoke_unity_command()` (~120 lines)
- Removed `import subprocess` from MCP server
- Removed `SCRIPT_DIR` and `INVOKE_SCRIPT` constants
- Deleted 5 PowerShell scripts from `unity/scripts/`: `send-command.ps1`, `Invoke-UnityCommand.ps1`, `BridgeUtilities.ps1`, `cleanup-bridge.ps1`, `test-mcp-diagnostic.ps1`
- Deleted 12 PowerShell scripts from `scripts/`: `run-unity-tests.ps1`, `run-unity-tests-automated.ps1`, `run-tests.ps1`, `analyze-allocations.ps1`, `asset-backup-system.ps1`, `code-formatter.ps1`, `performance-monitor.ps1`, `refactor-checkpoint.ps1`, `scene-validation.ps1`, `test-hook-setup.ps1`, `unity-asset-validator.ps1`, `unity-asset-validator-wrapper.ps1`
- Deleted `unity/scripts/bridge-operator.md` (31KB PowerShell-focused documentation)
- Removed PowerShell permission entries from `.claude/settings.local.json`
- Removed `zen-win` MCP server from enabled servers list

### Changed
- `bridge_utils.py`: Unity detection now uses heartbeat file instead of `psutil` process enumeration (works from WSL)
- `invoke_unity_command()` returns immediate error when DirectBridge unavailable instead of falling through to PowerShell
- Slash commands (`/unity-build`, `/unity-logs`) rewritten to use MCP bridge tools
- Updated all documentation to use Python/WSL paths and examples
- Settings: replaced PowerShell permissions with `Bash(python3:*)`

### Added
- `_check_heartbeat()` function in `bridge_utils.py` for heartbeat-based Unity detection
- `unity/requirements.txt` with runtime dependencies (aiofiles, mcp)
- `test_bridge_utils.py` - unit tests for heartbeat detection and file cleanup
- `test_wsl_compatibility.py` - tests verifying no PowerShell references remain

---

## [2.1.0] - 2026-01-06

### Added

#### Console Log Stack Trace Control
- `includeStackTrace` parameter for `unity_read_console` - toggle stack trace inclusion
- `maxStackTraceLines` parameter - limit stack trace lines per entry (default: 5, 0=unlimited, -1=none)
- `maxMessageLength` parameter - truncate long messages (default: 500 chars, 0=unlimited)
- Intelligent stack trace parsing separates message content from stack trace
- Truncation indicators show when content was trimmed
- Reduces context window usage when reading console logs with many errors

### Changed
- `ReadConsoleCommandHandler.cs` now parses and truncates stack traces
- `ReadConsoleParams` model extended with stack trace control parameters
- MCP tool schema updated with new optional parameters

---

## [2.0.0] - 2026-01-06

### Added

#### Auto-Update System
- Automatic version detection and update on MCP server startup
- SHA256 hash-based file change detection for selective updates
- `bridge_manifest.json` tracks installed version and file hashes
- Support for legacy installations (auto-generates manifest on first update)
- Safe file copying with file locking detection (handles Unity editor locks)
- CLI support: `install_bridge.py --check` to check update status
- Selective updates: only changed files are copied, reducing Unity recompilation

#### Phase 1: Quick Wins
- `unity_clear_console` tool - Clear Unity console logs
- `unity_get_selection` tool - Get currently selected objects in Unity Editor
- `unity_refresh_assets` tool - Force refresh of Unity asset database
- `unity_focus_object` tool - Focus camera on specific GameObject
- `unity_health_check` tool - Check Unity Bridge health status
- Smart timeout defaults per command type (TIMEOUT_DEFAULTS)
- Heartbeat system for health monitoring (HeartbeatGenerator.cs)
- Health monitoring via heartbeat.json (health_monitor.py)
- Retry logic with exponential backoff (retry_handler.py)

#### Phase 2: Architecture Simplification
- DirectBridge class for direct Python-to-file communication (direct_bridge.py)
- `unity_compile` tool - Trigger and monitor C# compilation
- `unity_execute_menu_item` tool - Execute Unity Editor menu items
- CompileCommandHandler.cs - C# handler for compilation commands
- ExecuteMenuItemCommandHandler.cs - C# handler for menu item execution
- Automatic fallback to PowerShell if DirectBridge unavailable

#### Phase 3: Developer Experience
- `unity_batch` tool - Execute multiple commands in single request
- `unity_help` tool - Get help for available tools and usage
- Response caching for read-only operations (response_cache.py)
- Cache integration with MCP server for improved latency
- Scene change detection for automatic cache invalidation

### Changed
- `invoke_unity_command()` now uses DirectBridge by default with PowerShell fallback
- MCP server imports DirectBridge, RetryConfig, and ResponseCache with graceful degradation
- ClaudeUnityBridge.cs now registers Phase 2 handlers (Compile, ExecuteMenuItem)
- Improved error handling with detailed error messages

### Technical Details
- DirectBridge provides ~50% latency reduction compared to PowerShell
- Response cache uses LRU eviction with configurable TTL
- Heartbeat updates every 5 seconds with Unity state information
- Retry handler uses exponential backoff (base_delay=0.1s, max_delay=2.0s)

### Dependencies
- Added: aiofiles (required for DirectBridge async file I/O)
- Python 3.10+ required

## [1.3.1] - Previous Release

- Initial Unity Bridge MCP implementation
- PowerShell-based command execution
- Basic Unity Editor integration
