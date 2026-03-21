# Tech Spec: Phase 2 - Developer Workflow APIs

**Status:** Draft (Revised)
**Author:** Claude Code
**Last Updated:** 2026-03-19
**Version:** 0.2.0

---

## 1. Overview

### Problem Statement

Unity developers using the bridge for automation lack access to five critical workflow
areas: undo/redo management, compilation pipeline introspection, granular prefab override
control, test discovery without execution, and common GameObject maintenance utilities.
These gaps force users to fall back to manual Editor interaction for routine tasks that
should be automatable.

### Goals

- Add 5 new capability areas (undo, compilation pipeline, prefab overrides, test listing,
  hierarchy utilities) totaling ~24 new subcommands
- Maintain the dual-interface pattern: all new features available through both CLI and MCP
- Decide and implement an undo integration strategy for existing mutating handlers
- Keep all new C# handlers under 500 LOC each; split where needed
- Add corresponding unit tests with mocked bridge

### Non-Goals

- Runtime undo (play mode undo is not supported by `UnityEditor.Undo`)
- Custom undo UI or undo visualization
- Compilation pipeline modification (adding/removing defines is deferred to a future phase)
- Test execution improvements (covered by existing `run-tests` command)
- Nested prefab variant creation (complex authoring workflow, out of scope)

---

## 2. Command Reference

### Command Tree

```
unity-bridge undo perform                         # Undo last operation
unity-bridge undo redo                             # Redo last undone operation
unity-bridge undo history [--limit N]              # List undo history
unity-bridge undo clear                            # Clear undo history
unity-bridge undo group-name                       # Get current undo group name
unity-bridge undo collapse <group-index> [--name N]  # Collapse operations from index into one undo step

unity-bridge compile assemblies                    # List project assemblies
unity-bridge compile defines <assembly>            # Get scripting defines
unity-bridge compile which <script-path>           # Which assembly owns a script
unity-bridge compile optimization [--set <mode>]   # Get/set code optimization

unity-bridge prefab overrides list <instance-path>                  # List all overrides
unity-bridge prefab overrides apply <instance-path> [--target T]    # Apply overrides
unity-bridge prefab overrides revert <instance-path> [--target T]   # Revert overrides
unity-bridge prefab status <path>                                   # Prefab type & status
unity-bridge prefab find-instances <asset-path>                     # Find instances in scene
unity-bridge prefab unpack <instance-path> [--completely]           # Unpack prefab

unity-bridge test list [--platform edit|play] [--filter P]          # List tests
unity-bridge test list --categories                                 # List test categories
unity-bridge test list --assemblies                                 # List test assemblies

unity-bridge hierarchy missing-scripts [--fix]                      # Find/fix missing scripts
unity-bridge hierarchy static-flags <object-path>                   # Get static flags
unity-bridge hierarchy set-static-flags <object-path> <flags...>    # Set static flags
unity-bridge hierarchy set-layer <object-path> <layer> [--recursive]  # Set layer (--recursive includes inactive children)
unity-bridge hierarchy set-tag <object-path> <tag>                  # Set tag
```

### Detailed Command Signatures

#### Undo System

| Command | Required Params | Optional Params | Returns |
|---------|----------------|-----------------|---------|
| `undo perform` | -- | `--timeout` | `{undone: bool, groupName: string}` |
| `undo redo` | -- | `--timeout` | `{redone: bool, groupName: string}` |
| `undo history` | -- | `--limit N` (default 20) | `{currentGroupName, recentOperations: [{name, id}], count, note}` |
| `undo clear` | -- | `--timeout` | `{cleared: bool}` |
| `undo group-name` | -- | `--timeout` | `{groupName: string}` |
| `undo collapse` | `group-index` | `--name N`, `--timeout` | `{collapsed: bool, groupIndex: int, name: string}` |

#### Compilation Pipeline Extended

| Command | Required Params | Optional Params | Returns |
|---------|----------------|-----------------|---------|
| `compile assemblies` | -- | `--timeout` | `{assemblies: [{name, path, sourceFileCount, defines, references}]}` |
| `compile defines` | `assembly` | `--timeout` | `{assembly, defines: [string]}` |
| `compile which` | `script-path` | `--timeout` | `{scriptPath, assembly, assemblyPath}` |
| `compile optimization` | -- | `--set none\|debug\|release`, `--timeout` | `{mode: string, changed: bool}` |

#### Prefab Override Management

| Command | Required Params | Optional Params | Returns |
|---------|----------------|-----------------|---------|
| `prefab overrides list` | `instance-path` | `--include-default-overrides`, `--timeout` | `{overrides: [{type, path, details}], hasOverrides, count}` |
| `prefab overrides apply` | `instance-path` | `--target T`, `--timeout` | `{applied: bool, count}` |
| `prefab overrides revert` | `instance-path` | `--target T`, `--timeout` | `{reverted: bool, count}` |
| `prefab status` | `path` | `--timeout` | `{prefabType, instanceStatus, assetPath, isVariant}` |
| `prefab find-instances` | `asset-path` | `--timeout` | `{instances: [{path, scene, hasOverrides}], count}` (root-level only, no nested instances) |
| `prefab unpack` | `instance-path` | `--completely`, `--timeout` | `{unpacked: bool, mode}` |

#### Test Runner Extended

| Command | Required Params | Optional Params | Returns |
|---------|----------------|-----------------|---------|
| `test list` | -- | `--platform`, `--filter`, `--timeout` | `{tests: [{fullName, className, methodName, categories}], count}` |
| `test list --categories` | -- | `--platform`, `--timeout` | `{categories: [string]}` |
| `test list --assemblies` | -- | `--platform`, `--timeout` | `{assemblies: [{name, testCount}]}` |

#### GameObject Utilities

| Command | Required Params | Optional Params | Returns |
|---------|----------------|-----------------|---------|
| `hierarchy missing-scripts` | -- | `--fix`, `--timeout` | `{found: [{path, count}], totalCount, removed}` |
| `hierarchy static-flags` | `object-path` | `--timeout` | `{path, flags: [string], rawValue}` |
| `hierarchy set-static-flags` | `object-path`, `flags` | `--timeout` | `{path, flags: [string], changed: bool}` |
| `hierarchy set-layer` | `object-path`, `layer` | `--recursive`, `--timeout` | `{path, layer, affectedCount}` |
| `hierarchy set-tag` | `object-path`, `tag` | `--timeout` | `{path, tag, changed: bool}` |

---

## 3. Architecture

### C# Command Handlers

New handler files in `ClaudeCodeBridge/`:

