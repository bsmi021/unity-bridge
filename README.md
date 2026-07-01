# Unity Bridge

CLI-first Unity Editor automation via a file-based bridge protocol. Control Unity from the command line: run tests, inspect hierarchies, manage assets, trigger builds, query editor state, and recover long-running operations through a durable operation ledger.

**Status:** the `unity-bridge` CLI is the only supported interface. The MCP server has been fully retired; there is no MCP compatibility layer.

**Last updated:** 2026-07-01.

**Requirements:** Python 3.10+, Unity Editor running with the C# bridge installed.

## Quick Start

```bash
# Install core CLI + bridge
pip install -e "."

# Install with test/lint tools
pip install -e ".[dev]"

# Install everything (file watcher + dev tools)
pip install -e ".[all]"

# Install the C# bridge into your Unity project
unity-bridge install

# Check that Unity is alive
unity-bridge status

# Run a full diagnostic check
unity-bridge doctor

# Run your EditMode tests
unity-bridge test run --platform EditMode

# Query the scene hierarchy
unity-bridge hierarchy --depth 3
```

The `install` command copies the C# bridge scripts into `Assets/Scripts/Editor/ClaudeCodeBridge/` inside your Unity project. The bridge runs as an Editor script via `EditorApplication.update` and requires no manual setup beyond installation.

Packaged installs include the C# bridge scripts and the `unity-bridge-cli` Codex skill bundle, so `unity-bridge install` works from both editable source installs and normal `pip install .` / wheel installs.

Repo-local Codex metadata lives in `.agents/skills/unity-bridge-cli/` and `.codex/agents/`. The shipped skill is intentionally CLI-first: it routes agents through `unity-bridge` commands instead of raw `.claude/unity` JSON.

## Global CLI Flags

All commands accept these flags:

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--project PATH` | `-p` | auto-detect | Unity project root |
| `--pretty` | | off | Indented JSON output |
| `--human` | `-H` | off | Human-readable formatted output |
| `--verbose` | `-v` | off | Set log level to DEBUG |
| `--quiet` | `-q` | off | Set log level to CRITICAL |
| `--timeout N` | `-t` | 30 | Default command timeout in seconds |
| `--no-color` | | off | Disable coloured output |

Output is JSON to stdout by default. Use `--human` for formatted text or `--pretty` for indented JSON.

## Command Reference

### Diagnostics

```
unity-bridge status                           # Quick alive/dead bridge check
unity-bridge doctor                           # Run full 9-check diagnostic suite
unity-bridge profiler [--memory] [--rendering] [--cpu]  # Capture profiler metrics
unity-bridge version                          # Show CLI, bridge, and Python versions
unity-bridge operation status COMMAND_ID      # Inspect persisted command lifecycle state
```

`status` reports both heartbeat liveness (`healthy`) and editor command readiness
(`ready`). During compile, AssetDatabase refresh, assembly reload, or play-mode
transition windows, Unity can be healthy but not ready; bridge commands wait for
readiness before writing command files.

```bash
# Example: full health check with human-readable output
unity-bridge doctor --human
```

### Lifecycle

```
unity-bridge install [--check] [--force]      # Install/update C# bridge files
unity-bridge init                             # Create .claude/unity/ directory structure
unity-bridge clean [--age N] [--all] [--dry-run]  # Remove orphaned command/response files, stale temp files, and old terminal operation files
```

```bash
# Example: check if bridge needs an update
unity-bridge install --check

# Example: force reinstall
unity-bridge install --force

