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
  package, resolve packages, or any request involving an open Unity Editor.
  Also trigger when about to write raw JSON to .claude/unity/commands/ -- use
  the CLI instead for retries, timeouts, caching, and error formatting.
---

# Unity Bridge CLI

`unity-bridge` communicates with Unity Editor through a file-based bridge
protocol. Every command returns JSON to stdout by default.

## Command Syntax

```
unity-bridge [GLOBAL FLAGS] COMMAND [COMMAND OPTIONS/ARGS]
```

Global flags go BEFORE the command name:

```bash
unity-bridge --human hierarchy --depth 3
unity-bridge -H console read --types error
unity-bridge -t 60 menu "File/Save"
unity-bridge --pretty component get Player Transform
unity-bridge -v -t 120 test run --platform EditMode
unity-bridge --project /path/to/project status
```

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
unity-bridge status                                     # Quick alive/dead check
unity-bridge doctor                                     # Full 9-check diagnostics
unity-bridge version                                    # CLI, bridge, Python versions
unity-bridge profiler --memory --rendering --cpu         # Performance snapshot
unity-bridge install                                    # Install/update C# bridge
unity-bridge install --check                            # Check status only
unity-bridge install --force                            # Force reinstall
unity-bridge init                                       # Create directory structure
unity-bridge clean                                      # Remove orphaned files (>5 min)
unity-bridge clean --dry-run                            # Preview deletions
unity-bridge clean --age 10                             # Files older than 10 min
unity-bridge clean --all                                # Delete all orphaned files
unity-bridge serve                                      # Start MCP server mode
```

### Hierarchy

```bash
unity-bridge hierarchy                                  # Default depth=5
unity-bridge hierarchy --depth 3                        # Limit depth (short: -d)
unity-bridge hierarchy --root "Player" --depth 2        # Subtree only (short: -r)
unity-bridge hierarchy --inactive                       # Include inactive objects
unity-bridge hierarchy --depth 4 --inactive --root "Environment"
unity-bridge hierarchy missing-scripts                  # Find broken scripts
unity-bridge hierarchy missing-scripts --fix            # Remove broken scripts
unity-bridge hierarchy static-flags "Environment/Tree"  # Get static flags
unity-bridge hierarchy set-static-flags "Environment/Tree" BatchingStatic NavigationStatic
unity-bridge hierarchy set-layer Player 8               # Set layer
unity-bridge hierarchy set-layer Player 8 -r            # Include children
unity-bridge hierarchy set-tag Player "Enemy"           # Set tag
unity-bridge hierarchy duplicate "Environment/Tree"     # Duplicate a GameObject
unity-bridge hierarchy create-primitive cube             # Create primitive/light/camera
unity-bridge hierarchy create-primitive point-light -n "MyLight" -p "Environment"
unity-bridge hierarchy set-active Player --inactive     # Deactivate a GameObject
unity-bridge hierarchy set-active Player --active       # Activate (default)
```

### Selection

```bash
unity-bridge selection                                  # Get current editor selection
unity-bridge selection --components                     # Include component lists
unity-bridge selection --children                       # Include child objects
unity-bridge select Player                              # Select a single object
unity-bridge select Player "Environment/Tree"           # Select multiple objects
unity-bridge select --clear                             # Clear the current selection
```

### Transform

```bash
unity-bridge transform get Player                       # Get all transform data
unity-bridge transform set Player -p 5,0,3              # Set world position
unity-bridge transform set Player -r 0,90,0             # Set rotation
unity-bridge transform set Player -s 2,2,2              # Set scale
unity-bridge transform set Player -p 1,0,0 --local      # Set local position
unity-bridge transform set Player -p 5,0,3 -r 0,90,0 -s 2,2,2
unity-bridge transform parent "Enemy" "EnemyGroup"      # Reparent to new parent
unity-bridge transform parent "Enemy"                   # Unparent (move to root)
unity-bridge transform parent "Enemy" "Group" --no-world-position-stays
unity-bridge transform sibling-index "Enemy" 0          # Set hierarchy order
```

### Serialized Properties

```bash
unity-bridge property list Player BoxCollider           # List all properties
unity-bridge property get Player BoxCollider "m_Size"   # Get property value
unity-bridge property set Player BoxCollider "m_Size" '{"x":2,"y":2,"z":2}'
```

### Components

```bash
unity-bridge component get Player Transform
unity-bridge component get Player Health --fields "currentHp,maxHp"
unity-bridge component get Player Health --deep         # Full EditorJsonUtility serialization
unity-bridge component set Player Health --update "currentHp:100"
unity-bridge component set Player Transform -u "position.x:5.0" -u "position.y:0"
unity-bridge component add Player "AudioSource"
unity-bridge component remove Player "Rigidbody"
unity-bridge component enable Player "AudioSource"
unity-bridge component disable Player "AudioSource"
```

### Scenes

```bash
unity-bridge scene load Assets/Scenes/Main.unity
unity-bridge scene load Assets/Scenes/Test.unity --save-current
unity-bridge scene load Assets/Scenes/UI.unity --additive
unity-bridge scene save
unity-bridge scene create Assets/Scenes/NewLevel.unity
unity-bridge scene load-additive Assets/Scenes/UI.unity
unity-bridge scene load-additive Assets/Scenes/UI.unity --save-current
unity-bridge scene unload Assets/Scenes/UI.unity
unity-bridge scene unload Assets/Scenes/UI.unity --keep
unity-bridge scene set-active Assets/Scenes/Main.unity
unity-bridge scene move-object "Player" Assets/Scenes/Gameplay.unity
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
unity-bridge scene-ext preview-close HANDLE             # Close preview scene (INTEGER)
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
unity-bridge prefab overrides apply "Enemy(Clone)" -t "Transform"
unity-bridge prefab overrides revert "Enemy(Clone)"
unity-bridge prefab overrides revert "Enemy(Clone)" -t "Transform"
```

### Testing & TDD

```bash
unity-bridge test run --platform EditMode
unity-bridge test run -P PlayMode --filter "Combat*"
unity-bridge test run --timeout 60
unity-bridge test list                                  # Discover tests
unity-bridge test list -P PlayMode -f "Combat*"
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
unity-bridge compile optimization --set Release         # Set to Release
```

### Console

```bash
unity-bridge console read                               # Read all logs
unity-bridge console read --types error,warning         # Filter by type (-T)
unity-bridge console read -T error -m 20                # Limit entries (--max)
unity-bridge console read --pattern "NullReference"     # Regex filter (-p)
unity-bridge console read --stack-trace                 # Include stack traces
unity-bridge console read --max-stack-lines 5           # Limit stack trace lines
unity-bridge console read --max-message-length 200      # Truncate messages
unity-bridge console watch                              # Follow mode (Ctrl+C to stop)
unity-bridge console watch -T error --poll-interval 0.5
unity-bridge console clear                              # Clear console
unity-bridge console log "Build started"                # Log custom message
unity-bridge console log "Something broke" -t error     # Log as error
```

### Play Mode

```bash
unity-bridge playmode play
unity-bridge playmode pause
unity-bridge playmode stop
```

### Editor Utilities

```bash
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