| File | Command Type | Unity API |
|------|-------------|-----------|
| `UndoCommandHandler.cs` | `undo-operation` | `UnityEditor.Undo` |
| `CompilationPipelineCommandHandler.cs` | `compilation-pipeline` | `CompilationPipeline` |
| `PrefabOverrideCommandHandler.cs` | `prefab-override` | `PrefabUtility` (override methods) |
| `TestListCommandHandler.cs` | `list-tests` | `TestRunnerApi.RetrieveTestTree` |
| `GameObjectUtilityCommandHandler.cs` | `gameobject-utility` | `GameObjectUtility`, `StaticEditorFlags` |

Each handler implements `ICommandHandler` and routes operations via a `switch` on the
`operation` field in `parametersJson`, matching the pattern used by
`PrefabOperationCommandHandler` and `CompileCommandHandler`.

### Python Command Modules

New and modified files in `src/unity_bridge/commands/`:

| File | Status | Contains |
|------|--------|----------|
| `undo.py` | **New** | `undo_perform`, `undo_redo`, `undo_history`, `undo_clear`, `undo_group_name`, `undo_collapse` + Typer CLI |
| `compile.py` | **New** | `compile_assemblies`, `compile_defines`, `compile_which`, `compile_optimization` + Typer CLI |
| `prefab.py` | **Modified** | Add `prefab_overrides_list`, `prefab_overrides_apply`, `prefab_overrides_revert`, `prefab_status`, `prefab_find_instances`, `prefab_unpack` |
| `testing.py` | **Modified** | Add `list_tests`, `list_test_categories`, `list_test_assemblies` |
| `hierarchy.py` | **Modified** | Add `missing_scripts`, `static_flags`, `set_static_flags`, `set_layer`, `set_tag` |

Each follows the dual-interface pattern:
```python
# Core async function
async def undo_perform(bridge: DirectBridge, timeout: float = 5.0) -> CommandResult:
    return await bridge.send_command_with_retry(
        command_type="undo-operation",
        parameters={"operation": "perform"},
        timeout=timeout,
    )

# Typer CLI wrapper
@undo_app.command("perform")
def undo_perform_cli(ctx: typer.Context) -> None:
    state: AppState = ctx.obj
    result = asyncio.run(undo_perform(state.bridge))
    print_result(result, state.formatter)
```

### MCP Tool Mappings

New entries in `mcp/tools.py` `TOOL_COMMAND_MAP`:

```python
# Undo
"unity_undo_operation": "undo-operation",

# Compilation pipeline
"unity_compilation_pipeline": "compilation-pipeline",

# Prefab overrides
"unity_prefab_overrides": "prefab-override",

# Test listing
"unity_list_tests": "list-tests",

# GameObject utilities
"unity_gameobject_utility": "gameobject-utility",
```

New tool definitions in `TOOL_DEFINITIONS`:

```python
{
    "name": "unity_undo_operation",
    "description": "Manage Unity Editor undo/redo history.",
    "inputSchema": schemas.undo_operation(),
},
{
    "name": "unity_compilation_pipeline",
    "description": "Query project assemblies, scripting defines, and code optimization.",
    "inputSchema": schemas.compilation_pipeline(),
},
{
    "name": "unity_prefab_overrides",
    "description": "List, apply, or revert prefab instance overrides.",
    "inputSchema": schemas.prefab_overrides(),
},
{
    "name": "unity_list_tests",
    "description": "Discover available tests without running them.",
    "inputSchema": schemas.list_tests(),
},
{
    "name": "unity_gameobject_utility",
    "description": "Find missing scripts, manage static flags, layers, and tags.",
    "inputSchema": schemas.gameobject_utility(),
},
```

New schema functions in `mcp/schemas.py`:

```python
def undo_operation() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["perform", "redo", "history", "clear", "group-name", "collapse"],
                "description": "Undo operation to perform",
            },
            "limit": {
                "type": "integer",
                "description": "Max history entries (for 'history' operation)",
                "default": 20,
            },
            "groupIndex": {
                "type": "integer",
                "description": "Undo group index to collapse from (for 'collapse' operation)",
            },
            "name": {
                "type": "string",
                "description": "Name for the collapsed undo group (for 'collapse' operation)",
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation"],
    }


def compilation_pipeline() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["assemblies", "defines", "which", "optimization"],
                "description": "Pipeline query to perform",
            },
            "assemblyName": {
                "type": "string",
                "description": "Assembly name (for 'defines' operation)",
            },
            "scriptPath": {
                "type": "string",
                "description": "Script asset path (for 'which' operation)",
            },
            "mode": {
                "type": "string",
                "enum": ["None", "Debug", "Release"],
                "description": "Optimization mode to set (for 'optimization' operation). None = not set / use project default.",
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation"],
    }


def prefab_overrides() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": [
                    "list", "apply", "revert",
                    "status", "find-instances", "unpack",
                ],
                "description": "Prefab override operation",
            },
            "instancePath": {
                "type": "string",
                "description": "Hierarchy path to prefab instance",
            },
            "assetPath": {
                "type": "string",
                "description": "Prefab asset path (for 'find-instances')",
            },
            "target": {
                "type": "string",
                "description": "Specific override to apply/revert (omit for all)",
            },
            "completely": {
                "type": "boolean",
                "description": "Fully unpack nested prefabs (for 'unpack')",
                "default": False,
            },
            "includeDefaultOverrides": {
                "type": "boolean",
                "description": "Include default overrides like position/rotation (for 'list')",
                "default": False,
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation"],
    }


def list_tests() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["tests", "categories", "assemblies"],
                "description": "What to list",
                "default": "tests",
            },
            "testPlatform": {
                "type": "string",
                "enum": ["EditMode", "PlayMode"],
                "description": "Test platform filter",
            },
            "filter": {
                "type": "string",
                "description": "Test name filter pattern",
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
    }


def gameobject_utility() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": [
                    "missing-scripts", "static-flags",
                    "set-static-flags", "set-layer", "set-tag",
                ],
                "description": "Utility operation",
            },
            "gameObjectPath": {
                "type": "string",
                "description": "Hierarchy path to target GameObject",
            },
            "fix": {
                "type": "boolean",
                "description": "Remove missing scripts (for 'missing-scripts')",
                "default": False,
            },
            "flags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Static flags to set",
            },
            "layer": {
                "type": "integer",
                "description": "Layer index (for 'set-layer')",
            },
            "tag": {
                "type": "string",
                "description": "Tag name (for 'set-tag')",
            },
            "recursive": {
                "type": "boolean",
                "description": "Apply to children, including inactive children (for 'set-layer')",
                "default": False,
            },
            "timeout": {
                "type": "number",
                "description": "Command timeout in seconds",
            },
        },
        "required": ["operation"],
    }
```

### Protocol Messages

All messages follow the existing envelope format defined in `BridgeModels.cs`:

