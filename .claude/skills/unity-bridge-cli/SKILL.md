---
name: unity-bridge-cli
description: >
  Use this skill whenever you need to interact with Unity Editor from the command
  line or from scripts. Trigger on phrases like "run tests", "compile Unity",
  "check the hierarchy", "get component data", "set component value", "load scene",
  "enter play mode", "read console", "take screenshot", "build for Android",
  "execute C# in Unity", "TDD workflow", "watch for changes", "snapshot the scene",
  "is Unity running", "install bridge", "clean orphaned files",
  "manage packages", "add package", "remove package", "list packages",
  "build profiles", "player settings", "scripting defines",
  "create asset", "delete asset", "copy asset", "move asset", "asset dependencies",
  "export package", "import package",
  "undo", "redo", "undo history",
  "list assemblies", "compilation defines",
  "prefab overrides", "apply overrides", "revert overrides", "prefab status",
  "find prefab instances", "unpack prefab",
  "list tests", "test categories",
  "missing scripts", "static flags", "set layer", "set tag",
  "shader list", "shader errors", "shader properties", "shader keywords",
  "bake lightmaps", "lightmap status",
  "import settings", "bulk import", "import template",
  "scene setup", "save scene layout", "restore scene layout",
  "play start scene", "cross-scene references", "preview scene",
  or any request that involves communicating with an open Unity Editor.
  Also trigger proactively whenever you are about to write raw JSON command files
  to .claude/unity/commands/ -- use the CLI instead, it handles retries, timeouts,
  caching, and error formatting automatically. If you need to do anything in Unity
  Editor and it is open, reach for this skill first.
---

# Unity Bridge CLI

`unity-bridge` is a command-line tool that communicates with Unity Editor through a
file-based bridge protocol. It replaces the need to write raw JSON command files or
use the MCP server directly. Every command returns JSON to stdout by default (pipe
to `jq` for filtering), or use `--human` for formatted output.

## Quick Start

```bash
unity-bridge status                      # Is Unity alive?
unity-bridge test run --platform EditMode # Run tests
unity-bridge tdd --filter MyTests        # Clear -> compile -> test -> console
unity-bridge hierarchy --depth 3         # Inspect scene tree
unity-bridge console watch               # Tail logs in real-time
unity-bridge package list                # List installed packages
unity-bridge shader list --errors-only   # Find broken shaders
unity-bridge undo history                # View recent operations
```

## When to Use Which Command

### "I need to verify code changes work"
```bash
unity-bridge tdd --platform EditMode --filter MyTests   # Full workflow
unity-bridge test run --platform EditMode                # Just run tests
unity-bridge test compile --wait                         # Just check compilation
unity-bridge compile assemblies                          # Which assemblies exist?
unity-bridge compile which Assets/Scripts/Player.cs      # Which assembly owns this?
```

### "I need to inspect the scene"
```bash
unity-bridge hierarchy --depth 3                         # Full tree
unity-bridge hierarchy --root "Player" --depth 2         # Subtree
unity-bridge component get Player Transform              # Read fields
unity-bridge selection --components                      # What is selected?
unity-bridge scene-ext list-loaded                       # All open scenes
unity-bridge scene-ext cross-refs                        # Cross-scene refs
```

### "I need to modify scene state"
```bash
unity-bridge component set Player Health --update 'currentHp:100'
unity-bridge component add Enemy "EnemyAI"
unity-bridge prefab instantiate Assets/Prefabs/Enemy.prefab --position 5,0,3
unity-bridge scene load Assets/Scenes/Main.unity --save-current
unity-bridge hierarchy set-layer Player 8 --recursive
unity-bridge hierarchy set-tag Player "Enemy"
unity-bridge hierarchy set-static-flags Terrain BatchingStatic NavigationStatic
```

### "I need to debug"
```bash
unity-bridge console read --types error,warning --max 20
unity-bridge console watch --types error                 # Follow mode
unity-bridge playmode play                               # Enter play mode
unity-bridge profiler --memory --rendering               # Performance snapshot
unity-bridge shader errors "Universal Render Pipeline/Lit"
unity-bridge hierarchy missing-scripts --fix             # Find/remove missing scripts
unity-bridge lightmap status                             # Bake progress
```

### "I need to manage the project"
```bash
unity-bridge status                    # Health check
unity-bridge doctor                    # Full diagnostics (9 checks)
unity-bridge install                   # Install/update C# bridge
unity-bridge clean                     # Remove orphaned command files
unity-bridge build --target StandaloneWindows64
unity-bridge refresh --force           # Force reimport assets
unity-bridge package list              # Installed packages
unity-bridge package add com.unity.textmeshpro@3.0.6
unity-bridge settings get companyName  # Player settings
unity-bridge profile list              # Build profiles (Unity 6)
```

