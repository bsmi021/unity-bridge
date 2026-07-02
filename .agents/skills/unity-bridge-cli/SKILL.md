---
name: unity-bridge-cli
description: >
  Use for Unity Editor automation through the unity-bridge CLI. Trigger on
  bridge health/status/doctor/install/clean, tests or compile checks,
  scene/hierarchy/component/prefab/asset/material/shader/package/build/settings
  workflows, profiler/editor utilities, operation ledger inspection, or
  Timeline/Cinemachine/Localization/Memory Profiler/VFX asset inspection.
  Prefer CLI commands over raw .claude/unity JSON for retries, timeouts,
  caching, and consistent output.
allowed-tools: Bash(unity-bridge *), Bash(unity-bridge), Read, Grep, Glob, mcp__unity-mcp__*
---

# Unity Bridge CLI

`unity-bridge` communicates with Unity Editor through a file-based bridge protocol.
Every command returns JSON to stdout by default.

## Command Syntax

```
unity-bridge [GLOBAL FLAGS] COMMAND [COMMAND OPTIONS/ARGS]
```

Global flags go BEFORE the command name:

| Global Flag | Short | Purpose |
|-------------|-------|---------|
| `--human` | `-H` | Human-readable output instead of JSON |
| `--pretty` | | Indented JSON output |
| `--verbose` | `-v` | Debug logging to stderr |
| `--quiet` | `-q` | Suppress all non-error output |
| `--timeout SEC` | `-t` | Override default command timeout |
| `--project PATH` | `-p` | Override auto-detected Unity project root |
| `--no-color` | | Disable colored output |

## Core Workflow

1. **Check health**: `unity-bridge status`
2. **Run command**: `unity-bridge [global flags] command [args]`
3. **Parse result**: Check `success` field in JSON output

## Codex Deployment And Scope

- This repo ships the Codex skill from `.agents/skills/unity-bridge-cli`; `unity-bridge install` copies it into target Unity projects.
- Keep the YAML description concise because Codex uses it for skill discovery. Put detailed command coverage in this body and the `references/` files.
- Use the CLI first for anything it covers. It is the only interface with retries, timeouts, bridge health checks, caching, and formatted errors. This repo's own internal MCP interface (a `mcp/` package + `serve` command) has been fully retired — do not reintroduce it. The unrelated third-party `unity-mcp` MCP server (tools prefixed `mcp__unity-mcp__`) may be connected in this environment as a supplemental tool for the specific capability gaps listed in "unity-bridge vs. unity-mcp" below; it bypasses this project's ledger/retry/caching guarantees, so only reach for it when the CLI genuinely cannot do the task.
- If Unity is busy, poll with `unity-bridge operation status COMMAND_ID` or `operation list`.
- If a changed skill is not visible in Codex, start a fresh Codex session before debugging the bridge behavior.
- Before changing this skill or its references, verify the live CLI surface with `unity-bridge --help` and targeted command help.

## unity-bridge vs. unity-mcp (external MCP server)

The third-party `unity-mcp` MCP server (tools prefixed `mcp__unity-mcp__`)
may be connected in this environment. It is a **different, independently
maintained Unity automation server** -- not this project's own retired
internal MCP interface (see "Codex Deployment And Scope" above).

**Default to the `unity-bridge` CLI for everything it covers.** It gives
retries, timeouts, a durable operation ledger with reload recovery, caching,
and consistent JSON. `unity-mcp` mutating calls have none of that.

**Escalate to `unity-mcp` only for capabilities `unity-bridge` genuinely
lacks** (verified in `docs/unity-bridge-audit-and-gap-analysis.md` and
`docs/unity-6.4-capability-delta-analysis.md` -- re-check those if this table
looks stale):

| Need | unity-mcp tool(s) | Why not unity-bridge |
|---|---|---|
| Create/delete C# scripts or perform AST-aware method insert/replace | `Unity_CreateScript`, `Unity_DeleteScript`, `Unity_ManageScript`, `Unity_ValidateScript`, `Unity_FindInFile`, `Unity_Grep` | `script-edit` covers safe line-range and exact-anchor text replacements only, not script creation/deletion or AST-aware edits |
| Generate a texture/material/sprite/animation from an AI prompt | `Unity_AssetGeneration_*` tools | unity-bridge has no generative capability |
| Browse console logs / artifacts as MCP resources rather than one-shot reads | `Unity_ListResources`, `Unity_ReadResource` | unity-bridge has no resources model |

