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
file-based bridge protocol. Every command returns JSON to stdout by default.

## Command Syntax

```
unity-bridge [GLOBAL FLAGS] COMMAND [COMMAND OPTIONS/ARGS]
```

Global flags (`--human`, `--pretty`, `--verbose`, `--quiet`, `--timeout`, `--project`,
`--no-color`) are placed between `unity-bridge` and the command name.

```bash
unity-bridge --human hierarchy --depth 3
unity-bridge -H console read --types error
unity-bridge -t 60 menu "Souls/Generate/All"
unity-bridge --pretty component get Player Transform
unity-bridge -v -t 120 test run --platform EditMode
unity-bridge --project /path/to/project status
```

| Global Flag | Short | Purpose |
|-------------|-------|---------|
| `--human` | `-H` | Human-readable output instead of JSON |
| `--pretty` | | Indented JSON output |
| `--verbose` | `-v` | Debug logging to stderr |
| `--quiet` | `-q` | Suppress non-error output |
| `--timeout SEC` | `-t` | Override default command timeout |
| `--project PATH` | `-p` | Override auto-detected Unity project root |
| `--no-color` | | Disable colored output |

## Core Workflow

Every interaction follows this pattern:

1. **Check health**: `unity-bridge status`
2. **Run command**: `unity-bridge [global flags] command [args]`
3. **Parse result**: Check `success` field in JSON output

```bash
unity-bridge status
unity-bridge hierarchy --depth 3
unity-bridge component get Player Health --fields "currentHp,maxHp"
unity-bridge component set Player Health -u "currentHp:100"
unity-bridge --human console read --types error
```

## Quick Reference: All Commands

### Diagnostics & Lifecycle

```bash
unity-bridge status                                     # Quick health check
unity-bridge doctor                                     # Full 9-check diagnostics
unity-bridge version                                    # Show versions
unity-bridge profiler --memory --rendering --cpu        # Performance snapshot
unity-bridge install                                    # Install/update C# bridge
unity-bridge install --check                            # Check status only
unity-bridge install --force                            # Force reinstall
unity-bridge init                                       # Create directory structure
unity-bridge clean                                      # Remove orphaned files
unity-bridge clean --dry-run                            # Preview deletions
unity-bridge clean --age 10                             # Files older than 10 min
unity-bridge serve                                      # Start MCP server mode
```

### Scene Hierarchy

```bash
unity-bridge hierarchy                                  # Default depth=5
unity-bridge hierarchy --depth 3                        # Limit depth
unity-bridge hierarchy --root "Player" --depth 2        # Subtree only
unity-bridge hierarchy --inactive                       # Include inactive objects
unity-bridge hierarchy --depth 4 --inactive --root "Environment"
unity-bridge hierarchy missing-scripts                  # Find broken scripts
unity-bridge hierarchy missing-scripts --fix            # Remove broken scripts
unity-bridge hierarchy static-flags "Environment/Tree"  # Get static flags
unity-bridge hierarchy set-static-flags "Environment/Tree" BatchingStatic NavigationStatic
unity-bridge hierarchy set-layer Player 8               # Set layer
unity-bridge hierarchy set-layer Player 8 --recursive   # Include children
unity-bridge hierarchy set-tag Player "Enemy"           # Set tag
```

### Components

```bash
unity-bridge component get Player Transform
unity-bridge component get Player Health --fields "currentHp,maxHp"
unity-bridge component get "UI/Canvas" Image --fields "color,sprite"
unity-bridge component set Player Health --update "currentHp:100"
unity-bridge component set Player Transform -u "position.x:5.0" -u "position.y:0"
unity-bridge component add Player "AudioSource"
unity-bridge component add Enemy "EnemyAI"
```

### Scenes

```bash
unity-bridge scene load Assets/Scenes/Main.unity
unity-bridge scene load Assets/Scenes/Test.unity --save-current
unity-bridge scene save
unity-bridge scene create Assets/Scenes/NewLevel.unity
```

### Extended Scene Management

