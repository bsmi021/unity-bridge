# Unity Bridge CLI -- Complete Command Reference

Every command example uses the EXACT syntax from `unity-bridge --help`.

**CRITICAL SYNTAX RULE: `unity-bridge [GLOBAL FLAGS] COMMAND [COMMAND OPTIONS]`**

`--human`, `--pretty`, `--verbose`, `--quiet`, `--timeout`, `--project`, `--no-color`
are GLOBAL flags. They MUST go BEFORE the command name. Placing them after the command
causes "No such option" errors. Most commands do NOT have their own `--timeout` or
`--human` — use the global flags instead.

```bash
unity-bridge --human console read --types error     # CORRECT
unity-bridge console read --types error --human     # WRONG: "No such option: --human"
unity-bridge -t 60 menu "File/Save"                 # CORRECT
unity-bridge menu "File/Save" --timeout 60          # WRONG: "No such option: --timeout"
```

## Table of Contents

1. [Testing & Compilation](#testing--compilation)
2. [Hierarchy & Components](#hierarchy--components)
3. [Scene Management](#scene-management)
4. [Prefab Operations](#prefab-operations)
5. [Play Mode Control](#play-mode-control)
6. [Console & Logging](#console--logging)
7. [Editor Utilities](#editor-utilities)
8. [Asset Operations](#asset-operations)
9. [Extended Asset Operations](#extended-asset-operations)
10. [Material Operations](#material-operations)
11. [Build Operations](#build-operations)
12. [Animator Operations](#animator-operations)
13. [Workflow Commands](#workflow-commands)
14. [Scripting](#scripting)
15. [Diagnostics & Lifecycle](#diagnostics--lifecycle)
16. [Batch & Serve](#batch--serve)
17. [Compile Group](#compile-group)
18. [Undo Group](#undo-group)
19. [Settings Group](#settings-group)
20. [Profile Group](#profile-group)
21. [Package Group](#package-group)
22. [Lightmap Group](#lightmap-group)
23. [Shader Group](#shader-group)
24. [Scene Extensions Group](#scene-extensions-group)
25. [Import Settings Group](#import-settings-group)
26. [Hierarchy Duplicate](#hierarchy-duplicate)
27. [Select Group](#select-group)
28. [Transform Group](#transform-group)
29. [Property Group](#property-group)
30. [Prefs Group](#prefs-group)
31. [Build Scenes Group](#build-scenes-group)
32. [Physics Group](#physics-group)
33. [Quality Group](#quality-group)
34. [Tags Group](#tags-group)
35. [Layers Group](#layers-group)
36. [Sorting Layers Group](#sorting-layers-group)
37. [Editor Config Group](#editor-config-group)
38. [Bridge Command Types](#bridge-command-types)

---

## Testing & Compilation

### `test run`

Run EditMode or PlayMode tests.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--platform` | TEXT | `EditMode` | `EditMode` or `PlayMode` |
| `--filter` | TEXT | none | Test name filter pattern |
| `--timeout` | INT | 300 | Seconds to wait |

```bash
unity-bridge test run --platform EditMode
unity-bridge test run --platform PlayMode --filter "Combat*"
unity-bridge test run --filter InventoryTests --timeout 60
```

### `test list`

List available tests without running them.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--platform` | TEXT | `EditMode` | `EditMode` or `PlayMode` |
| `--filter` | TEXT | none | Test name filter pattern |
| `--categories` | flag | false | Include test categories |
| `--assemblies` | flag | false | Include assembly info |

```bash
unity-bridge test list --platform EditMode
unity-bridge test list --categories --assemblies
unity-bridge test list --filter "Combat*"
```

### `test compile`

Trigger script compilation and wait for results.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--wait/--no-wait` | flag | true | Wait for compilation to complete |
| `--timeout` | INT | 120 | Seconds to wait |

```bash
unity-bridge test compile
unity-bridge test compile --no-wait
```

---

## Hierarchy & Components

### `hierarchy` (direct query)

Query the active scene GameObject tree. Options are on the group itself, NOT a subcommand.
There is no `hierarchy list` -- just use `hierarchy` with options.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--depth` | INT | 5 | Max depth to traverse |
| `--inactive` | flag | false | Include inactive GameObjects |
| `--root` | TEXT | none | Start from this GameObject path |

```bash
unity-bridge hierarchy
unity-bridge hierarchy --depth 2
unity-bridge hierarchy --root "Player" --inactive
unity-bridge --human hierarchy --depth 3   # Human-readable tree view
```

### `hierarchy missing-scripts`

Find GameObjects with missing script references.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--fix` | flag | false | Remove missing script components |

```bash
unity-bridge hierarchy missing-scripts
unity-bridge hierarchy missing-scripts --fix
```

### `hierarchy static-flags`

Get static flags for a GameObject.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | GameObject path |

```bash
unity-bridge hierarchy static-flags "Environment/Tree"
```

### `hierarchy set-static-flags`

Set static flags on a GameObject.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | GameObject path |
| `FLAGS` | positional (variadic) | yes | Static flags to set |

```bash
unity-bridge hierarchy set-static-flags "Environment/Tree" BatchingStatic LightmapStatic
```

### `hierarchy set-layer`

Set the layer of a GameObject.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | GameObject path |
| `LAYER` | positional | yes | Layer number |
| `--recursive` | flag | false | Apply to all children |

```bash
unity-bridge hierarchy set-layer Player 8
unity-bridge hierarchy set-layer Environment 10 --recursive
```

### `hierarchy set-tag`

Set the tag of a GameObject.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | GameObject path |
| `TAG` | positional | yes | Tag name |

```bash
unity-bridge hierarchy set-tag Player "Player"
unity-bridge hierarchy set-tag Enemy "Enemy"
```

### `component get`

Read field values from a component. Arguments are positional (bare values, not flags).

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | GameObject path (e.g., `Player`) |
| `COMPONENT_TYPE` | positional | yes | Component type (e.g., `Transform`, `PlayerStats`) |
| `--fields` | TEXT | no | Comma-separated field names to read |

```bash
unity-bridge component get Player Transform
unity-bridge component get "Environment/Tree" MeshRenderer --fields "material,enabled"
unity-bridge --human component get Player Health
```

### `component set`

Modify field values on a component. Supports multiple `--update` (`-u`) flags in one call.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | GameObject path |
| `COMPONENT_TYPE` | positional | yes | Component type |
| `--update` / `-u` | TEXT (repeatable) | yes | `FIELD:JSON_VALUE` pairs |

```bash
unity-bridge component set Player Health --update "currentHp:100"
unity-bridge component set Player Transform -u "position.x:5.0" -u "position.y:0"
```

### `component add`

Add a component to a GameObject.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | GameObject path |
| `COMPONENT_TYPE` | positional | yes | Component type to add |

```bash
unity-bridge component add Player "AudioSource"
unity-bridge component add Enemy "EnemyAI"
```

---

## Scene Management

### `scene load`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | positional | yes | Scene asset path |
| `--save-current` | flag | no | Save current scene before loading |

```bash
unity-bridge scene load Assets/Scenes/Main.unity
unity-bridge scene load Assets/Scenes/Test.unity --save-current
```

### `scene save`

Save the current scene. No arguments.

```bash
unity-bridge scene save
```

### `scene create`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | positional | yes | Path for the new scene |

```bash
unity-bridge scene create Assets/Scenes/NewLevel.unity
```

---

## Prefab Operations

### `prefab validate`

Check prefab integrity and missing references.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | positional | yes | Prefab asset path |

```bash
unity-bridge prefab validate Assets/Prefabs/Player.prefab
```

### `prefab instantiate`

Create a prefab instance in the scene.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | positional | yes | Prefab asset path |
| `--position` | TEXT | no | `X,Y,Z` world position |

```bash
unity-bridge prefab instantiate Assets/Prefabs/Enemy.prefab
unity-bridge prefab instantiate Assets/Prefabs/Enemy.prefab --position 5,0,3
```

### `prefab destroy`

Remove a prefab instance from the scene (does NOT delete the asset).

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `INSTANCE_PATH` | positional | yes | GameObject path in scene |

```bash
unity-bridge prefab destroy "Enemy(Clone)"
```

### `prefab status`

Get the prefab status of an instance.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | positional | yes | Instance path in scene |

```bash
unity-bridge prefab status "Player"
```

### `prefab find-instances`

Find all instances of a prefab asset in the current scene.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `ASSET_PATH` | positional | yes | Prefab asset path |

```bash
unity-bridge prefab find-instances Assets/Prefabs/Enemy.prefab
```

### `prefab unpack`

Unpack a prefab instance.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `INSTANCE_PATH` | positional | yes | Instance path in scene |
| `--completely` | flag | no | Fully unpack (recursive) |

```bash
unity-bridge prefab unpack "Player"
unity-bridge prefab unpack "Player" --completely
```

### `prefab overrides list`

List property overrides on a prefab instance.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `INSTANCE_PATH` | positional | yes | Instance path in scene |
| `--include-default-overrides` | flag | no | Include default overrides |

```bash
unity-bridge prefab overrides list "Player"
unity-bridge prefab overrides list "Player" --include-default-overrides
```

### `prefab overrides apply`

Apply overrides from instance back to the prefab asset.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `INSTANCE_PATH` | positional | yes | Instance path in scene |
| `--target` | TEXT | no | Specific override target |

```bash
unity-bridge prefab overrides apply "Player"
unity-bridge prefab overrides apply "Player" --target Transform
```

### `prefab overrides revert`

Revert overrides on a prefab instance.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `INSTANCE_PATH` | positional | yes | Instance path in scene |
| `--target` | TEXT | no | Specific override target |

```bash
unity-bridge prefab overrides revert "Player"
```

---

## Play Mode Control

### `playmode`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `ACTION` | positional | yes | `play`, `pause`, or `stop` |

```bash
unity-bridge playmode play
unity-bridge playmode pause
unity-bridge playmode stop
```

---

## Console & Logging

### `console read`

One-shot read of Unity console logs.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--types` | TEXT | all | Comma-separated: `error,warning,log` |
| `--max` | INT | 50 | Max entries to return |
| `--pattern` | TEXT | none | Regex filter pattern |
| `--stack-trace/--no-stack-trace` | flag | true | Include stack traces |
| `--max-stack-lines` | INT | 5 | Lines per stack trace (0=unlimited, -1=none) |
| `--max-message-length` | INT | 500 | Truncate messages (0=unlimited) |

```bash
unity-bridge console read --types error --max 10
unity-bridge console read --pattern "NullReference" --no-stack-trace
unity-bridge --human console read --types error,warning
```

### `console watch`

Follow mode -- tail console logs in real-time until Ctrl+C.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--types` | TEXT | all | Comma-separated log types |
| `--poll-interval` | FLOAT | 1.0 | Seconds between polls |

```bash
unity-bridge console watch --types error,warning
unity-bridge console watch --poll-interval 0.5
```

### `console clear`

Clear all Unity console logs. No arguments.

```bash
unity-bridge console clear
```

---

## Editor Utilities

### `selection`

Get currently selected GameObjects.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--components` | flag | false | Include component lists |
| `--children` | flag | false | Include child objects |

```bash
unity-bridge selection
unity-bridge selection --components
unity-bridge selection --children
unity-bridge --human selection --components
```

### `refresh`

Refresh the Unity asset database.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--force` | flag | false | Force reimport all assets |

```bash
unity-bridge refresh
unity-bridge refresh --force
```

### `focus`

Select and frame a GameObject in the scene view.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | GameObject path |
| `--no-frame` | flag | false | Select without framing |

```bash
unity-bridge focus Player
unity-bridge focus "Environment/Tree" --no-frame
```

### `menu`

Execute any Unity Editor menu command.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `MENU_PATH` | positional | yes | Full menu path |
| `--validate-only` | flag | false | Check existence without executing |

```bash
unity-bridge menu "File/Save"
unity-bridge menu "GameObject/Create Empty"
unity-bridge menu "Assets/Refresh" --validate-only
```

### `screenshot`

Capture the game view.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OUTPUT_PATH` | positional | yes | Where to save the image |
| `--camera` | TEXT | `Main Camera` | Camera to capture from |
| `--width` | INT | none | Screenshot width |
| `--height` | INT | none | Screenshot height |

```bash
unity-bridge screenshot screenshots/test.png
unity-bridge screenshot output.png --width 1920 --height 1080
unity-bridge screenshot debug.png --camera "Debug Camera"
```

### `profiler`

Capture a performance profiler snapshot.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--memory` | flag | false | Include memory profiling |
| `--rendering` | flag | false | Include rendering stats |
| `--cpu` | flag | false | Include CPU profiling |

```bash
unity-bridge profiler --memory --rendering
unity-bridge profiler --cpu
unity-bridge profiler --memory --rendering --cpu
```

---

## Asset Operations

### `asset`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `ACTION` | positional | yes | `find`, `query`, `import`, or `refresh` |
| `--path` | TEXT | no | Asset path or search directory |
| `--type` | TEXT | no | Asset type filter (`Prefab`, `Material`, `Scene`) |
| `--pattern` | TEXT | no | Search pattern |

```bash
unity-bridge asset find --type Prefab --pattern "Enemy*"
unity-bridge asset query --path Assets/Materials/
unity-bridge asset import --path Assets/Models/character.fbx
unity-bridge asset refresh
```

---

## Extended Asset Operations

### `asset-ext create`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | positional | yes | Asset path to create |
| `--type` | TEXT | yes | Asset type to create |

```bash
unity-bridge asset-ext create Assets/Scripts/NewScript.cs --type MonoScript
```

### `asset-ext delete`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | positional | yes | Asset path to delete |
| `--trash` | flag | no | Move to trash instead of permanent delete |

```bash
unity-bridge asset-ext delete Assets/Old/unused.mat
unity-bridge asset-ext delete Assets/Old/unused.mat --trash
```

### `asset-ext copy`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `SOURCE` | positional | yes | Source asset path |
| `DEST` | positional | yes | Destination path |

```bash
unity-bridge asset-ext copy Assets/Materials/Old.mat Assets/Materials/New.mat
```

### `asset-ext move`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `SOURCE` | positional | yes | Source asset path |
| `DEST` | positional | yes | Destination path |

```bash
unity-bridge asset-ext move Assets/Old/script.cs Assets/New/script.cs
```

### `asset-ext deps`

Get dependencies of an asset.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | positional | yes | Asset path |
| `--recursive/--no-recursive` | flag | false | Include transitive dependencies |

```bash
unity-bridge asset-ext deps Assets/Prefabs/Player.prefab
unity-bridge asset-ext deps Assets/Prefabs/Player.prefab --recursive
```

### `asset-ext guid`

Get the GUID for an asset path, or resolve a GUID to a path.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH_OR_GUID` | positional | yes | Asset path or GUID string |

```bash
unity-bridge asset-ext guid Assets/Prefabs/Player.prefab
unity-bridge asset-ext guid a1b2c3d4e5f6...
```

### `asset-ext folder-create`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | positional | yes | Folder path to create |

```bash
unity-bridge asset-ext folder-create Assets/NewFeature
```

### `asset-ext folder-list`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | positional | yes | Folder path to list |

```bash
unity-bridge asset-ext folder-list Assets/Scripts
```

### `asset-ext export`

Export assets to a Unity package.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATHS` | positional (variadic) | yes | Asset paths to export |
| `--output` | TEXT | yes | Output .unitypackage file path |

```bash
unity-bridge asset-ext export Assets/Prefabs Assets/Materials --output mypackage.unitypackage
```

### `asset-ext import-package`

Import a Unity package.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `FILE` | positional | yes | .unitypackage file to import |

```bash
unity-bridge asset-ext import-package mypackage.unitypackage
```

---

## Material Operations

### `material`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `ACTION` | positional | yes | `modify`, `create`, or `duplicate` |
| `PATH` | positional | yes | Material asset path |
| `--properties` | JSON | no | JSON properties to set |

```bash
unity-bridge material modify Assets/Materials/Player.mat --properties '{"_Color": {"r":1,"g":0,"b":0,"a":1}}'
unity-bridge material create Assets/Materials/NewMat.mat
unity-bridge material duplicate Assets/Materials/Old.mat
```

---

## Build Operations

### `build`

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--target` | TEXT | none | Platform target |
| `--validate-only` | flag | false | Validate without building |
| `--output` | TEXT | none | Build output path |
| `--dev` | flag | false | Development build |
| `--timeout` | INT | 600 | Build timeout |

**Targets:** `StandaloneWindows64`, `StandaloneWindows`, `StandaloneLinux64`, `StandaloneOSX`, `Android`, `iOS`, `WebGL`

```bash
unity-bridge build --target StandaloneWindows64 --output builds/win64/
unity-bridge build --target Android --dev
unity-bridge build --target WebGL --validate-only
```

---

## Animator Operations

### `animator`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `ACTION` | positional | yes | Animator action |
| `OBJECT_PATH` | positional | yes | GameObject with Animator |
| `--state-name` | TEXT | no | Animator state name |
| `--param-name` | TEXT | no | Parameter name |
| `--param-value` | TEXT | no | Parameter value |
| `--layer` | INT | 0 | Animator layer index |

```bash
unity-bridge animator get-state Player
unity-bridge animator set-param Player --param-name "Speed" --param-value 5.0
unity-bridge animator set-state Player --state-name "Running"
unity-bridge animator get-params Player --layer 1
```

---

## Workflow Commands

### `tdd`

Compound workflow: clear console -> compile -> run tests -> read console (on failure).

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--platform` | TEXT | `EditMode` | Test platform |
| `--filter` | TEXT | none | Test filter |
| `--strict` | flag | false | Treat warnings as failures |

```bash
unity-bridge tdd --filter CombatTests
unity-bridge tdd --platform PlayMode --strict
unity-bridge tdd --platform EditMode --filter InventoryTests
```

---

## Scripting

### `script`

Execute arbitrary C# expressions in Unity Editor.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `EXPRESSION` | positional | yes* | C# expression to evaluate |
| `--file` | PATH | no | Read expression from file |
| `--timeout` | INT | 30 | Execution timeout |

*Required unless `--file` is provided.

```bash
unity-bridge script "EditorApplication.isPlaying"
unity-bridge script "Selection.activeGameObject.name"
unity-bridge script --file setup.cs
unity-bridge script --file long_task.cs --timeout 120
```

---

## Diagnostics & Lifecycle

### `status`

Quick alive/dead check. Returns within 100ms. Exit code 0 if healthy, 2 if not.

```bash
unity-bridge status
```

### `doctor`

Full diagnostic suite: project structure, bridge installed, version compat,
heartbeat, directory permissions, orphaned files, dependencies, Unity process, version.

```bash
unity-bridge doctor
unity-bridge --human doctor
```

### `version`

Show CLI version, C# bridge version, Python version, platform.

```bash
unity-bridge version
```

### `install`

Install or update the C# bridge files into the Unity project.

| Argument | Type | Description |
|----------|------|-------------|
| `--check` | flag | Report status without changes |
| `--force` | flag | Force reinstall |

```bash
unity-bridge install
unity-bridge install --check
unity-bridge install --force
```

### `init`

Create the `.claude/unity/` directory structure (commands/, responses/).

```bash
unity-bridge init
```

### `clean`

Remove orphaned command/response files.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--age` | INT | 5 | Minutes threshold |
| `--all` | flag | false | Remove all (alias for --age 0) |
| `--dry-run` | flag | false | Show what would be deleted |

```bash
unity-bridge clean
unity-bridge clean --dry-run
unity-bridge clean --age 1
unity-bridge clean --all
```

---

## Batch & Serve

### `batch`

Execute multiple commands from a JSON file.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `FILE` | positional | yes | JSON file with commands array |
| `--stop-on-error` | flag | true | Halt on first failure |
| `--parallel` | flag | false | Run read-only commands concurrently |

```bash
unity-bridge batch commands.json
unity-bridge batch commands.json --parallel
```

**Batch file format:**
```json
{
  "commands": [
    {"type": "clear-console"},
    {"type": "compile", "parameters": {"waitForCompletion": true}},
    {"type": "run-tests", "parameters": {"testPlatform": "EditMode"}}
  ]
}
```

### `serve`

Start the MCP server for Claude Code integration.

```bash
unity-bridge serve
```

---

## Compile Group

Script compilation analysis commands. Note: to trigger compilation and wait,
use `test compile`. This group is for inspecting assembly/define state.

### `compile assemblies`

List all assemblies in the project.

```bash
unity-bridge compile assemblies
```

### `compile defines`

List scripting define symbols for an assembly.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `ASSEMBLY_NAME` | positional | yes | Assembly name |

```bash
unity-bridge compile defines Assembly-CSharp
```

### `compile which`

Find which assembly a script belongs to.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `SCRIPT_PATH` | positional | yes | Script asset path |

```bash
unity-bridge compile which Assets/Scripts/Player.cs
```

### `compile optimization`

Get or set the compilation optimization level.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--set` | TEXT | none | Set level: `none`, `debug`, or `release` |

```bash
unity-bridge compile optimization
unity-bridge compile optimization --set debug
unity-bridge compile optimization --set release
```

---

## Undo Group

### `undo perform`

Undo the last recorded action.

```bash
unity-bridge undo perform
```

### `undo redo`

Redo the last undone action.

```bash
unity-bridge undo redo
```

### `undo history`

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--limit` | INT | none | Max number of entries |

```bash
unity-bridge undo history
unity-bridge undo history --limit 10
```

### `undo clear`

Clear the entire undo stack.

```bash
unity-bridge undo clear
```

### `undo group-name`

Get the name of the current undo group.

```bash
unity-bridge undo group-name
```

### `undo collapse`

Collapse undo operations into a single group.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `GROUP_INDEX` | positional | yes | Group index to collapse |
| `--name` | TEXT | no | Name for the collapsed group |

```bash
unity-bridge undo collapse 0
unity-bridge undo collapse 0 --name "Batch edit"
```

---

## Settings Group

### `settings get`

Get editor settings. Optionally pass a specific key.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `KEY` | positional | no | Specific setting key (omit for all) |

```bash
unity-bridge settings get
unity-bridge settings get "EditorSettings.serializationMode"
```

### `settings set`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `KEY` | positional | yes | Setting key |
| `VALUE` | positional | yes | Setting value |

```bash
unity-bridge settings set "EditorSettings.serializationMode" "ForceText"
```

### `settings defines`

Manage scripting define symbols.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `ACTION` | positional | yes | `list`, `add`, or `remove` |
| `--symbol` | TEXT | no | Symbol name (required for add/remove) |
| `--platform` | TEXT | no | Target platform |

```bash
unity-bridge settings defines list
unity-bridge settings defines add --symbol ENABLE_LOGGING
unity-bridge settings defines remove --symbol ENABLE_LOGGING
```

---

## Profile Group

### `profile list`

List available quality profiles.

```bash
unity-bridge profile list
```

### `profile active`

Get the currently active quality profile.

```bash
unity-bridge profile active
```

### `profile set`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PROFILE_PATH` | positional | yes | Profile asset path |

```bash
unity-bridge profile set "Assets/Settings/HighQuality.asset"
```

### `profile info`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PROFILE_PATH` | positional | yes | Profile asset path |

```bash
unity-bridge profile info "Assets/Settings/HighQuality.asset"
```

---

## Package Group

### `package list`

List installed packages.

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--offline` | flag | false | Use cached data only |
| `--include-indirect` | flag | false | Include transitive dependencies |
| `--source` | TEXT | none | Filter by source |

```bash
unity-bridge package list
unity-bridge package list --include-indirect
unity-bridge package list --offline
```

### `package search`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `QUERY` | positional | yes | Search query |
| `--all` | flag | false | Show all results |

```bash
unity-bridge package search "input system"
unity-bridge package search cinemachine --all
```

### `package add`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `IDENTIFIER` | positional | yes | Package identifier (e.g., com.unity.inputsystem) |

```bash
unity-bridge package add com.unity.inputsystem
unity-bridge package add com.unity.cinemachine@3.0.0
```

### `package remove`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `NAME` | positional | yes | Package name |

```bash
unity-bridge package remove com.unity.inputsystem
```

### `package info`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `NAME` | positional | yes | Package name |

```bash
unity-bridge package info com.unity.inputsystem
```

### `package embed`

Embed a package into the project for local editing.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `NAME` | positional | yes | Package name |

```bash
unity-bridge package embed com.unity.inputsystem
```

### `package resolve`

Force package resolution.

```bash
unity-bridge package resolve
```

---

## Lightmap Group

### `lightmap bake`

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--run-async/--no-run-async` | flag | false | Run bake asynchronously |
| `--timeout` | FLOAT | none | Timeout in seconds |

```bash
unity-bridge lightmap bake
unity-bridge lightmap bake --run-async
unity-bridge lightmap bake --timeout 600
```

### `lightmap cancel`

Cancel an in-progress lightmap bake.

```bash
unity-bridge lightmap cancel
```

### `lightmap clear`

Clear baked lightmap data.

```bash
unity-bridge lightmap clear
```

### `lightmap status`

Get the current lightmap bake status.

```bash
unity-bridge lightmap status
```

### `lightmap settings`

Get current lightmap settings.

```bash
unity-bridge lightmap settings
```

---

## Shader Group

### `shader list`

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--errors-only` | flag | false | Only show shaders with errors |

```bash
unity-bridge shader list
unity-bridge shader list --errors-only
```

### `shader info`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `NAME` | positional | yes | Shader name |

```bash
unity-bridge shader info "Standard"
unity-bridge shader info "Universal Render Pipeline/Lit"
```

### `shader errors`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `NAME` | positional | yes | Shader name |

```bash
unity-bridge shader errors "Custom/MyShader"
```

### `shader properties`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `NAME` | positional | yes | Shader name |

```bash
unity-bridge shader properties "Standard"
```

### `shader find-by-property`

Find shaders that have a specific property.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PROPERTY_NAME` | positional | yes | Property name to search for |

```bash
unity-bridge shader find-by-property _MainTex
unity-bridge shader find-by-property _Color
```

### `shader keywords`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `NAME` | positional | yes | Shader name |
| `--global` | flag | false | Show global keywords |
| `--local` | flag | false | Show local keywords |

```bash
unity-bridge shader keywords "Standard"
unity-bridge shader keywords "Standard" --global
unity-bridge shader keywords "Standard" --local
```

---

## Scene Extensions Group

### `scene-ext setup save`

Save the current scene setup (loaded scenes, active scene) under a name.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `NAME` | positional | yes | Setup name |

```bash
unity-bridge scene-ext setup save "development"
```

### `scene-ext setup restore`

Restore a previously saved scene setup.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `NAME` | positional | yes | Setup name |

```bash
unity-bridge scene-ext setup restore "development"
```

### `scene-ext setup list`

List all saved scene setups.

```bash
unity-bridge scene-ext setup list
```

### `scene-ext play-start`

Configure the play mode start scene.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--set` | PATH | no | Scene path to use as play start |
| `--clear` | flag | no | Clear the play start scene |

```bash
unity-bridge scene-ext play-start --set Assets/Scenes/Main.unity
unity-bridge scene-ext play-start --clear
```

### `scene-ext cross-refs`

Find cross-scene references.

```bash
unity-bridge scene-ext cross-refs
```

### `scene-ext list-loaded`

List all currently loaded scenes.

```bash
unity-bridge scene-ext list-loaded
```

### `scene-ext preview-create`

Create a preview scene.

```bash
unity-bridge scene-ext preview-create
```

### `scene-ext preview-close`

Close a preview scene.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `HANDLE` | positional | yes | Preview scene handle |

```bash
unity-bridge scene-ext preview-close 12345
```

---

## Import Settings Group

### `import-settings get`

Get import settings for an asset.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | positional | yes | Asset path |

```bash
unity-bridge import-settings get Assets/Textures/icon.png
unity-bridge import-settings get Assets/Models/character.fbx
```

### `import-settings set`

Set import settings on an asset. Use `-s` / `--setting` (repeatable) for each setting.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | positional | yes | Asset path |
| `--setting` / `-s` | TEXT (repeatable) | yes | `KEY:VALUE` pairs |

```bash
unity-bridge import-settings set Assets/Textures/icon.png -s "maxTextureSize:512"
unity-bridge import-settings set Assets/Textures/icon.png -s "maxTextureSize:512" -s "filterMode:Bilinear"
```

### `import-settings reimport`

Force reimport an asset.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | positional | yes | Asset path |
| `--force` | flag | no | Force reimport even if unchanged |

```bash
unity-bridge import-settings reimport Assets/Textures/icon.png
unity-bridge import-settings reimport Assets/Textures/icon.png --force
```

### `import-settings bulk-set`

Apply import settings to all matching assets in a folder.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `FOLDER` | positional | yes | Folder path |
| `--setting` / `-s` | TEXT (repeatable) | yes | `KEY:VALUE` pairs |
| `--filter` | TEXT | no | File filter pattern |

```bash
unity-bridge import-settings bulk-set Assets/Textures -s "maxTextureSize:256"
unity-bridge import-settings bulk-set Assets/Textures -s "maxTextureSize:256" --filter "*.png"
```

### `import-settings template-save`

Save current import settings as a reusable template.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `NAME` | positional | yes | Template name |
| `PATH` | positional | yes | Source asset to capture settings from |

```bash
unity-bridge import-settings template-save "mobile-texture" Assets/Textures/icon.png
```

### `import-settings template-apply`

Apply a saved template to an asset.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `NAME` | positional | yes | Template name |
| `PATH` | positional | yes | Target asset path |

```bash
unity-bridge import-settings template-apply "mobile-texture" Assets/Textures/bg.png
```

---

## Hierarchy Duplicate

### `hierarchy duplicate`

Duplicate a GameObject in the scene.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | Hierarchy path to the GameObject |

```bash
unity-bridge hierarchy duplicate "Environment/Tree"
unity-bridge hierarchy duplicate "Player"
```

---

## Select Group

### `select`

Set or clear the Unity Editor selection.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECTS` | positional (variadic) | no | GameObject paths to select |
| `--clear` | flag | no | Clear the current selection |

```bash
unity-bridge select Player
unity-bridge select Player "Environment/Tree"
unity-bridge select --clear
```

---

## Transform Group

### `transform get`

Get all transform data (position, rotation, scale) for a GameObject.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | Hierarchy path to the GameObject |

```bash
unity-bridge transform get Player
unity-bridge --human transform get "Environment/Tree"
```

### `transform set`

Set transform position, rotation, and/or scale.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | Hierarchy path to the GameObject |
| `--position` / `-p` | TEXT | no | Position as X,Y,Z |
| `--rotation` / `-r` | TEXT | no | Euler rotation as X,Y,Z |
| `--scale` / `-s` | TEXT | no | Local scale as X,Y,Z |
| `--local` | flag | no | Use local position instead of world |

```bash
unity-bridge transform set Player -p 5,0,3
unity-bridge transform set Player -r 0,90,0
unity-bridge transform set Player -s 2,2,2
unity-bridge transform set Player -p 1,0,0 --local
unity-bridge transform set Player -p 5,0,3 -r 0,90,0 -s 2,2,2
```

### `transform parent`

Reparent a GameObject.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | Hierarchy path to the GameObject |
| `NEW_PARENT` | positional | no | Hierarchy path of new parent (omit to unparent) |
| `--world-position-stays` / `--no-world-position-stays` | flag | true | Preserve world position |

```bash
unity-bridge transform parent "Enemy" "EnemyGroup"
unity-bridge transform parent "Enemy"
unity-bridge transform parent "Enemy" "Group" --no-world-position-stays
```

### `transform sibling-index`

Set hierarchy order within parent.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | Hierarchy path to the GameObject |
| `INDEX` | INTEGER | yes | Target sibling index |

```bash
unity-bridge transform sibling-index "Enemy" 0
unity-bridge transform sibling-index "UI/Button" 3
```

---

## Property Group

SerializedProperty access commands for fine-grained component field manipulation.

### `property list`

List all serialized properties on a component.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | Hierarchy path to the GameObject |
| `COMPONENT_TYPE` | positional | yes | Component type name |

```bash
unity-bridge property list Player BoxCollider
unity-bridge property list "UI/Canvas" CanvasScaler
```

### `property get`

Get a serialized property value.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | Hierarchy path to the GameObject |
| `COMPONENT_TYPE` | positional | yes | Component type name |
| `PROPERTY_PATH` | positional | yes | SerializedProperty path |

```bash
unity-bridge property get Player BoxCollider "m_Size"
unity-bridge property get Player Transform "m_LocalPosition"
```

### `property set`

Set a serialized property value.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | Hierarchy path to the GameObject |
| `COMPONENT_TYPE` | positional | yes | Component type name |
| `PROPERTY_PATH` | positional | yes | SerializedProperty path |
| `VALUE` | positional | yes | JSON value to set |

```bash
unity-bridge property set Player BoxCollider "m_Size" '{"x":2,"y":2,"z":2}'
unity-bridge property set Player MeshRenderer "m_Enabled" "true"
```

---

## Prefs Group

EditorPrefs and SessionState commands.

### `prefs get`

Get an EditorPrefs or SessionState value.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `KEY` | positional | yes | Preference key |
| `--type / -t` | TEXT | no | Value type: string, int, float, bool (default: string) |
| `--scope / -s` | TEXT | no | Storage scope: prefs or session (default: prefs) |

```bash
unity-bridge prefs get MyPlugin.Setting
unity-bridge prefs get MyPlugin.Setting -t int
unity-bridge prefs get MyKey -s session
unity-bridge prefs get MyPlugin.Debug -t bool -s session
```

### `prefs set`

Set an EditorPrefs or SessionState value.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `KEY` | positional | yes | Preference key |
| `VALUE` | positional | yes | Value to set |
| `--type / -t` | TEXT | no | Value type: string, int, float, bool (default: string) |
| `--scope / -s` | TEXT | no | Storage scope: prefs or session (default: prefs) |

```bash
unity-bridge prefs set MyPlugin.Setting "value"
unity-bridge prefs set MyPlugin.Count 42 -t int
unity-bridge prefs set MyFlag true -t bool -s session
```

### `prefs delete`

Delete an EditorPrefs or SessionState key.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `KEY` | positional | yes | Preference key to delete |
| `--scope / -s` | TEXT | no | Storage scope: prefs or session (default: prefs) |

```bash
unity-bridge prefs delete MyPlugin.Setting
unity-bridge prefs delete MyKey -s session
```

### `prefs has`

Check if an EditorPrefs or SessionState key exists.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `KEY` | positional | yes | Preference key to check |
| `--scope / -s` | TEXT | no | Storage scope: prefs or session (default: prefs) |

```bash
unity-bridge prefs has MyPlugin.Setting
unity-bridge prefs has MyKey -s session
```

---

## Build Scenes Group

Manage the Build Settings scene list.

### `build-scenes list`

List all scenes in Build Settings. No arguments.

```bash
unity-bridge build-scenes list
```

### `build-scenes add`

Add a scene to the Build Settings list.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `SCENE_PATH` | positional | yes | Scene asset path |
| `--index / -i` | INTEGER | no | Position to insert at (-1 = append, default: -1) |

```bash
unity-bridge build-scenes add Assets/Scenes/Main.unity
unity-bridge build-scenes add Assets/Scenes/Main.unity -i 0
```

### `build-scenes remove`

Remove a scene from the Build Settings list.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `SCENE_PATH` | positional | yes | Scene asset path to remove |

```bash
unity-bridge build-scenes remove Assets/Scenes/Old.unity
```

### `build-scenes enable`

Enable a scene in the Build Settings list.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `SCENE_PATH` | positional | yes | Scene asset path to enable |

```bash
unity-bridge build-scenes enable Assets/Scenes/Main.unity
```

### `build-scenes disable`

Disable a scene in the Build Settings list.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `SCENE_PATH` | positional | yes | Scene asset path to disable |

```bash
unity-bridge build-scenes disable Assets/Scenes/Test.unity
```

---

## Physics Group

Physics configuration commands.

### `physics get`

Get current physics settings. No arguments.

```bash
unity-bridge physics get
```

### `physics set`

Set physics configuration values.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--gravity / -g` | TEXT | no | Gravity as X,Y,Z (e.g. `0,-9.81,0`) |
| `--solver-iterations` | INTEGER | no | Default solver iterations |

```bash
unity-bridge physics set -g "0,-9.81,0"
unity-bridge physics set --solver-iterations 12
unity-bridge physics set -g "0,-20,0" --solver-iterations 8
```

### `physics collision get`

Get the layer collision matrix. No arguments.

```bash
unity-bridge physics collision get
```

### `physics collision set`

Set collision between two layers.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `LAYER1` | INTEGER | yes | First layer index (0-31) |
| `LAYER2` | INTEGER | yes | Second layer index (0-31) |
| `--ignore / --collide` | flag | no | Ignore or enable collisions (default: `--collide`) |

```bash
unity-bridge physics collision set 8 9 --ignore
unity-bridge physics collision set 8 9 --collide
```

---

## Quality Group

Quality settings commands.

### `quality list`

List all quality levels. No arguments.

```bash
unity-bridge quality list
```

### `quality get`

Get current quality settings. No arguments.

```bash
unity-bridge quality get
```

### `quality set-level`

Switch active quality level.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `LEVEL` | INTEGER | yes | Quality level index |

```bash
unity-bridge quality set-level 0
unity-bridge quality set-level 2
```

---

## Tags Group

Tag management commands.

### `tags list`

List all project tags. No arguments.

```bash
unity-bridge tags list
```

### `tags add`

Add a custom tag.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `TAG_NAME` | positional | yes | Tag name to add |

```bash
unity-bridge tags add "Interactable"
unity-bridge tags add "Collectible"
```

---

## Layers Group

Layer management commands.

### `layers list`

List all layers. No arguments.

```bash
unity-bridge layers list
```

### `layers add`

Add a layer to a user slot.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `LAYER_NAME` | positional | yes | Layer name to add |
| `--index / -i` | INTEGER | no | Specific slot index (8-31) |

```bash
unity-bridge layers add "Interactables"
unity-bridge layers add "Interactables" -i 10
```

---

## Sorting Layers Group

Sorting layer commands.

### `sorting-layers list`

List all sorting layers. No arguments.

```bash
unity-bridge sorting-layers list
```

### `sorting-layers add`

Add a sorting layer.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `NAME` | positional | yes | Sorting layer name |

```bash
unity-bridge sorting-layers add "Foreground"
unity-bridge sorting-layers add "UI Overlay"
```

---

## Editor Config Group

Editor configuration commands.

### `editor-config get`

Get current editor settings. No arguments.

```bash
unity-bridge editor-config get
```

### `editor-config set`

Set an editor configuration value.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `KEY` | positional | yes | Setting key |
| `VALUE` | positional | yes | New value |

```bash
unity-bridge editor-config set "enterPlayModeOptionsEnabled" "true"
unity-bridge editor-config set "serializationMode" "ForceText"
```

---

## Bridge Command Types

For batch files and advanced use, these are the bridge command type strings and
their CLI equivalents:

| Command Type | CLI Equivalent |
|---|---|
| `run-tests` | `test run` |
| `compile` | `test compile` |
| `query-hierarchy` | `hierarchy` |
| `get-component-data` | `component get` |
| `set-component-data` | `component set` |
| `add-component` | `component add` |
| `validate-prefab` | `prefab validate` |
| `prefab-operation` | `prefab instantiate/destroy/...` |
| `scene-operation` | `scene load/save/create` |
| `playmode-control` | `playmode` |
| `read-console` | `console read` |
| `clear-console` | `console clear` |
| `capture-screenshot` | `screenshot` |
| `profiler-sample` | `profiler` |
| `material-operation` | `material` |
| `asset-operation` | `asset` |
| `build-operation` | `build` |
| `animator-operation` | `animator` |
| `get-selection` | `selection` |
| `refresh-assets` | `refresh` |
| `focus-object` | `focus` |
| `execute-menu-item` | `menu` |
| `execute-script` | `script` |
| `duplicate-object` | `hierarchy duplicate` |
| `set-selection` | `select` |
| `transform-operation` | `transform get/set/parent/sibling-index` |
| `serialized-property` | `property list/get/set` |
| `editor-prefs` | `prefs get/set/delete/has` |
| `build-scenes-operation` | `build-scenes list/add/remove/enable/disable` |
| `physics-operation` | `physics get/set` |
| `physics-collision` | `physics collision get/set` |
| `quality-operation` | `quality list/get/set-level` |
| `tags-operation` | `tags list/add` |
| `layers-operation` | `layers list/add` |
| `sorting-layers-operation` | `sorting-layers list/add` |
| `editor-config-operation` | `editor-config get/set` |
