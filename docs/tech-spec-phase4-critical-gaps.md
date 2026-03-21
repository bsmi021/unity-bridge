# Tech Spec: Phase 4 - Critical Gaps & Bugfixes

**Status:** Draft
**Author:** Claude Code
**Last Updated:** 2026-03-21
**Version:** 0.1.0

---

## 1. Overview

### Problem Statement

After three phases of expansion (Core Platform APIs, Developer Workflow APIs, Specialized APIs), the unity-bridge covers 39 MCP tools across 29 CLI command groups. However, several critical editing primitives are missing that prevent complete automation workflows:

1. **No selection control.** `get-selection` is read-only. There is no way to programmatically select GameObjects, which is a prerequisite for many Editor workflows (Inspector operations, multi-object editing, context menus).
2. **No transform manipulation.** Position, rotation, scale, reparenting, and sibling reordering all require manual Inspector interaction. This is arguably the most fundamental scene editing operation.
3. **No SerializedProperty access.** `set-component-data` uses `FieldInfo` reflection with `BindingFlags.Public | BindingFlags.Instance`, which misses `[SerializeField] private` fields -- the *recommended* Unity pattern. The proper API is `SerializedObject`/`SerializedProperty`, which also provides automatic undo and handles all property types.
4. **No EditorPrefs/SessionState access.** Editor preferences and session state values cannot be read or written, blocking tool configuration and workflow state persistence.
5. **No Build Settings scene list control.** Adding, removing, reordering, and enabling/disabling scenes in the Build Settings list is impossible without the Editor UI.
6. **No GameObject duplication.** Duplicating objects requires manual Ctrl+D or menu interaction.

Additionally, three correctness bugs exist in shipped handlers:

- `GameObjectOperationCommandHandler.CreateGameObject` uses `new GameObject()` instead of `ObjectFactory.CreateGameObject()`, missing Preset application and undo registration.
- `SetComponentDataCommandHandler` only accesses public fields via reflection, silently skipping `[SerializeField] private` fields.
- `GameObjectOperationCommandHandler.DeleteGameObject` uses `Object.DestroyImmediate()` instead of `Undo.DestroyObjectImmediate()`, making deletions non-undoable.

### Goals

- **G1:** Add 6 new command areas (selection-set, transform, serialized-property, editor-prefs, build-scenes, duplicate) with full C#, Python CLI, and MCP implementations.
- **G2:** Fix 3 correctness bugs in existing handlers (ObjectFactory, SerializedProperty fallback, undo-aware destroy).
- **G3:** Add 4 Tier 2 quick-win command areas (physics-config, quality-config, editor-config, tags-layers) if implementation stays simple.
- **G4:** Maintain the dual-interface pattern: all features in both CLI and MCP with zero logic duplication.
- **G5:** Keep all files under 500 LOC, all functions under 50 LOC.
- **G6:** Add 10 new MCP tools (6 critical + 4 Tier 2), bringing total from 39 to 49.
- **G7:** Unit tests for all new Python command modules.

### Non-Goals

- Modifying the file-based communication protocol.
- Runtime (play mode) transform manipulation -- all operations are Editor-only.
- Custom property drawers or inspector extensions.
- Full ProjectSettings serialization (only EditorPrefs, SessionState, and specific settings APIs).
- Physics simulation or raycasting.
- Quality level creation/deletion (only reading and switching).

---

## 2. Command Reference

### Command Tree

```
unity-bridge
│
├── select <path> [<path>...]                    # 4A.1: Set editor selection
│
├── transform                                     # 4A.2: Transform manipulation
│   ├── get <object-path>                        # Get current transform
│   ├── set <object-path> [options]              # Set position/rotation/scale
│   ├── parent <object-path> <new-parent>        # Reparent with undo
│   └── sibling <object-path> --index N          # Set sibling index
│
├── property                                      # 4A.3: SerializedProperty access
│   ├── get <object-path> <component> <prop>     # Read property value
│   ├── set <object-path> <component> <prop> <val> # Write property value
│   └── list <object-path> <component>           # List all serialized properties
│
├── prefs                                         # 4A.4: EditorPrefs
│   ├── get <key> [--type TYPE]                  # Read preference value
│   ├── set <key> <value> --type TYPE            # Write preference value
│   ├── delete <key>                             # Delete preference key
│   └── has <key>                                # Check if key exists
│
├── session                                       # 4A.4: SessionState (same handler)
│   ├── get <key> [--type TYPE]                  # Read session value
│   ├── set <key> <value> --type TYPE            # Write session value
│   └── delete <key>                             # Delete session key
│
├── build-scenes                                  # 4A.5: Build Settings scenes
│   ├── list                                     # List scenes in build settings
│   ├── add <scene-path> [--index N]             # Add scene
│   ├── remove <scene-path>                      # Remove scene
│   ├── enable <scene-path>                      # Enable scene
│   ├── disable <scene-path>                     # Disable scene
│   └── reorder --from N --to N                  # Move scene position
│
├── hierarchy
│   └── duplicate <object-path> [--count N]      # 4A.6: Duplicate GameObject
│
├── physics                                       # 4C.7: Physics configuration
│   ├── get                                      # Get physics settings
│   ├── set [options]                            # Set physics settings
│   ├── collision-matrix get                     # Get layer collision matrix
│   └── collision-matrix set <L1> <L2> [options] # Set layer collision
│
├── quality                                       # 4C.8: Quality settings
│   ├── get [--level N]                          # Get quality settings
│   ├── set-level <N>                            # Set active quality level
│   └── list                                     # List all quality levels
│
├── editor-config                                 # 4C.9: Editor settings
│   ├── get                                      # Get all editor settings
│   └── set <key> <value>                        # Set editor setting
│
├── tags                                          # 4C.10: Tags
│   ├── list                                     # List all tags
│   └── add <tag>                                # Add new tag
│
├── layers                                        # 4C.10: Layers
│   ├── list                                     # List all layers
│   └── add <name> --index N                     # Add layer at index
│
└── sorting-layers                                # 4C.10: Sorting layers
    ├── list                                     # List all sorting layers
    └── add <name>                               # Add sorting layer
```

### Detailed Command Signatures

#### 2.1 Selection (4A.1)

| Command | Arguments | Options | Description |
|---------|-----------|---------|-------------|
| `select` | `paths...` (one or more) | `--asset` | Set selection to GameObjects by hierarchy path. `--asset` selects asset objects by asset path instead of scene objects. |

#### 2.2 Transform (4A.2)

| Command | Arguments | Options | Description |
|---------|-----------|---------|-------------|
| `transform get` | `object-path` | -- | Get world position, rotation (euler), local position, local rotation, local scale. |
| `transform set` | `object-path` | `--position X,Y,Z`, `--rotation X,Y,Z`, `--scale X,Y,Z`, `--local` | Set transform properties. `--local` uses local space for position/rotation. |
| `transform parent` | `object-path`, `new-parent` | `--world-position-stays` (default true) | Reparent a GameObject under a new parent. Pass empty string `""` for new-parent to unparent to root. |
| `transform sibling` | `object-path` | `--index N` | Set sibling index in hierarchy. |

#### 2.3 Serialized Property (4A.3)

| Command | Arguments | Options | Description |
|---------|-----------|---------|-------------|
| `property get` | `object-path`, `component-type`, `property-path` | -- | Read a serialized property value. Property path supports nested paths (e.g. `m_Speed`, `m_Data.m_Items`). |
| `property set` | `object-path`, `component-type`, `property-path`, `value` | -- | Write a serialized property value as JSON. Automatically calls `ApplyModifiedProperties()`. |
| `property list` | `object-path`, `component-type` | `--depth N` (default 1) | List all visible serialized properties with name, type, and current value. |

#### 2.4 EditorPrefs / SessionState (4A.4)

| Command | Arguments | Options | Description |
|---------|-----------|---------|-------------|
| `prefs get` | `key` | `--type string\|int\|float\|bool` (default `string`) | Read an EditorPrefs value. |
| `prefs set` | `key`, `value` | `--type string\|int\|float\|bool` (default `string`) | Write an EditorPrefs value. |
| `prefs delete` | `key` | -- | Delete an EditorPrefs key. |
| `prefs has` | `key` | -- | Check if an EditorPrefs key exists. |
| `session get` | `key` | `--type string\|int\|float\|bool` (default `string`) | Read a SessionState value. |
| `session set` | `key`, `value` | `--type string\|int\|float\|bool` (default `string`) | Write a SessionState value. |
| `session delete` | `key` | -- | Delete a SessionState key. |