Note: editing an already-imported asset's importer settings (texture, model, or
**audio** import properties like `forceToMono`) is *not* a gap -- `import-settings
set` already reaches `TextureImporter`/`ModelImporter`/`AudioImporter` fields.

For anything not in this table -- hierarchy, components, transforms, scenes,
prefabs, testing, console, playmode, compilation, assets, materials, shaders,
build, settings, packages, undo, lightmaps, and everything else in the
Quick-Scan below -- use `unity-bridge`, even though `unity-mcp` also exposes
overlapping tools (`ManageGameObject`, `ManageScene`, `ManageAsset`,
`ManageShader`, `ManageEditor`, `PackageManager_*`, etc.). Those overlapping
`unity-mcp` tools bypass this project's operation ledger and retry logic, so
they are a strictly worse choice whenever `unity-bridge` already covers the
task.

**After any mutating `unity-mcp` call** (especially script edits), verify
with `unity-bridge test compile` and `unity-bridge console read -T error` --
`unity-mcp` writes bypass the bridge's reload-recovery and won't show up in
`operation status`.

## Decision Tree: "I need to..."

**Inspect the scene:**
- `hierarchy --depth 3` -- see the GameObject tree
- `component get Player Health` -- read component fields
- `transform get Player` -- get position/rotation/scale
- `property list Player BoxCollider` -- list serialized properties

**Modify objects:**
- `component set Player Health -u "currentHp:100"` -- update fields
- `transform set Player -p 5,0,3` -- move object
- `hierarchy create-primitive cube` -- create new object
- `component add Player "AudioSource"` -- add component

**Manage scenes:**
- `scene load Assets/Scenes/Main.unity` -- load scene
- `scene load-additive Assets/Scenes/UI.unity` -- additive load
- `scene save` -- save current scene
- `scene-ext setup save my-layout` -- save multi-scene layout

**Work with prefabs:**
- `prefab instantiate Assets/Prefabs/Enemy.prefab --position 5,0,3`
- `prefab overrides list "Enemy(Clone)"` -- see overrides
- `prefab overrides apply "Enemy(Clone)"` -- apply back to asset

**Test and compile:**
- `test run --platform EditMode` -- run tests
- `test cancel --command-id ID` -- cancel an active bridge-initiated test run
- `test compile` -- trigger compilation
- `coverage availability` / `coverage summarize` -- inspect optional Code Coverage support and reports
- `coverage install` -- add `com.unity.testtools.codecoverage` when a project is missing it
- `tdd --filter CombatTests` -- full TDD cycle
- `console read --types error` -- check for errors

**Build:**
- `build -T StandaloneWindows64 -o builds/` -- build project
- `profile list` / `profile set` -- manage build profiles
- `profile scenes PATH` / `profile defines PATH` -- inspect profile content
- `profile build PATH --output builds/` -- build through a Unity 6 build profile
- `build-scenes add Assets/Scenes/Main.unity` -- manage build scenes

**Assets and imports:**
- `asset find --type Prefab --pattern "Enemy*"` -- search assets
- `asset-ext deps Assets/Prefabs/Player.prefab` -- dependencies
- `import-settings set path -s "maxTextureSize:512"` -- change import
- `material modify path --properties '{...}'` -- edit materials
- `package list --source git` -- enumerate packages by source
- `package batch --add com.unity.inputsystem --remove com.unity.timeline` -- one package solve
- `package pack Packages/com.company.tools Build/Packages` -- create a UPM .tgz
- `addressables profiles` / `addressables labels` -- inspect Addressables metadata

**Author UI and input assets:**
- `ui-toolkit list-documents` -- find UIDocument components
- `ui-toolkit inspect-uxml Assets/UI/Hud.uxml` -- inspect UXML structure
- `ui-toolkit create-panel-settings Assets/UI/Panel.asset` -- create PanelSettings
- `input-system create Assets/Input/Game.inputactions --overwrite` -- create input asset
- `input-system add-map PATH Player --overwrite` -- add or replace action map
- `input-system add-action PATH --map Player --name Jump --binding "<Keyboard>/space"`
- `input-system add-control-scheme PATH --name Gamepad --device "<Gamepad>"`