# Example: preview what clean would delete
unity-bridge clean --dry-run
```

### Scene Management

```
unity-bridge scene load PATH [--save-current]  # Load a scene
unity-bridge scene save                        # Save the current scene
unity-bridge scene create PATH                 # Create a new scene
```

```bash
# Example: load a scene, saving the current one first
unity-bridge scene load "Assets/Scenes/Main.unity" --save-current
```

### Extended Scene Management

```
unity-bridge scene-ext setup save NAME         # Save current multi-scene layout
unity-bridge scene-ext setup restore NAME      # Restore a saved layout
unity-bridge scene-ext setup list              # List all saved setups
unity-bridge scene-ext play-start [--set PATH] [--clear]  # Get/set/clear play mode start scene
unity-bridge scene-ext cross-refs              # Detect cross-scene references
unity-bridge scene-ext list-loaded             # List all loaded scenes with status
unity-bridge scene-ext preview-create          # Create an empty preview scene
unity-bridge scene-ext preview-close HANDLE    # Close a preview scene
```

```bash
# Example: save and restore a multi-scene layout
unity-bridge scene-ext setup save my-combat-setup
unity-bridge scene-ext setup restore my-combat-setup

# Example: set a specific scene to play on Enter Play Mode
unity-bridge scene-ext play-start --set "Assets/Scenes/Boot.unity"
```

### Hierarchy

```
unity-bridge hierarchy [--depth N] [--inactive] [--root PATH]  # Query scene hierarchy
unity-bridge hierarchy missing-scripts [--fix]                  # Find/fix missing scripts
unity-bridge hierarchy static-flags OBJECT_PATH                 # Get static flags
unity-bridge hierarchy set-static-flags OBJECT_PATH FLAG...     # Set static flags
unity-bridge hierarchy set-layer OBJECT_PATH LAYER [--recursive]  # Set layer
unity-bridge hierarchy set-tag OBJECT_PATH TAG                  # Set tag
```

```bash
# Example: query hierarchy from a specific root, including inactive objects
unity-bridge hierarchy --depth 4 --inactive --root "Environment"

# Example: find and remove missing scripts
unity-bridge hierarchy missing-scripts --fix
```

### Components

```
unity-bridge component get OBJECT_PATH TYPE [--fields FIELDS]   # Get component data
unity-bridge component set OBJECT_PATH TYPE --update FIELD:VAL  # Set component fields
unity-bridge component add OBJECT_PATH TYPE                     # Add a component
```

```bash
# Example: read Transform data
unity-bridge component get "Player" "Transform"

# Example: modify a component field
unity-bridge component set "Player" "CharacterStats" --update "health:100" --update "speed:5.5"

# Example: add a Rigidbody
unity-bridge component add "Player" "Rigidbody"
```

### Prefabs

```
unity-bridge prefab validate PATH              # Validate a prefab asset
unity-bridge prefab instantiate PATH [--position X,Y,Z]  # Instantiate a prefab
unity-bridge prefab destroy INSTANCE_PATH      # Destroy a prefab instance
unity-bridge prefab status PATH                # Get prefab type and status
unity-bridge prefab find-instances ASSET_PATH  # Find all scene instances of a prefab
unity-bridge prefab unpack INSTANCE_PATH [--completely]  # Unpack a prefab instance
unity-bridge prefab overrides list INSTANCE_PATH [--include-default-overrides]
unity-bridge prefab overrides apply INSTANCE_PATH [--target TARGET]
unity-bridge prefab overrides revert INSTANCE_PATH [--target TARGET]
```

```bash
# Example: instantiate a prefab at a specific position
unity-bridge prefab instantiate "Assets/Prefabs/Enemy.prefab" --position 10,0,5

# Example: list and apply overrides
unity-bridge prefab overrides list "Enemy(Clone)"
unity-bridge prefab overrides apply "Enemy(Clone)"
```

### Editor Controls

```
unity-bridge selection [--components] [--children]  # Get current editor selection
unity-bridge refresh [--force]                      # Refresh asset database
unity-bridge focus OBJECT_PATH [--no-frame]         # Focus a GameObject in scene view
unity-bridge menu MENU_PATH [--validate-only]       # Execute a menu item
unity-bridge screenshot OUTPUT_PATH [--camera NAME] [--width N] [--height N]
```

```bash
# Example: execute a menu item
unity-bridge menu "File/Save"