```json
// Command envelope (Python -> Unity)
{
  "commandId": "<uuid>",
  "commandType": "<kebab-case-type>",
  "timestamp": "<ISO 8601>",
  "parametersJson": "<escaped JSON string>"
}

// Response envelope (Unity -> Python)
{
  "commandId": "<uuid>",
  "commandType": "<kebab-case-type>",
  "status": "success" | "error" | "running",
  "timestamp": "<ISO 8601>",
  "dataJson": "<escaped JSON string>",
  "errorMessage": "<string or null>"
}
```

#### 3.1 Undo Operation Messages

**Command type:** `undo-operation`

```json
// undo perform
{
  "commandId": "a1b2c3d4-...",
  "commandType": "undo-operation",
  "timestamp": "2026-03-19T10:00:00Z",
  "parametersJson": "{\"operation\":\"perform\"}"
}
// Response dataJson:
{"success": true, "undone": true, "groupName": "Set Transform.position"}

// undo redo
{"operation": "redo"}
// Response dataJson:
{"success": true, "redone": true, "groupName": "Set Transform.position"}

// undo history
// Full undo history enumeration is not supported by Unity's public API.
// Only the current undo group name and operations tracked since bridge
// initialization are available.
{"operation": "history", "limit": 20}
// Response dataJson:
{
  "success": true,
  "currentGroupName": "Set Transform.position",
  "recentOperations": [
    {"name": "Set Transform.position", "id": 42},
    {"name": "Add Component Rigidbody", "id": 41},
    {"name": "Delete GameObject Enemy", "id": 40}
  ],
  "count": 3,
  "note": "Only includes operations tracked since bridge initialization. Full undo history enumeration is not supported by Unity's public API."
}

// undo clear
// WARNING: Clears ALL undo history, including non-bridge operations.
// This affects the entire Editor undo stack, not just bridge operations.
{"operation": "clear"}
// Response dataJson:
{"success": true, "cleared": true, "warning": "All undo history has been cleared, including non-bridge operations."}

// undo group-name
{"operation": "group-name"}
// Response dataJson:
{"success": true, "groupName": ""}

// undo collapse
// Collapses all undo operations from the given group index into a single undo step.
// Useful for AI workflows making multiple changes that should be one undo step.
// Uses Undo.CollapseUndoOperations(groupIndex).
{"operation": "collapse", "groupIndex": 42, "name": "AI: Refactor PlayerController"}
// Response dataJson:
{"success": true, "collapsed": true, "groupIndex": 42, "name": "AI: Refactor PlayerController"}
```

#### 3.2 Compilation Pipeline Messages

**Command type:** `compilation-pipeline`

```json
// compile assemblies
{"operation": "assemblies"}
// Response dataJson:
{
  "success": true,
  "assemblies": [
    {
      "name": "Assembly-CSharp",
      "path": "Library/ScriptAssemblies/Assembly-CSharp.dll",
      "sourceFileCount": 147,
      "defines": ["UNITY_EDITOR", "UNITY_6000_0_OR_NEWER"],
      "references": ["UnityEngine", "UnityEditor"]
    },
    {
      "name": "Assembly-CSharp-Editor",
      "path": "Library/ScriptAssemblies/Assembly-CSharp-Editor.dll",
      "sourceFileCount": 23,
      "defines": ["UNITY_EDITOR"],
      "references": ["Assembly-CSharp", "UnityEngine", "UnityEditor"]
    }
  ]
}

// compile defines
{"operation": "defines", "assemblyName": "Assembly-CSharp"}
// Response dataJson:
{
  "success": true,
  "assembly": "Assembly-CSharp",
  "defines": ["UNITY_EDITOR", "UNITY_6000_0_OR_NEWER", "ENABLE_INPUT_SYSTEM"]
}

// compile which
{"operation": "which", "scriptPath": "Assets/Scripts/Player/PlayerController.cs"}
// Response dataJson:
{
  "success": true,
  "scriptPath": "Assets/Scripts/Player/PlayerController.cs",
  "assembly": "Assembly-CSharp",
  "assemblyPath": "Library/ScriptAssemblies/Assembly-CSharp.dll"
}

// compile optimization (get)
{"operation": "optimization"}
// Response dataJson:
{"success": true, "mode": "Debug", "changed": false}

// compile optimization (set)
{"operation": "optimization", "mode": "Release"}
// Response dataJson:
{"success": true, "mode": "Release", "changed": true}
```

#### 3.3 Prefab Override Messages

**Command type:** `prefab-override`

```json
// prefab overrides list
// hasOverrides uses includeDefaultOverrides: false by default, which excludes
// default overrides (position/rotation set during instantiation).
// Pass "includeDefaultOverrides": true to include them.
{"operation": "list", "instancePath": "Player", "includeDefaultOverrides": false}
// Response dataJson:
{
  "success": true,
  "hasOverrides": true,
  "count": 4,
  "overrides": [
    {
      "type": "PropertyModification",
      "objectPath": "Player",
      "componentType": "Transform",
      "propertyPath": "m_LocalPosition.x",
      "originalValue": "0",
      "currentValue": "5.2"
    },
    {
      "type": "AddedComponent",
      "objectPath": "Player",
      "componentType": "AudioSource",
      "details": "Added AudioSource component"
    },
    {
      "type": "RemovedComponent",
      "objectPath": "Player/OldCollider",
      "componentType": "BoxCollider",
      "details": "Removed BoxCollider component"
    },
    {
      "type": "AddedGameObject",
      "objectPath": "Player/NewChild",
      "details": "Added child GameObject"
    }
  ]
}

// prefab overrides apply (all)
{"operation": "apply", "instancePath": "Player"}
// Response dataJson:
{"success": true, "applied": true, "count": 4}

// prefab overrides apply (specific)
{"operation": "apply", "instancePath": "Player", "target": "PropertyModification:Transform"}
// Response dataJson:
{"success": true, "applied": true, "count": 1}

// prefab overrides revert (all)
// Uses InteractionMode.AutomatedAction (single-param RevertPrefabInstance is obsolete in Unity 6)
{"operation": "revert", "instancePath": "Player"}
// Response dataJson:
{"success": true, "reverted": true, "count": 4}

// prefab status
{"operation": "status", "instancePath": "Player"}
// Response dataJson:
// prefabType uses PrefabAssetType values: NotAPrefab, Regular, Model, Variant, MissingAsset
// instanceStatus uses PrefabInstanceStatus values: NotAPrefab, Connected, MissingAsset
{
  "success": true,
  "prefabType": "Regular",
  "instanceStatus": "Connected",
  "assetPath": "Assets/Prefabs/Player.prefab",
  "isVariant": false,
  "isPartOfPrefab": true
}

// prefab find-instances
// NOTE: Does not include nested prefab instances. Only root-level instances
// of this prefab are returned (uses PrefabUtility.FindAllInstancesOfPrefab
// which only finds top-level instances in loaded scenes).
{"operation": "find-instances", "assetPath": "Assets/Prefabs/Enemy.prefab"}
// Response dataJson:
{
  "success": true,
  "instances": [
    {"path": "Enemy (1)", "scene": "Assets/Scenes/Level1.unity", "hasOverrides": true},
    {"path": "Spawner/Enemy (2)", "scene": "Assets/Scenes/Level1.unity", "hasOverrides": false}
  ],
  "count": 2
}

// prefab unpack
{"operation": "unpack", "instancePath": "Player", "completely": false}
// Response dataJson:
{"success": true, "unpacked": true, "mode": "OutermostRoot"}

// prefab unpack completely
{"operation": "unpack", "instancePath": "Player", "completely": true}
// Response dataJson:
{"success": true, "unpacked": true, "mode": "Completely"}
```

