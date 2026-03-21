---
name: unity-bridge-cli
description: >
  Use this skill whenever you need to interact with Unity Editor from the command
  line or from scripts -- running tests, compiling, inspecting the scene hierarchy,
  modifying components, managing scenes/prefabs, controlling play mode, reading
  console logs, taking screenshots, building, or executing C# expressions. Trigger
  on phrases like "run tests", "compile Unity", "check the hierarchy", "get component
  data", "set component value", "load scene", "enter play mode", "read console",
  "take screenshot", "build for Android", "execute C# in Unity", "TDD workflow",
  "watch for changes", "is Unity running", "install bridge", "clean orphaned files",
  "list packages", "bake lightmaps", "shader info", "undo", "import settings",
  "quality profile", "scene setup", "asset dependencies", or any request that
  involves communicating with an open Unity Editor. Also trigger proactively whenever
  you are about to write raw JSON command files to .claude/unity/commands/ -- use the
  CLI instead, it handles retries, timeouts, caching, and error formatting
  automatically. If you need to do anything in Unity Editor and it is open, reach
  for this skill first.
---

# Unity Bridge CLI

`unity-bridge` is a command-line tool that communicates with Unity Editor through a
file-based bridge protocol. It replaces the need to write raw JSON command files or
use the MCP server directly. Every command returns JSON to stdout by default (pipe
to `jq` for filtering), or use `--human` for formatted output.

## CRITICAL: Syntax Rules (Read Before Every Command)

**RULE 1: Global flags MUST go BEFORE the command name.** `--human`, `--pretty`,
`--verbose`, `--quiet`, `--timeout`, `--project`, and `--no-color` are NOT
per-command options. They ONLY work when placed between `unity-bridge` and the
command. Putting them after the command WILL FAIL with "No such option".

**RULE 2: `--timeout` and `--human` are GLOBAL-ONLY flags.** Most commands do NOT
accept `--timeout` or `--human` as their own options. The only commands with a
local `--timeout` are: `test run`, `script`, `build`, and `lightmap bake`.
For everything else, use the global `-t` flag before the command.

**RULE 3: `hierarchy` queries directly.** There is no `hierarchy list` subcommand.
Use `unity-bridge hierarchy --depth 3`, not `unity-bridge hierarchy list --depth 3`.

```bash
# CORRECT
unity-bridge --human hierarchy --depth 3
unity-bridge -t 60 menu "File/Save"
unity-bridge --human console read --types error
unity-bridge -H -v component get Player Transform
unity-bridge hierarchy --depth 3                     # direct query, no "list"

# WRONG -- these will ALL fail with "No such option"
unity-bridge hierarchy --depth 3 --human             # WRONG: --human after command
unity-bridge menu "File/Save" --timeout 60           # WRONG: --timeout after command
unity-bridge console read --types error --human      # WRONG: --human after command
unity-bridge hierarchy list --depth 3                # WRONG: "list" doesn't exist
```

## Quick Start

```bash
unity-bridge status                                  # Is Unity alive?
unity-bridge --human test run --platform EditMode    # Run tests, human output
unity-bridge tdd --filter MyTests                    # Clear -> compile -> test -> console
unity-bridge hierarchy --depth 3                     # Inspect scene tree
unity-bridge console watch                           # Tail logs in real-time
```

## Decision Tree: Choose the Right Command

### "I need to verify code changes work"
```bash
unity-bridge tdd --platform EditMode --filter MyTests   # Full workflow
unity-bridge test run --platform EditMode                # Just run tests
unity-bridge test compile                                # Just check compilation
unity-bridge test list --platform EditMode --categories  # See available tests
```

### "I need to inspect the scene"
```bash
unity-bridge hierarchy --depth 3                         # Full tree
unity-bridge hierarchy --root "Player" --depth 2         # Subtree only
unity-bridge hierarchy --inactive                        # Include inactive objects
unity-bridge component get Player Transform              # Read component fields
unity-bridge component get "UI/Canvas" Image --fields "color,sprite"
unity-bridge selection --components                      # What is selected?
unity-bridge hierarchy missing-scripts                   # Find broken refs
```