# Example: capture a screenshot at specific resolution
unity-bridge screenshot "./capture.png" --width 1920 --height 1080
```

### Assets

```
unity-bridge asset ACTION [--path PATH] [--type TYPE] [--pattern PATTERN]
```

Where `ACTION` is one of: `find`, `query`, `import`, `refresh`.

```bash
# Example: find all materials in a folder
unity-bridge asset find --path "Assets/Materials" --type Material

# Example: search by pattern
unity-bridge asset find --pattern "Player*"
```

### Extended Asset Operations

```
unity-bridge asset-ext create PATH --type TYPE     # Create a new asset
unity-bridge asset-ext delete PATH [--trash]       # Delete an asset
unity-bridge asset-ext copy SOURCE DEST            # Copy an asset
unity-bridge asset-ext move SOURCE DEST            # Move/rename an asset
unity-bridge asset-ext deps PATH [--recursive/--no-recursive]  # List dependencies
unity-bridge asset-ext guid INPUT                  # Convert between path and GUID
unity-bridge asset-ext folder-create PATH          # Create a folder
unity-bridge asset-ext folder-list PATH            # List subfolders
unity-bridge asset-ext export --output FILE PATHS...  # Export as .unitypackage
unity-bridge asset-ext import-package FILE [--interactive]  # Import a .unitypackage
```

```bash
# Example: create a ScriptableObject asset
unity-bridge asset-ext create "Assets/Data/Config.asset" --type ScriptableObject

# Example: find all dependencies of a prefab
unity-bridge asset-ext deps "Assets/Prefabs/Player.prefab"

# Example: export assets as a package
unity-bridge asset-ext export --output "backup.unitypackage" "Assets/Scripts" "Assets/Prefabs"
```

### Import Settings

```
unity-bridge import-settings get PATH              # Get import settings for an asset
unity-bridge import-settings set PATH --setting KEY:VALUE  # Modify and reimport
unity-bridge import-settings reimport PATH [--force]       # Reimport an asset
unity-bridge import-settings bulk-set FOLDER --setting KEY:VALUE [--filter GLOB]
unity-bridge import-settings template-save NAME PATH       # Save settings as template
unity-bridge import-settings template-apply NAME PATH      # Apply a template to an asset
```

```bash
# Example: set texture import settings
unity-bridge import-settings set "Assets/Textures/Albedo.png" \
    --setting "maxTextureSize:1024" --setting "textureCompression:Compressed"

# Example: bulk-set all PNGs in a folder
unity-bridge import-settings bulk-set "Assets/Textures/UI" \
    --setting "spritePixelsPerUnit:100" --filter "*.png"

# Example: save and apply a template
unity-bridge import-settings template-save mobile-texture "Assets/Textures/Reference.png"
unity-bridge import-settings template-apply mobile-texture "Assets/Textures/NewAsset.png"
```

### Materials

```
unity-bridge material modify PATH [--properties JSON]
unity-bridge material create PATH
unity-bridge material duplicate PATH
unity-bridge material enable-keyword PATH KEYWORD
unity-bridge material disable-keyword PATH KEYWORD
unity-bridge material get-keywords PATH
unity-bridge material set-render-queue PATH VALUE
unity-bridge material copy-properties TARGET_PATH SOURCE_PATH
```

```bash
# Example: create a new material
unity-bridge material create "Assets/Materials/NewMat.mat"

# Example: modify material properties
unity-bridge material modify "Assets/Materials/Player.mat" \
    --properties '{"_Color": {"r": 1, "g": 0, "b": 0, "a": 1}}'

# Example: enable a shader keyword
unity-bridge material enable-keyword "Assets/Materials/Player.mat" "_EMISSION"
```

### Shaders

```
unity-bridge shader list [--errors-only]           # List all shaders
unity-bridge shader info NAME                      # Get detailed shader info
unity-bridge shader errors NAME                    # Get shader compilation errors
unity-bridge shader properties NAME                # Enumerate shader properties
unity-bridge shader find-by-property PROPERTY_NAME # Find shaders with a property
unity-bridge shader keywords NAME [--filter TYPE]  # List shader keywords
```

```bash
# Example: find all shaders with errors
unity-bridge shader list --errors-only

