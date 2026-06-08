# Unity 6.4 Bridge Implementation Roadmap

Last updated: 2026-06-01

## Acceptance Criteria

The full implementation is complete only when every Unity 6.4 opportunity is available as a verified bridge capability with CLI, MCP, protocol, tests, and documentation where applicable.

## Phase 0: Surface Hardening

Status: complete as of 2026-06-01.

Acceptance:
- Existing late-phase CLI command groups are reachable from `unity-bridge --help`.
- MCP definitions include Phase 4 extension, Phase 4 misc, Phase 6 settings, Phase 6b, and Phase 7 tools.
- Every MCP bridge tool maps to a command type or explicit special handler.
- Every mapped command type has an explicit protocol timeout default.
- Every `ClaudeCodeBridge/*.cs` file has a sibling `.cs.meta`.

## Phase 1: Unity 6.4 Identity and Audit

Status: complete as of 2026-06-01.

Targets:
- `EntityId`/legacy instance ID normalization across hierarchy, selection, search, serialized properties, and object lookups.
- Project Auditor run/export/diff/fix bridge operations.

Implemented:
- `object-identity` CLI group and `unity_object_identity` MCP tool.
- `ProjectAuditorCommandHandler` exposed through `project-auditor` CLI group and `unity_project_auditor` MCP tool.
- Reflection-safe optional API handling for `EntityId` and `com.unity.project-auditor`.

## Phase 2: Authoring Systems

Status: complete as of 2026-06-01.

Targets:
- UI Toolkit UXML/USS/PanelSettings/UIDocument operations.
- Input System action, binding, and control scheme CRUD.
- Addressables profile, label, schema, and Analyze workflows.

Implemented:
- `ui-toolkit` CLI group and `unity_ui_toolkit` MCP tool for UXML/USS/PanelSettings/UIDocument operations.
- Extended `input-system` CLI/MCP surface for action-map, action, binding, and control-scheme authoring.
- Extended `addressables` CLI/MCP surface for profiles, labels, schemas, and Analyze.

## Phase 3: Rendering and Build

Status: complete as of 2026-06-01.

Targets:
- Render pipeline asset inspection and mutation.
- Shader stripping and PSO/`GraphicsStateCollection` trace/warmup workflows.
- Build Profile scene/define/settings inspection and build-by-profile execution.

Implemented:
- `render-pipeline` CLI group and `unity_render_pipeline` MCP tool for listing, inspecting, and assigning render pipeline assets.
- `graphics-state` CLI group and `unity_graphics_state` MCP tool for `GraphicsStateCollection` create/load/trace/save/warmup workflows.
- Extended `build-profile-operation` with scene lists, scripting defines, and build-by-profile execution with structured build reports.

## Phase 4: Graphs and Deterministic Editor State

Status: complete as of 2026-06-01.

Targets:
- Graph Toolkit read-only inspection and export.
- SceneView grid, snap, gizmo, overlay, and active tool state for deterministic screenshots.

Implemented:
- `graph-toolkit` CLI group and `unity_graph_toolkit` MCP tool for module availability, asset listing, graph inspection, and graph export.
- `scene-state` CLI group and `unity_scene_state` MCP tool for snap/grid/gizmo/tool/overlay state inspection and mutation.

## Phase 5: Built-In Core Packages

Status: complete as of 2026-06-01.

Targets:
- Entities core package world/system/entity-count inspection.
- Adaptive Performance scaler profile/settings inspection.
- Multiplayer Play Mode package/module and current-player inspection where API surface is stable enough.

Implemented:
- `entities` CLI group and `unity_entities` MCP tool for package/API availability, loaded world listing, default/named world summaries, entity counts, managed system inspection, and bounded archetype/component-type inspection.
- `adaptive-performance` CLI group and `unity_adaptive_performance` MCP tool for module availability, project settings, loader state, scaler profile listing, and scaler setting inspection.
- `multiplayer-playmode` CLI group and `unity_multiplayer_playmode` MCP tool for read-only Multiplayer Play Mode package/module availability, current player role, and current player tags.
- Reflection-safe optional API handling for `com.unity.entities`, `com.unity.adaptiveperformance`, and Multiplayer Play Mode APIs so projects without those packages still compile.

Out of scope:
- Multiplayer Play Mode mutation, clone orchestration, scenario editing, and package installation remain intentionally unsupported until a stable public editor API is proven and separately accepted.

## Validation Gates

- `python3 -m ruff check src/ tests/`
- Targeted pytest suites for each feature.
- Full unit suite before final delivery.
- Unity Bridge compile validation when a Unity project is available.