```bash
unity-bridge scene-ext setup save my-layout             # Save multi-scene layout
unity-bridge scene-ext setup restore my-layout          # Restore layout
unity-bridge scene-ext setup list                       # List saved layouts
unity-bridge scene-ext play-start --set Assets/Scenes/Boot.unity
unity-bridge scene-ext play-start --clear               # Clear start scene
unity-bridge scene-ext play-start                       # Get current start scene
unity-bridge scene-ext cross-refs                       # Detect cross-scene refs
unity-bridge scene-ext list-loaded                      # All loaded scenes
unity-bridge scene-ext preview-create                   # Create preview scene
unity-bridge scene-ext preview-close HANDLE             # Close preview scene
```

### Prefabs

```bash
unity-bridge prefab validate Assets/Prefabs/Player.prefab
unity-bridge prefab instantiate Assets/Prefabs/Enemy.prefab
unity-bridge prefab instantiate Assets/Prefabs/Enemy.prefab --position 5,0,3
unity-bridge prefab destroy "Enemy(Clone)"
unity-bridge prefab status "Enemy(Clone)"
unity-bridge prefab find-instances Assets/Prefabs/Enemy.prefab
unity-bridge prefab unpack "Enemy(Clone)"
unity-bridge prefab unpack "Enemy(Clone)" --completely
unity-bridge prefab overrides list "Enemy(Clone)"
unity-bridge prefab overrides list "Enemy(Clone)" --include-default-overrides
unity-bridge prefab overrides apply "Enemy(Clone)"
unity-bridge prefab overrides apply "Enemy(Clone)" --target "Transform"
unity-bridge prefab overrides revert "Enemy(Clone)"
```

### Testing & Compilation

```bash
unity-bridge test run --platform EditMode
unity-bridge test run --platform PlayMode --filter "Combat*"
unity-bridge test run --platform EditMode --timeout 60
unity-bridge test list --platform EditMode              # Discover tests
unity-bridge test list --categories                     # List categories
unity-bridge test list --assemblies                     # List test assemblies
unity-bridge test compile                               # Trigger compilation
unity-bridge test compile --no-wait                     # Don't wait for result
unity-bridge tdd --platform EditMode --filter CombatTests
unity-bridge tdd --strict                               # Warnings = failures
```

### Compilation Pipeline

```bash
unity-bridge compile assemblies                         # List project assemblies
unity-bridge compile defines Assembly-CSharp            # Get defines for assembly
unity-bridge compile which Assets/Scripts/Player.cs     # Which assembly owns this?
unity-bridge compile optimization                       # Get current mode
unity-bridge compile optimization --set release         # Set to Release
```

### Console

```bash
unity-bridge console read                               # Read all logs
unity-bridge console read --types error,warning         # Filter by type
unity-bridge console read --types error --max 20        # Limit entries
unity-bridge console read --pattern "NullReference"     # Regex filter
unity-bridge console read --no-stack-trace              # Skip stack traces
unity-bridge console watch                              # Follow mode (Ctrl+C to stop)
unity-bridge console watch --types error --poll-interval 0.5
unity-bridge console clear                              # Clear console
```

### Play Mode

```bash
unity-bridge playmode play
unity-bridge playmode pause
unity-bridge playmode stop
```

### Editor Utilities

```bash
unity-bridge selection                                  # Get current selection
unity-bridge selection --components                     # Include components
unity-bridge selection --children                       # Include children
unity-bridge refresh                                    # Refresh asset database
unity-bridge refresh --force                            # Force full refresh
unity-bridge focus Player                               # Focus in scene view
unity-bridge focus "Environment/Tree" --no-frame        # Select without framing
unity-bridge menu "File/Save"                           # Execute menu item
unity-bridge menu "GameObject/Create Empty"
unity-bridge menu "Assets/Refresh" --validate-only      # Check existence only
unity-bridge screenshot output.png                      # Capture screenshot
unity-bridge screenshot shot.png --width 1920 --height 1080
unity-bridge screenshot shot.png --camera "Main Camera"
```