# Example: inspect a URP shader
unity-bridge shader info "Universal Render Pipeline/Lit"

# Example: find all shaders using _MainTex
unity-bridge shader find-by-property "_MainTex"
```

### Build

```
unity-bridge build --target TARGET [--validate-only] [--output PATH] [--dev] [--timeout N]
```

```bash
# Example: build for Windows
unity-bridge build --target StandaloneWindows64 --output "./Builds/Win64"

# Example: validate build config without building
unity-bridge build --target Android --validate-only

# Example: development build
unity-bridge build --target StandaloneWindows64 --dev
```

### Build Profiles (Unity 6)

```
unity-bridge profile list                      # List all build profiles
unity-bridge profile active                    # Get the active profile
unity-bridge profile set PATH                  # Set the active profile
unity-bridge profile info PATH                 # Get profile details
unity-bridge profile scenes PATH               # Get profile scenes
unity-bridge profile set-scenes PATH --scene Assets/Scenes/Main.unity
unity-bridge profile defines PATH              # Get profile scripting defines
unity-bridge profile set-defines PATH --define DEVELOPMENT_BUILD
unity-bridge profile build PATH --output Builds/Windows/Game.exe
```

```bash
# Example: switch active build profile
unity-bridge profile set "Assets/Settings/BuildProfiles/Android.asset"
```

### Compilation Pipeline

```
unity-bridge compile assemblies                # List all project assemblies
unity-bridge compile defines ASSEMBLY          # Get defines for an assembly
unity-bridge compile which SCRIPT_PATH         # Find which assembly owns a script
unity-bridge compile optimization [--set MODE] # Get or set optimization level
```

```bash
# Example: find which assembly owns a script
unity-bridge compile which "Assets/Scripts/Combat/DamageSystem.cs"

# Example: list defines for Assembly-CSharp
unity-bridge compile defines "Assembly-CSharp"

# Example: set optimization to Release
unity-bridge compile optimization --set Release
```

### Testing

```
unity-bridge test run [--platform PLATFORM] [--filter PATTERN] [--test-name NAME] [--group REGEX] [--category CAT] [--assembly ASM] [--min-tests N] [--timeout N]
unity-bridge test cancel [--command-id ID] [--timeout N]
unity-bridge test preflight [--platform PLATFORM] [--filter PATTERN] [--test-name NAME] [--group REGEX] [--category CAT] [--assembly ASM] [--min-tests N]
unity-bridge test list [--platform PLATFORM] [--filter PATTERN] [--categories] [--assemblies]
unity-bridge test compile [--wait/--no-wait] [--timeout N]
unity-bridge test results [--last|--command-id ID]
unity-bridge test failures [--last|--command-id ID]
unity-bridge test progress [--last|--command-id ID]
unity-bridge test events [--last|--command-id ID] [--max-events N]
unity-bridge test rerun-failed [--last|--command-id ID] [--platform PLATFORM] [--timeout N]
unity-bridge test history [--max-results N]
unity-bridge coverage availability
unity-bridge coverage install [--version VERSION]
unity-bridge coverage start|pause|resume|stop
unity-bridge coverage find-reports [--path PATH] [--max-results N]
unity-bridge coverage summarize [PATH]
```

```bash
# Example: run EditMode tests matching a pattern
unity-bridge test run --platform EditMode --filter "Combat*"

# Example: verify a filtered run would select at least one test
unity-bridge test preflight --platform EditMode --filter "Combat*" --min-tests 1

# Example: run a smoke category from one test assembly
unity-bridge test run --platform EditMode --category Smoke --assembly Game.Editor.Tests --min-tests 1