**Settings and config:**
- `settings get` / `settings set key value` -- player settings
- `physics get` / `physics set -g "0,-9.81,0"` -- physics
- `quality list` / `quality set-level 2` -- quality levels
- `editor-config get` / `editor-config set key value` -- editor settings
- `render-pipeline current` / `render-pipeline inspect PATH` -- pipeline state
- `graphics-state begin-trace` / `graphics-state end-trace-save PATH` -- PSO trace
- `scene-state get` / `scene-state list-overlays` -- editor view state

**Editor utilities:**
- `console read -T error` / `console clear` -- console
- `playmode play` / `pause` / `stop` -- play mode
- `refresh` -- refresh asset database
- `undo perform` / `undo redo` -- undo/redo

**Create/delete scripts, perform AST-aware script edits, or generate assets
from a prompt:** unity-bridge does not support these -- see
"unity-bridge vs. unity-mcp" above for the matching `mcp__unity-mcp__*`
tool. For line-range or exact-anchor MonoScript text edits, use
`script-edit`.
- `object-identity selection` / `object-identity resolve --asset-path PATH` -- IDs
- `project-auditor run --output PATH` -- run Project Auditor if available
- `search query "t:Material"` -- query Unity Search
- `sync-solution` -- regenerate `.sln` / `.csproj`

**Inspect Unity 6.4 package surfaces:**
- `entities availability` / `entities list-worlds` -- Entities package and worlds
- `entities list-systems --world "Default World"` -- managed systems
- `entities list-archetypes --max-archetypes 25` -- ECS archetypes
- `graph-toolkit list-assets` / `graph-toolkit inspect PATH` -- graph assets
- `adaptive-performance settings` -- Adaptive Performance project state
- `multiplayer-playmode current-player` -- local MPP role/tags

**Author Timeline, Cinemachine, Localization; inspect Memory/VFX (package-provided systems):**
- `timeline create-track ASSET_PATH AnimationTrack` -- add a track (requires com.unity.timeline)
- `timeline create-clip ASSET_PATH TRACK_INDEX` -- add a clip on that track
- `timeline get-clips ASSET_PATH TRACK_INDEX` -- list clips (re-query after any mutation, indices shift)
- `timeline evaluate DIRECTOR_PATH --time 2.5` -- scrub a PlayableDirector
- `cinemachine list-cameras` -- full scene enumeration, including inactive cameras (requires com.unity.cinemachine 3.x)
- `cinemachine set-priority CAMERA_PATH 20` / `cinemachine set-lens CAMERA_PATH --fov 50`
- `cinemachine active` -- current live/blended camera via CinemachineBrain
- `localization list-locales` / `add-locale fr` / `set-selected-locale de` (requires com.unity.localization)
- `localization create-string-table-collection MyStrings` / `add-entry MyStrings greeting "Hello"`
- `localization export-csv MyStrings out.csv` / `import-csv MyStrings in.csv`
- `memory-profiler take-snapshot --path out.snap` -- capture only, no live Unity instance needed beyond the bridge itself; load/diff of `.snap` files has no public Unity API and is out of scope
- `vfx get-info --asset-path Assets/VFX/Explosion.vfx` -- read-only event names + exposed properties (requires com.unity.visualeffectgraph); graph authoring has no public API, do not attempt it

## Quick-Scan: All Command Groups