### Script Execution

```bash
unity-bridge script "EditorApplication.isPlaying"
unity-bridge script "Selection.activeGameObject.name"
unity-bridge script --file Assets/Editor/setup.cs
unity-bridge script -f setup.cs --timeout 60
```

### Assets

```bash
unity-bridge asset find --type Prefab --path Assets/Prefabs/
unity-bridge asset find -t Material --pattern "Player*"
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
unity-bridge asset-ext export Assets/Prefabs/ -o export.unitypackage
unity-bridge asset-ext export Assets/Prefabs/ -o export.unitypackage --no-deps
unity-bridge asset-ext import-package downloaded.unitypackage
unity-bridge asset-ext import-package downloaded.unitypackage --interactive
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
unity-bridge material modify Assets/Materials/Player.mat --properties '{"_Color":{"r":1}}'
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
unity-bridge shader keywords "Standard" --filter global # Global keywords only
unity-bridge shader keywords "Standard" --filter local  # Local keywords only
```

### Builds

```bash
unity-bridge build --target StandaloneWindows64
unity-bridge build -T Android --dev
unity-bridge build -T WebGL --validate-only
unity-bridge build -T StandaloneWindows64 -o builds/win64/ --timeout 900
unity-bridge build -T Android --compress lz4hc --subtarget Player
unity-bridge build -T StandaloneLinux64 --scenes "Assets/Scenes/A.unity,Assets/Scenes/B.unity"
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
unity-bridge settings defines add -s MY_FEATURE --platform Android
unity-bridge settings defines remove -s OLD_FEATURE
```

### Package Manager

```bash
unity-bridge package list                               # Installed packages
unity-bridge package list --offline                     # Cached data only
unity-bridge package list --include-indirect            # Include transitive deps
unity-bridge package list --source registry             # Filter by source
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
unity-bridge undo history                               # Recent undo history (default 20)
unity-bridge undo history -n 10                         # Limit entries
unity-bridge undo clear                                 # Clear all undo history
unity-bridge undo group-name                            # Current undo group
unity-bridge undo collapse 5                            # Collapse from group 5
unity-bridge undo collapse 5 -n "Batch edit"            # With custom name
```

### Lightmapping

```bash
unity-bridge lightmap bake                              # Start async bake
unity-bridge lightmap bake --no-run-async               # Wait for completion
unity-bridge lightmap bake --timeout 3600               # Custom timeout
unity-bridge lightmap cancel                            # Cancel active bake
unity-bridge lightmap clear                             # Clear baked data
unity-bridge lightmap status                            # Check progress
unity-bridge lightmap settings                          # Current settings (read-only)
unity-bridge lightmap set-settings --lightmap-size 2048 --bounces 4
unity-bridge lightmap set-settings --baked-gi --compress
```

### Editor Preferences