#### 3.4 Test Listing Messages

**Command type:** `list-tests`

```json
// list tests
{"mode": "tests", "testPlatform": "EditMode", "filter": "Combat*"}
// Response dataJson:
{
  "success": true,
  "tests": [
    {
      "fullName": "Tests.Combat.CombatControllerTests.AttackDealsDamage",
      "className": "CombatControllerTests",
      "methodName": "AttackDealsDamage",
      "categories": ["Combat", "Unit"],
      "assembly": "Assembly-CSharp-Editor-Tests"
    },
    {
      "fullName": "Tests.Combat.CombatControllerTests.BlockReducesDamage",
      "className": "CombatControllerTests",
      "methodName": "BlockReducesDamage",
      "categories": ["Combat", "Unit"],
      "assembly": "Assembly-CSharp-Editor-Tests"
    }
  ],
  "count": 2
}

// list categories
{"mode": "categories", "testPlatform": "EditMode"}
// Response dataJson:
{
  "success": true,
  "categories": ["Combat", "Unit", "Integration", "Movement", "AI"]
}

// list assemblies
{"mode": "assemblies", "testPlatform": "EditMode"}
// Response dataJson:
{
  "success": true,
  "assemblies": [
    {"name": "Assembly-CSharp-Editor-Tests", "testCount": 47},
    {"name": "MyGame.Tests", "testCount": 12}
  ]
}
```

#### 3.5 GameObject Utility Messages

**Command type:** `gameobject-utility`

```json
// missing-scripts (find only)
{"operation": "missing-scripts", "fix": false}
// Response dataJson:
{
  "success": true,
  "found": [
    {"path": "Environment/BrokenLight", "count": 1},
    {"path": "UI/OldPanel", "count": 2}
  ],
  "totalCount": 3,
  "removed": 0
}

// missing-scripts (find and fix)
{"operation": "missing-scripts", "fix": true}
// Response dataJson:
{
  "success": true,
  "found": [
    {"path": "Environment/BrokenLight", "count": 1},
    {"path": "UI/OldPanel", "count": 2}
  ],
  "totalCount": 3,
  "removed": 3
}

// static-flags (get)
{"operation": "static-flags", "gameObjectPath": "Environment/Building"}
// Response dataJson:
{
  "success": true,
  "path": "Environment/Building",
  "flags": ["BatchingStatic", "OccluderStatic", "OccludeeStatic"],
  "rawValue": 14
}

// set-static-flags
{
  "operation": "set-static-flags",
  "gameObjectPath": "Environment/Building",
  "flags": ["BatchingStatic", "NavigationStatic", "OccluderStatic"]
}
// Response dataJson:
{
  "success": true,
  "path": "Environment/Building",
  "flags": ["BatchingStatic", "NavigationStatic", "OccluderStatic"],
  "changed": true
}

// set-layer
{
  "operation": "set-layer",
  "gameObjectPath": "Player",
  "layer": 8,
  "recursive": true
}
// Response dataJson:
{"success": true, "path": "Player", "layer": 8, "affectedCount": 5}

// set-tag
{
  "operation": "set-tag",
  "gameObjectPath": "Player",
  "tag": "Player"
}
// Response dataJson:
{"success": true, "path": "Player", "tag": "Player", "changed": true}
```

---

## 4. Implementation Details

### 4.1 Undo Integration Strategy

This is the most consequential design decision in Phase 2. The question: should existing
mutating handlers (`set-component-data`, `prefab-operation`, `gameobject-operation`,
`add-component`, `material-operation`, `scene-operation`) automatically wrap their
mutations in `Undo.RecordObject()` calls?

**Recommendation: Retrofit existing handlers with always-on undo recording.**

Rationale:

1. **User expectation.** When an AI tool modifies a scene, the developer expects Ctrl+Z to
   work. Silently making non-undoable changes is a data-loss risk.

2. **Performance impact is negligible.** `Undo.RecordObject()` records a serialized
   snapshot of the target object. For the small, targeted mutations the bridge performs
   (setting a few fields, adding one component), the overhead is measured in microseconds.
   The file I/O for the bridge protocol itself dwarfs undo recording cost.

3. **Implementation is straightforward.** Each mutating handler needs 1-3 lines added
   before the mutation. No architectural change.

4. **An `--undoable` flag adds complexity without benefit.** It would require threading an
   extra parameter through every mutating command, and the default "not undoable" behavior
   would surprise users. The flag inverts the expected default.

**Implementation plan for undo retrofitting:**

For each existing mutating handler, add `Undo.RecordObject()` before the mutation and
use `Undo.SetCurrentGroupName()` with a descriptive label:

```csharp
// In SetComponentDataCommandHandler.Execute(), before the foreach loop:
Undo.SetCurrentGroupName($"Bridge: Set {parameters.componentType} on {parameters.gameObjectPath}");
Undo.RecordObject(component, $"Set {parameters.componentType}");

// After all mutations:
// (EditorUtility.SetDirty is already called; no additional change needed)
```

**Handlers to retrofit:**

| Handler | Undo Call Site | Group Name Pattern |
|---------|--------------|-------------------|
| `SetComponentDataCommandHandler` | Before field loop | `Bridge: Set {componentType} on {path}` |
| `AddComponentCommandHandler` | Before `AddComponent()` | `Bridge: Add {componentType} to {path}` |
| `GameObjectOperationCommandHandler` | Before create/delete/rename | `Bridge: {operation} {name}` |
| `PrefabOperationCommandHandler` | Before create/instantiate/apply/revert | `Bridge: Prefab {operation} {path}` |
| `MaterialOperationCommandHandler` | Before property changes | `Bridge: Material {operation} {path}` |
| `SceneOperationCommandHandler` | Before scene modifications | `Bridge: Scene {operation}` |

For handlers using `Undo.AddComponent()` and `Undo.DestroyObjectImmediate()`, replace
the direct Unity API calls with their Undo-aware equivalents:

```csharp
// Before (AddComponentCommandHandler):
gameObject.AddComponent(componentType);

// After:
Undo.AddComponent(gameObject, componentType);
```