### "I need to work with assets"
```bash
unity-bridge asset find --type Prefab --pattern "Enemy*"
unity-bridge asset-ext create Assets/Data/Config.asset --type ScriptableObject
unity-bridge asset-ext copy Assets/Mats/Old.mat Assets/Mats/New.mat
unity-bridge asset-ext deps Assets/Prefabs/Player.prefab
unity-bridge asset-ext guid Assets/Scripts/Player.cs
unity-bridge asset-ext export Assets/Scenes/ --output export.unitypackage
unity-bridge import-settings get Assets/Textures/Albedo.png
unity-bridge import-settings bulk-set Assets/Textures/ -s maxTextureSize:1024 --filter "*.png"
```

### "I need to manage prefabs"
```bash
unity-bridge prefab validate Assets/Prefabs/Player.prefab
unity-bridge prefab status Player
unity-bridge prefab overrides list Player
unity-bridge prefab overrides apply Player
unity-bridge prefab overrides revert Player --target "Transform"
unity-bridge prefab find-instances Assets/Prefabs/Enemy.prefab
unity-bridge prefab unpack Player --completely
```

### "I need to undo/redo"
```bash
unity-bridge undo perform           # Undo last operation
unity-bridge undo redo              # Redo
unity-bridge undo history --limit 10
unity-bridge undo clear             # WARNING: clears ALL editor undo history
unity-bridge undo group-name        # Current undo group
unity-bridge undo collapse 5 --name "Batch edit"
```

### "I need to automate or script"
```bash
unity-bridge script "EditorApplication.isPlaying"
unity-bridge script --file setup.cs
unity-bridge batch commands.json --parallel
unity-bridge snapshot save before.json --depth 3
unity-bridge snapshot diff before.json after.json
unity-bridge scene-ext setup save my-layout
unity-bridge scene-ext setup restore my-layout
```

## Global Flags

Every command accepts these flags:

| Flag | Short | Purpose |
|------|-------|---------|
| `--project PATH` | `-p` | Override auto-detected Unity project root |
| `--human` | `-H` | Human-readable output instead of JSON |
| `--pretty` | | Indented JSON output |
| `--verbose` | `-v` | Debug logging to stderr |
| `--quiet` | `-q` | Suppress non-error output |
| `--timeout SEC` | `-t` | Override default command timeout |
| `--no-color` | | Disable colored output |

## Command Groups Overview

| Group | CLI Name | Description |
|-------|----------|-------------|
| Testing | `test` | Run tests, compile, list tests |
| Hierarchy | `hierarchy` | Scene tree, static flags, layers, tags, missing scripts |
| Components | `component` | Get/set/add component data |
| Scene | `scene` | Load, save, create scenes |
| Scene Extended | `scene-ext` | Multi-scene layouts, cross-refs, preview scenes |
| Prefab | `prefab` | Validate, instantiate, destroy, overrides, status, unpack |
| Play Mode | `playmode` | Play, pause, stop |
| Console | `console` | Read, watch, clear logs |
| Editor | `selection`, `refresh`, `focus`, `menu`, `screenshot` | Editor utilities |
| Asset | `asset` | Find, query, import, refresh assets |
| Asset Extended | `asset-ext` | Create, delete, copy, move, deps, guid, folders, export/import |
| Material | `material` | Modify, create, duplicate materials |
| Build | `build` | Build for target platforms |
| Build Profiles | `profile` | List, get/set active, info (Unity 6) |
| Animator | `animator` | State machine and parameter control |
| Settings | `settings` | Player settings, scripting defines |
| Package | `package` | List, search, add, remove, info, embed, resolve |
| Compile | `compile` | Assembly listing, defines, which-assembly, optimization |
| Undo | `undo` | Undo, redo, history, clear, collapse |
| Shader | `shader` | List, info, errors, properties, keywords |
| Lightmap | `lightmap` | Bake, cancel, clear, status, settings |
| Import Settings | `import-settings` | Get/set/reimport, bulk-set, templates |
| Scripting | `script` | Execute C# expressions |
| Workflow | `tdd`, `test watch` | TDD cycle, file watcher |
| Snapshot | `snapshot` | Save/diff scene state |
| Batch | `batch` | Multi-command execution |
| Diagnostics | `status`, `doctor`, `profiler` | Health checks, diagnostics |
| Lifecycle | `install`, `init`, `clean`, `version` | Bridge management |
| Serve | `serve` | MCP server mode |

## Command Reference

For full details on every command, argument, option, and default, see:
- `references/command-reference.md`

## Output Format

All commands return JSON by default:

```json
{"success": true, "data": {...}, "command_id": "uuid", "execution_time_ms": 123}
```

On failure:

```json
{"success": false, "error": "message", "exit_code": 1}
```

Parse `success` to determine if the command worked. All keys are `snake_case`.

## Exit Codes

| Code | Meaning | What to Do |
|------|---------|------------|
| 0 | Success | Proceed normally |
| 1 | Command failed | Read `error` field for details |
| 2 | Bridge unavailable | Run `unity-bridge doctor`, check Unity is open |
| 3 | Invalid input | Check your arguments |
| 4 | Timeout | Increase `--timeout` or check if Unity is frozen |
| 5 | Internal error | Report bug |
| 130 | Interrupted | User pressed Ctrl+C |

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `UNITY_BRIDGE_PROJECT` | Override project root path |
| `UNITY_BRIDGE_LOG_LEVEL` | Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL, OFF) |
| `UNITY_BRIDGE_TIMEOUT` | Default timeout in seconds |
| `UNITY_BRIDGE_CONFIG` | Path to config JSON file |
| `NO_COLOR` | Disable colored output (any value) |

## Configuration Precedence

CLI flags > environment variables > config file > defaults.

Config file search order:
1. `$UNITY_BRIDGE_CONFIG`
2. `<project_root>/unity_bridge_config.json`
3. `<project_root>/.claude/unity_bridge_config.json`

## Common Workflows

### TDD Cycle
The `tdd` command chains: clear console -> compile -> run tests -> read console (on failure).
```bash
unity-bridge tdd --platform EditMode --filter CombatTests
```

### Watch Mode
Auto-rerun tests when .cs files change (requires `watchfiles`):
```bash
unity-bridge test watch --platform EditMode --filter CombatTests --path Assets/Scripts/
```

### Scene State Comparison
```bash
unity-bridge snapshot save before.json --depth 3
unity-bridge snapshot save after.json --depth 3
unity-bridge snapshot diff before.json after.json
```

### Package Management
```bash
unity-bridge package list
unity-bridge package list --source git
unity-bridge package search "input system"
unity-bridge package add com.unity.inputsystem@1.7.0
unity-bridge package remove com.unity.textmeshpro
unity-bridge package info com.unity.inputsystem
unity-bridge package embed com.unity.inputsystem
unity-bridge package resolve
```

### Shader Debugging
```bash
unity-bridge shader list --errors-only
unity-bridge shader errors "Custom/MyShader"
unity-bridge shader properties "Universal Render Pipeline/Lit"
unity-bridge shader find-by-property "_MainTex"
unity-bridge shader keywords "Custom/MyShader" --filter global
```

### Lightmap Baking
```bash
unity-bridge lightmap settings
unity-bridge lightmap bake
unity-bridge lightmap status
unity-bridge lightmap cancel
unity-bridge lightmap bake --no-run-async
unity-bridge lightmap clear
```

### Import Standardization
```bash
unity-bridge import-settings get Assets/Textures/Hero.png
unity-bridge import-settings set Assets/Textures/Hero.png -s maxTextureSize:2048
unity-bridge import-settings reimport Assets/Textures/Hero.png --force
unity-bridge import-settings bulk-set Assets/Textures/ -s maxTextureSize:1024 --filter "*.png"
unity-bridge import-settings template-save mobile-texture Assets/Textures/Reference.png
unity-bridge import-settings template-apply mobile-texture Assets/Textures/NewAsset.png
```

### Scene Layout Management
```bash
unity-bridge scene-ext setup save combat-setup
unity-bridge scene-ext setup list
unity-bridge scene-ext setup restore combat-setup
unity-bridge scene-ext play-start --set Assets/Scenes/Boot.unity
unity-bridge scene-ext play-start --clear
unity-bridge scene-ext list-loaded
unity-bridge scene-ext cross-refs
unity-bridge scene-ext preview-create
unity-bridge scene-ext preview-close 12345
```

### Undo Workflows
```bash
unity-bridge undo perform
unity-bridge undo redo
unity-bridge undo history --limit 5
unity-bridge undo collapse 5 --name "Level setup"
```

### Batch Operations
```bash
unity-bridge batch commands.json
unity-bridge batch commands.json --parallel
```

## Important Notes

- Unity Editor must be open with the ClaudeUnityBridge active for commands to work
- If `unity-bridge status` shows unhealthy, run `unity-bridge doctor` for diagnostics
- The bridge uses file-based I/O -- the CLI handles all of this automatically
- Timeouts vary by command type (5s quick reads, 300s tests, 600s builds, 3600s sync lightmap bake)
- Asset paths use forward slashes relative to project root: `Assets/Scenes/Main.unity`
- Undo operations affect the entire Unity Editor -- `undo clear` removes ALL history
- Shader inspection operations are read-only and safe for parallel batch execution
- Build profiles require Unity 6 or later