### Assets

```bash
unity-bridge asset find --type Prefab --path Assets/Prefabs/
unity-bridge asset find --type Material --pattern "Player*"
unity-bridge asset query --path Assets/Materials/
unity-bridge asset import --path Assets/Textures/new.png
unity-bridge asset refresh
```

### Extended Asset Operations

```bash
unity-bridge asset-ext create Assets/Data/Config.asset --type ScriptableObject
unity-bridge asset-ext delete Assets/Old/unused.mat
unity-bridge asset-ext delete Assets/Old/unused.mat --trash
unity-bridge asset-ext copy Assets/Materials/Base.mat Assets/Materials/Copy.mat
unity-bridge asset-ext move Assets/Old/file.cs Assets/New/file.cs
unity-bridge asset-ext deps Assets/Prefabs/Player.prefab
unity-bridge asset-ext deps Assets/Prefabs/Player.prefab --no-recursive
unity-bridge asset-ext guid Assets/Scenes/Main.unity    # Path to GUID
unity-bridge asset-ext guid abc123def456                 # GUID to path
unity-bridge asset-ext folder-create Assets/NewFolder
unity-bridge asset-ext folder-list Assets/Scripts
unity-bridge asset-ext export Assets/Prefabs/ --output export.unitypackage
unity-bridge asset-ext import-package downloaded.unitypackage
```

### Import Settings

```bash
unity-bridge import-settings get Assets/Textures/icon.png
unity-bridge import-settings set Assets/Textures/icon.png -s "maxTextureSize:512"
unity-bridge import-settings set Assets/Textures/icon.png -s "maxTextureSize:512" -s "mipmapEnabled:false"
unity-bridge import-settings reimport Assets/Textures/icon.png
unity-bridge import-settings reimport Assets/Textures/icon.png --force
unity-bridge import-settings bulk-set Assets/Textures/ -s "maxTextureSize:1024" --filter "*.png"
unity-bridge import-settings template-save mobile-tex Assets/Textures/icon.png
unity-bridge import-settings template-apply mobile-tex Assets/Textures/other.png
```

### Materials

```bash
unity-bridge material modify Assets/Materials/Player.mat --properties '{"_Color":{"r":1,"g":0,"b":0,"a":1}}'
unity-bridge material create Assets/Materials/New.mat
unity-bridge material duplicate Assets/Materials/Base.mat
```

### Shaders

```bash
unity-bridge shader list                                # All shaders
unity-bridge shader list --errors-only                  # Only broken shaders
unity-bridge shader info "Universal Render Pipeline/Lit"
unity-bridge shader errors "Universal Render Pipeline/Lit"
unity-bridge shader properties "Standard"               # All properties
unity-bridge shader find-by-property "_MainTex"         # Find by property
unity-bridge shader keywords "Standard"                 # List keywords
unity-bridge shader keywords "Standard" --global        # Global keywords only
unity-bridge shader keywords "Standard" --local         # Local keywords only
```

### Builds

```bash
unity-bridge build --target StandaloneWindows64
unity-bridge build --target Android --dev
unity-bridge build --target WebGL --validate-only
unity-bridge build --target StandaloneWindows64 --output builds/win64/ --timeout 900
```

### Build Profiles (Unity 6)

```bash
unity-bridge profile list                               # List all profiles
unity-bridge profile active                             # Current active profile
unity-bridge profile set Assets/Settings/BuildProfiles/High.asset
unity-bridge profile info Assets/Settings/BuildProfiles/High.asset
```

### Animator

```bash
unity-bridge animator get-state Player
unity-bridge animator get-params Player
unity-bridge animator set-state Player --state-name "Idle"
unity-bridge animator set-param Player --param-name "Speed" --param-value 5.0
unity-bridge animator set-param Player --param-name "IsRunning" --param-value true --layer 0
```

### Player Settings