### "I need to modify scene state"
```bash
unity-bridge component set Player Health --update "currentHp:100"
unity-bridge component set Player Transform -u "position.x:5.0" -u "position.y:0"
unity-bridge component add Enemy "EnemyAI"
unity-bridge prefab instantiate Assets/Prefabs/Enemy.prefab --position 5,0,3
unity-bridge scene load Assets/Scenes/Main.unity --save-current
unity-bridge hierarchy set-tag Player "Enemy"
unity-bridge hierarchy set-layer Player 8 --recursive
```

### "I need to debug"
```bash
unity-bridge console read --types error,warning --max 20
unity-bridge console read --pattern "NullReference" --no-stack-trace
unity-bridge console watch --types error                 # Follow mode
unity-bridge playmode play                               # Enter play mode
unity-bridge playmode stop                               # Exit play mode
unity-bridge profiler --memory --rendering               # Performance snapshot
unity-bridge --human doctor                              # Full diagnostics
```

### "I need to manage the project"
```bash
unity-bridge status                                      # Health check
unity-bridge doctor                                      # Full diagnostics
unity-bridge install                                     # Install/update C# bridge
unity-bridge install --check                             # Check without modifying
unity-bridge clean --dry-run                             # See what would be removed
unity-bridge clean                                       # Remove orphaned files
unity-bridge build --target StandaloneWindows64
unity-bridge refresh --force                             # Force reimport assets
unity-bridge package list                                # List installed packages
unity-bridge settings get                                # View editor settings
```

### "I need to automate or script"
```bash
unity-bridge script "EditorApplication.isPlaying"        # Evaluate C# expression
unity-bridge script "Selection.activeGameObject.name"    # Return a value
unity-bridge script --file setup.cs                      # Run script file
unity-bridge batch commands.json                         # Run multiple commands
unity-bridge batch commands.json --parallel              # Parallel read-only
```

### "I need to manage assets"
```bash
unity-bridge asset find --type Prefab --pattern "Enemy*"
unity-bridge asset-ext create Assets/Scripts/New.cs --type MonoScript
unity-bridge asset-ext deps Assets/Prefabs/Player.prefab --recursive
unity-bridge asset-ext copy Assets/Old.mat Assets/New.mat
unity-bridge import-settings get Assets/Textures/icon.png
unity-bridge import-settings set Assets/Textures/icon.png -s "maxTextureSize:512"
```

### "I need lighting, shaders, or rendering"
```bash
unity-bridge lightmap bake                               # Bake lightmaps
unity-bridge lightmap status                             # Check bake status
unity-bridge shader list --errors-only                   # Find broken shaders
unity-bridge shader info "Standard"                      # Shader details
unity-bridge shader properties "Standard"                # List shader props
```

### "I need to manage quality/build profiles"
```bash
unity-bridge profile list                                # List quality profiles
unity-bridge profile active                              # Current profile
unity-bridge profile set "Assets/Settings/High.asset"    # Switch profile
```

### "I need undo/redo"
```bash
unity-bridge undo perform                                # Undo last action
unity-bridge undo redo                                   # Redo
unity-bridge undo history --limit 10                     # Recent history
unity-bridge undo clear                                  # Clear undo stack
```

## Global Flags

Every command accepts these flags. They MUST go BEFORE the command name.

| Flag | Short | Purpose |
|------|-------|---------|
| `--project PATH` | `-p` | Override auto-detected Unity project root |
| `--human` | `-H` | Human-readable output instead of JSON |
| `--pretty` | | Indented JSON output |
| `--verbose` | `-v` | Debug logging to stderr |
| `--quiet` | `-q` | Suppress non-error output |
| `--timeout SEC` | `-t` | Override default command timeout |
| `--no-color` | | Disable colored output |

**Syntax: `unity-bridge [GLOBAL FLAGS] COMMAND [COMMAND OPTIONS]`**

## Essential Commands Quick Reference