#### 2.5 Build Settings Scenes (4A.5)

| Command | Arguments | Options | Description |
|---------|-----------|---------|-------------|
| `build-scenes list` | -- | -- | List all scenes in Build Settings with path, enabled, and index. |
| `build-scenes add` | `scene-path` | `--index N` (default: append) | Add scene to Build Settings. |
| `build-scenes remove` | `scene-path` | -- | Remove scene from Build Settings. |
| `build-scenes enable` | `scene-path` | -- | Enable scene in Build Settings. |
| `build-scenes disable` | `scene-path` | -- | Disable scene in Build Settings. |
| `build-scenes reorder` | -- | `--from N`, `--to N` | Move scene from one index to another. |

#### 2.6 Duplicate (4A.6)

| Command | Arguments | Options | Description |
|---------|-----------|---------|-------------|
| `hierarchy duplicate` | `object-path` | `--count N` (default 1) | Duplicate a GameObject N times. Each duplicate is registered with Undo. |

#### 2.7 Physics Configuration (4C.7)

| Command | Arguments | Options | Description |
|---------|-----------|---------|-------------|
| `physics get` | -- | -- | Get all physics settings (gravity, solver iterations, etc.). |
| `physics set` | -- | `--gravity X,Y,Z`, `--solver-iterations N`, `--bounce-threshold F` | Set physics settings. |
| `physics collision-matrix get` | -- | -- | Get full 32x32 layer collision matrix. |
| `physics collision-matrix set` | `layer1`, `layer2` | `--ignore` / `--collide` | Set collision between two layers. |

#### 2.8 Quality Settings (4C.8)

| Command | Arguments | Options | Description |
|---------|-----------|---------|-------------|
| `quality get` | -- | `--level N` | Get quality settings for a specific level (default: current). |
| `quality set-level` | `level` | -- | Switch to quality level by index. |
| `quality list` | -- | -- | List all quality levels with names and active indicator. |

#### 2.9 Editor Settings (4C.9)

| Command | Arguments | Options | Description |
|---------|-----------|---------|-------------|
| `editor-config get` | -- | -- | Get all configurable editor settings. |
| `editor-config set` | `key`, `value` | -- | Set an editor setting by key. |

#### 2.10 Tags and Layers (4C.10)

| Command | Arguments | Options | Description |
|---------|-----------|---------|-------------|
| `tags list` | -- | -- | List all tags (built-in + custom). |
| `tags add` | `tag` | -- | Add a new custom tag. |
| `layers list` | -- | -- | List all layers with indices. |
| `layers add` | `name` | `--index N` | Add a layer at specified index (must be in user range 6-31). |
| `sorting-layers list` | -- | -- | List all sorting layers with IDs. |
| `sorting-layers add` | `name` | -- | Add a new sorting layer. |

---

## 3. Architecture

### 3.1 C# Command Handlers

#### New Handlers (Phase 4A)

| Handler Class | Command Type | File(s) |
|---------------|-------------|---------|
| `SetSelectionCommandHandler` | `set-selection` | `SetSelectionCommandHandler.cs` |
| `TransformOperationCommandHandler` | `transform-operation` | `TransformOperationCommandHandler.cs` |
| `SerializedPropertyCommandHandler` | `serialized-property` | `SerializedPropertyCommandHandler.cs`, `SerializedPropertyHelpers.cs` |
| `EditorPrefsCommandHandler` | `editor-prefs-operation` | `EditorPrefsCommandHandler.cs` |
| `BuildScenesCommandHandler` | `build-scenes-operation` | `BuildScenesCommandHandler.cs` |

The `duplicate` operation is added to the existing `GameObjectOperationCommandHandler` as a new case in its operation dispatch.

#### New Handlers (Phase 4C - Tier 2)

| Handler Class | Command Type | File(s) |
|---------------|-------------|---------|
| `PhysicsConfigCommandHandler` | `physics-config` | `PhysicsConfigCommandHandler.cs` |
| `QualityConfigCommandHandler` | `quality-config` | `QualityConfigCommandHandler.cs` |
| `EditorConfigCommandHandler` | `editor-config` | `EditorConfigCommandHandler.cs` |
| `TagsLayersCommandHandler` | `tags-layers-operation` | `TagsLayersCommandHandler.cs` |

#### Modified Handlers (Bugfixes 4B)

| File | Change |
|------|--------|
| `GameObjectOperationCommandHandler.cs` | Replace `new GameObject(name)` with `ObjectFactory.CreateGameObject(name)` in CreateGameObject; replace `Object.DestroyImmediate(go)` with `Undo.DestroyObjectImmediate(go)` in DeleteGameObject |
| `SetComponentDataCommandHandler.cs` | Add SerializedProperty as primary setter, fall back to reflection for non-serialized public fields |

#### New Model Files

| File | Models |
|------|--------|
| `BridgeModelsPhase4.cs` | `SetSelectionParams`, `SetSelectionResult`, `TransformOperationParams`, `TransformOperationResult`, `TransformData`, `SerializedPropertyParams`, `SerializedPropertyResult`, `PropertyInfo`, `EditorPrefsParams`, `EditorPrefsResult`, `BuildScenesParams`, `BuildScenesResult`, `BuildSceneInfo` |
| `BridgeModelsPhase4Tier2.cs` | `PhysicsConfigParams`, `PhysicsConfigResult`, `CollisionMatrixEntry`, `QualityConfigParams`, `QualityConfigResult`, `QualityLevelInfo`, `EditorConfigParams`, `EditorConfigResult`, `TagsLayersParams`, `TagsLayersResult`, `LayerInfo`, `SortingLayerInfo` |

### 3.2 Python Command Modules

| Module | Typer App | Core Functions |
|--------|-----------|----------------|
| `commands/select.py` | -- (single command) | `set_selection` |
| `commands/transform.py` | `transform_app` | `transform_get`, `transform_set`, `transform_parent`, `transform_sibling` |
| `commands/serialized_property.py` | `property_app` | `property_get`, `property_set`, `property_list` |
| `commands/editor_prefs.py` | `prefs_app`, `session_app` | `prefs_get`, `prefs_set`, `prefs_delete`, `prefs_has`, `session_get`, `session_set`, `session_delete` |
| `commands/build_scenes.py` | `build_scenes_app` | `build_scenes_list`, `build_scenes_add`, `build_scenes_remove`, `build_scenes_enable`, `build_scenes_disable`, `build_scenes_reorder` |
| `commands/hierarchy.py` (extended) | `hierarchy_app` (new subcommand) | `duplicate_gameobject` |
| `commands/physics_config.py` | `physics_app` | `physics_get`, `physics_set`, `collision_matrix_get`, `collision_matrix_set` |
| `commands/quality_config.py` | `quality_app` | `quality_get`, `quality_set_level`, `quality_list` |
| `commands/editor_config.py` | `editor_config_app` | `editor_config_get`, `editor_config_set` |
| `commands/tags_layers.py` | `tags_app`, `layers_app`, `sorting_layers_app` | `tags_list`, `tags_add`, `layers_list`, `layers_add`, `sorting_layers_list`, `sorting_layers_add` |

### 3.3 MCP Tool Mappings

Phase 4 adds 10 new MCP tools, following the consolidation pattern (one tool per command type with operation dispatch):

| MCP Tool Name | Bridge Command Type | Operations |
|---------------|-------------------|------------|
| `unity_set_selection` | `set-selection` | -- (single operation) |
| `unity_transform_operation` | `transform-operation` | `get`, `set`, `parent`, `sibling` |
| `unity_serialized_property` | `serialized-property` | `get`, `set`, `list` |
| `unity_editor_prefs` | `editor-prefs-operation` | `prefs-get`, `prefs-set`, `prefs-delete`, `prefs-has`, `session-get`, `session-set`, `session-delete` |
| `unity_build_scenes` | `build-scenes-operation` | `list`, `add`, `remove`, `enable`, `disable`, `reorder` |
| `unity_physics_config` | `physics-config` | `get`, `set`, `collision-matrix-get`, `collision-matrix-set` |
| `unity_quality_config` | `quality-config` | `get`, `set-level`, `list` |
| `unity_editor_config` | `editor-config` | `get`, `set` |
| `unity_tags_layers` | `tags-layers-operation` | `tags-list`, `tags-add`, `layers-list`, `layers-add`, `sorting-layers-list`, `sorting-layers-add` |