# Example: list all PlayMode test categories
unity-bridge test list --platform PlayMode --categories

# Example: trigger a compilation and wait
unity-bridge test compile --wait

# Example: inspect the last persisted test result without re-running Unity
unity-bridge test results --last

# Example: inspect progress for a long-running test command
unity-bridge test progress --last

# Example: inspect structured per-test progress events
unity-bridge test events --last --max-events 50

# Example: rerun only the tests that failed in the last persisted result
unity-bridge test rerun-failed --last --platform EditMode

# Example: cancel an active bridge-initiated test run
unity-bridge test cancel --command-id <run-tests-command-id>

# Example: check optional Code Coverage package/API support
unity-bridge coverage availability

# Example: inspect an existing ReportGenerator summary
unity-bridge coverage summarize CoverageResults/Report/Summary.json
```

### Play Mode

```
unity-bridge playmode ACTION
```

Where `ACTION` is one of: `play`, `pause`, `stop`.

```bash
unity-bridge playmode play
unity-bridge playmode stop
```

### Console

```
unity-bridge console read [--types TYPES] [--max N] [--pattern REGEX] [--stack-trace]
unity-bridge console watch [--types TYPES] [--poll-interval N]
unity-bridge console clear
```

```bash
# Example: read only errors and warnings
unity-bridge console read --types "error,warning" --max 20

# Example: follow console output in real time
unity-bridge console watch --types "error"

# Example: clear the console
unity-bridge console clear
```

### TDD Workflow

```
unity-bridge tdd [--platform PLATFORM] [--filter PATTERN] [--strict]
```

Runs a multi-step workflow: clear console, compile, run tests, and read console on failure.

```bash
# Example: TDD with strict mode (warnings are failures)
unity-bridge tdd --platform EditMode --filter "Combat*" --strict
```

### Batch Execution

```
unity-bridge batch FILE [--stop-on-error/--no-stop-on-error] [--parallel]
```

Execute multiple commands from a JSON file. The `--parallel` flag runs read-only commands concurrently.

```bash
# Example: run a batch file
unity-bridge batch commands.json --parallel
```

Batch file format:

```json
[
    {"type": "clear-console"},
    {"type": "compile", "parameters": {"waitForCompletion": true}},
    {"type": "run-tests", "parameters": {"testPlatform": "EditMode"}}
]
```

### Script Execution

```
unity-bridge script EXPRESSION [--file PATH] [--timeout N]
```

Execute a C# expression or script file in the Unity Editor context.

```bash
# Example: execute an inline expression
unity-bridge script "Debug.Log(Application.unityVersion)"

# Example: run a script file
unity-bridge script --file "./scripts/setup-scene.cs"
```

### Project Settings

```
unity-bridge settings get [KEY]                    # Get player settings (all or specific)
unity-bridge settings set KEY VALUE                # Set a player setting
unity-bridge settings defines ACTION [--symbol S] [--platform P]  # Manage scripting defines
```

Where defines `ACTION` is one of: `list`, `add`, `remove`.

```bash
# Example: read all player settings
unity-bridge settings get

# Example: set company name
unity-bridge settings set companyName "MyStudio"

# Example: add a scripting define
unity-bridge settings defines add --symbol "ENABLE_ANALYTICS"
```

### Package Manager

```
unity-bridge package list [--offline] [--include-indirect] [--source TYPE]
unity-bridge package search QUERY [--all]
unity-bridge package add IDENTIFIER
unity-bridge package batch [--add IDENTIFIER] [--remove NAME]
unity-bridge package remove NAME
unity-bridge package info NAME
unity-bridge package embed NAME
unity-bridge package pack PACKAGE_FOLDER TARGET_FOLDER
unity-bridge package clear-cache --yes
unity-bridge package resolve
```

```bash
# Example: list installed packages
unity-bridge package list

# Example: add a package by name@version
unity-bridge package add "com.unity.inputsystem@1.7.0"