```csharp
// Before (GameObjectOperationCommandHandler, delete):
Object.DestroyImmediate(gameObject);

// After:
Undo.DestroyObjectImmediate(gameObject);
```

**New undo-aware operations in Phase 2 handlers:**

All new Phase 2 handlers that mutate state will use undo recording from the start:
- `PrefabOverrideCommandHandler` (apply, revert, unpack)
- `GameObjectUtilityCommandHandler` (missing-scripts --fix, set-static-flags, set-layer, set-tag)

### 4.2 New Bridge Command Types

Added to `core/protocol.py` `TIMEOUT_DEFAULTS`:

```python
# Quick operations (read-only or instant)
"undo-operation": 5,
"list-tests": 30,
"compilation-pipeline": 15,
"gameobject-utility": 15,

# Medium operations (mutating)
"prefab-override": 30,
```

Added to `PARALLEL_SAFE_COMMANDS`:

```python
"list-tests",
```

Note: `compilation-pipeline` is NOT parallel-safe because the `optimization` operation
with a `mode` parameter is a write operation. While other operations (assemblies, defines,
which) are read-only, the command type as a whole cannot be classified as parallel-safe
since parallel execution could race on the optimization mode setter.

### 4.3 Error Handling

All new handlers follow the existing error pattern:

| Condition | Response | Exit Code |
|-----------|----------|-----------|
| Missing required parameter | `BridgeResponse.Error(...)` with message | 3 (invalid input) |
| GameObject not found | `BridgeResponse.Error(...)` with path | 1 (command failure) |
| Not a prefab instance | `BridgeResponse.Error(...)` with context | 1 |
| Assembly not found | `BridgeResponse.Error(...)` with name | 1 |
| No assembly for script | `BridgeResponse.Error(...)` with script path | 1 |
| No undo history | `BridgeResponse.Success(...)` with `undone: false` | 0 |
| Test retrieval timeout | `BridgeResponse.Error(...)` with timeout info | 4 (timeout) |
| `EditorApplication.isCompiling` | `BridgeResponse.Error(...)` "Cannot execute while scripts are compiling." | 2 |
| `EditorApplication.isPlaying` (undo/mutating ops) | `BridgeResponse.Error(...)` "Not supported during play mode." | 1 |
| `Undo.isProcessing` (undo perform/redo) | `BridgeResponse.Error(...)` "Undo operation already in progress." | 1 |

Design principle: operations that "do nothing" (e.g., undo when history is empty) return
success with a flag indicating nothing happened, rather than an error. Only genuinely
invalid operations (bad paths, missing objects) return errors.

**Guard patterns applied to all Phase 2 handlers:**

- `EditorApplication.isCompiling` — checked at the top of `Execute()` for handlers that
  query compilation state or require stable assemblies (`compilation-pipeline`,
  `list-tests`). Returns error "Cannot execute while scripts are compiling."
- `EditorApplication.isPlaying` — checked for all mutating undo operations (`perform`,
  `redo`, `clear`, `collapse`) and test tree retrieval. Play mode undo is not supported
  by `UnityEditor.Undo`.
- `Undo.isProcessing` — checked for `undo perform` and `undo redo` to prevent re-entrant
  undo operations.
- `set-layer --recursive` affects all children including inactive GameObjects, using
  `GetComponentsInChildren<Transform>(true)` to traverse the full hierarchy.

---

## 5. C# Implementation Notes

### 5.1 New Files Needed

All files go in `ClaudeCodeBridge/` with corresponding `.meta` files.

#### UndoCommandHandler.cs (~120 LOC)

```csharp
using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    public class UndoCommandHandler : ICommandHandler
    {
        public string CommandType => "undo-operation";

        public BridgeResponse Execute(BridgeCommand command)
        {
            var parameters = JsonUtility.FromJson<UndoOperationParams>(command.parametersJson ?? "{}");

            // Guard: undo/redo operations cannot run during play mode
            if (EditorApplication.isPlaying && parameters.operation is "perform" or "redo" or "clear" or "collapse")
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "Undo operations are not supported during play mode.");

            // Guard: prevent re-entrant undo operations
            if (Undo.isProcessing && parameters.operation is "perform" or "redo")
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "Undo operation already in progress.");

            switch (parameters.operation)
            {
                case "perform":   return PerformUndo(command);
                case "redo":      return PerformRedo(command);
                case "history":   return GetHistory(command, parameters.limit);
                case "clear":     return ClearHistory(command);
                case "group-name": return GetGroupName(command);
                case "collapse":  return CollapseOperations(command, parameters.groupIndex, parameters.name);
                default:
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        $"Unknown operation: {parameters.operation}");
            }
        }
        // ... operation methods
    }

    [Serializable]
    public class UndoOperationParams
    {
        public string operation;
        public int limit = 20;
        public int groupIndex;
        public string name;
    }
}
```

Key implementation detail for `GetHistory`: Full undo history enumeration is **not
supported** by Unity's public API. `Undo.GetCurrentGroupName()` returns only the current
group name. The `Edit > Undo History` window uses internal APIs.

**Design decision (downscoped):** The `undo history` command returns only:
1. The current undo group name via `Undo.GetCurrentGroupName()`
2. Recent operations tracked since bridge initialization via `Undo.undoRedoPerformed` hook

```csharp
private static List<UndoGroupInfo> _recentOperations = new(100);

[InitializeOnLoadMethod]
private static void InitUndoTracking()
{
    Undo.undoRedoPerformed += () =>
    {
        var name = Undo.GetCurrentGroupName();
        if (_recentOperations.Count >= 100)
            _recentOperations.RemoveAt(0);
        _recentOperations.Add(new UndoGroupInfo { name = name, id = Undo.GetCurrentGroup() });
    };
}

private BridgeResponse GetHistory(BridgeCommand command, int limit)
{
    var currentName = Undo.GetCurrentGroupName();
    var recent = _recentOperations.TakeLast(Math.Min(limit, _recentOperations.Count)).ToList();
    // Return currentGroupName + recentOperations
}
```

> **Limitation:** Full undo history enumeration is not supported by Unity's public API.
> Only the current undo group name and operations tracked since bridge initialization
> are available. The rolling log is capped at 100 entries.

#### CompilationPipelineCommandHandler.cs (~150 LOC)