```bash
# Diagnostics & Lifecycle
unity-bridge status                    # Quick alive/dead check
unity-bridge doctor                    # Full 9-check diagnostics
unity-bridge version                   # CLI versions
unity-bridge install [--check|--force|--include-claude] # Install/update C# bridge + project skill
unity-bridge init                      # Create directory structure
unity-bridge clean [--dry-run]         # Remove orphaned/stale bridge state files
unity-bridge operation status COMMAND_ID | operation list
unity-bridge profiler --memory --cpu   # Performance snapshot
unity-bridge profiler-control set-areas --areas Physics,Audio [--allocation-callstacks]
unity-bridge profiler-frame top-time-samples FRAME_INDEX [--count N]
unity-bridge profiler-frame gc-alloc [--frame N | --start N --end N]

# Hierarchy & GameObjects
unity-bridge hierarchy [--depth N] [--root PATH] [--inactive]
unity-bridge hierarchy missing-scripts [--fix]
unity-bridge hierarchy static-flags PATH | set-static-flags PATH FLAGS...
unity-bridge hierarchy set-layer PATH N [-r] | set-tag PATH TAG
unity-bridge hierarchy duplicate PATH | create-primitive TYPE [-n NAME]
unity-bridge hierarchy set-active PATH [--inactive|--active]

# Selection & Transform
unity-bridge selection [--components] | select PATH... [--clear]
unity-bridge transform get PATH | set PATH [-p X,Y,Z] [-r X,Y,Z] [-s X,Y,Z]
unity-bridge transform parent CHILD [PARENT] | sibling-index PATH N

# Components & Properties
unity-bridge component get PATH TYPE [--fields F] [--deep]
unity-bridge component set PATH TYPE -u "field:value"
unity-bridge component add|remove|enable|disable PATH TYPE
unity-bridge property list|get|set PATH TYPE [PROP] [VALUE]

# Scenes
unity-bridge scene load|save|create PATH [--save-current] [--additive]
unity-bridge scene load-additive|unload|set-active|move-object PATH
unity-bridge scene-ext setup save|restore|list NAME
unity-bridge scene-ext play-start [--set PATH|--clear] | cross-refs | list-loaded

# Prefabs
unity-bridge prefab validate|instantiate|destroy|status|find-instances|unpack PATH
unity-bridge prefab overrides list|apply|revert PATH [-t TARGET]

# Testing & TDD
unity-bridge test run [--platform P] [--filter F] [--test-name NAME] [--group REGEX] [--category CAT] [--assembly ASM] [--min-tests N] [--timeout N]
unity-bridge test cancel [--command-id ID] [--timeout N]
unity-bridge test preflight [--platform P] [--filter F] [--min-tests N]
unity-bridge test list [--categories] [--assemblies] | compile [--no-wait]
unity-bridge test results|failures|progress|events [--last|--command-id ID] | rerun-failed [--last|--command-id ID] | history [--max-results N]
unity-bridge coverage availability | install [--version V]
unity-bridge coverage start|pause|resume|stop | find-reports | summarize [PATH]
unity-bridge tdd [--platform P] [--filter F] [--strict]

# Console & Play Mode
unity-bridge console read [-T types] [-m max] [-p pattern] [--stack-trace]
unity-bridge console watch [-T types] | clear | log MSG [-t type]
unity-bridge playmode play|pause|stop

# Compilation
unity-bridge compile assemblies | defines ASM | which SCRIPT | optimization [--set]

# Editor Utilities
unity-bridge refresh [--force] | focus PATH | menu "Menu/Path"
unity-bridge screenshot PATH [--width W --height H --camera CAM] [--inline-base64] [--multi-angle]
unity-bridge script "expression" | --file PATH
unity-bridge script-edit range PATH --start-line N --end-line N -r TEXT [--if-match SHA]
unity-bridge script-edit anchor PATH -a ANCHOR -r TEXT [-n OCCURRENCE] [--if-match SHA]
unity-bridge sync-solution
unity-bridge search query "t:Material" | providers

# Assets & Import
unity-bridge asset find|query|import|refresh [--type T] [--path P] [--pattern P]
unity-bridge asset-ext create|delete|copy|move|deps|guid|hash|export|import-package|import-model
unity-bridge import-settings get|set|reimport|bulk-set|template-save|template-apply
unity-bridge material ACTION PATH [--properties JSON]
unity-bridge shader list|info|errors|properties|find-by-property|keywords NAME
unity-bridge addressables profiles|set-profile|labels|set-label|schemas|analyze

# Build & Deploy
unity-bridge build [-T target] [-o path] [--dev] [--compress] [--scenes]
unity-bridge profile list|active|create|set|info|scenes|set-scenes|defines|set-defines|build
unity-bridge build-scenes list|add|remove|enable|disable PATH

# Settings & Config
unity-bridge settings get [KEY] | set KEY VALUE | defines list|add|remove
unity-bridge physics get|set [-g X,Y,Z] | collision get|set L1 L2
unity-bridge physics2d get|set|matrix|set-collision
unity-bridge quality list|get|set-level N
unity-bridge tags list|add | layers list|add [-i N] | sorting-layers list|add
unity-bridge editor-config get|set KEY VALUE
unity-bridge prefs get|set|delete|has KEY [-t type] [-s scope]
unity-bridge time-settings get|set | audio-settings get|set
unity-bridge graphics-settings get|set | environment-settings get|set
unity-bridge cloud project-id|environments|active-environment

# Packages & Undo
unity-bridge package list [--source registry|git|embedded|local]
unity-bridge package search QUERY [--all]
unity-bridge package add IDENTIFIER
unity-bridge package batch [--add IDENTIFIER] [--remove NAME]
unity-bridge package remove|info|embed NAME
unity-bridge package pack PACKAGE_FOLDER TARGET_FOLDER
unity-bridge package clear-cache --yes
unity-bridge package resolve
unity-bridge undo perform|redo|history|clear|group-name|collapse
unity-bridge lightmap bake|cancel|clear|status|settings|set-settings
unity-bridge batch FILE [--parallel] [--no-stop-on-error]

# Authoring Systems
unity-bridge ui-toolkit list-documents|inspect-uxml|inspect-uss|create-uxml
unity-bridge ui-toolkit create-panel-settings|add-document
unity-bridge input-system list|get|export|import|create
unity-bridge input-system add-map|add-action|add-binding|add-control-scheme
unity-bridge input-system control-schemes

# Unity 6.4 Editor and Built-in Package Surfaces
unity-bridge object-identity selection|resolve|ping
unity-bridge project-auditor availability|run|load
unity-bridge render-pipeline list-assets|current|set-default|set-quality|inspect
unity-bridge graphics-state create|info|begin-trace|end-trace-save|warmup
unity-bridge graphics-state clear-variants
unity-bridge graph-toolkit availability|list-assets|inspect|export
unity-bridge scene-state get|set|reset-snap|list-overlays
unity-bridge entities availability|list-worlds|world-summary|list-systems
unity-bridge entities list-archetypes
unity-bridge adaptive-performance availability|settings|list-profiles|inspect-profile
unity-bridge multiplayer-playmode availability|current-player|packages

# Package-Provided Systems (Timeline, Cinemachine, Localization, Memory Profiler, VFX)
unity-bridge timeline create-track PATH TRACK_TYPE [--track-name NAME]
unity-bridge timeline create-clip PATH TRACK_INDEX [--clip-asset-path PATH]
unity-bridge timeline get-clips PATH TRACK_INDEX | get-info PATH
unity-bridge timeline delete-clip PATH TRACK_INDEX CLIP_INDEX
unity-bridge timeline evaluate DIRECTOR_PATH [--time SEC] [--timeline-asset-path PATH]
unity-bridge cinemachine list-cameras | info CAMERA_PATH | active
unity-bridge cinemachine set-priority CAMERA_PATH VALUE
unity-bridge cinemachine set-lens CAMERA_PATH [--fov F] [--ortho-size S] [--near-clip N] [--far-clip F] [--dutch D]
unity-bridge cinemachine set-follow|set-lookat CAMERA_PATH TARGET_PATH
unity-bridge localization list-locales | add-locale|remove-locale CODE
unity-bridge localization get-selected-locale | set-selected-locale CODE
unity-bridge localization create-string-table-collection|get-string-table-collection NAME
unity-bridge localization add-entry NAME KEY VALUE
unity-bridge localization export-csv|import-csv NAME FILE_PATH
unity-bridge localization export-xliff|import-xliff NAME FILE_PATH
unity-bridge memory-profiler take-snapshot [--path PATH] [--capture-flags F1,F2]
unity-bridge vfx get-info [--asset-path PATH | --guid GUID]
```