# Example: add and remove packages in one dependency solve
unity-bridge package batch --add "com.unity.inputsystem" --remove "com.unity.timeline"

# Example: search for packages
unity-bridge package search "input"

# Example: embed a package for local editing
unity-bridge package embed "com.unity.inputsystem"

# Example: pack a local UPM package into a .tgz
unity-bridge package pack "Packages/com.company.tools" "Build/Packages"
```

### Undo/Redo

```
unity-bridge undo perform                      # Undo the last operation
unity-bridge undo redo                         # Redo the last undone operation
unity-bridge undo history [--limit N]          # List recent undo operations
unity-bridge undo clear                        # Clear all undo history (WARNING)
unity-bridge undo group-name                   # Get current undo group name
unity-bridge undo collapse INDEX [--name NAME] # Collapse undo operations into one step
```

```bash
# Example: view recent undo history
unity-bridge undo history --limit 10
```

### Animator

```
unity-bridge animator ACTION OBJECT_PATH [OPTIONS]
```

Where `ACTION` is one of: `get-state`, `set-state`, `get-params`, `set-param`.

```bash
# Example: get current animator state
unity-bridge animator get-state "Player"

# Example: set an animator parameter
unity-bridge animator set-param "Player" --param-name "Speed" --param-value "5.0"

# Example: check parameters on a specific layer
unity-bridge animator get-params "Player" --layer 1
```

### Lightmap

```
unity-bridge lightmap bake [--run-async/--no-run-async] [--timeout N]
unity-bridge lightmap cancel
unity-bridge lightmap clear
unity-bridge lightmap status
unity-bridge lightmap settings
```

```bash
# Example: start a synchronous bake and wait
unity-bridge lightmap bake --no-run-async

# Example: check bake progress
unity-bridge lightmap status
```

### Snapshot

```
unity-bridge snapshot save FILE [--depth N] [--max-objects N] [--root PATH]
unity-bridge snapshot diff FILE1 FILE2
```

```bash
# Example: save a snapshot and compare later
unity-bridge snapshot save before.json --depth 5
# ... make changes ...
unity-bridge snapshot save after.json --depth 5
unity-bridge snapshot diff before.json after.json
```

### Extended Command Groups (Phase 4-Unity 6.4)

Beyond the core examples above, the live CLI exposes 92 top-level entries: 67 command groups and 25 top-level commands. Run `unity-bridge --help` for the full list, or `unity-bridge GROUP --help` for any group below.

**Selection & editor state:** `select`, `prefs`, `editor-config`, `window`, `scene-state`
**Transform & object manipulation:** `transform`, `property`, `hierarchy`, `component`, `object-identity`
**Physics / quality / rendering:** `physics`, `quality`, `graphics-settings`, `environment-settings`, `render-pipeline`, `graphics-state`, `reflection-probe`, `occlusion`
**Project settings (domain-specific):** `time-settings`, `audio-settings`, `input-system`, `ui-toolkit`, `tags`, `layers`, `sorting-layers`
**Build pipeline:** `build-scenes`, `script-execution-order`, `assembly-lock`, `assembly-unlock`, `assembly-status`, `sync-solution`
**Scene & asset tooling:** `scene-view`, `game-view`, `scene-template`, `clipboard`, `preset`, `deep-serialize`, `script-info`, `find-references`, `addressables`, `search`, `project-auditor`, `graph-toolkit`
**Built-in package inspection:** `entities`, `adaptive-performance`, `multiplayer-playmode`
**Graphics & geometry:** `navmesh`, `animation`, `animation-clip`, `terrain`, `tilemap`
**Component and material lifecycle extensions:** `component copy`, `component paste`, `component reset`, `component remove`, `component enable`, `component disable`, `material`
**Profiling & diagnostics:** `profiler`, `profiler-control`, `console log`, `cloud`, `physics2d`

```bash
# Example: list all groups
unity-bridge --help