The `duplicate` operation is served by the existing `unity_gameobject_operation` MCP tool (command type `gameobject-operation`) with a new `"operation": "duplicate"` value.

Schemas defined in `schemas_phase4.py` to keep existing schema files under 500 LOC.

Total MCP tools after Phase 4: **48** (39 existing + 9 new tools; duplicate uses existing tool).

### 3.4 Protocol Messages

All messages follow the established envelope format. Examples show `parametersJson` content and response `dataJson` content.

#### Envelope Format (reminder)

**Command file** (`<project>/.claude/unity/commands/{uuid}-{command-type}.json`):
```json
{
  "commandId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "commandType": "set-selection",
  "timestamp": "2026-03-21T10:00:00.000Z",
  "parametersJson": "{\"paths\":[\"Player\",\"Enemy\"]}"
}
```

**Response file** (`<project>/.claude/unity/responses/{uuid}-{command-type}.json`):
```json
{
  "commandId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "commandType": "set-selection",
  "status": "success",
  "timestamp": "2026-03-21T10:00:00.050Z",
  "dataJson": "{...}",
  "errorMessage": null
}
```

#### 3.4.1 Set Selection Protocol (4A.1)

**`set-selection`**

Parameters:
```json
{
  "paths": ["Player", "Environment/Ground"],
  "asset": false
}
```

Response `dataJson`:
```json
{
  "selectedCount": 2,
  "selectedPaths": ["Player", "Environment/Ground"],
  "activeObject": "Player",
  "success": true,
  "message": "Selected 2 objects"
}
```

**`set-selection` (asset mode)**

Parameters:
```json
{
  "paths": ["Assets/Prefabs/Player.prefab"],
  "asset": true
}
```

Response `dataJson`:
```json
{
  "selectedCount": 1,
  "selectedPaths": ["Assets/Prefabs/Player.prefab"],
  "activeObject": "Assets/Prefabs/Player.prefab",
  "success": true,
  "message": "Selected 1 asset(s)"
}
```

#### 3.4.2 Transform Operation Protocol (4A.2)

**`transform-operation` / `get`**

Parameters:
```json
{
  "operation": "get",
  "gameObjectPath": "Player"
}
```

Response `dataJson`:
```json
{
  "operation": "get",
  "gameObjectPath": "Player",
  "transform": {
    "position": {"x": 0.0, "y": 1.0, "z": -5.0},
    "rotation": {"x": 0.0, "y": 180.0, "z": 0.0},
    "localPosition": {"x": 0.0, "y": 1.0, "z": -5.0},
    "localRotation": {"x": 0.0, "y": 180.0, "z": 0.0},
    "localScale": {"x": 1.0, "y": 1.0, "z": 1.0},
    "lossyScale": {"x": 1.0, "y": 1.0, "z": 1.0}
  },
  "parentPath": "",
  "siblingIndex": 0,
  "childCount": 3,
  "success": true,
  "message": "Transform retrieved"
}
```

**`transform-operation` / `set`**

Parameters:
```json
{
  "operation": "set",
  "gameObjectPath": "Player",
  "position": {"x": 10.0, "y": 0.0, "z": 5.0},
  "rotation": {"x": 0.0, "y": 90.0, "z": 0.0},
  "scale": {"x": 2.0, "y": 2.0, "z": 2.0},
  "local": false
}
```

Response `dataJson`:
```json
{
  "operation": "set",
  "gameObjectPath": "Player",
  "transform": {
    "position": {"x": 10.0, "y": 0.0, "z": 5.0},
    "rotation": {"x": 0.0, "y": 90.0, "z": 0.0},
    "localPosition": {"x": 10.0, "y": 0.0, "z": 5.0},
    "localRotation": {"x": 0.0, "y": 90.0, "z": 0.0},
    "localScale": {"x": 2.0, "y": 2.0, "z": 2.0},
    "lossyScale": {"x": 2.0, "y": 2.0, "z": 2.0}
  },
  "success": true,
  "message": "Transform updated"
}
```

**`transform-operation` / `parent`**

Parameters:
```json
{
  "operation": "parent",
  "gameObjectPath": "Weapon",
  "newParentPath": "Player/RightHand",
  "worldPositionStays": true
}
```

Response `dataJson`:
```json
{
  "operation": "parent",
  "gameObjectPath": "Player/RightHand/Weapon",
  "previousParentPath": "",
  "newParentPath": "Player/RightHand",
  "success": true,
  "message": "Reparented 'Weapon' under 'Player/RightHand'"
}
```

**`transform-operation` / `sibling`**

Parameters:
```json
{
  "operation": "sibling",
  "gameObjectPath": "Player/Weapon",
  "siblingIndex": 0
}
```

Response `dataJson`:
```json
{
  "operation": "sibling",
  "gameObjectPath": "Player/Weapon",
  "previousIndex": 2,
  "newIndex": 0,
  "success": true,
  "message": "Sibling index set to 0"
}
```

#### 3.4.3 Serialized Property Protocol (4A.3)

**`serialized-property` / `get`**

Parameters:
```json
{
  "operation": "get",
  "gameObjectPath": "Player",
  "componentType": "CharacterStats",
  "propertyPath": "m_MaxHealth"
}
```

Response `dataJson`:
```json
{
  "operation": "get",
  "gameObjectPath": "Player",
  "componentType": "CharacterStats",
  "propertyPath": "m_MaxHealth",
  "propertyType": "Integer",
  "value": "100",
  "success": true,
  "message": "Property value retrieved"
}
```

**`serialized-property` / `set`**

Parameters:
```json
{
  "operation": "set",
  "gameObjectPath": "Player",
  "componentType": "CharacterStats",
  "propertyPath": "m_MaxHealth",
  "valueJson": "150"
}
```

Response `dataJson`:
```json
{
  "operation": "set",
  "gameObjectPath": "Player",
  "componentType": "CharacterStats",
  "propertyPath": "m_MaxHealth",
  "previousValue": "100",
  "newValue": "150",
  "success": true,
  "message": "Property set to 150"
}
```

**`serialized-property` / `list`**

Parameters:
```json
{
  "operation": "list",
  "gameObjectPath": "Player",
  "componentType": "CharacterStats",
  "depth": 1
}
```

Response `dataJson`:
```json
{
  "operation": "list",
  "gameObjectPath": "Player",
  "componentType": "CharacterStats",
  "properties": [
    {
      "path": "m_MaxHealth",
      "displayName": "Max Health",
      "type": "Integer",
      "value": "100",
      "isExpanded": false,
      "hasChildren": false,
      "depth": 0,
      "editable": true
    },
    {
      "path": "m_CurrentHealth",
      "displayName": "Current Health",
      "type": "Integer",
      "value": "100",
      "isExpanded": false,
      "hasChildren": false,
      "depth": 0,
      "editable": true
    },
    {
      "path": "m_Speed",
      "displayName": "Speed",
      "type": "Float",
      "value": "5.5",
      "isExpanded": false,
      "hasChildren": false,
      "depth": 0,
      "editable": true
    }
  ],
  "propertyCount": 3,
  "success": true,
  "message": "Found 3 properties"
}
```

#### 3.4.4 EditorPrefs / SessionState Protocol (4A.4)

**`editor-prefs-operation` / `prefs-get`**

Parameters:
```json
{
  "operation": "prefs-get",
  "key": "MyTool.LastPath",
  "valueType": "string"
}
```

Response `dataJson`:
```json
{
  "operation": "prefs-get",
  "store": "EditorPrefs",
  "key": "MyTool.LastPath",
  "valueType": "string",
  "value": "Assets/Scenes/",
  "exists": true,
  "success": true,
  "message": "Value retrieved"
}
```

**`editor-prefs-operation` / `prefs-set`**

Parameters:
```json
{
  "operation": "prefs-set",
  "key": "MyTool.MaxItems",
  "valueType": "int",
  "value": "50"
}
```

Response `dataJson`:
```json
{
  "operation": "prefs-set",
  "store": "EditorPrefs",
  "key": "MyTool.MaxItems",
  "valueType": "int",
  "value": "50",
  "success": true,
  "message": "Value set"
}
```

**`editor-prefs-operation` / `prefs-delete`**