```bash
unity-bridge settings get                               # All settings
unity-bridge settings get companyName                   # Specific key
unity-bridge settings set companyName "My Studio"
unity-bridge settings defines list                      # List defines
unity-bridge settings defines list --platform Standalone
unity-bridge settings defines add --symbol MY_FEATURE
unity-bridge settings defines add --symbol MY_FEATURE --platform Android
unity-bridge settings defines remove --symbol OLD_FEATURE
```

### Package Manager

```bash
unity-bridge package list                               # Installed packages
unity-bridge package list --offline                     # Cached data only
unity-bridge package list --include-indirect            # Include transitive deps
unity-bridge package search com.unity.inputsystem       # Search by ID
unity-bridge package search com.unity.inputsystem --all # Search all registry
unity-bridge package add com.unity.inputsystem          # Install package
unity-bridge package add com.unity.inputsystem@1.5.0    # Specific version
unity-bridge package remove com.unity.inputsystem       # Uninstall
unity-bridge package info com.unity.inputsystem         # Package details
unity-bridge package embed com.unity.inputsystem        # Embed for editing
unity-bridge package resolve                            # Force re-resolve
```

### Undo/Redo

```bash
unity-bridge undo perform                               # Undo last action
unity-bridge undo redo                                  # Redo last undone action
unity-bridge undo history                               # Recent undo history
unity-bridge undo history --limit 10                    # Limit entries
unity-bridge undo clear                                 # Clear all undo history
unity-bridge undo group-name                            # Current undo group
unity-bridge undo collapse 5                            # Collapse from group 5
unity-bridge undo collapse 5 --name "Batch edit"        # With custom name
```

### Lightmapping

```bash
unity-bridge lightmap bake                              # Start async bake
unity-bridge lightmap bake --no-run-async               # Wait for completion
unity-bridge lightmap bake --timeout 3600               # Custom timeout
unity-bridge lightmap cancel                            # Cancel active bake
unity-bridge lightmap clear                             # Clear baked data
unity-bridge lightmap status                            # Check progress
unity-bridge lightmap settings                          # Current settings
```

### Script Execution

```bash
unity-bridge script "EditorApplication.isPlaying"
unity-bridge script "Selection.activeGameObject.name"
unity-bridge script "var go = new GameObject(\"Test\"); go.name"
unity-bridge script --file Assets/Editor/setup.cs
unity-bridge script --file setup.cs --timeout 60
```

## Command Chaining

Commands can be chained with `&&` for multi-step workflows:

```bash
unity-bridge test compile && unity-bridge --human console read --types error
unity-bridge scene load Assets/Scenes/Test.unity --save-current && unity-bridge hierarchy --depth 2
unity-bridge console clear && unity-bridge test run --platform EditMode && unity-bridge --human console read --types error
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

Parse `success` to determine if the command worked. All keys are `snake_case`.

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

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `UNITY_BRIDGE_PROJECT` | Override project root path |
| `UNITY_BRIDGE_LOG_LEVEL` | Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL, OFF) |
| `UNITY_BRIDGE_TIMEOUT` | Default timeout in seconds |
| `UNITY_BRIDGE_CONFIG` | Path to config JSON file |
| `NO_COLOR` | Disable colored output (any value) |

### Precedence

CLI flags > environment variables > config file > defaults.

## Deep-Dive Reference

For complete argument lists, types, defaults, and short flags for every command:
- See [references/command-reference.md](references/command-reference.md)

## Notes

- Unity Editor must be open with ClaudeUnityBridge active.
- If `unity-bridge status` shows unhealthy, run `unity-bridge doctor`.
- Asset paths use forward slashes relative to project root: `Assets/Scenes/Main.unity`.
- The `-u` flag is shorthand for `--update` on `component set`. Pass multiple: `-u "field1:val" -u "field2:val"`.
- The `-s` flag is shorthand for `--setting` on `import-settings set` and `import-settings bulk-set`.
- `compile` is a command group (assemblies/defines/which/optimization). Use `test compile` to trigger script compilation.
- Timeouts vary by command (5s reads, 300s tests, 600s builds). Override globally with `-t SEC`.