# Example: explore a specific group
unity-bridge navmesh --help
unity-bridge preset --help
```

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `UNITY_BRIDGE_PROJECT` | Override project root path |
| `UNITY_BRIDGE_LOG_LEVEL` | Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL, OFF) |
| `UNITY_BRIDGE_TIMEOUT` | Default timeout in seconds |
| `UNITY_BRIDGE_EDITOR_READY_TIMEOUT` | Max seconds to wait for Unity Editor command readiness before reporting `editor_busy` |
| `UNITY_BRIDGE_IN_FLIGHT_BUSY_GRACE` | Hard max seconds to keep an in-flight response wait alive while Unity reports busy/reloading |
| `UNITY_BRIDGE_CONFIG` | Path to config JSON file |
| `NO_COLOR` | Disable coloured output (any value) |

## Configuration

Configuration is resolved with the following precedence: CLI flags > environment variables > config file > defaults.

Config file search order:

1. Path in `$UNITY_BRIDGE_CONFIG`
2. `<project_root>/unity_bridge_config.json`
3. `<project_root>/.claude/unity_bridge_config.json`

## Architecture

### File-Based Bridge Protocol

The Python CLI writes JSON command files to `<project>/.claude/unity/commands/`. A C# Editor script (`ClaudeUnityBridge.cs`) running via `EditorApplication.update` picks them up, executes them inside Unity, and writes JSON responses to `<project>/.claude/unity/responses/`. Each command is identified by a unique UUID. This file-based IPC works across WSL2/Windows boundaries via `/mnt/c/` path mapping.

Each command also gets durable lifecycle state in `<project>/.claude/unity/operations/<commandId>.json` plus transition history in `<commandId>.events.jsonl`. Current-state JSON is used for reload recovery and client polling; JSONL is diagnostic history. Unity writes accepted/running/terminal states through `BridgeOperationLedger`, and `unity-bridge operation status COMMAND_ID` can inspect the latest state without sending another Unity command. `unity-bridge clean` prunes old terminal operation snapshots and event logs while preserving active operations.

### Single Interface

The `unity-bridge` CLI is the only interface. Each command module exposes an async core function (returns `CommandResult`) plus a thin synchronous Typer wrapper that calls `asyncio.run()` on it. There is no MCP server, no MCP tool surface, and no MCP compatibility layer — it was fully retired.

### Project Auto-Detection

The CLI walks up from the current working directory looking for `Assets/` + `ProjectSettings/` directories. Override with `--project` or the `UNITY_BRIDGE_PROJECT` environment variable.

## Development

### Running Tests

```bash
python3 -m pytest tests/                     # All tests (integration skipped without Unity)
python3 -m pytest tests/unit/                # Unit tests only
python3 -m pytest tests/unit/test_bridge.py  # Single file
python3 -m pytest -x --tb=short              # Stop on first failure
python3 -m pytest --cov=unity_bridge         # With coverage report
python3 -m pytest tests --cov=unity_bridge --cov-report=term-missing --cov-fail-under=90
```

Unit tests mock `DirectBridge` and never require a running Unity instance. Integration tests are marked with `@pytest.mark.integration` and are automatically skipped when Unity is not available.

### Linting

```bash
ruff check src/ tests/       # Lint
ruff format src/ tests/      # Format
```

### Project Structure

```
unity-bridge/
├── src/unity_bridge/
│   ├── app.py               # Typer entry point, AppState, global flags
│   ├── core/                # Shared modules (bridge, config, health, operation, cache, retry, output)
│   └── commands/            # 84 command modules (one per domain)
├── ClaudeCodeBridge/        # C# Editor scripts installed into Unity
├── tests/                   # pytest suite (unit + integration)
└── docs/                    # Tech specs
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Command failure (Unity error, tests failed) |
| 2 | Bridge unavailable (Unity not running, heartbeat stale) |
| 3 | Invalid input |
| 4 | Timeout or editor busy/reloading |
| 5 | Internal error |
| 130 | Interrupted (Ctrl+C) |

## License

MIT