```bash
unity-bridge prefs get MyPlugin.Setting                 # Get EditorPrefs value
unity-bridge prefs get MyPlugin.Setting -t int          # Get as specific type
unity-bridge prefs get MyKey -s session                 # Get from SessionState
unity-bridge prefs set MyPlugin.Setting "value"         # Set EditorPrefs value
unity-bridge prefs set MyPlugin.Count 42 -t int         # Set as int
unity-bridge prefs set MyFlag true -t bool -s session   # Set SessionState bool
unity-bridge prefs delete MyPlugin.Setting              # Delete a key
unity-bridge prefs delete MyKey -s session              # Delete from SessionState
unity-bridge prefs has MyPlugin.Setting                 # Check if key exists
unity-bridge prefs has MyKey -s session                 # Check in SessionState
```

### Build Settings Scenes

```bash
unity-bridge build-scenes list                          # List all build scenes
unity-bridge build-scenes add Assets/Scenes/Main.unity  # Append scene
unity-bridge build-scenes add Assets/Scenes/Main.unity -i 0  # Insert at index
unity-bridge build-scenes remove Assets/Scenes/Old.unity     # Remove scene
unity-bridge build-scenes enable Assets/Scenes/Main.unity    # Enable scene
unity-bridge build-scenes disable Assets/Scenes/Test.unity   # Disable scene
```

### Physics Configuration

```bash
unity-bridge physics get                                # Get physics settings
unity-bridge physics set -g "0,-9.81,0"                 # Set gravity
unity-bridge physics set --solver-iterations 12         # Set solver iterations
unity-bridge physics set -g "0,-20,0" --solver-iterations 8
unity-bridge physics collision get                      # Get collision matrix
unity-bridge physics collision set 8 9 --ignore         # Ignore collisions
unity-bridge physics collision set 8 9 --collide        # Enable collisions
```

### Quality Settings

```bash
unity-bridge quality list                               # List all quality levels
unity-bridge quality get                                # Get current quality settings
unity-bridge quality set-level 2                        # Switch quality level by index
```

### Tags & Layers

```bash
unity-bridge tags list                                  # List all project tags
unity-bridge tags add "Interactable"                    # Add a custom tag
unity-bridge layers list                                # List all layers
unity-bridge layers add "Interactables"                 # Add layer to next free slot
unity-bridge layers add "Interactables" -i 10           # Add to specific slot (8-31)
unity-bridge sorting-layers list                        # List all sorting layers
unity-bridge sorting-layers add "Foreground"            # Add a sorting layer
```

### Editor Configuration

```bash
unity-bridge editor-config get                          # Get all editor settings
unity-bridge editor-config set "enterPlayModeOptionsEnabled" "true"
unity-bridge editor-config set "serializationMode" "ForceText"
```

### Batch Execution

```bash
unity-bridge batch commands.json                        # Execute batch commands
unity-bridge batch commands.json --no-stop-on-error     # Continue on failures
unity-bridge batch commands.json --parallel             # Run read-only commands concurrently
```

## Common Patterns

### TDD Cycle

```bash
unity-bridge console clear && unity-bridge test compile && unity-bridge test run -P EditMode -f "Combat*" && unity-bridge --human console read -T error
```

### Scene Investigation

```bash
unity-bridge hierarchy --depth 2
unity-bridge component get Player Health
unity-bridge transform get Player
unity-bridge property list Player BoxCollider
```

### Prefab Workflow

```bash
unity-bridge prefab instantiate Assets/Prefabs/Enemy.prefab --position 5,0,3
unity-bridge component set "Enemy(Clone)" Health -u "maxHp:200"
unity-bridge prefab overrides list "Enemy(Clone)"
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

| Variable | Purpose |
|----------|---------|
| `UNITY_BRIDGE_PROJECT` | Override project root path |
| `UNITY_BRIDGE_LOG_LEVEL` | Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL, OFF) |
| `UNITY_BRIDGE_TIMEOUT` | Default timeout in seconds |
| `UNITY_BRIDGE_CONFIG` | Path to config JSON file |
| `NO_COLOR` | Disable colored output (any value) |

Precedence: CLI flags > environment variables > config file > defaults.

## Deep-Dive Reference

For complete argument tables, types, defaults, and short flags for every command:
- See [references/command-reference.md](references/command-reference.md)

## Notes

- Unity Editor must be open with ClaudeUnityBridge active.
- If `unity-bridge status` shows unhealthy, run `unity-bridge doctor`.
- Asset paths use forward slashes relative to project root: `Assets/Scenes/Main.unity`.
- The `-u` flag is shorthand for `--update` on `component set`. Pass multiple: `-u "field1:val" -u "field2:val"`.
- The `-s` flag is shorthand for `--setting` on `import-settings set` and `import-settings bulk-set`.
- `compile` is a command group (assemblies/defines/which/optimization). Use `test compile` to trigger script compilation.
- The `-s` flag on `prefs` commands is `--scope` (values: `prefs` or `session`).
- The `-t` flag on `prefs` and `console log` commands is `--type`, not the global `--timeout`.
- Timeouts vary by command (5s reads, 300s tests, 600s builds). Override globally with `-t SEC`.