## Common Multi-Step Patterns

### TDD Cycle
```bash
unity-bridge console clear && unity-bridge test compile && unity-bridge test run -P EditMode -f "Combat*" && unity-bridge --human console read -T error
```

### Scene Investigation
```bash
unity-bridge hierarchy --depth 2
unity-bridge component get Player Health
unity-bridge transform get Player
```

### Prefab Workflow
```bash
unity-bridge prefab instantiate Assets/Prefabs/Enemy.prefab --position 5,0,3
unity-bridge component set "Enemy(Clone)" Health -u "maxHp:200"
unity-bridge prefab overrides apply "Enemy(Clone)"
```

### Multi-Scene Setup
```bash
unity-bridge scene load Assets/Scenes/Main.unity
unity-bridge scene load-additive Assets/Scenes/UI.unity
unity-bridge scene set-active Assets/Scenes/Main.unity
unity-bridge scene-ext setup save my-layout
```

## Output Format

All commands return JSON by default:
```json
{"success": true, "data": {...}, "command_id": "uuid", "execution_time_ms": 123}
```

On failure:
```json
{"success": false, "error": "message", "exit_code": 1}
```

## Exit Codes

| Code | Meaning | What to Do |
|------|---------|------------|
| 0 | Success | Proceed normally |
| 1 | Command failed | Read `error` field for details |
| 2 | Bridge unavailable | Run `unity-bridge doctor`, check Unity is open |
| 3 | Invalid input | Check your arguments |
| 4 | Timeout | Use `-t SEC` with a higher value |
| 5 | Internal error | Check logs with `-v` |
| 130 | Interrupted | User pressed Ctrl+C |