### Top-Level Commands (no subgroup)

| Command | Syntax |
|---------|--------|
| playmode | `playmode ACTION` (play/pause/stop) |
| status | `status` |
| doctor | `doctor` |
| profiler | `profiler [--memory] [--rendering] [--cpu]` |
| install | `install [--check] [--force]` |
| init | `init` |
| clean | `clean [--age N] [--all] [--dry-run]` |
| version | `version` |
| tdd | `tdd [--platform TEXT] [--filter TEXT] [--strict]` |
| script | `script [EXPRESSION] [--file PATH] [--timeout N]` |
| batch | `batch FILE [--stop-on-error] [--parallel]` |
| serve | `serve` |
| selection | `selection [--components] [--children]` |
| refresh | `refresh [--force]` |
| focus | `focus OBJECT_PATH [--no-frame]` |
| menu | `menu MENU_PATH [--validate-only]` |
| screenshot | `screenshot OUTPUT_PATH [--camera TEXT] [--width N] [--height N]` |
| asset | `asset ACTION [--path TEXT] [--type TEXT] [--pattern TEXT]` (find/query/import/refresh) |
| material | `material ACTION PATH [--properties JSON]` (modify/create/duplicate) |
| build | `build [--target TEXT] [--validate-only] [--output TEXT] [--dev] [--timeout N]` |
| animator | `animator ACTION OBJECT_PATH [--state-name] [--param-name] [--param-value] [--layer N]` |

### Command Groups

| Group | Subcommands |
|-------|------------|
| hierarchy | (direct query with --depth/--inactive/--root), missing-scripts, static-flags, set-static-flags, set-layer, set-tag |
| component | get, set, add |
| scene | load, save, create |
| prefab | validate, instantiate, destroy, status, find-instances, unpack, overrides list/apply/revert |
| console | read, watch, clear |
| test | run, list, compile |
| compile | assemblies, defines, which, optimization |
| undo | perform, redo, history, clear, group-name, collapse |
| settings | get, set, defines |
| profile | list, active, set, info |
| asset-ext | create, delete, copy, move, deps, guid, folder-create, folder-list, export, import-package |
| package | list, search, add, remove, info, embed, resolve |
| lightmap | bake, cancel, clear, status, settings |
| shader | list, info, errors, properties, find-by-property, keywords |
| scene-ext | setup save/restore/list, play-start, cross-refs, list-loaded, preview-create, preview-close |
| import-settings | get, set, reimport, bulk-set, template-save, template-apply |

## Common Multi-Step Workflows

### TDD Cycle
The `tdd` command chains: clear console -> compile -> run tests -> read console (on failure).
```bash
unity-bridge tdd --platform EditMode --filter CombatTests
# Returns steps array showing each phase result
```

### Investigate and Fix a Compile Error
```bash
unity-bridge test compile                           # Check compilation
unity-bridge --human console read --types error     # See errors
# ... fix the code ...
unity-bridge test compile                           # Verify fix
unity-bridge tdd --filter CombatTests               # Run full cycle
```

### Scene Inspection Workflow
```bash
unity-bridge --human hierarchy --depth 2            # Overview
unity-bridge component get Player Transform         # Check position
unity-bridge component get Player Health --fields "currentHp,maxHp"
unity-bridge --human selection --components         # What is selected?
```

### Prefab Workflow
```bash
unity-bridge prefab validate Assets/Prefabs/Player.prefab
unity-bridge prefab instantiate Assets/Prefabs/Enemy.prefab --position 5,0,3
unity-bridge prefab overrides list "Enemy(Clone)"
unity-bridge prefab overrides apply "Enemy(Clone)"
unity-bridge prefab destroy "Enemy(Clone)"
```

### Asset Investigation
```bash
unity-bridge asset find --type Material --pattern "Player*"
unity-bridge asset-ext deps Assets/Prefabs/Player.prefab --recursive
unity-bridge shader properties "Standard"
unity-bridge import-settings get Assets/Textures/icon.png
```