Parameters:
```json
{
  "operation": "prefs-delete",
  "key": "MyTool.OldKey"
}
```

Response `dataJson`:
```json
{
  "operation": "prefs-delete",
  "store": "EditorPrefs",
  "key": "MyTool.OldKey",
  "success": true,
  "message": "Key deleted"
}
```

**`editor-prefs-operation` / `prefs-has`**

Parameters:
```json
{
  "operation": "prefs-has",
  "key": "MyTool.Initialized"
}
```

Response `dataJson`:
```json
{
  "operation": "prefs-has",
  "store": "EditorPrefs",
  "key": "MyTool.Initialized",
  "exists": true,
  "success": true,
  "message": "Key exists"
}
```

**`editor-prefs-operation` / `session-get`**

Parameters:
```json
{
  "operation": "session-get",
  "key": "MyTool.TempState",
  "valueType": "bool"
}
```

Response `dataJson`:
```json
{
  "operation": "session-get",
  "store": "SessionState",
  "key": "MyTool.TempState",
  "valueType": "bool",
  "value": "true",
  "exists": true,
  "success": true,
  "message": "Value retrieved"
}
```

SessionState `set` and `delete` follow the same pattern as EditorPrefs, substituting `"store": "SessionState"`.

#### 3.4.5 Build Scenes Protocol (4A.5)

**`build-scenes-operation` / `list`**

Parameters:
```json
{
  "operation": "list"
}
```

Response `dataJson`:
```json
{
  "operation": "list",
  "scenes": [
    {
      "path": "Assets/Scenes/MainMenu.unity",
      "guid": "abc123",
      "enabled": true,
      "index": 0
    },
    {
      "path": "Assets/Scenes/Gameplay.unity",
      "guid": "def456",
      "enabled": true,
      "index": 1
    },
    {
      "path": "Assets/Scenes/Credits.unity",
      "guid": "ghi789",
      "enabled": false,
      "index": 2
    }
  ],
  "count": 3,
  "success": true,
  "message": "Found 3 scenes in build settings"
}
```

**`build-scenes-operation` / `add`**

Parameters:
```json
{
  "operation": "add",
  "scenePath": "Assets/Scenes/Loading.unity",
  "index": 1
}
```

Response `dataJson`:
```json
{
  "operation": "add",
  "scenePath": "Assets/Scenes/Loading.unity",
  "index": 1,
  "totalScenes": 4,
  "success": true,
  "message": "Added scene at index 1"
}
```

**`build-scenes-operation` / `remove`**

Parameters:
```json
{
  "operation": "remove",
  "scenePath": "Assets/Scenes/Credits.unity"
}
```

Response `dataJson`:
```json
{
  "operation": "remove",
  "scenePath": "Assets/Scenes/Credits.unity",
  "totalScenes": 2,
  "success": true,
  "message": "Removed scene from build settings"
}
```

**`build-scenes-operation` / `enable` / `disable`**

Parameters:
```json
{
  "operation": "enable",
  "scenePath": "Assets/Scenes/Credits.unity"
}
```

Response `dataJson`:
```json
{
  "operation": "enable",
  "scenePath": "Assets/Scenes/Credits.unity",
  "enabled": true,
  "success": true,
  "message": "Scene enabled"
}
```

**`build-scenes-operation` / `reorder`**

Parameters:
```json
{
  "operation": "reorder",
  "fromIndex": 2,
  "toIndex": 0
}
```

Response `dataJson`:
```json
{
  "operation": "reorder",
  "fromIndex": 2,
  "toIndex": 0,
  "movedScene": "Assets/Scenes/Credits.unity",
  "totalScenes": 3,
  "success": true,
  "message": "Moved scene from index 2 to 0"
}
```

#### 3.4.6 Duplicate Protocol (4A.6)

Uses the existing `gameobject-operation` command type with new `"operation": "duplicate"`.

**`gameobject-operation` / `duplicate`**

Parameters:
```json
{
  "operation": "duplicate",
  "gameObjectPath": "Player",
  "count": 2
}
```

Response `dataJson`:
```json
{
  "operation": "duplicate",
  "gameObjectPath": "Player",
  "duplicates": [
    {"name": "Player (1)", "path": "Player (1)"},
    {"name": "Player (2)", "path": "Player (2)"}
  ],
  "count": 2,
  "success": true,
  "message": "Duplicated 'Player' 2 times"
}
```

#### 3.4.7 Physics Configuration Protocol (4C.7)

**`physics-config` / `get`**

Parameters:
```json
{
  "operation": "get"
}
```

Response `dataJson`:
```json
{
  "operation": "get",
  "gravity": {"x": 0.0, "y": -9.81, "z": 0.0},
  "defaultSolverIterations": 6,
  "defaultSolverVelocityIterations": 1,
  "bounceThreshold": 2.0,
  "sleepThreshold": 0.005,
  "defaultContactOffset": 0.01,
  "defaultMaxAngularSpeed": 50.0,
  "autoSyncTransforms": false,
  "reuseCollisionCallbacks": true,
  "success": true,
  "message": "Physics settings retrieved"
}
```

**`physics-config` / `set`**

Parameters:
```json
{
  "operation": "set",
  "gravity": {"x": 0.0, "y": -20.0, "z": 0.0},
  "defaultSolverIterations": 10
}
```

Response `dataJson`:
```json
{
  "operation": "set",
  "changed": ["gravity", "defaultSolverIterations"],
  "success": true,
  "message": "Updated 2 physics settings"
}
```

**`physics-config` / `collision-matrix-get`**

Parameters:
```json
{
  "operation": "collision-matrix-get"
}
```

Response `dataJson`:
```json
{
  "operation": "collision-matrix-get",
  "ignoredPairs": [
    {"layer1": 8, "layer1Name": "Player", "layer2": 9, "layer2Name": "Projectile"},
    {"layer1": 10, "layer1Name": "UI", "layer2": 11, "layer2Name": "Trigger"}
  ],
  "success": true,
  "message": "Retrieved collision matrix (2 ignored pairs)"
}
```

> **Design note:** Only the ignored pairs are returned to keep the response compact. The full 32x32 matrix has 528 unique pairs; returning only the non-default entries is far more useful for auditing.

**`physics-config` / `collision-matrix-set`**

Parameters:
```json
{
  "operation": "collision-matrix-set",
  "layer1": 8,
  "layer2": 9,
  "ignore": true
}
```

Response `dataJson`:
```json
{
  "operation": "collision-matrix-set",
  "layer1": 8,
  "layer1Name": "Player",
  "layer2": 9,
  "layer2Name": "Projectile",
  "ignore": true,
  "success": true,
  "message": "Set Player/Projectile collision to ignored"
}
```

#### 3.4.8 Quality Configuration Protocol (4C.8)

**`quality-config` / `get`**

Parameters:
```json
{
  "operation": "get",
  "level": -1
}
```

> `level: -1` or omitted means the current active level.

Response `dataJson`:
```json
{
  "operation": "get",
  "levelIndex": 2,
  "levelName": "High",
  "pixelLightCount": 4,
  "shadowDistance": 150.0,
  "shadowCascades": 4,
  "antiAliasing": 4,
  "vSyncCount": 1,
  "lodBias": 2.0,
  "maximumLODLevel": 0,
  "anisotropicTextures": "ForceEnable",
  "textureQuality": 0,
  "softParticles": true,
  "realtimeReflectionProbes": true,
  "billboardsFaceCameraPosition": true,
  "success": true,
  "message": "Quality settings for 'High' (level 2)"
}
```

**`quality-config` / `set-level`**

Parameters:
```json
{
  "operation": "set-level",
  "level": 0
}
```

Response `dataJson`:
```json
{
  "operation": "set-level",
  "previousLevel": 2,
  "previousLevelName": "High",
  "newLevel": 0,
  "newLevelName": "Low",
  "success": true,
  "message": "Quality level set to 'Low' (0)"
}
```

**`quality-config` / `list`**

Parameters:
```json
{
  "operation": "list"
}
```

Response `dataJson`:
```json
{
  "operation": "list",
  "levels": [
    {"index": 0, "name": "Low", "active": false},
    {"index": 1, "name": "Medium", "active": false},
    {"index": 2, "name": "High", "active": true},
    {"index": 3, "name": "Very High", "active": false},
    {"index": 4, "name": "Ultra", "active": false}
  ],
  "activeLevel": 2,
  "count": 5,
  "success": true,
  "message": "Found 5 quality levels"
}
```

