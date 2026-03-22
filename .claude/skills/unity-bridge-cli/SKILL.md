---
name: unity-bridge-cli
description: >
  Use this skill for ANY Unity Editor interaction from the command line. Trigger
  on: unity-bridge, run tests, compile Unity, check hierarchy, get component,
  set component, add component, remove component, enable component, disable
  component, load scene, save scene, create scene, additive scene, unload scene,
  move object scene, enter play mode, pause play mode, stop play mode, read
  console, watch console, clear console, log message, take screenshot, build
  project, build target, execute C# expression, script expression, TDD workflow,
  is Unity running, health check, doctor diagnostics, install bridge, clean
  orphaned files, list packages, add package, remove package, search package,
  bake lightmaps, lightmap settings, shader info, shader keywords, shader errors,
  shader properties, undo, redo, undo history, import settings, reimport asset,
  bulk import, import template, quality settings, scene setup, scene layout,
  cross-scene references, asset dependencies, asset guid, create asset, delete
  asset, copy asset, move asset, export unitypackage, select objects, clear
  selection, transform position, transform rotation, transform scale, reparent,
  sibling index, serialized property, editor prefs, session state, build scenes,
  physics settings, gravity, collision matrix, quality level, tags, layers,
  sorting layers, editor config, duplicate object, missing scripts, static flags,
  create primitive, set active, activate deactivate, prefab instantiate, prefab
  validate, prefab overrides, unpack prefab, destroy prefab, find prefab instances,
  build profile, player settings, scripting defines, compile assemblies, compile
  defines, compile which, compile optimization, animator state, animator params,
  asset find, asset query, material modify, material create, material duplicate,
  batch commands, MCP server, profiler metrics, focus gameobject, menu item,
  refresh assets, editor selection, preview scene, play start scene, set layer,
  set tag, component data, move to scene, folder create, folder list, embed
  package, resolve packages, navmesh bake, animation clip, terrain, tilemap,
  addressables, reflection probes, occlusion culling, time settings, graphics
  settings, environment fog, audio settings, game view, scene view camera,
  clipboard, presets, scene templates, script info, deep serialize, window
  management, input system, execution order, assembly lock, find references,
  component copy, component paste, component reset, material keywords, or any
  request involving an open Unity Editor.
  Also trigger when about to write raw JSON to .claude/unity/commands/ -- use
  the CLI instead for retries, timeouts, caching, and error formatting.
allowed-tools: Bash(unity-bridge *), Bash(unity-bridge), Read, Grep, Glob
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
- `test compile` -- trigger compilation
- `tdd --filter CombatTests` -- full TDD cycle
- `console read --types error` -- check for errors

**Build:**
- `build -T StandaloneWindows64 -o builds/` -- build project
- `profile list` / `profile set` -- manage build profiles
- `build-scenes add Assets/Scenes/Main.unity` -- manage build scenes

**Assets and imports:**
- `asset find --type Prefab --pattern "Enemy*"` -- search assets
- `asset-ext deps Assets/Prefabs/Player.prefab` -- dependencies
- `import-settings set path -s "maxTextureSize:512"` -- change import
- `material modify path --properties '{...}'` -- edit materials

**Settings and config:**
- `settings get` / `settings set key value` -- player settings
- `physics get` / `physics set -g "0,-9.81,0"` -- physics
- `quality list` / `quality set-level 2` -- quality levels
- `editor-config get` / `editor-config set key value` -- editor settings

**Editor utilities:**
- `console read -T error` / `console clear` -- console
- `playmode play` / `pause` / `stop` -- play mode
- `refresh` -- refresh asset database
- `undo perform` / `undo redo` -- undo/redo

## Quick-Scan: All Command Groups