## Configuration

| Variable | Purpose |
|----------|---------|
| `UNITY_BRIDGE_PROJECT` | Override project root path |
| `UNITY_BRIDGE_LOG_LEVEL` | Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL, OFF) |
| `UNITY_BRIDGE_TIMEOUT` | Default timeout in seconds |
| `UNITY_BRIDGE_CONFIG` | Path to config JSON file |
| `NO_COLOR` | Disable colored output (any value) |

Precedence: CLI flags > environment variables > config file > defaults.

## Domain Reference Files

For detailed argument tables, types, defaults, and examples, read the appropriate reference:

| I need... | Read this reference |
|-----------|-------------------|
| Scene loading, saving, multi-scene, scene view | [references/scene-commands.md](references/scene-commands.md) |
| Components, properties, serialization, copy/paste | [references/component-commands.md](references/component-commands.md) |
| Assets, import settings, materials, shaders, presets | [references/asset-commands.md](references/asset-commands.md) |
| Building, profiles, build scenes, platform switch, structured build reports | [references/build-commands.md](references/build-commands.md) |
| Player settings, physics, Physics2D, quality, time, graphics, render pipeline, audio, tags, layers, prefs | [references/settings-commands.md](references/settings-commands.md) |
| NavMesh, animation, terrain, tilemap, addressables, Project Auditor, Graph Toolkit, Entities, Adaptive Performance, Multiplayer Play Mode, Timeline, Cinemachine, Localization, Memory Profiler, VFX asset inspection | [references/specialized-commands.md](references/specialized-commands.md) |
| Profiler, game view, scene view, scene state, clipboard, windows, UI Toolkit, input system, execution order, scripts, object identity, search, sync solution | [references/tools-commands.md](references/tools-commands.md) |

## Notes

- Unity Editor must be open with ClaudeUnityBridge active.
- If `unity-bridge status` shows unhealthy, run `unity-bridge doctor`.
- `unity-bridge install` deploys both the C# bridge and this skill to the Unity project; the canonical skill target is `.agents/skills/unity-bridge-cli`. Codex and GitHub Copilot both scan `.agents/skills` natively, so no further step is needed for them. Claude Code only scans `.claude/skills`, so pass `--include-claude` to also create `.claude/skills/unity-bridge-cli` as a symlink (or an NTFS junction on Windows when symlink privilege is unavailable) back to the canonical directory -- one physical skill, reused across agents.
- Runtime bridge files live under `.claude/unity/`; do not write raw command JSON there unless you are debugging the bridge protocol itself.
- In-flight command lifecycle state lives under `.claude/unity/operations/`; use `unity-bridge operation status COMMAND_ID` or `operation list` to inspect accepted/running/recovered commands.
- `unity-bridge clean` prunes orphaned command/response files, stale `*.tmp` bridge files, and old terminal operation records while preserving active operation records.
- Asset paths use forward slashes relative to project root: `Assets/Scenes/Main.unity`.
- The `-u` flag is shorthand for `--update` on `component set`. Pass multiple: `-u "a:1" -u "b:2"`.
- The `-s` flag on `import-settings` is `--setting`; on `prefs` it is `--scope`.
- The `-t` flag on `prefs` and `console log` is `--type`, not the global `--timeout`.
- `compile` is a query group (assemblies/defines/which/optimization). Use `test compile` to trigger compilation.
- Timeouts vary by command (5s reads, 300s tests, 600s builds). Override with `-t SEC`.
- `UNITY_BRIDGE_EDITOR_READY_TIMEOUT` controls editor readiness waits; `UNITY_BRIDGE_IN_FLIGHT_BUSY_GRACE` controls how long active in-flight work keeps the bridge marked busy.