#### 3.4.9 Editor Config Protocol (4C.9)

**`editor-config` / `get`**

Parameters:
```json
{
  "operation": "get"
}
```

Response `dataJson`:
```json
{
  "operation": "get",
  "enterPlayModeOptionsEnabled": true,
  "enterPlayModeOptions": "DisableDomainReload",
  "serializationMode": "ForceText",
  "assetPipelineMode": "Version2",
  "spritePackerMode": "AlwaysOnAtlas",
  "lineEndingsForNewScripts": "OSNative",
  "defaultBehaviorMode": "Mode3D",
  "prefabRegularEnvironment": "",
  "prefabUIEnvironment": "",
  "success": true,
  "message": "Editor settings retrieved"
}
```

**`editor-config` / `set`**

Parameters:
```json
{
  "operation": "set",
  "key": "enterPlayModeOptionsEnabled",
  "value": "true"
}
```

Response `dataJson`:
```json
{
  "operation": "set",
  "key": "enterPlayModeOptionsEnabled",
  "previousValue": "false",
  "newValue": "true",
  "success": true,
  "message": "Editor setting updated"
}
```

#### 3.4.10 Tags and Layers Protocol (4C.10)

**`tags-layers-operation` / `tags-list`**

Parameters:
```json
{
  "operation": "tags-list"
}
```

Response `dataJson`:
```json
{
  "operation": "tags-list",
  "tags": ["Untagged", "Respawn", "Finish", "EditorOnly", "MainCamera", "Player", "GameController", "Enemy", "Collectible"],
  "builtInCount": 7,
  "customCount": 2,
  "success": true,
  "message": "Found 9 tags"
}
```

**`tags-layers-operation` / `tags-add`**

Parameters:
```json
{
  "operation": "tags-add",
  "tag": "Interactable"
}
```

Response `dataJson`:
```json
{
  "operation": "tags-add",
  "tag": "Interactable",
  "success": true,
  "message": "Tag 'Interactable' added"
}
```

**`tags-layers-operation` / `layers-list`**

Parameters:
```json
{
  "operation": "layers-list"
}
```

Response `dataJson`:
```json
{
  "operation": "layers-list",
  "layers": [
    {"index": 0, "name": "Default", "builtIn": true},
    {"index": 1, "name": "TransparentFX", "builtIn": true},
    {"index": 2, "name": "Ignore Raycast", "builtIn": true},
    {"index": 3, "name": "", "builtIn": true},
    {"index": 4, "name": "Water", "builtIn": true},
    {"index": 5, "name": "UI", "builtIn": true},
    {"index": 6, "name": "", "builtIn": false},
    {"index": 7, "name": "", "builtIn": false},
    {"index": 8, "name": "Player", "builtIn": false},
    {"index": 9, "name": "Enemy", "builtIn": false}
  ],
  "totalCount": 32,
  "usedCount": 8,
  "success": true,
  "message": "Found 32 layers (8 in use)"
}
```

**`tags-layers-operation` / `layers-add`**

Parameters:
```json
{
  "operation": "layers-add",
  "layerName": "Projectile",
  "layerIndex": 10
}
```

Response `dataJson`:
```json
{
  "operation": "layers-add",
  "layerName": "Projectile",
  "layerIndex": 10,
  "success": true,
  "message": "Layer 'Projectile' added at index 10"
}
```

**`tags-layers-operation` / `sorting-layers-list`**

Parameters:
```json
{
  "operation": "sorting-layers-list"
}
```

Response `dataJson`:
```json
{
  "operation": "sorting-layers-list",
  "sortingLayers": [
    {"name": "Default", "uniqueId": 0, "value": 0},
    {"name": "Background", "uniqueId": 1234567, "value": 1},
    {"name": "Foreground", "uniqueId": 2345678, "value": 2}
  ],
  "count": 3,
  "success": true,
  "message": "Found 3 sorting layers"
}
```

**`tags-layers-operation` / `sorting-layers-add`**

Parameters:
```json
{
  "operation": "sorting-layers-add",
  "sortingLayerName": "UI-Overlay"
}
```

Response `dataJson`:
```json
{
  "operation": "sorting-layers-add",
  "sortingLayerName": "UI-Overlay",
  "success": true,
  "message": "Sorting layer 'UI-Overlay' added"
}
```

---

## 4. Implementation Details

### 4A.1 Set Selection

**C# handler:** `SetSelectionCommandHandler`

```csharp
// Core logic (simplified)
public BridgeResponse Execute(BridgeCommand command)
{
    var p = JsonUtility.FromJson<SetSelectionParams>(command.parametersJson);

    if (p.asset)
    {
        // Asset selection: load by path
        var objects = p.paths.Select(path =>
            AssetDatabase.LoadMainAssetAtPath(path))
            .Where(obj => obj != null).ToArray();
        Selection.objects = objects;
        Selection.activeObject = objects.FirstOrDefault();
    }
    else
    {
        // Scene object selection: find by hierarchy path
        var gameObjects = p.paths.Select(FindGameObjectByPath)
            .Where(go => go != null).ToArray();
        Selection.objects = gameObjects;
        Selection.activeGameObject = gameObjects.FirstOrDefault();
    }
    // Return result with selected paths
}
```

Key Unity APIs: `Selection.objects`, `Selection.activeGameObject`, `Selection.activeObject`, `AssetDatabase.LoadMainAssetAtPath`.

### 4A.2 Transform Manipulation

**C# handler:** `TransformOperationCommandHandler`

All mutating operations wrap with `Undo.RecordObject(transform, "description")` before changes.

- **get**: Read `transform.position`, `transform.localPosition`, `transform.eulerAngles`, `transform.localEulerAngles`, `transform.localScale`, `transform.lossyScale`.
- **set**: Parse optional position/rotation/scale from params. If `local` is true, set `localPosition`/`localEulerAngles`; otherwise set `position`/`eulerAngles`. Always set `localScale`.
- **parent**: Use `Undo.SetTransformParent(transform, newParent, "Reparent")`. For unparent, pass `null`.
- **sibling**: Use `Undo.RecordObject` then `transform.SetSiblingIndex(index)`.

All mutating operations mark the scene dirty.

Key Unity APIs: `Undo.RecordObject`, `Undo.SetTransformParent`, `Transform.SetSiblingIndex`, `EditorSceneManager.MarkSceneDirty`.

### 4A.3 SerializedProperty Access

**C# handler:** `SerializedPropertyCommandHandler` + `SerializedPropertyHelpers.cs`

This is the most complex new handler. The helper file handles property value serialization/deserialization for all `SerializedPropertyType` values.

**Supported property types and their JSON representations:**

| SerializedPropertyType | JSON Value Format | Example |
|----------------------|------------------|---------|
| `Integer` | number | `42` |
| `Boolean` | boolean | `true` |
| `Float` | number | `3.14` |
| `String` | string | `"hello"` |
| `Color` | `{"r":F,"g":F,"b":F,"a":F}` | `{"r":1,"g":0,"b":0,"a":1}` |
| `ObjectReference` | `{"instanceId":N}` or `{"assetPath":"..."}` | `{"assetPath":"Assets/Textures/Albedo.png"}` |
| `LayerMask` | number (bitmask) | `256` |
| `Enum` | number (index) | `2` |
| `Vector2` | `{"x":F,"y":F}` | `{"x":1,"y":2}` |
| `Vector3` | `{"x":F,"y":F,"z":F}` | `{"x":1,"y":2,"z":3}` |
| `Vector4` | `{"x":F,"y":F,"z":F,"w":F}` | `{"x":1,"y":2,"z":3,"w":4}` |
| `Rect` | `{"x":F,"y":F,"width":F,"height":F}` | `{"x":0,"y":0,"width":100,"height":100}` |
| `Bounds` | `{"center":V3,"size":V3}` | nested Vector3 objects |
| `Quaternion` | `{"x":F,"y":F,"z":F,"w":F}` | `{"x":0,"y":0,"z":0,"w":1}` |
| `Vector2Int` | `{"x":N,"y":N}` | `{"x":1,"y":2}` |
| `Vector3Int` | `{"x":N,"y":N,"z":N}` | `{"x":1,"y":2,"z":3}` |
| `RectInt` | `{"x":N,"y":N,"width":N,"height":N}` | `{"x":0,"y":0,"width":100,"height":100}` |
| `BoundsInt` | `{"position":V3I,"size":V3I}` | nested Vector3Int objects |
| `ArraySize` | number | `5` (resizes array) |
| `AnimationCurve` | string (not editable via bridge) | read-only display |
| `Gradient` | string (not editable via bridge) | read-only display |