```bash
# Diagnostics & Lifecycle
unity-bridge status                    # Quick alive/dead check
unity-bridge doctor                    # Full 9-check diagnostics
unity-bridge version                   # CLI versions
unity-bridge install [--check|--force] # Install/update C# bridge
unity-bridge init                      # Create directory structure
unity-bridge clean [--dry-run]         # Remove orphaned files
unity-bridge serve                     # Start MCP server
unity-bridge profiler --memory --cpu   # Performance snapshot

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
unity-bridge test run [--platform P] [--filter F] [--timeout N]
unity-bridge test list [--categories] [--assemblies] | compile [--no-wait]
unity-bridge tdd [--platform P] [--filter F] [--strict]

# Console & Play Mode
unity-bridge console read [-T types] [-m max] [-p pattern] [--stack-trace]
unity-bridge console watch [-T types] | clear | log MSG [-t type]
unity-bridge playmode play|pause|stop

# Compilation
unity-bridge compile assemblies | defines ASM | which SCRIPT | optimization [--set]

# Editor Utilities
unity-bridge refresh [--force] | focus PATH | menu "Menu/Path"
unity-bridge screenshot PATH [--width W --height H --camera CAM]
unity-bridge script "expression" | --file PATH

# Assets & Import
unity-bridge asset find|query|import|refresh [--type T] [--path P] [--pattern P]
unity-bridge asset-ext create|delete|copy|move|deps|guid|export|import-package
unity-bridge import-settings get|set|reimport|bulk-set|template-save|template-apply
unity-bridge material ACTION PATH [--properties JSON]
unity-bridge shader list|info|errors|properties|find-by-property|keywords NAME

# Build & Deploy
unity-bridge build [-T target] [-o path] [--dev] [--compress] [--scenes]
unity-bridge profile list|active|set|info PATH
unity-bridge build-scenes list|add|remove|enable|disable PATH

# Settings & Config
unity-bridge settings get [KEY] | set KEY VALUE | defines list|add|remove
unity-bridge physics get|set [-g X,Y,Z] | collision get|set L1 L2
unity-bridge quality list|get|set-level N
unity-bridge tags list|add | layers list|add [-i N] | sorting-layers list|add
unity-bridge editor-config get|set KEY VALUE
unity-bridge prefs get|set|delete|has KEY [-t type] [-s scope]

# Packages & Undo
unity-bridge package list|search|add|remove|info|embed|resolve
unity-bridge undo perform|redo|history|clear|group-name|collapse
unity-bridge lightmap bake|cancel|clear|status|settings|set-settings
unity-bridge batch FILE [--parallel] [--no-stop-on-error]
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

For full argument tables, types, defaults, and examples, read the appropriate reference:

| I need... | Read this reference |
|-----------|-------------------|
| Scene loading, saving, multi-scene, scene view | [references/scene-commands.md](references/scene-commands.md) |
| Components, properties, serialization, copy/paste | [references/component-commands.md](references/component-commands.md) |
| Assets, import settings, materials, shaders, presets | [references/asset-commands.md](references/asset-commands.md) |
| Building, profiles, build scenes, platform switch | [references/build-commands.md](references/build-commands.md) |
| Player settings, physics, quality, time, graphics, audio, tags, layers, prefs | [references/settings-commands.md](references/settings-commands.md) |
| NavMesh, animation, terrain, tilemap, addressables, reflection probes, occlusion | [references/specialized-commands.md](references/specialized-commands.md) |
| Profiler, game view, clipboard, windows, input system, execution order, scripts | [references/tools-commands.md](references/tools-commands.md) |
| Complete single-file reference (all commands, all args) | [references/command-reference.md](references/command-reference.md) |

## Notes

- Unity Editor must be open with ClaudeUnityBridge active.
- If `unity-bridge status` shows unhealthy, run `unity-bridge doctor`.
- Asset paths use forward slashes relative to project root: `Assets/Scenes/Main.unity`.
- The `-u` flag is shorthand for `--update` on `component set`. Pass multiple: `-u "a:1" -u "b:2"`.
- The `-s` flag on `import-settings` is `--setting`; on `prefs` it is `--scope`.
- The `-t` flag on `prefs` and `console log` is `--type`, not the global `--timeout`.
- `compile` is a query group (assemblies/defines/which/optimization). Use `test compile` to trigger compilation.
- Timeouts vary by command (5s reads, 300s tests, 600s builds). Override with `-t SEC`.