```csharp
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.Compilation;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    public class CompilationPipelineCommandHandler : ICommandHandler
    {
        public string CommandType => "compilation-pipeline";

        public BridgeResponse Execute(BridgeCommand command)
        {
            if (EditorApplication.isCompiling)
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "Cannot query compilation pipeline while scripts are compiling.");

            var parameters = JsonUtility.FromJson<CompilationPipelineParams>(
                command.parametersJson ?? "{}");

            switch (parameters.operation)
            {
                case "assemblies":    return GetAssemblies(command);
                case "defines":       return GetDefines(command, parameters.assemblyName);
                case "which":         return WhichAssembly(command, parameters.scriptPath);
                case "optimization":  return HandleOptimization(command, parameters.mode);
                default:
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        $"Unknown operation: {parameters.operation}");
            }
        }

        private BridgeResponse GetAssemblies(BridgeCommand command)
        {
            var assemblies = CompilationPipeline.GetAssemblies(AssembliesType.PlayerWithoutTestAssemblies);
            // Also get editor assemblies
            var editorAssemblies = CompilationPipeline.GetAssemblies(AssembliesType.Editor);
            var all = assemblies.Concat(editorAssemblies);
            // Serialize and return
        }

        private BridgeResponse GetDefines(BridgeCommand command, string assemblyName)
        {
            var defines = CompilationPipeline.GetDefinesFromAssemblyName(assemblyName);
            // GetDefinesFromAssemblyName can return null if assembly not found
            if (defines is null)
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Assembly not found: {assemblyName}");
            // Serialize and return
        }

        private BridgeResponse WhichAssembly(BridgeCommand command, string scriptPath)
        {
            var assemblyName = CompilationPipeline.GetAssemblyNameFromScriptPath(scriptPath);
            // GetAssemblyNameFromScriptPath can return null if no assembly owns the script
            if (string.IsNullOrEmpty(assemblyName))
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"No assembly found for script: {scriptPath}");
            // Serialize and return
        }

        private BridgeResponse HandleOptimization(BridgeCommand command, string mode)
        {
            if (string.IsNullOrEmpty(mode))
            {
                // Get current
                var current = CompilationPipeline.codeOptimization;
                // Return current mode
            }
            else
            {
                // Set mode (None = not set / use project default)
                var newMode = mode switch
                {
                    "Release" => CodeOptimization.Release,
                    "Debug" => CodeOptimization.Debug,
                    "None" => CodeOptimization.None,
                    _ => CodeOptimization.None,
                };
                CompilationPipeline.codeOptimization = newMode;
                // Return new mode with changed=true
            }
        }
    }

    [Serializable]
    public class CompilationPipelineParams
    {
        public string operation;
        public string assemblyName;
        public string scriptPath;
        public string mode;
    }
}
```

#### PrefabOverrideCommandHandler.cs (~250 LOC)

This handler is separate from the existing `PrefabOperationCommandHandler` to maintain
single-responsibility and stay under 500 LOC per file.

```csharp
namespace BWS.Editor.ClaudeCodeBridge
{
    public class PrefabOverrideCommandHandler : ICommandHandler
    {
        public string CommandType => "prefab-override";
        // Routes: list, apply, revert, status, find-instances, unpack
    }
}
```

### 5.2 Prefab Override Serialization Format

Override types map to the `PrefabUtility` API as follows:

| Override Type | Unity API | Serialized `type` Field |
|--------------|-----------|------------------------|
| Property modification | `PrefabUtility.GetPropertyModifications()` | `"PropertyModification"` |
| Added component | `PrefabUtility.GetAddedComponents()` | `"AddedComponent"` |
| Removed component | `PrefabUtility.GetRemovedComponents()` | `"RemovedComponent"` |
| Added GameObject | `PrefabUtility.GetAddedGameObjects()` | `"AddedGameObject"` |

For `list` operation, each override includes:

```csharp
[Serializable]
public class PrefabOverrideInfo
{
    public string type;           // "PropertyModification", "AddedComponent", etc.
    public string objectPath;     // Path within the prefab hierarchy
    public string componentType;  // Component type name (if applicable)
    public string propertyPath;   // SerializedProperty path (for PropertyModification)
    public string originalValue;  // Original value from prefab asset
    public string currentValue;   // Current value on instance
    public string details;        // Human-readable summary
}
```

For targeted apply/revert, the `target` parameter accepts these formats:
- `"PropertyModification:Transform"` — all property modifications on Transform
- `"AddedComponent:AudioSource"` — specific added component
- `"RemovedComponent:BoxCollider"` — specific removed component
- `"AddedGameObject:NewChild"` — specific added GameObject

Apply uses `PrefabUtility.ApplyPropertyOverride()`, `ApplyAddedComponent()`,
`ApplyRemovedComponent()`, or `ApplyAddedGameObject()` with
`InteractionMode.AutomatedAction`.

Revert uses `PrefabUtility.RevertPropertyOverride()`, `RevertAddedComponent()`,
`RevertRemovedComponent()`, or `RevertAddedGameObject()` with
`InteractionMode.AutomatedAction`.

> **Unity 6 Note:** The single-parameter overload `RevertPrefabInstance(GameObject)` is
> obsolete. ALL apply and revert calls MUST explicitly pass `InteractionMode.AutomatedAction`
> as the second parameter. For whole-instance revert, use:
> `PrefabUtility.RevertPrefabInstance(go, InteractionMode.AutomatedAction)`

### 5.3 Test Tree Retrieval Pattern

`TestRunnerApi.RetrieveTestTree()` uses a direct `Action<ITestAdaptor>` callback, NOT the
`ICallbacks` interface pattern. The `RetrieveTestList` method is **obsolete** in Unity 6
and must not be used.

```csharp
public class TestListCommandHandler : ICommandHandler
{
    public string CommandType => "list-tests";

    private static Dictionary<string, TestListContext> _activeRequests = new();

    public BridgeResponse Execute(BridgeCommand command)
    {
        if (EditorApplication.isCompiling)
            return BridgeResponse.Error(command.commandId, command.commandType,
                "Cannot retrieve test tree while scripts are compiling.");

        if (EditorApplication.isPlaying)
            return BridgeResponse.Error(command.commandId, command.commandType,
                "Cannot retrieve test tree during play mode.");

        var parameters = JsonUtility.FromJson<ListTestsParams>(command.parametersJson ?? "{}");
        var testRunnerApi = ScriptableObject.CreateInstance<TestRunnerApi>();

        var filter = new Filter { testMode = ParseTestMode(parameters.testPlatform) };
        if (!string.IsNullOrEmpty(parameters.filter))
            filter.testNames = new[] { parameters.filter };

        _activeRequests[command.commandId] = new TestListContext
        {
            CommandId = command.commandId,
            Api = testRunnerApi,
        };

        // RetrieveTestTree uses a direct Action<ITestAdaptor> callback,
        // NOT the ICallbacks interface used by Execute().
        testRunnerApi.RetrieveTestTree(
            ParseTestMode(parameters.testPlatform),
            (ITestAdaptor testTree) =>
            {
                var tests = FlattenTestTree(testTree);
                ClaudeUnityBridge.WriteResponseStatic(
                    BridgeResponse.Success(command.commandId, "list-tests",
                        JsonUtility.ToJson(result))
                );
                _activeRequests.Remove(command.commandId);
            }
        );

        return BridgeResponse.Running(command.commandId, command.commandType,
            "{\"success\":true,\"message\":\"Retrieving test tree...\"}");
    }
}
```