**Property path resolution:**

```csharp
var so = new SerializedObject(component);
var sp = so.FindProperty(propertyPath);
// For arrays: "m_Items.Array.data[0]"
// For nested: "m_Data.m_Value"
```

**`list` operation:** Iterates visible properties using `SerializedProperty.NextVisible()`. The `depth` parameter controls how deep into nested structures to enumerate (default 1 = top-level only).

**`set` operation flow:**
1. Create `SerializedObject` from component
2. Call `Update()` to refresh
3. Find property by path
4. Set value based on `propertyType`
5. Call `ApplyModifiedProperties()` (auto-registers undo)

### 4A.4 EditorPrefs / SessionState

**C# handler:** `EditorPrefsCommandHandler`

Single handler serves both EditorPrefs and SessionState via the `operation` prefix (`prefs-*` vs `session-*`).

```csharp
// Dispatch pattern
switch (operation)
{
    case "prefs-get": return GetPref(EditorPrefs, params);
    case "prefs-set": return SetPref(EditorPrefs, params);
    case "session-get": return GetSession(SessionState, params);
    // ...
}
```

Type dispatch uses the `valueType` parameter:
- `string`: `EditorPrefs.GetString` / `SetString`
- `int`: `EditorPrefs.GetInt` / `SetInt`
- `float`: `EditorPrefs.GetFloat` / `SetFloat`
- `bool`: `EditorPrefs.GetBool` / `SetBool`

**Security consideration:** EditorPrefs can contain sensitive data (license keys, auth tokens). The handler should not support `DeleteAll` to prevent accidental data loss. Only individual key operations are exposed.

### 4A.5 Build Settings Scenes

**C# handler:** `BuildScenesCommandHandler`

Uses `EditorBuildSettings.scenes` (get/set array of `EditorBuildSettingsScene`).

```csharp
// Pattern for modifications:
var scenes = EditorBuildSettings.scenes.ToList();
// ... modify list ...
EditorBuildSettings.scenes = scenes.ToArray();
```

Each `EditorBuildSettingsScene` has:
- `path` (string)
- `guid` (GUID)
- `enabled` (bool)

**Validation:** The `add` operation verifies the scene file exists at the given path before adding. The `remove`/`enable`/`disable` operations match by path (case-insensitive on Windows).

### 4A.6 Duplicate

Added as a new `"duplicate"` case in the existing `GameObjectOperationCommandHandler`.

```csharp
case "duplicate":
    result = DuplicateGameObject(parameters);
    break;
```

Implementation uses `Unsupported.DuplicateGameObjectsUsingPasteboard` for exact Unity duplicate behavior, or the simpler approach:

```csharp
// Select the object, then duplicate via menu
Selection.activeGameObject = go;
Unsupported.DuplicateGameObjectsUsingPasteboard();
// The duplicated objects are now selected
var duplicates = Selection.gameObjects;
```

Alternative approach using `Object.Instantiate`:
```csharp
for (int i = 0; i < count; i++)
{
    var duplicate = Object.Instantiate(go, go.transform.parent);
    duplicate.name = $"{go.name} ({i + 1})";
    Undo.RegisterCreatedObjectUndo(duplicate, "Duplicate GameObject");
}
```

The `Object.Instantiate` approach is preferred because it does not require manipulating the selection and handles the `count` parameter naturally.

**Model extension:** `GameObjectOperationParams` gains a `count` field (default 1). `GameObjectOperationResult` gains a `duplicates` list.

### 4B.1 ObjectFactory Bugfix

**File:** `ClaudeCodeBridge/GameObjectOperationCommandHandler.cs`
**Line ~122:** Replace `new GameObject(parameters.gameObjectName)` with:

```csharp
var newGameObject = ObjectFactory.CreateGameObject(parameters.gameObjectName);
```

`ObjectFactory.CreateGameObject`:
- Automatically registers the undo operation
- Applies default Presets configured for GameObjects
- Fires `ObjectFactory.componentWasAdded` callback

The existing `EditorUtility.SetDirty` call can remain for safety but is technically redundant after this change.

### 4B.2 SerializedProperty Fallback for SetComponentData

**File:** `ClaudeCodeBridge/SetComponentDataCommandHandler.cs`

Replace the current `FieldInfo`-based setter with a dual strategy:

```csharp
foreach (var fieldUpdate in parameters.fieldUpdates)
{
    // Strategy 1: Try SerializedProperty (handles [SerializeField] private)
    var so = new SerializedObject(component);
    so.Update();
    var sp = so.FindProperty(fieldUpdate.fieldName);
    if (sp != null)
    {
        SetSerializedPropertyValue(sp, fieldUpdate.valueJson);
        so.ApplyModifiedProperties(); // auto-undo
        result.updatedFields.Add(fieldUpdate.fieldName);
        result.fieldsUpdated++;
        continue;
    }

    // Strategy 2: Fall back to reflection for public non-serialized fields
    var field = component.GetType().GetField(
        fieldUpdate.fieldName,
        BindingFlags.Public | BindingFlags.Instance);
    if (field != null)
    {
        Undo.RecordObject(component, "Set Component Data");
        var value = DeserializeFieldValue(fieldUpdate.valueJson, field.FieldType);
        field.SetValue(component, value);
        result.updatedFields.Add(fieldUpdate.fieldName);
        result.fieldsUpdated++;
        continue;
    }

    BridgeLogger.LogWarning($"Field not found: {fieldUpdate.fieldName}");
}
```

The `SetSerializedPropertyValue` helper can be shared with the new `SerializedPropertyCommandHandler` via a static utility class (`SerializedPropertyHelpers.cs`).

### 4B.3 Undo-aware Destroy

**File:** `ClaudeCodeBridge/GameObjectOperationCommandHandler.cs`
**Line ~192:** Replace `UnityEngine.Object.DestroyImmediate(gameObject)` with:

```csharp
Undo.DestroyObjectImmediate(gameObject);
```

This makes delete operations undoable. Also remove the orphan cleanup line (line ~132) that destroys the new object on parent-not-found:
```csharp
// Before: UnityEngine.Object.DestroyImmediate(newGameObject);
// After: Undo.DestroyObjectImmediate(newGameObject);
```

### 4C.7 Physics Configuration

**C# handler:** `PhysicsConfigCommandHandler`

Read-only `get` uses `Physics.gravity`, `Physics.defaultSolverIterations`, etc.

Write `set` modifies only the fields present in the params, using a null-check pattern:

```csharp
if (p.gravity.HasValue)
    Physics.gravity = p.gravity.Value;
if (p.defaultSolverIterations > 0)
    Physics.defaultSolverIterations = p.defaultSolverIterations;
```

**Collision matrix:** Uses `Physics.GetIgnoreLayerCollision(layer1, layer2)` and `Physics.IgnoreLayerCollision(layer1, layer2, ignore)`.

For the `collision-matrix-get` operation, iterate all 528 unique pairs (i < j for layers 0-31) and return only pairs where `GetIgnoreLayerCollision` returns true.

Key Unity APIs: `Physics.gravity`, `Physics.defaultSolverIterations`, `Physics.defaultSolverVelocityIterations`, `Physics.bounceThreshold`, `Physics.sleepThreshold`, `Physics.defaultContactOffset`, `Physics.IgnoreLayerCollision`, `Physics.GetIgnoreLayerCollision`.

### 4C.8 Quality Settings

**C# handler:** `QualityConfigCommandHandler`

- **get**: Read properties from `QualitySettings` (static class). If `level` is specified and differs from current, temporarily switch with `QualitySettings.SetQualityLevel(level, false)`, read, then switch back.
- **set-level**: `QualitySettings.SetQualityLevel(level, true)`.
- **list**: Use `QualitySettings.names` for the name array; `QualitySettings.GetQualityLevel()` for the active level.

Key Unity APIs: `QualitySettings.GetQualityLevel()`, `QualitySettings.SetQualityLevel()`, `QualitySettings.names`, plus all property getters.

### 4C.9 Editor Settings

**C# handler:** `EditorConfigCommandHandler`