### Batch Operations
Run multiple commands from a JSON file:
```bash
unity-bridge batch batch.json
unity-bridge batch batch.json --parallel   # For read-only commands
```

Batch file format:
```json
{
  "commands": [
    {"type": "clear-console"},
    {"type": "compile", "parameters": {"waitForCompletion": true}},
    {"type": "run-tests", "parameters": {"testPlatform": "EditMode"}}
  ]
}
```

### Package Management
```bash
unity-bridge package list                            # Installed packages
unity-bridge package search "input system"           # Find packages
unity-bridge package add com.unity.inputsystem       # Install
unity-bridge package info com.unity.inputsystem      # Details
unity-bridge package remove com.unity.inputsystem    # Uninstall
```

## Output Format

All commands return JSON by default. The structure is always:

```json
{"success": true, "data": {...}, "command_id": "uuid", "execution_time_ms": 123}
```

or on failure:

```json
{"success": false, "error": "message", "exit_code": 1}
```

Parse `success` to determine if the command worked. All keys are `snake_case`.

Use `--human` (before the command) for formatted, readable output.
Use `--pretty` (before the command) for indented JSON.

## Exit Codes

| Code | Meaning | What to Do |
|------|---------|------------|
| 0 | Success | Proceed normally |
| 1 | Command failed | Read `error` field for details |
| 2 | Bridge unavailable | Run `unity-bridge doctor`, check Unity is open |
| 3 | Invalid input | Check your arguments |
| 4 | Timeout | Increase `--timeout` or check if Unity is frozen |
| 5 | Internal error | Check logs with `--verbose` |
| 130 | Interrupted | User pressed Ctrl+C |

## Configuration and Environment

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `UNITY_BRIDGE_PROJECT` | Override project root path |
| `UNITY_BRIDGE_LOG_LEVEL` | Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL, OFF) |
| `UNITY_BRIDGE_TIMEOUT` | Default timeout in seconds |
| `UNITY_BRIDGE_CONFIG` | Path to config JSON file |
| `NO_COLOR` | Disable colored output (any value) |

### Configuration Precedence

CLI flags > environment variables > config file > defaults.

Config file search order:
1. `$UNITY_BRIDGE_CONFIG`
2. `<project_root>/unity_bridge_config.json`
3. `<project_root>/.claude/unity_bridge_config.json`

## Command Reference

For complete argument lists, types, defaults, and examples for every command, see:
`references/command-reference.md`

## Important Notes and Gotchas

1. **Global flags go BEFORE the command name.** `unity-bridge --human hierarchy` not
   `unity-bridge hierarchy --human`.

2. **`hierarchy` queries directly with options** -- it is NOT `hierarchy list`.
   `unity-bridge hierarchy --depth 3` is correct. There is no `hierarchy list` subcommand.

3. **Positional args are bare values, not flags.** `unity-bridge component get Player Transform`
   not `unity-bridge component get --path Player --type Transform`.

4. **Unity Editor must be open** with the ClaudeUnityBridge active for commands to work.
   If `unity-bridge status` shows unhealthy, run `unity-bridge doctor` for diagnostics.

5. **The bridge uses file-based I/O.** Commands are written to `.claude/unity/commands/` and
   responses appear in `.claude/unity/responses/`. The CLI handles all of this automatically.
   Never write raw command files -- use the CLI.

6. **Timeouts vary by command type** (5s for quick reads, 300s for tests, 600s for builds).
   Override with `--timeout` (global flag, before the command) if needed.

7. **Asset paths use forward slashes** relative to project root: `Assets/Scenes/Main.unity`.

8. **The `-u` flag is shorthand for `--update`** on `component set`. Multiple updates can
   be passed: `component set Obj Type -u "field1:val" -u "field2:val"`.

9. **The `-s` flag is shorthand for `--setting`** on `import-settings set` and
   `import-settings bulk-set`.

10. **`compile` is a command GROUP** with subcommands (assemblies, defines, which, optimization),
    not a standalone command. Use `test compile` to trigger and wait for script compilation.