Key differences from `Execute()` + `ICallbacks`:
- `RetrieveTestTree()` takes a `TestMode` enum and an `Action<ITestAdaptor>` callback directly
- No `ICallbacks` registration is needed
- The callback receives the root `ITestAdaptor` node representing the test tree
- The tree is walked recursively; leaf nodes (where `IsSuite == false`) are individual test methods
- The `RetrieveTestList` method is obsolete in Unity 6 and should not be used

### 5.4 Missing Script Detection Approach

```csharp
private BridgeResponse HandleMissingScripts(BridgeCommand command, bool fix)
{
    var allObjects = Resources.FindObjectsOfTypeAll<GameObject>();
    var results = new List<MissingScriptInfo>();
    int totalRemoved = 0;

    foreach (var go in allObjects)
    {
        // Skip assets (only process scene objects)
        if (EditorUtility.IsPersistent(go)) continue;

        int missingCount = GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(go);
        if (missingCount > 0)
        {
            results.Add(new MissingScriptInfo
            {
                path = GetGameObjectPath(go),
                count = missingCount
            });

            if (fix)
            {
                Undo.SetCurrentGroupName($"Bridge: Remove missing scripts from {go.name}");
                Undo.RegisterCompleteObjectUndo(go, "Remove Missing Scripts");
                int removed = GameObjectUtility.RemoveMonoBehavioursWithMissingScript(go);
                totalRemoved += removed;
            }
        }
    }

    // Serialize and return
}
```

### 5.5 Handler Registration

Add to `ClaudeUnityBridge.Initialize()`:

```csharp
// Phase 2 handlers
RegisterHandler(new UndoCommandHandler());
RegisterHandler(new CompilationPipelineCommandHandler());
RegisterHandler(new PrefabOverrideCommandHandler());
RegisterHandler(new TestListCommandHandler());
RegisterHandler(new GameObjectUtilityCommandHandler());
```

### 5.6 BridgeModels.cs Additions

New parameter and result classes (add at end of file within the namespace):

```csharp
#region Undo Operation

[Serializable]
public class UndoOperationParams
{
    public string operation;
    public int limit = 20;
    public int groupIndex;
    public string name;
}

[Serializable]
public class UndoOperationResult
{
    public bool success;
    public bool undone;
    public bool redone;
    public bool cleared;
    public bool collapsed;
    public string groupName;
    public string currentGroupName;
    public List<UndoGroupInfo> recentOperations = new List<UndoGroupInfo>();
    public int count;
    public int groupIndex;
    public string name;
    public string warning;
    public string note;
}

[Serializable]
public class UndoGroupInfo
{
    public string name;
    public int id;
}

#endregion

#region Compilation Pipeline

[Serializable]
public class CompilationPipelineParams
{
    public string operation;
    public string assemblyName;
    public string scriptPath;
    public string mode;
}

[Serializable]
public class CompilationPipelineResult
{
    public bool success;
    public List<AssemblyInfo> assemblies = new List<AssemblyInfo>();
    public string assembly;
    public string assemblyPath;
    public string scriptPath;
    public List<string> defines = new List<string>();
    public string mode;
    public bool changed;
}

[Serializable]
public class AssemblyInfo
{
    public string name;
    public string path;
    public int sourceFileCount;
    public List<string> defines = new List<string>();
    public List<string> references = new List<string>();
}

#endregion

#region Prefab Override

[Serializable]
public class PrefabOverrideParams
{
    public string operation;
    public string instancePath;
    public string assetPath;
    public string target;
    public bool completely = false;
    public bool includeDefaultOverrides = false;
}

[Serializable]
public class PrefabOverrideResult
{
    public bool success;
    public string operation;
    public bool hasOverrides;
    public int count;
    public List<PrefabOverrideInfo> overrides = new List<PrefabOverrideInfo>();
    public bool applied;
    public bool reverted;
    public bool unpacked;
    public string mode;
    public string prefabType;      // PrefabAssetType: NotAPrefab, Regular, Model, Variant, MissingAsset
    public string instanceStatus;  // PrefabInstanceStatus: NotAPrefab, Connected, MissingAsset
    public string assetPath;
    public bool isVariant;
    public bool isPartOfPrefab;
    public string path;
    public List<PrefabInstanceInfo> instances = new List<PrefabInstanceInfo>();
}

[Serializable]
public class PrefabOverrideInfo
{
    public string type;
    public string objectPath;
    public string componentType;
    public string propertyPath;
    public string originalValue;
    public string currentValue;
    public string details;
}

[Serializable]
public class PrefabInstanceInfo
{
    public string path;
    public string scene;
    public bool hasOverrides;
}

#endregion

#region Test Listing

[Serializable]
public class ListTestsParams
{
    public string mode = "tests";
    public string testPlatform;
    public string filter;
}

[Serializable]
public class ListTestsResult
{
    public bool success;
    public List<TestInfo> tests = new List<TestInfo>();
    public List<string> categories = new List<string>();
    public List<TestAssemblyInfo> assemblies = new List<TestAssemblyInfo>();
    public int count;
}

[Serializable]
public class TestInfo
{
    public string fullName;
    public string className;
    public string methodName;
    public List<string> categories = new List<string>();
    public string assembly;
}

[Serializable]
public class TestAssemblyInfo
{
    public string name;
    public int testCount;
}

#endregion

#region GameObject Utility

[Serializable]
public class GameObjectUtilityParams
{
    public string operation;
    public string gameObjectPath;
    public bool fix = false;
    public List<string> flags = new List<string>();
    public int layer;
    public string tag;
    public bool recursive = false;
}

[Serializable]
public class GameObjectUtilityResult
{
    public bool success;
    public string operation;
    public string path;
    public List<MissingScriptInfo> found = new List<MissingScriptInfo>();
    public int totalCount;
    public int removed;
    public List<string> flags = new List<string>();
    public int rawValue;
    public int layer;
    public string tag;
    public int affectedCount;
    public bool changed;
}

[Serializable]
public class MissingScriptInfo
{
    public string path;
    public int count;
}

#endregion
```

---

## 6. Testing Strategy

### Unit Tests (Python)

New test files in `tests/unit/`:

| File | Covers |
|------|--------|
| `test_undo.py` | All 6 undo subcommands (perform, redo, history, clear, group-name, collapse) |
| `test_compile_extended.py` | All 4 compilation pipeline subcommands |
| `test_prefab_overrides.py` | All 6 prefab override/status/find/unpack commands |
| `test_test_listing.py` | All 3 test list modes |
| `test_hierarchy_utilities.py` | All 5 hierarchy utility commands |