Reads/writes `EditorSettings` static properties. The `get` operation returns all commonly automated settings. The `set` operation uses a key-value dispatch:

```csharp
switch (key)
{
    case "enterPlayModeOptionsEnabled":
        EditorSettings.enterPlayModeOptionsEnabled = bool.Parse(value);
        break;
    case "enterPlayModeOptions":
        EditorSettings.enterPlayModeOptions = (EnterPlayModeOptions)Enum.Parse(
            typeof(EnterPlayModeOptions), value);
        break;
    case "serializationMode":
        EditorSettings.serializationMode = (SerializationMode)Enum.Parse(
            typeof(SerializationMode), value);
        break;
    // ...
}
```

Supported keys: `enterPlayModeOptionsEnabled`, `enterPlayModeOptions`, `serializationMode`, `assetPipelineMode`, `spritePackerMode`, `lineEndingsForNewScripts`, `defaultBehaviorMode`, `prefabRegularEnvironment`, `prefabUIEnvironment`.

### 4C.10 Tags and Layers

**C# handler:** `TagsLayersCommandHandler`

Tags use the `UnityEditorInternal.InternalEditorUtility` API:
- `InternalEditorUtility.tags` -- returns all tags
- `InternalEditorUtility.AddTag(tag)` -- add new tag

Layers use the `TagManager.asset` serialized object approach:
- Open `SerializedObject` on `AssetDatabase.LoadMainAssetAtPath("ProjectSettings/TagManager.asset")`
- Read `layers` property for the full layer list
- Write to specific array element for `layers-add`

Sorting layers:
- `SortingLayer.layers` -- read all sorting layers
- Adding requires modifying the TagManager.asset serialized object's `m_SortingLayers` array

Key Unity APIs: `InternalEditorUtility.tags`, `InternalEditorUtility.AddTag`, `InternalEditorUtility.layers`, `SortingLayer.layers`, `SerializedObject` on TagManager.

---

## 5. C# Implementation Notes

### 5.1 Undo Integration

All Phase 4A mutating operations use Unity's Undo system:

| Operation | Undo Method |
|-----------|-------------|
| Set selection | No undo needed (selection is not undoable) |
| Transform set/parent/sibling | `Undo.RecordObject` / `Undo.SetTransformParent` |
| SerializedProperty set | `SerializedObject.ApplyModifiedProperties()` (implicit undo) |
| EditorPrefs set/delete | No undo (prefs are not undoable) |
| Build scenes modify | No undo (`EditorBuildSettings.scenes` is not undoable) |
| Duplicate | `Undo.RegisterCreatedObjectUndo` |
| Physics set | No undo (physics settings are project-level) |
| Quality set-level | No undo (quality level is project-level) |
| Editor config set | No undo (editor settings are project-level) |
| Tags/layers add | No undo (TagManager changes are project-level) |

### 5.2 Play Mode Guards

All mutating scene operations (transform, serialized property set, duplicate) must reject during play mode:

```csharp
if (EditorApplication.isPlaying)
{
    return BridgeResponse.Error(commandId, commandType,
        "Mutating scene operations are not supported during play mode.");
}
```

Read-only operations (transform get, property list, prefs get, etc.) are allowed during play mode.

### 5.3 Compilation Guards

All handlers check `EditorApplication.isCompiling` before execution:

```csharp
if (EditorApplication.isCompiling)
{
    return BridgeResponse.Error(commandId, commandType,
        "Cannot execute while scripts are compiling.");
}
```

### 5.4 File Organization

New C# files:

```
ClaudeCodeBridge/
├── SetSelectionCommandHandler.cs          # ~80 LOC
├── TransformOperationCommandHandler.cs    # ~200 LOC
├── SerializedPropertyCommandHandler.cs    # ~250 LOC
├── SerializedPropertyHelpers.cs           # ~300 LOC (value read/write for all types)
├── EditorPrefsCommandHandler.cs           # ~200 LOC
├── BuildScenesCommandHandler.cs           # ~200 LOC
├── PhysicsConfigCommandHandler.cs         # ~200 LOC
├── QualityConfigCommandHandler.cs         # ~180 LOC
├── EditorConfigCommandHandler.cs          # ~150 LOC
├── TagsLayersCommandHandler.cs            # ~250 LOC
├── BridgeModelsPhase4.cs                  # ~200 LOC
└── BridgeModelsPhase4Tier2.cs             # ~180 LOC
```

Modified C# files:

```
ClaudeCodeBridge/
├── GameObjectOperationCommandHandler.cs   # +50 LOC (duplicate, ObjectFactory, Undo destroy)
├── SetComponentDataCommandHandler.cs      # +40 LOC (SerializedProperty fallback)
├── BridgeCommandRegistry.cs               # +10 LOC (new handler registrations)
└── BridgeModelsPhase3.cs                  # +10 LOC (GameObjectOperationParams.count, duplicates list)
```

### 5.5 Shared Utility: FindGameObjectByPath

Multiple existing handlers duplicate the `FindGameObjectByPath` method. Phase 4 should extract this into a shared utility:

```csharp
// New file: BridgeUtilities.cs
public static class BridgeUtilities
{
    public static GameObject FindGameObjectByPath(string path) { ... }
    public static string GetGameObjectPath(GameObject go) { ... }
}
```

Existing handlers can then delegate to the shared utility, reducing code duplication. This is a non-breaking refactor since the methods are private in each handler.

---

## 6. Testing Strategy

### 6.1 Unit Tests (Python)

All new Python command modules get unit tests with mocked `DirectBridge`:

| Test File | Covers |
|-----------|--------|
| `tests/unit/test_select.py` | `set_selection` |
| `tests/unit/test_transform.py` | `transform_get`, `transform_set`, `transform_parent`, `transform_sibling` |
| `tests/unit/test_serialized_property.py` | `property_get`, `property_set`, `property_list` |
| `tests/unit/test_editor_prefs.py` | All prefs and session operations |
| `tests/unit/test_build_scenes.py` | All build scenes operations |
| `tests/unit/test_physics_config.py` | Physics get/set and collision matrix |
| `tests/unit/test_quality_config.py` | Quality get/set-level/list |
| `tests/unit/test_editor_config.py` | Editor config get/set |
| `tests/unit/test_tags_layers.py` | All tags/layers/sorting-layers operations |

Each test file follows the existing pattern:
```python
@pytest.fixture
def mock_bridge(mocker):
    bridge = mocker.AsyncMock(spec=DirectBridge)
    bridge.send_command_with_retry.return_value = CommandResult(
        success=True, data={...}
    )
    return bridge

async def test_transform_get(mock_bridge):
    result = await transform_get(mock_bridge, "Player")
    mock_bridge.send_command_with_retry.assert_called_once_with(
        command_type="transform-operation",
        parameters={"operation": "get", "gameObjectPath": "Player"},
        timeout=10.0,
    )
    assert result.success
```

Test the duplicate operation in the existing `tests/unit/test_hierarchy.py` file.

### 6.2 Integration Tests

Integration tests require a running Unity Editor and are marked with `@pytest.mark.integration`:

- Transform set/get round-trip
- SerializedProperty set/get round-trip
- Build scenes add/remove round-trip
- Selection set then get-selection verification

### 6.3 Test Totals

Expected new tests: ~90 (approximately 9 per command module).

---

## 7. Migration & Compatibility

### 7.1 Protocol Compatibility

All new commands use new command types. No existing command types are modified in protocol behavior.

The bugfix in `SetComponentDataCommandHandler` (4B.2) is backward-compatible: fields that previously worked via public reflection continue to work. The SerializedProperty path additionally resolves `[SerializeField] private` fields that were previously silently skipped.

### 7.2 MCP Tool Compatibility

All new MCP tools use new tool names. No existing tool schemas change.

The duplicate operation reuses the existing `unity_gameobject_operation` tool but adds a new `"operation": "duplicate"` value. Existing clients that only use `create`, `delete`, `rename` are unaffected.

### 7.3 CLI Compatibility

New CLI groups (`select`, `transform`, `property`, `prefs`, `session`, `build-scenes`, `physics`, `quality`, `editor-config`, `tags`, `layers`, `sorting-layers`) are all new additions. The `hierarchy duplicate` subcommand extends the existing `hierarchy` group.

### 7.4 C# Bridge Installation

New C# files must be copied to Unity projects via the `lifecycle install` command. The existing install mechanism copies all files from `ClaudeCodeBridge/` to `Assets/Scripts/Editor/ClaudeCodeBridge/`, so new handlers are automatically included.

