# Unity Bridge CLI -- Complete Command Reference

## Table of Contents

1. [Testing Commands](#testing-commands)
2. [Hierarchy & Components](#hierarchy--components)
3. [Scene Management](#scene-management)
4. [Scene Extended](#scene-extended)
5. [Prefab Operations](#prefab-operations)
6. [Play Mode Control](#play-mode-control)
7. [Console & Logging](#console--logging)
8. [Editor Utilities](#editor-utilities)
9. [Asset Operations](#asset-operations)
10. [Asset Extended Operations](#asset-extended-operations)
11. [Material Operations](#material-operations)
12. [Build Operations](#build-operations)
13. [Build Profiles](#build-profiles)
14. [Animator Operations](#animator-operations)
15. [Player Settings](#player-settings)
16. [Package Manager](#package-manager)
17. [Compilation Pipeline](#compilation-pipeline)
18. [Undo System](#undo-system)
19. [Shader Inspection](#shader-inspection)
20. [Lightmap Operations](#lightmap-operations)
21. [Import Settings](#import-settings)
22. [Workflow Commands](#workflow-commands)
23. [Scripting](#scripting)
24. [Diagnostics & Lifecycle](#diagnostics--lifecycle)
25. [Batch & Serve](#batch--serve)
26. [Bridge Command Types](#bridge-command-types)

---

## Testing Commands

### `unity-bridge test run`

Run EditMode or PlayMode tests.

| Argument | Short | Type | Default | Description |
|---|---|---|---|---|
| `--platform` | `-P` | string | `EditMode` | `EditMode` or `PlayMode` |
| `--filter` | `-f` | string | none | Test name filter pattern |
| `--timeout` |  | int | 300 | Seconds to wait |

```bash
unity-bridge test run --platform EditMode
unity-bridge test run -P PlayMode --filter "Combat*"
unity-bridge test run --filter InventoryTests --timeout 60
```
### `unity-bridge test compile`

Trigger script compilation and wait for results.

| Argument | Type | Default | Description |
|---|---|---|---|
| `--wait/--no-wait` | bool | true | Wait for compilation to complete |
| `--timeout` | int | 120 | Seconds to wait |

```bash
unity-bridge test compile
unity-bridge test compile --no-wait
```
### `unity-bridge test list`

Discover available tests without executing them.

| Argument | Short | Type | Default | Description |
|---|---|---|---|---|
| `--platform` | `-P` | string | none | `EditMode` or `PlayMode` filter |
| `--filter` | `-f` | string | none | Test name filter pattern |
| `--categories` |  | flag | false | List test categories instead of tests |
| `--assemblies` |  | flag | false | List test assemblies instead of tests |

```bash
unity-bridge test list
unity-bridge test list --platform EditMode
unity-bridge test list --filter "Combat*"
unity-bridge test list --categories
unity-bridge test list --assemblies
```

---

## Hierarchy & Components

### `unity-bridge hierarchy`

Query the active scene's GameObject tree.

| Argument | Short | Type | Default | Description |
|---|---|---|---|---|
| `--depth` | `-d` | int | 5 | Max depth to traverse |
| `--inactive` |  | flag | false | Include inactive GameObjects |
| `--root` | `-r` | string | none | Start from this GameObject path |

```bash
unity-bridge hierarchy --depth 2
unity-bridge hierarchy --root "Player" --inactive
unity-bridge hierarchy --depth 1 --human  # Tree view output
```
### `unity-bridge component get`

Read field values from a component.

| Argument | Type | Required | Description |
|---|---|---|---|
| `OBJECT` | positional | yes | GameObject path (e.g. `Player`) |
| `TYPE` | positional | yes | Component type (e.g. `Transform`, `PlayerStats`) |
| `--fields` / `-F` | string | no | Comma-separated field names to read |

```bash
unity-bridge component get Player Transform
unity-bridge component get "Environment/Tree" MeshRenderer --fields "material,enabled"
```
### `unity-bridge component set`

Modify field values on a component. Supports multiple updates in one call.

| Argument | Short | Type | Required | Description |
|---|---|---|---|---|
| `OBJECT` |  | positional | yes | GameObject path |
| `TYPE` |  | positional | yes | Component type |
| `--update` | `-u` | repeatable | yes | `FIELD:JSON_VALUE` pairs |

```bash
unity-bridge component set Player Health --update 'currentHp:100'
unity-bridge component set Player Transform --update 'position.x:5.0' --update 'position.y:0'
```
### `unity-bridge component add`

Add a component to a GameObject.

| Argument | Type | Required | Description |
|---|---|---|---|
| `OBJECT` | positional | yes | GameObject path |
| `TYPE` | positional | yes | Component type to add |

```bash
unity-bridge component add Player "AudioSource"
unity-bridge component add Enemy "EnemyAI"
```
### `unity-bridge hierarchy missing-scripts`

Find (and optionally remove) missing MonoBehaviour scripts.

| Argument | Type | Default | Description |
|---|---|---|---|
| `--fix` | flag | false | Remove missing scripts instead of just listing |

```bash
unity-bridge hierarchy missing-scripts
unity-bridge hierarchy missing-scripts --fix
```
### `unity-bridge hierarchy static-flags`

Get static editor flags for a GameObject.

| Argument | Type | Required | Description |
|---|---|---|---|
| `OBJECT` | positional | yes | Hierarchy path to the GameObject |

```bash
unity-bridge hierarchy static-flags Player
```
### `unity-bridge hierarchy set-static-flags`

Set static editor flags on a GameObject.

| Argument | Type | Required | Description |
|---|---|---|---|
| `OBJECT` | positional | yes | Hierarchy path to the GameObject |
| `FLAGS...` | positional | yes | Flag names (e.g. BatchingStatic, NavigationStatic) |

```bash
unity-bridge hierarchy set-static-flags Terrain BatchingStatic NavigationStatic OccludeeStatic
```
### `unity-bridge hierarchy set-layer`

Set layer on a GameObject.

| Argument | Short | Type | Required | Description |
|---|---|---|---|---|
| `OBJECT` |  | positional | yes | Hierarchy path to the GameObject |
| `LAYER` |  | positional | yes | Layer index (int) |
| `--recursive` | `-r` | flag | no | Apply to all children (including inactive) |

```bash
unity-bridge hierarchy set-layer Player 8
unity-bridge hierarchy set-layer Environment/Trees 10 --recursive
```
### `unity-bridge hierarchy set-tag`

Set tag on a GameObject.

| Argument | Type | Required | Description |
|---|---|---|---|
| `OBJECT` | positional | yes | Hierarchy path to the GameObject |
| `TAG` | positional | yes | Tag name to set |

```bash
unity-bridge hierarchy set-tag Player "Player"
unity-bridge hierarchy set-tag Enemy "Enemy"
```

---

## Scene Management

### `unity-bridge scene load`

Load a scene in the Unity Editor.

| Argument | Type | Required | Description |
|---|---|---|---|
| `PATH` | positional | yes | Scene asset path |
| `--save-current` | flag | no | Save current scene before loading |

```bash
unity-bridge scene load Assets/Scenes/Main.unity
unity-bridge scene load Assets/Scenes/Test.unity --save-current
```
### `unity-bridge scene save`

Save the current scene. No arguments.

### `unity-bridge scene create`

Create a new scene at the given path.

| Argument | Type | Required | Description |
|---|---|---|---|
| `PATH` | positional | yes | Path for the new scene |

```bash
unity-bridge scene create Assets/Scenes/NewLevel.unity
```

---

## Scene Extended

### `unity-bridge scene-ext setup save`

Save the current multi-scene layout as a named setup.

| Argument | Type | Required | Description |
|---|---|---|---|
| `NAME` | positional | yes | Setup name (alphanumeric, hyphens, underscores, max 64) |

```bash
unity-bridge scene-ext setup save combat-setup
```
### `unity-bridge scene-ext setup restore`

Restore a previously saved multi-scene layout.

| Argument | Type | Required | Description |
|---|---|---|---|
| `NAME` | positional | yes | Setup name to restore |

```bash
unity-bridge scene-ext setup restore combat-setup
```
### `unity-bridge scene-ext setup list`

List all saved scene setups. No arguments.

### `unity-bridge scene-ext play-start`

Get, set, or clear the play mode start scene.

| Argument | Type | Default | Description |
|---|---|---|---|
| `--set` | string | none | Scene path to set as play mode start scene |
| `--clear` | flag | false | Clear the play mode start scene |

```bash
unity-bridge scene-ext play-start
unity-bridge scene-ext play-start --set Assets/Scenes/Boot.unity
unity-bridge scene-ext play-start --clear
```
### `unity-bridge scene-ext cross-refs`

Detect cross-scene references across all loaded scenes. No arguments.

### `unity-bridge scene-ext list-loaded`

List all loaded scenes with status (active, loaded, dirty, path). No arguments.

### `unity-bridge scene-ext preview-create`

Create an empty preview scene for isolated testing. No arguments.


Returns a `handle` integer used to close the preview later.
### `unity-bridge scene-ext preview-close`

Close a previously created preview scene.

| Argument | Type | Required | Description |
|---|---|---|---|
| `HANDLE` | positional (int) | yes | Preview scene handle from preview-create |

```bash
unity-bridge scene-ext preview-close 12345
```

---

## Prefab Operations

### `unity-bridge prefab validate`

Check prefab integrity and missing references.

| Argument | Type | Required | Description |
|---|---|---|---|
| `PATH` | positional | yes | Prefab asset path |

```bash
unity-bridge prefab validate Assets/Prefabs/Player.prefab
```
### `unity-bridge prefab instantiate`

Create a prefab instance in the scene.

| Argument | Short | Type | Required | Description |
|---|---|---|---|---|
| `PATH` |  | positional | yes | Prefab asset path |
| `--position` | `-pos` | string | no | `X,Y,Z` position |

```bash
unity-bridge prefab instantiate Assets/Prefabs/Enemy.prefab
unity-bridge prefab instantiate Assets/Prefabs/Enemy.prefab --position 5,0,3
```
### `unity-bridge prefab destroy`

Remove a prefab instance from the scene (does NOT delete the asset).

| Argument | Type | Required | Description |
|---|---|---|---|
| `INSTANCE_PATH` | positional | yes | GameObject path in scene |

```bash
unity-bridge prefab destroy "Enemy(Clone)"
```
### `unity-bridge prefab overrides list`

List all overrides on a prefab instance.

| Argument | Type | Default | Description |
|---|---|---|---|
| `INSTANCE_PATH` | positional (required) |  | Hierarchy path to prefab instance |
| `--include-default-overrides` | flag | false | Include default overrides (position/rotation) |

```bash
unity-bridge prefab overrides list Player
unity-bridge prefab overrides list Player --include-default-overrides
```
### `unity-bridge prefab overrides apply`

Apply overrides from a prefab instance to the prefab asset.

| Argument | Short | Type | Default | Description |
|---|---|---|---|---|
| `INSTANCE_PATH` |  | positional (required) |  | Hierarchy path to prefab instance |
| `--target` | `-t` | string | none | Specific override to apply (omit for all) |

```bash
unity-bridge prefab overrides apply Player
unity-bridge prefab overrides apply Player --target "Transform"
```
### `unity-bridge prefab overrides revert`

Revert overrides on a prefab instance back to the prefab asset state.

| Argument | Short | Type | Default | Description |
|---|---|---|---|---|
| `INSTANCE_PATH` |  | positional (required) |  | Hierarchy path to prefab instance |
| `--target` | `-t` | string | none | Specific override to revert (omit for all) |

```bash
unity-bridge prefab overrides revert Player
unity-bridge prefab overrides revert Player --target "Transform"
```
### `unity-bridge prefab status`

Get prefab type and instance status.

| Argument | Type | Required | Description |
|---|---|---|---|
| `PATH` | positional | yes | Hierarchy path or asset path to query |

```bash
unity-bridge prefab status Player
unity-bridge prefab status Assets/Prefabs/Player.prefab
```
### `unity-bridge prefab find-instances`

Find all scene instances of a prefab asset (root-level only).

| Argument | Type | Required | Description |
|---|---|---|---|
| `ASSET_PATH` | positional | yes | Prefab asset path |

```bash
unity-bridge prefab find-instances Assets/Prefabs/Enemy.prefab
```
### `unity-bridge prefab unpack`

Unpack a prefab instance.

| Argument | Type | Default | Description |
|---|---|---|---|
| `INSTANCE_PATH` | positional (required) |  | Hierarchy path to prefab instance |
| `--completely` | flag | false | Fully unpack nested prefabs |

```bash
unity-bridge prefab unpack Player
unity-bridge prefab unpack Player --completely
```

---

## Play Mode Control

### `unity-bridge playmode`

Control Unity Editor play mode.

| Argument | Type | Required | Description |
|---|---|---|---|
| `ACTION` | positional | yes | `play`, `pause`, or `stop` |

```bash
unity-bridge playmode play
unity-bridge playmode pause
unity-bridge playmode stop
```

---

## Console & Logging

### `unity-bridge console read`

One-shot read of Unity console logs.

| Argument | Short | Type | Default | Description |
|---|---|---|---|---|
| `--types` | `-T` | string | all | Comma-separated: `error,warning,log` |
| `--max` | `-m` | int | none | Max entries to return |
| `--pattern` | `-p` | string | none | Regex filter pattern |
| `--stack-trace` |  | flag | false | Include stack traces |
| `--max-stack-lines` |  | int | none | Lines per stack trace |
| `--max-message-length` |  | int | none | Truncate messages (0=unlimited) |

```bash
unity-bridge console read --types error --max 10
unity-bridge console read --pattern "NullReference"
unity-bridge console read --types error,warning --human
```
### `unity-bridge console watch`

Follow mode -- tail console logs in real-time until Ctrl+C.

| Argument | Short | Type | Default | Description |
|---|---|---|---|---|
| `--types` | `-T` | string | all | Comma-separated log types |
| `--poll-interval` |  | float | 2.0 | Seconds between polls |

```bash
unity-bridge console watch --types error,warning
unity-bridge console watch --poll-interval 0.5
```
### `unity-bridge console clear`

Clear all Unity console logs. No arguments.


---

## Editor Utilities

### `unity-bridge selection`

Get currently selected GameObjects.

| Argument | Type | Default | Description |
|---|---|---|---|
| `--components` | flag | false | Include component lists |
| `--children` | flag | false | Include child objects |
### `unity-bridge refresh`

Refresh the Unity asset database.

| Argument | Type | Default | Description |
|---|---|---|---|
| `--force` | flag | false | Force reimport all assets |
### `unity-bridge focus`

Frame a GameObject in the scene view.

| Argument | Type | Required | Description |
|---|---|---|---|
| `OBJECT` | positional | yes | GameObject path |
| `--no-frame` | flag | no | Select without framing |
### `unity-bridge menu`

Execute any Unity Editor menu command.

| Argument | Type | Required | Description |
|---|---|---|---|
| `MENU_PATH` | positional | yes | Full menu path |
| `--validate-only` | flag | no | Check existence without executing |

```bash
unity-bridge menu "File/Save"
unity-bridge menu "GameObject/Create Empty"
unity-bridge menu "Assets/Refresh" --validate-only
```
### `unity-bridge screenshot`

Capture the game view.

| Argument | Type | Required | Description |
|---|---|---|---|
| `OUTPUT_PATH` | positional | yes | Where to save the image |
| `--camera` | string | no | Camera to capture from |
| `--width` | int | no | Screenshot width |
| `--height` | int | no | Screenshot height |

```bash
unity-bridge screenshot screenshots/test.png
unity-bridge screenshot output.png --width 1920 --height 1080
```

---

## Asset Operations

### `unity-bridge asset`

Basic asset database operations.

| Argument | Short | Type | Required | Description |
|---|---|---|---|---|
| `ACTION` |  | positional | yes | `find`, `query`, `import`, or `refresh` |
| `--path` | `-p` | string | no | Asset path or search directory |
| `--type` | `-t` | string | no | Asset type filter (`Prefab`, `Material`, `Scene`) |
| `--pattern` |  | string | no | Search pattern |

```bash
unity-bridge asset find --type Prefab --pattern "Enemy*"
unity-bridge asset query --path Assets/Materials/
```

---

## Asset Extended Operations

### `unity-bridge asset-ext create`

Create a new asset at the specified path.

| Argument | Short | Type | Required | Description |
|---|---|---|---|---|
| `PATH` |  | positional | yes | Asset path (e.g. `Assets/Data/Config.asset`) |
| `--type` | `-t` | string | yes | Asset type (ScriptableObject, Material, etc.) |

```bash
unity-bridge asset-ext create Assets/Data/Config.asset --type ScriptableObject
```
### `unity-bridge asset-ext delete`

Delete an asset (permanently or to trash).

| Argument | Type | Default | Description |
|---|---|---|---|
| `PATH` | positional (required) |  | Asset path to delete |
| `--trash` | flag | false | Move to trash instead of permanent delete |

```bash
unity-bridge asset-ext delete Assets/Data/OldConfig.asset
unity-bridge asset-ext delete Assets/Data/OldConfig.asset --trash
```
### `unity-bridge asset-ext copy`

Copy an asset to a new path.

| Argument | Type | Required | Description |
|---|---|---|---|
| `SOURCE` | positional | yes | Source asset path |
| `DEST` | positional | yes | Destination asset path |

```bash
unity-bridge asset-ext copy Assets/Mats/Old.mat Assets/Mats/New.mat
```
### `unity-bridge asset-ext move`

Move or rename an asset.

| Argument | Type | Required | Description |
|---|---|---|---|
| `SOURCE` | positional | yes | Source asset path |
| `DEST` | positional | yes | Destination asset path |

```bash
unity-bridge asset-ext move Assets/Mats/Temp.mat Assets/Mats/Final.mat
```
### `unity-bridge asset-ext deps`

List dependencies of an asset.

| Argument | Type | Default | Description |
|---|---|---|---|
| `PATH` | positional (required) |  | Asset path to check |
| `--recursive/--no-recursive` | bool | true | Include transitive dependencies |

```bash
unity-bridge asset-ext deps Assets/Prefabs/Player.prefab
unity-bridge asset-ext deps Assets/Prefabs/Player.prefab --no-recursive
```
### `unity-bridge asset-ext guid`

Convert between asset path and GUID.

| Argument | Type | Required | Description |
|---|---|---|---|
| `INPUT` | positional | yes | Asset path or GUID to convert |

```bash
unity-bridge asset-ext guid Assets/Scripts/Player.cs
unity-bridge asset-ext guid a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```
### `unity-bridge asset-ext folder-create`

Create a folder in the Unity project.

| Argument | Type | Required | Description |
|---|---|---|---|
| `PATH` | positional | yes | Folder path to create |

```bash
unity-bridge asset-ext folder-create Assets/Data/Configs
```
### `unity-bridge asset-ext folder-list`

List subfolders of a folder.

| Argument | Type | Required | Description |
|---|---|---|---|
| `PATH` | positional | yes | Folder path to list |

```bash
unity-bridge asset-ext folder-list Assets/
```
### `unity-bridge asset-ext export`

Export assets as a .unitypackage file.

| Argument | Short | Type | Required | Description |
|---|---|---|---|---|
| `PATHS...` |  | positional | yes | Asset paths to export |
| `--output` | `-o` | string | yes | Output .unitypackage path |
| `--include-deps/--no-deps` |  | bool | default true | Include dependencies |

```bash
unity-bridge asset-ext export Assets/Prefabs/ Assets/Materials/ --output export.unitypackage
unity-bridge asset-ext export Assets/Scenes/Main.unity --output scene.unitypackage --no-deps
```
### `unity-bridge asset-ext import-package`

Import a .unitypackage file.

| Argument | Type | Default | Description |
|---|---|---|---|
| `PACKAGE` | positional (required) |  | Path to .unitypackage file |
| `--interactive` | flag | false | Show import dialog |

```bash
unity-bridge asset-ext import-package export.unitypackage
unity-bridge asset-ext import-package export.unitypackage --interactive
```

---

## Material Operations

### `unity-bridge material`

Material operations.

| Argument | Type | Required | Description |
|---|---|---|---|
| `ACTION` | positional | yes | `modify`, `create`, or `duplicate` |
| `PATH` | positional | yes | Material asset path |
| `--properties` | string | no | JSON properties to set |

```bash
unity-bridge material modify Assets/Materials/Player.mat --properties '{"_Color": {"r":1,"g":0,"b":0,"a":1}}'
```

---

## Build Operations

### `unity-bridge build`

Build the Unity project for a target platform.

| Argument | Short | Type | Default | Description |
|---|---|---|---|---|
| `--target` | `-T` | string | required | Platform target |
| `--validate-only` |  | flag | false | Validate without building |
| `--output` | `-o` | string | none | Build output path |
| `--dev` |  | flag | false | Development build |
| `--timeout` |  | int | 600 | Build timeout |

**Targets:** `StandaloneWindows64`, `StandaloneWindows`, `StandaloneLinux64`, `StandaloneOSX`, `Android`, `iOS`, `WebGL`

```bash
unity-bridge build --target StandaloneWindows64 --output builds/win64/
unity-bridge build --target Android --dev
unity-bridge build --target WebGL --validate-only
```

---

## Build Profiles

Requires Unity 6 or later.

### `unity-bridge profile list`

List all build profiles in the project. No arguments.

### `unity-bridge profile active`

Get the currently active build profile. No arguments.

### `unity-bridge profile set`

Set the active build profile.

| Argument | Type | Required | Description |
|---|---|---|---|
| `PATH` | positional | yes | Asset path to build profile |

```bash
unity-bridge profile set Assets/Settings/BuildProfiles/Android.asset
```
### `unity-bridge profile info`

Get detailed info about a build profile.

| Argument | Type | Required | Description |
|---|---|---|---|
| `PATH` | positional | yes | Asset path to build profile |

```bash
unity-bridge profile info Assets/Settings/BuildProfiles/Android.asset
```

---

## Animator Operations

### `unity-bridge animator`

Animator state and parameter operations.

| Argument | Type | Required | Description |
|---|---|---|---|
| `ACTION` | positional | yes | `get-state`, `set-state`, `get-params`, `set-param` |
| `OBJECT` | positional | yes | GameObject with Animator |
| `--state-name` | string | no | Animator state name (for set-state) |
| `--param-name` | string | no | Parameter name (for set-param) |
| `--param-value` | string | no | Parameter value (for set-param) |
| `--layer` | int | no | Animator layer index |

```bash
unity-bridge animator get-state Player
unity-bridge animator set-param Player --param-name "Speed" --param-value 5.0
unity-bridge animator get-params Player
```

---

## Player Settings

### `unity-bridge settings get`

Get player settings (all or a specific key).

| Argument | Type | Required | Description |
|---|---|---|---|
| `KEY` | positional | no | Setting key (omit for all settings) |

```bash
unity-bridge settings get
unity-bridge settings get companyName
```
### `unity-bridge settings set`

Set a player setting value.

| Argument | Type | Required | Description |
|---|---|---|---|
| `KEY` | positional | yes | Setting key to modify |
| `VALUE` | positional | yes | New value |

```bash
unity-bridge settings set companyName "MyStudio"
unity-bridge settings set productName "MyGame"
```
### `unity-bridge settings defines`

Manage scripting define symbols.

| Argument | Short | Type | Required | Description |
|---|---|---|---|---|
| `ACTION` |  | positional | yes | `list`, `add`, or `remove` |
| `--symbol` | `-s` | string | for add/remove | Define symbol name |
| `--platform` | `-p` | string | no | Target platform (default: active) |

```bash
unity-bridge settings defines list
unity-bridge settings defines add --symbol ENABLE_DEBUG
unity-bridge settings defines remove --symbol ENABLE_DEBUG
unity-bridge settings defines list --platform Android
```

---

## Package Manager

### `unity-bridge package list`

List installed packages.

| Argument | Short | Type | Default | Description |
|---|---|---|---|---|
| `--offline` |  | flag | false | Use cached data only |
| `--include-indirect` |  | flag | false | Include transitive dependencies |
| `--source` | `-s` | string | none | Filter by source (registry, git, embedded, local) |

```bash
unity-bridge package list
unity-bridge package list --source git
unity-bridge package list --include-indirect
```
### `unity-bridge package search`

Search for packages by ID/name.

| Argument | Type | Required | Description |
|---|---|---|---|
| `QUERY` | positional | yes | Package ID or name to search for |
| `--all` | flag | no | List all available packages instead of searching |

```bash
unity-bridge package search "input system"
unity-bridge package search textmeshpro
unity-bridge package search unused --all
```
### `unity-bridge package add`

Add a package by identifier.

| Argument | Type | Required | Description |
|---|---|---|---|
| `IDENTIFIER` | positional | yes | Package identifier (name@version or git URL) |

```bash
unity-bridge package add com.unity.inputsystem@1.7.0
unity-bridge package add com.unity.textmeshpro
unity-bridge package add https://github.com/user/repo.git
```
### `unity-bridge package remove`

Remove a package.

| Argument | Type | Required | Description |
|---|---|---|---|
| `NAME` | positional | yes | Package name to remove |

```bash
unity-bridge package remove com.unity.textmeshpro
```
### `unity-bridge package info`

Get detailed package information.

| Argument | Type | Required | Description |
|---|---|---|---|
| `NAME` | positional | yes | Package name to get info for |

```bash
unity-bridge package info com.unity.inputsystem
```
### `unity-bridge package embed`

Embed a package into the Packages/ folder for local editing.

| Argument | Type | Required | Description |
|---|---|---|---|
| `NAME` | positional | yes | Package name to embed |

```bash
unity-bridge package embed com.unity.inputsystem
```
### `unity-bridge package resolve`

Trigger package resolution. No arguments.


---

## Compilation Pipeline

### `unity-bridge compile assemblies`

List all project assemblies with metadata. No arguments.


```bash
unity-bridge compile assemblies
```
### `unity-bridge compile defines`

Get scripting defines for a named assembly.

| Argument | Type | Required | Description |
|---|---|---|---|
| `ASSEMBLY` | positional | yes | Assembly name (e.g. `Assembly-CSharp`) |

```bash
unity-bridge compile defines Assembly-CSharp
unity-bridge compile defines Assembly-CSharp-Editor
```
### `unity-bridge compile which`

Determine which assembly owns a script file.

| Argument | Type | Required | Description |
|---|---|---|---|
| `SCRIPT_PATH` | positional | yes | Script asset path |

```bash
unity-bridge compile which Assets/Scripts/Player.cs
```
### `unity-bridge compile optimization`

Get or set the code optimization level.

| Argument | Type | Default | Description |
|---|---|---|---|
| `--set` | string | none | Set optimization mode: `None`, `Debug`, or `Release` |

```bash
unity-bridge compile optimization
unity-bridge compile optimization --set Debug
unity-bridge compile optimization --set Release
```

---

## Undo System

### `unity-bridge undo perform`

Undo the last operation. No arguments.

### `unity-bridge undo redo`

Redo the last undone operation. No arguments.

### `unity-bridge undo history`

List recent undo operations (bridge-tracked only).

| Argument | Short | Type | Default | Description |
|---|---|---|---|---|
| `--limit` | `-n` | int | 20 | Max history entries to return |

```bash
unity-bridge undo history
unity-bridge undo history --limit 5
```
### `unity-bridge undo clear`

Clear all undo history.


**WARNING:** Clears ALL undo history, including non-bridge operations. This cannot be undone.
### `unity-bridge undo group-name`

Get the current undo group name. No arguments.

### `unity-bridge undo collapse`

Collapse undo operations from a group index into one undo step.

| Argument | Short | Type | Default | Description |
|---|---|---|---|---|
| `GROUP_INDEX` |  | positional (int) | required | Undo group index to collapse from |
| `--name` | `-n` | string | none | Optional name for the collapsed undo group |

```bash
unity-bridge undo collapse 5
unity-bridge undo collapse 5 --name "Level setup"
```

---

## Shader Inspection

All shader operations are read-only and safe for parallel batch execution.

### `unity-bridge shader list`

List all available shaders.

| Argument | Type | Default | Description |
|---|---|---|---|
| `--errors-only` | flag | false | Only show shaders with compilation errors |

```bash
unity-bridge shader list
unity-bridge shader list --errors-only
```
### `unity-bridge shader info`

Get detailed info about a specific shader.

| Argument | Type | Required | Description |
|---|---|---|---|
| `NAME` | positional | yes | Full shader name |

```bash
unity-bridge shader info "Universal Render Pipeline/Lit"
unity-bridge shader info "Custom/MyShader"
```
### `unity-bridge shader errors`

Get compilation errors and warnings for a shader.

| Argument | Type | Required | Description |
|---|---|---|---|
| `NAME` | positional | yes | Full shader name |

```bash
unity-bridge shader errors "Custom/MyShader"
```
### `unity-bridge shader properties`

Enumerate all properties of a shader.

| Argument | Type | Required | Description |
|---|---|---|---|
| `NAME` | positional | yes | Full shader name |

```bash
unity-bridge shader properties "Universal Render Pipeline/Lit"
```
### `unity-bridge shader find-by-property`

Find all shaders that declare a given property.

| Argument | Type | Required | Description |
|---|---|---|---|
| `PROPERTY_NAME` | positional | yes | Shader property name (e.g. `_MainTex`) |

```bash
unity-bridge shader find-by-property "_MainTex"
unity-bridge shader find-by-property "_BumpMap"
```
### `unity-bridge shader keywords`

List shader keywords and variants.

| Argument | Type | Default | Description |
|---|---|---|---|
| `NAME` | positional (required) |  | Full shader name |
| `--filter` | string | none | `global` or `local` to filter keyword type |

```bash
unity-bridge shader keywords "Universal Render Pipeline/Lit"
unity-bridge shader keywords "Custom/MyShader" --filter global
```

---

## Lightmap Operations

### `unity-bridge lightmap bake`

Start a lightmap bake.

| Argument | Type | Default | Description |
|---|---|---|---|
| `--run-async/--no-run-async` | bool | true | Return immediately (async) or wait for completion (sync) |
| `--timeout` | float | 30 async / 3600 sync | Timeout in seconds |

```bash
unity-bridge lightmap bake
unity-bridge lightmap bake --no-run-async
unity-bridge lightmap bake --no-run-async --timeout 7200
```
### `unity-bridge lightmap cancel`

Cancel an in-progress lightmap bake. No arguments.

### `unity-bridge lightmap clear`

Clear all baked lightmap data from disk. No arguments.

### `unity-bridge lightmap status`

Get current lightmap bake status and progress. No arguments.

### `unity-bridge lightmap settings`

Get current lightmap settings (read-only). No arguments.


---

## Import Settings

### `unity-bridge import-settings get`

Get current import settings for an asset.

| Argument | Type | Required | Description |
|---|---|---|---|
| `PATH` | positional | yes | Asset path (e.g. `Assets/Textures/Albedo.png`) |

```bash
unity-bridge import-settings get Assets/Textures/Albedo.png
```
### `unity-bridge import-settings set`

Modify import settings and reimport.

| Argument | Short | Type | Required | Description |
|---|---|---|---|---|
| `PATH` |  | positional | yes | Asset path |
| `--setting` | `-s` | repeatable | yes | Setting as `key:value` (repeatable) |

```bash
unity-bridge import-settings set Assets/Textures/Albedo.png -s maxTextureSize:2048
unity-bridge import-settings set Assets/Textures/Albedo.png -s maxTextureSize:2048 -s filterMode:Bilinear
```
### `unity-bridge import-settings reimport`

Reimport an asset with current settings.

| Argument | Type | Default | Description |
|---|---|---|---|
| `PATH` | positional (required) |  | Asset path |
| `--force` | flag | false | Force reimport even if unchanged |

```bash
unity-bridge import-settings reimport Assets/Textures/Albedo.png
unity-bridge import-settings reimport Assets/Textures/Albedo.png --force
```
### `unity-bridge import-settings bulk-set`

Bulk-modify import settings for all matching assets in a folder.

| Argument | Short | Type | Required | Description |
|---|---|---|---|---|
| `FOLDER` |  | positional | yes | Folder path |
| `--setting` | `-s` | repeatable | yes | Setting as `key:value` (repeatable) |
| `--filter` |  | string | no | Glob filter (e.g. `*.png`) |

```bash
unity-bridge import-settings bulk-set Assets/Textures/ -s maxTextureSize:1024 --filter "*.png"
```
### `unity-bridge import-settings template-save`

Save current import settings of an asset as a named template.

| Argument | Type | Required | Description |
|---|---|---|---|
| `NAME` | positional | yes | Template name (alphanumeric, hyphens, underscores, max 64) |
| `PATH` | positional | yes | Source asset path |

```bash
unity-bridge import-settings template-save mobile-texture Assets/Textures/Reference.png
```
### `unity-bridge import-settings template-apply`

Apply a saved template to an asset.

| Argument | Type | Required | Description |
|---|---|---|---|
| `NAME` | positional | yes | Template name |
| `PATH` | positional | yes | Target asset path |

```bash
unity-bridge import-settings template-apply mobile-texture Assets/Textures/NewAsset.png
```

---

## Workflow Commands

### `unity-bridge tdd`

Compound workflow: clear console -> compile -> run tests -> read console (on failure).

| Argument | Short | Type | Default | Description |
|---|---|---|---|---|
| `--platform` | `-P` | string | `EditMode` | Test platform |
| `--filter` | `-f` | string | none | Test filter |
| `--strict` |  | flag | false | Treat warnings as failures |

```bash
unity-bridge tdd --filter CombatTests
unity-bridge tdd --platform PlayMode --strict
```
### `unity-bridge test watch`

Auto-rerun tests on .cs file changes. Requires `pip install unity-bridge[watch]`.

| Argument | Short | Type | Default | Description |
|---|---|---|---|---|
| `--platform` | `-P` | string | `EditMode` | Test platform |
| `--filter` | `-f` | string | none | Test filter |
| `--path` |  | path | `Assets/` | Directory to watch |
### `unity-bridge snapshot save`

Capture scene hierarchy to a JSON file.

| Argument | Short | Type | Default | Description |
|---|---|---|---|---|
| `FILE` |  | positional | required | Output file path |
| `--depth` | `-d` | int | 5 | Max hierarchy depth |
| `--max-objects` |  | int | 1000 | Truncation limit |
| `--root` | `-r` | string | none | Start from subtree |
### `unity-bridge snapshot diff`

Compare two snapshots. Returns added/removed/modified objects.

| Argument | Type | Required |
|---|---|---|
| `FILE1` | positional | yes |
| `FILE2` | positional | yes |

---

## Scripting

### `unity-bridge script`

Execute arbitrary C# expressions in Unity Editor.

| Argument | Short | Type | Required | Description |
|---|---|---|---|---|
| `EXPRESSION` |  | positional | yes* | C# expression to evaluate |
| `--file` | `-f` | path | no | Read expression from file |
| `--timeout` |  | int | no (default 30) | Execution timeout |

*Required unless `--file` is provided.

```bash
unity-bridge script "EditorApplication.isPlaying"
unity-bridge script "Selection.activeGameObject.name"
unity-bridge script --file setup.cs
```

---

## Diagnostics & Lifecycle

### `unity-bridge status`

Quick alive/dead check. Returns within 100ms. Exit code 0 if healthy, 2 if not.

### `unity-bridge doctor`

Full diagnostic suite (9 checks): project structure, bridge installed, version compat, heartbeat, directory permissions, orphaned files, dependencies, Unity process, version.

### `unity-bridge version`

Show CLI version, C# bridge version, Python version, platform.

### `unity-bridge install`

Install or update the C# bridge files into the Unity project.

| Argument | Type | Description |
|---|---|---|
| `--project` | path | Explicit project path |
| `--check` | flag | Report status without changes |
| `--force` | flag | Force reinstall |
### `unity-bridge init`

Create the `.claude/unity/` directory structure (commands/, responses/).

### `unity-bridge clean`

Remove orphaned command/response files.

| Argument | Type | Default | Description |
|---|---|---|---|
| `--age` | int | 5 | Minutes threshold |
| `--all` | flag | false | Remove all (alias for --age 0) |
| `--dry-run` | flag | false | Show what would be deleted |
### `unity-bridge profiler`

Capture Unity profiler metrics.

| Argument | Type | Default | Description |
|---|---|---|---|
| `--memory` | flag | false | Include memory statistics |
| `--rendering` | flag | false | Include rendering statistics |
| `--cpu` | flag | false | Include CPU statistics |

---

## Batch & Serve

### `unity-bridge batch`

Execute multiple commands from a JSON file.

| Argument | Type | Default | Description |
|---|---|---|---|
| `FILE` | positional (required) |  | JSON file with commands array |
| `--stop-on-error/--no-stop-on-error` | bool | true | Halt on first failure |
| `--parallel` | flag | false | Run read-only commands concurrently |

**File format:**
```json
{
  "commands": [
    {"type": "clear-console"},
    {"type": "compile", "parameters": {"waitForCompletion": true}},
    {"type": "run-tests", "parameters": {"testPlatform": "EditMode"}}
  ]
}
```
### `unity-bridge serve`

Start the MCP server for Claude Code integration. No arguments.


---

## Bridge Command Types

For batch files and advanced use. Maps bridge command types to CLI equivalents.

| Command Type | Default Timeout | CLI Equivalent |
|---|---|---|
| `run-tests` | 300s | `test run` |
| `compile` | 120s | `test compile` |
| `list-tests` | 30s | `test list` |
| `query-hierarchy` | 10s | `hierarchy` |
| `get-component-data` | 10s | `component get` |
| `set-component-data` | 30s | `component set` |
| `add-component` | 30s | `component add` |
| `gameobject-utility` | 15s | `hierarchy missing-scripts/static-flags/set-layer/set-tag` |
| `validate-prefab` | 30s | `prefab validate` |
| `prefab-operation` | 30s | `prefab instantiate/destroy` |
| `prefab-override` | 30s | `prefab overrides/status/find-instances/unpack` |
| `scene-operation` | 30s | `scene load/save/create` |
| `scene-setup-operation` | 30s | `scene-ext setup/play-start/cross-refs/list-loaded/preview` |
| `playmode-control` | 10s | `playmode` |
| `read-console` | 10s | `console read` |
| `clear-console` | 5s | `console clear` |
| `capture-screenshot` | 30s | `screenshot` |
| `profiler-sample` | 30s | `profiler` |
| `material-operation` | 30s | `material` |
| `asset-operation` | 60s | `asset` |
| `asset-extended-operation` | 60s | `asset-ext` |
| `build-operation` | 600s | `build` |
| `build-profile-operation` | 30s | `profile` |
| `animator-operation` | 30s | `animator` |
| `player-settings-operation` | 15s | `settings` |
| `package-operation` | 60s | `package` |
| `compilation-pipeline` | 15s | `compile` |
| `undo-operation` | 5s | `undo` |
| `shader-inspection` | 15s | `shader` |
| `lightmap-operation` | 30s | `lightmap` |
| `import-settings-operation` | 60s | `import-settings` |
| `get-selection` | 5s | `selection` |
| `refresh-assets` | 15s | `refresh` |
| `focus-object` | 5s | `focus` |
| `execute-menu-item` | 30s | `menu` |
| `execute-script` | 30s | `script` |
| `health-check` | 5s | `status` |

**Parallel-safe commands** (can run concurrently in batch `--parallel` mode):
`query-hierarchy`, `get-component-data`, `get-selection`, `read-console`, `validate-prefab`, `health-check`, `list-tests`, `shader-inspection`