Each test mocks `DirectBridge.send_command_with_retry` and verifies:
1. Correct `command_type` is sent
2. Correct `parameters` dict (camelCase keys) is constructed
3. Return value is a `CommandResult`
4. Optional parameters have correct defaults

Example test pattern:

```python
async def test_undo_perform(mock_bridge):
    mock_bridge.send_command_with_retry.return_value = CommandResult(
        success=True,
        data={"undone": True, "groupName": "Set Transform.position"},
    )
    result = await undo_perform(mock_bridge)
    assert result.success
    mock_bridge.send_command_with_retry.assert_called_once_with(
        command_type="undo-operation",
        parameters={"operation": "perform"},
        timeout=5.0,
    )
```

### MCP Schema Tests

Verify each new schema function returns valid JSON Schema:
- All required fields are present
- Enum values are correct
- Default values match expected types

### Integration Tests

Marked `@pytest.mark.integration`, require Unity running:

| Test | Validates |
|------|-----------|
| `test_undo_roundtrip` | Modify component, undo, verify reverted |
| `test_compile_assemblies` | Returns at least `Assembly-CSharp` |
| `test_prefab_overrides_list` | Create override, list, verify present |
| `test_list_tests` | Returns non-empty test list for EditMode |
| `test_missing_scripts_scan` | Scan returns without error |

### Coverage Targets

- `commands/undo.py`: 90%+
- `commands/compile.py`: 90%+
- `commands/prefab.py` (new functions): 85%+
- `commands/testing.py` (new functions): 85%+
- `commands/hierarchy.py` (new functions): 85%+
- `mcp/schemas.py` (new functions): 100%

---

## 7. Migration & Compatibility

### Impact on Existing Commands

#### Undo Retrofitting (Breaking Behavior Change)

Adding `Undo.RecordObject()` to existing handlers changes their behavior: mutations
that were previously not undoable become undoable. This is a **positive breaking change**
but should be documented.

**Migration notes:**
- No wire protocol changes. Command/response JSON format is identical.
- No Python-side changes needed for undo retrofitting (C# only).
- Existing MCP clients continue to work without modification.
- The undo history will now show bridge operations, which may surprise users who
  previously saw a clean undo stack.

#### Existing `prefab-operation` Command

The new `prefab-override` command type is **separate** from the existing
`prefab-operation`. They coexist:

- `prefab-operation`: create, instantiate, apply (whole prefab), revert (whole prefab),
  get-info
- `prefab-override`: granular override list/apply/revert, status, find-instances, unpack

The existing `prefab-operation` apply/revert operations remain for whole-prefab
apply/revert. The new `prefab-override` adds granular per-override control.

#### Existing `compile` Command

The new `compilation-pipeline` command type is separate from the existing `compile`
command. They coexist:

- `compile`: Trigger script compilation, wait for completion, collect errors/warnings
- `compilation-pipeline`: Query assembly structure, defines, ownership, optimization mode

#### Existing `run-tests` Command

The new `list-tests` command type is separate from `run-tests`. They coexist:

- `run-tests`: Execute tests and return results
- `list-tests`: Discover tests without executing

#### Existing `query-hierarchy` and Hierarchy Commands

New hierarchy utility operations use a separate `gameobject-utility` command type:

- `query-hierarchy`: Read-only tree traversal (unchanged)
- `gameobject-utility`: Missing scripts, static flags, layer/tag management

### Version Compatibility

- **Unity:** Requires Unity 2021.3+ for `CompilationPipeline.GetAssemblies()`,
  `PrefabUtility.GetAddedComponents()`, `GameObjectUtility.GetMonoBehavioursWithMissingScriptCount()`.
  All APIs are stable since Unity 2021 LTS.
- **Python:** No new dependencies. Uses existing `DirectBridge` infrastructure.
- **MCP:** New tools are additive. Existing 30 tools unchanged (26 Phase 0 + 4 Phase 1).
  Phase 2 adds 5 new tools. Cumulative total: 35 tools.

---

## 8. Risks & Open Questions

### Open Questions

1. **Undo history depth.** Resolved: downscoped to current group name + bridge-tracked
   operations via `Undo.undoRedoPerformed` hook (see Section 5.1). Full history enumeration
   is not supported by Unity's public API.

2. **Test tree callback timing.** `RetrieveTestTree()` is asynchronous. If the test
   framework is not initialized, it may return an empty list. Should we add a retry or
   wait mechanism? **Recommendation:** Return what we get; document that Unity may need
   a moment after domain reload.

3. **Compilation pipeline `which` for non-asmdef projects.** In projects without assembly
   definitions, all scripts belong to `Assembly-CSharp`. The `which` command is still
   useful for projects with asmdef files. Should we add a note in the response when the
   project has no custom assembly definitions? **Recommendation:** Yes, include an
   `hasCustomAssemblies` flag in the `assemblies` response.

4. **Prefab override target format.** The proposed `"PropertyModification:Transform"`
   format is concise but may be ambiguous if multiple components of the same type exist.
   Alternative: `"PropertyModification:Transform:m_LocalPosition.x"` for full specificity.
   **Recommendation:** Support both — short form for bulk operations, long form for
   precision.

5. **Static flags enum validation.** Should the C# handler validate flag names against
   the `StaticEditorFlags` enum, or accept raw integer values too?
   **Recommendation:** Accept both. Named flags for usability, raw int for automation.

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Undo retrofit breaks existing workflows | Low | Medium | Undo recording is additive; test existing integration tests after retrofit |
| `RetrieveTestTree` callback not invoked on malformed test assemblies | Low | High | Implement timeout; if callback not received within timeout, return error |
| `BridgeModels.cs` exceeds 500 LOC with new models | High | Low | Split into `BridgeModels.cs` and `BridgeModelsPhase2.cs`; both in same namespace |
| Undo history logging adds memory pressure | Low | Low | Cap rolling log at 100 entries; oldest entries evicted |
| `CompilationPipeline.GetAssemblies()` slow on large projects | Medium | Low | Cache assembly list; invalidate on `compilationFinished` event |

### Implementation Order

Recommended sequence (each step is independently shippable):

1. **Undo retrofitting** — Modify existing handlers. Run full integration test suite.
2. **Undo command handler** — New `undo-operation` command + Python module + MCP tool.
3. **Compilation pipeline** — New `compilation-pipeline` command (read-only, low risk).
4. **Test listing** — New `list-tests` command (read-only, follows existing test runner pattern).
5. **GameObject utilities** — New `gameobject-utility` command (mix of read and write).
6. **Prefab overrides** — New `prefab-override` command (most complex, depends on understanding existing prefab handler).

Each step includes: C# handler, Python command module, MCP schema + tool registration,
unit tests, and protocol.py timeout entry.