### 7.5 Version Compatibility

- **Unity 2022.x+**: All Phase 4A and 4B features use APIs available since Unity 2020+.
- **Unity 6 (6000.0+)**: No Unity 6-specific APIs are used in Phase 4. No `#if UNITY_6000_0_OR_NEWER` guards needed.
- **Python 3.10+**: Continues to use `X | Y` union syntax and modern type hints.

---

## 8. Risks & Open Questions

### 8.1 Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| SerializedProperty type coverage gaps | Some exotic property types (managed references, fixed buffers) may not serialize cleanly to JSON | Start with the 20 most common types (listed in 4A.3), return "unsupported" for others. Add more types as needed. |
| TagManager.asset serialization fragility | Writing to TagManager via SerializedObject could break if Unity changes the internal format | Read-only operations are safe. Write operations (tags-add, layers-add) should validate the SerializedObject structure before modifying. |
| `Unsupported.DuplicateGameObjectsUsingPasteboard` is internal API | Could break in future Unity versions | Use `Object.Instantiate` + `Undo.RegisterCreatedObjectUndo` instead (public, stable API). |
| EditorPrefs key namespace collisions | Bridge operations could accidentally overwrite important editor preferences | Document that users must use namespaced keys (e.g., `MyTool.Setting`). Do not expose `DeleteAll`. |
| Physics settings persistence | Physics settings are project-wide and saved to ProjectSettings | Changes are immediate and saved automatically. Warn in documentation that physics changes affect all users of the project. |

### 8.2 Open Questions

1. **Should `set-selection` support InstanceID-based selection?** Some MCP workflows might have instance IDs from previous responses. Current spec uses path-only selection. Adding InstanceID support would require `EditorUtility.InstanceIDToObject()` but adds complexity.

2. **Should `serialized-property list` include private fields by default?** The `NextVisible()` iterator respects the Inspector visibility rules. An alternative `Next(true)` iterator would show all properties including hidden ones. Current spec uses `NextVisible()` for consistency with what users see in the Inspector.

3. **Should physics/quality/editor-config operations be consolidated into a single `project-settings` handler?** They are currently separate handlers for single-responsibility, but could be merged into one handler with operation dispatch if the individual handlers would be too small (< 100 LOC each).

4. **Should the `duplicate` operation preserve component values exactly?** `Object.Instantiate` copies all values. Should there be an option to reset specific components (e.g., unique IDs)?

5. **Should the `transform set` command accept quaternion rotation instead of (or in addition to) Euler angles?** Euler angles are more human-friendly but can have gimbal lock issues. Could accept both with a `--quaternion` flag.

---

## Appendix A: File Inventory

### New Files

| Path | LOC (est.) | Purpose |
|------|------------|---------|
| `ClaudeCodeBridge/SetSelectionCommandHandler.cs` | 80 | Set editor selection |
| `ClaudeCodeBridge/TransformOperationCommandHandler.cs` | 200 | Transform manipulation |
| `ClaudeCodeBridge/SerializedPropertyCommandHandler.cs` | 250 | SerializedProperty access |
| `ClaudeCodeBridge/SerializedPropertyHelpers.cs` | 300 | Property value serialization |
| `ClaudeCodeBridge/EditorPrefsCommandHandler.cs` | 200 | EditorPrefs/SessionState |
| `ClaudeCodeBridge/BuildScenesCommandHandler.cs` | 200 | Build Settings scenes |
| `ClaudeCodeBridge/PhysicsConfigCommandHandler.cs` | 200 | Physics settings |
| `ClaudeCodeBridge/QualityConfigCommandHandler.cs` | 180 | Quality settings |
| `ClaudeCodeBridge/EditorConfigCommandHandler.cs` | 150 | Editor settings |
| `ClaudeCodeBridge/TagsLayersCommandHandler.cs` | 250 | Tags, layers, sorting layers |
| `ClaudeCodeBridge/BridgeModelsPhase4.cs` | 200 | Phase 4A models |
| `ClaudeCodeBridge/BridgeModelsPhase4Tier2.cs` | 180 | Phase 4C models |
| `ClaudeCodeBridge/BridgeUtilities.cs` | 50 | Shared FindGameObjectByPath |
| `src/unity_bridge/commands/select.py` | 60 | Selection CLI + core |
| `src/unity_bridge/commands/transform.py` | 180 | Transform CLI + core |
| `src/unity_bridge/commands/serialized_property.py` | 150 | SerializedProperty CLI + core |
| `src/unity_bridge/commands/editor_prefs.py` | 200 | EditorPrefs/SessionState CLI + core |
| `src/unity_bridge/commands/build_scenes.py` | 180 | Build scenes CLI + core |
| `src/unity_bridge/commands/physics_config.py` | 150 | Physics CLI + core |
| `src/unity_bridge/commands/quality_config.py` | 120 | Quality CLI + core |
| `src/unity_bridge/commands/editor_config.py` | 100 | Editor config CLI + core |
| `src/unity_bridge/commands/tags_layers.py` | 200 | Tags/layers CLI + core |
| `src/unity_bridge/mcp/schemas_phase4.py` | 450 | Phase 4 MCP schemas |
| `tests/unit/test_select.py` | 40 | Selection tests |
| `tests/unit/test_transform.py` | 100 | Transform tests |
| `tests/unit/test_serialized_property.py` | 100 | SerializedProperty tests |
| `tests/unit/test_editor_prefs.py` | 100 | EditorPrefs tests |
| `tests/unit/test_build_scenes.py` | 100 | Build scenes tests |
| `tests/unit/test_physics_config.py` | 80 | Physics tests |
| `tests/unit/test_quality_config.py` | 60 | Quality tests |
| `tests/unit/test_editor_config.py` | 60 | Editor config tests |
| `tests/unit/test_tags_layers.py` | 100 | Tags/layers tests |

### Modified Files

| Path | Change |
|------|--------|
| `ClaudeCodeBridge/GameObjectOperationCommandHandler.cs` | ObjectFactory, Undo destroy, duplicate operation |
| `ClaudeCodeBridge/SetComponentDataCommandHandler.cs` | SerializedProperty fallback |
| `ClaudeCodeBridge/BridgeCommandRegistry.cs` | Register new handlers |
| `ClaudeCodeBridge/BridgeModelsPhase3.cs` | Extend GameObjectOperationParams/Result |
| `src/unity_bridge/commands/hierarchy.py` | Add duplicate_gameobject + CLI wrapper |
| `src/unity_bridge/mcp/tools.py` | Add 9 new tool definitions + TOOL_COMMAND_MAP entries |
| `src/unity_bridge/core/protocol.py` | Add timeout defaults + parallel-safe entries |
| `src/unity_bridge/app.py` | Register new CLI groups |
| `CHANGELOG.md` | Phase 4 entries |

### Timeout Defaults (additions to `protocol.py`)

```python
# Phase 4A: Critical gaps
"set-selection": 5,
"transform-operation": 10,
"serialized-property": 15,
"editor-prefs-operation": 5,
"build-scenes-operation": 10,
# Phase 4C: Tier 2
"physics-config": 10,
"quality-config": 10,
"editor-config": 10,
"tags-layers-operation": 10,
```

### Parallel-Safe Additions

```python
PARALLEL_SAFE_COMMANDS.update({
    "editor-prefs-operation",  # read operations only, but handler validates
    "physics-config",          # get operations are read-only
    "quality-config",          # get/list are read-only
    "tags-layers-operation",   # list operations are read-only
})
```

> **Note:** These commands contain both read and write operations. The `PARALLEL_SAFE_COMMANDS` set is used for batch parallelism. Since the batch system sends the full command (including operation), the C# handler must individually determine safety. However, for simplicity, only truly read-only command types should be in this set. The above additions are acceptable because their write operations are rare and fast.

> **Revision:** On reflection, only add to `PARALLEL_SAFE_COMMANDS` if ALL operations are read-only. Remove `editor-prefs-operation` from this set since it has write operations. Physics/quality/tags-layers all have write operations too. Only `set-selection` is excluded (it is always mutating). The `transform-operation` `get` is read-only but `set` is not, so exclude it.

**Final parallel-safe additions:** None. All Phase 4 command types include mutating operations. Read-only operations within these types benefit from the existing timeout system but are not eligible for parallel batch execution.
