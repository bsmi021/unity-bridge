# Tech Spec: Phase 1 - Core Platform APIs

**Status:** Draft (Revised)
**Author:** Claude Code
**Last Updated:** 2026-03-19
**Version:** 0.2.0

---

## 1. Overview

### Problem Statement

The unity-bridge currently provides 26 MCP tools covering scene manipulation, hierarchy
inspection, testing, and build automation. However, several foundational Unity Editor APIs
remain inaccessible:

1. **No Package Manager access.** Adding, removing, or querying UPM packages requires
   manual Unity Editor interaction or batch-mode CLI scripts.
2. **No Build Profile support.** Unity 6 replaced the legacy Build Settings window with
   Build Profiles, but the bridge has no awareness of this system.
3. **Limited AssetDatabase coverage.** The current `asset-operation` handler supports find,
   import, refresh, get-dependencies, and get-info, but lacks create, delete, copy, move,
   GUID conversion, folder management, and package export/import.
4. **No Player Settings access.** Scripting defines, product name, version, and other
   PlayerSettings values cannot be read or modified through the bridge.

These gaps force developers to leave the CLI/MCP workflow for routine project configuration
tasks, breaking automation continuity.

### Goals

- **G1:** Add 4 new command groups (package, build profile, asset extended, settings) with
  full CLI, MCP, and C# handler implementations.
- **G2:** Maintain the dual-interface pattern -- all new functionality exposed through both
  CLI and MCP with zero logic duplication.
- **G3:** Handle async Unity APIs correctly (PackageManager polling, recompilation waits).
- **G4:** Keep all source files under 500 LOC and all functions under 50 LOC.
- **G5:** Provide unit tests with mocked bridge for all new Python command modules.
- **G6:** Add 4 new MCP tools, bringing the total from 26 to 30.

### Non-Goals

- Modifying the file-based communication protocol (JSON files in `.claude/unity/`).
- Supporting Unity versions below Unity 6 (2022.x LTS or earlier).
- Providing a GUI or REST API for the new commands.
- Implementing ScopedRegistry or custom registry support for Package Manager.
- Implementing every PlayerSettings field -- only the most commonly automated subset.

---

## 2. Command Reference

### Command Tree

```
unity-bridge
|
+-- package                          # NEW: Unity Package Manager
|   +-- list                         # List installed packages
|   +-- search <query>               # Search by package ID/name (not free-text)
|   +-- search --all                 # Discover all available packages
|   +-- add <identifier>             # Add package (name@version or git URL)
|   +-- remove <name>                # Remove package
|   +-- info <name>                  # Detailed package info
|   +-- embed <name>                 # Embed package for local editing
|   +-- resolve                      # Force package dependency resolution
|
+-- build                            # EXISTING: build commands
|   +-- profile                      # NEW: Build Profiles (Unity 6)
|       +-- list                     # List all build profiles
|       +-- active                   # Get active build profile
|       +-- set <path>               # Set active build profile
|       +-- info <path>              # Get profile details
|
+-- asset                            # EXTENDED: additional subcommands
|   +-- (existing: find, query, import, refresh)
|   +-- create <path> --type <type>  # Create asset
|   +-- delete <path> [--trash]      # Delete asset
|   +-- copy <source> <dest>         # Copy asset
|   +-- move <source> <dest>         # Move/rename asset
|   +-- deps <path> [--recursive]    # Dependency graph
|   +-- guid <path-or-guid>          # Path <-> GUID conversion
|   +-- folder create <path>         # Create folder
|   +-- folder list <path>           # List subfolders
|   +-- export <paths...> -o <file>  # Export .unitypackage
|   +-- import-package <file>        # Import .unitypackage
|
+-- settings                         # NEW: Player Settings
    +-- get                          # Get all player settings
    +-- set <key> <value>            # Set a player setting
    +-- defines list [--platform P]  # List scripting defines
    +-- defines add <sym> [--plat P] # Add scripting define
    +-- defines remove <sym> [--p P] # Remove scripting define
```

### Detailed Command Signatures

#### Package Manager

```
unity-bridge package list [--source registry|git|embedded|local]
    List installed packages. Optional filter by source type.
    Flags:
      --source TEXT           Filter by package source (registry, git, embedded, local)
      --offline               Use offline mode (cached data only, no registry requests)
      --include-indirect      Include indirect (transitive) dependencies in results
      --timeout INT           Command timeout in seconds (default: 30)

unity-bridge package search <query>
    Search by package ID or name (not free-text keyword search).
    Uses Client.Search() which matches against package identifiers.
    Args:
      query            Package ID or name to search for
    Flags:
      --all            Use Client.SearchAll() to discover all available packages
      --timeout INT    Command timeout in seconds (default: 30)

unity-bridge package add <identifier>
    Add a package. Accepts name@version, name (latest), or git URL.
    Args:
      identifier       Package identifier (e.g. com.unity.textmeshpro@3.0.6)
    Flags:
      --timeout INT    Command timeout in seconds (default: 120)

unity-bridge package remove <name>
    Remove an installed package.
    Args:
      name             Package name (e.g. com.unity.textmeshpro)
    Flags:
      --timeout INT    Command timeout in seconds (default: 60)

unity-bridge package info <name>
    Get detailed info for a package.
    Args:
      name             Package name
    Flags:
      --timeout INT    Command timeout in seconds (default: 30)

unity-bridge package embed <name>
    Embed a package into the project Packages/ folder for local editing.
    Args:
      name             Package name to embed
    Flags:
      --timeout INT    Command timeout in seconds (default: 60)

unity-bridge package resolve
    Force package dependency resolution. Calls Client.Resolve() directly.
    Client.Resolve() returns void -- the command returns success immediately
    without polling. Do not attempt to poll the result.
    Flags:
      --timeout INT    Command timeout in seconds (default: 15)
```

#### Build Profiles

```
unity-bridge build profile list
    List all build profiles in the project.
    Flags:
      --timeout INT    Command timeout in seconds (default: 15)

unity-bridge build profile active
    Get the currently active build profile.
    Flags:
      --timeout INT    Command timeout in seconds (default: 10)

unity-bridge build profile set <path>
    Set the active build profile.
    Args:
      path             Asset path to build profile (e.g. Assets/Settings/BuildProfiles/Win64.asset)
    Flags:
      --timeout INT    Command timeout in seconds (default: 30)

unity-bridge build profile info <path>
    Get detailed info for a build profile.
    Args:
      path             Asset path to build profile
    Flags:
      --timeout INT    Command timeout in seconds (default: 10)
```

#### Asset Extended

```
unity-bridge asset create <path> --type <type>
    Create a new asset at the specified path.
    Note: Cannot create prefabs. AssetDatabase.CreateAsset() does not support
    prefab creation. Use PrefabUtility.SaveAsPrefabAsset() via the prefab
    command group instead. The C# handler checks for prefab types and returns
    a clear error with guidance.
    Args:
      path             Asset path (e.g. Assets/Data/MyConfig.asset)
    Flags:
      --type TEXT      Asset type to create (ScriptableObject, Material, AnimatorController, etc.)
      --timeout INT    Command timeout in seconds (default: 30)

unity-bridge asset delete <path> [--trash]
    Delete an asset from the project.
    Args:
      path             Asset path to delete
    Flags:
      --trash          Move to OS trash instead of permanent delete (default: false)
      --timeout INT    Command timeout in seconds (default: 15)

unity-bridge asset copy <source> <dest>
    Copy an asset to a new location.
    Args:
      source           Source asset path
      dest             Destination asset path
    Flags:
      --timeout INT    Command timeout in seconds (default: 15)

unity-bridge asset move <source> <dest>
    Move or rename an asset.
    Args:
      source           Source asset path
      dest             Destination asset path
    Flags:
      --timeout INT    Command timeout in seconds (default: 15)

unity-bridge asset deps <path> [--recursive]
    Get dependency graph for an asset.
    Args:
      path             Asset path
    Flags:
      --recursive      Include transitive dependencies (default: true)
      --timeout INT    Command timeout in seconds (default: 30)

unity-bridge asset guid <path-or-guid>
    Convert between asset path and GUID.
    Args:
      path-or-guid     An asset path or a 32-char hex GUID
    Flags:
      --timeout INT    Command timeout in seconds (default: 5)

unity-bridge asset folder create <path>
    Create a folder in the asset database.
    Args:
      path             Folder path (e.g. Assets/Data/Configs)
    Flags:
      --timeout INT    Command timeout in seconds (default: 10)

unity-bridge asset folder list <path>
    List immediate subfolders of a path.
    Args:
      path             Parent folder path
    Flags:
      --timeout INT    Command timeout in seconds (default: 10)

unity-bridge asset export <paths...> -o <file>
    Export assets as a .unitypackage file.
    Args:
      paths            One or more asset paths to export
    Flags:
      -o, --output     Output .unitypackage file path (required)
      --include-deps   Include dependencies in export (default: true)
      --timeout INT    Command timeout in seconds (default: 120)

unity-bridge asset import-package <file>
    Import a .unitypackage file into the project.
    Args:
      file             Path to .unitypackage file
    Flags:
      --interactive    Show import dialog (default: false, imports all)
      --timeout INT    Command timeout in seconds (default: 120)
```

#### Player Settings

```
unity-bridge settings get [--key <key>]
    Get player settings. Without --key, returns all common settings.
    Flags:
      --key TEXT       Specific setting key (e.g. companyName, productName)
      --timeout INT    Command timeout in seconds (default: 10)

unity-bridge settings set <key> <value>
    Set a player setting value.
    Args:
      key              Setting key (e.g. companyName, productName, bundleVersion)
      value            New value
    Flags:
      --timeout INT    Command timeout in seconds (default: 15)

unity-bridge settings defines list [--platform <target>]
    List scripting define symbols.
    Flags:
      --platform TEXT  Named build target (default: active platform)
      --timeout INT    Command timeout in seconds (default: 10)

unity-bridge settings defines add <symbol> [--platform <target>]
    Add a scripting define symbol. Triggers recompilation.
    Args:
      symbol           Define symbol (e.g. MY_FEATURE_ENABLED)
    Flags:
      --platform TEXT  Named build target (default: active platform)
      --timeout INT    Command timeout in seconds (default: 120)

unity-bridge settings defines remove <symbol> [--platform <target>]
    Remove a scripting define symbol. Triggers recompilation.
    Args:
      symbol           Define symbol to remove
    Flags:
      --platform TEXT  Named build target (default: active platform)
      --timeout INT    Command timeout in seconds (default: 120)
```

---

## 3. Architecture

### 3.1 C# Command Handlers

Four new `ICommandHandler` implementations, each in its own `.cs` file under
`ClaudeCodeBridge/`:

| File | CommandType | Unity API |
|------|-------------|-----------|
| `PackageManagerCommandHandler.cs` | `package-operation` | `UnityEditor.PackageManager.Client` |
| `BuildProfileCommandHandler.cs` | `build-profile-operation` | `UnityEditor.Build.Profile.BuildProfile` |
| `AssetExtendedCommandHandler.cs` | `asset-extended-operation` | `UnityEditor.AssetDatabase` (extended) |
| `PlayerSettingsCommandHandler.cs` | `player-settings-operation` | `UnityEditor.PlayerSettings` |

All handlers implement `ICommandHandler` and are registered in
`ClaudeUnityBridge.Initialize()`.

### 3.2 Python Command Modules

| File | Typer App | Core Async Functions |
|------|-----------|---------------------|
| `src/unity_bridge/commands/package.py` | `package_app` | `package_operation()` |
| `src/unity_bridge/commands/build_profile.py` | `build_profile_app` | `build_profile_operation()` |
| `src/unity_bridge/commands/asset.py` (extended) | `asset_app` (extended) | `asset_extended_operation()` |
| `src/unity_bridge/commands/settings.py` | `settings_app` | `player_settings_operation()` |

The existing `asset.py` will be extended with new actions. The `asset_extended_operation()`
function handles the new operations separately from the existing `asset_operation()` to
keep the C# handlers distinct and the Python functions focused.

### 3.3 MCP Tool Mappings

4 new MCP tools (one per command type with an `operation` field), matching Phase 2's
consolidated tool pattern:

| MCP Tool Name | Bridge Command Type | Operations | Description |
|---------------|-------------------|------------|-------------|
| `unity_package_operation` | `package-operation` | `list`, `search`, `search-all`, `add`, `remove`, `info`, `embed`, `resolve` | Unity Package Manager operations |
| `unity_build_profile` | `build-profile-operation` | `list`, `get-active`, `set-active`, `get-info` | Build Profile operations (Unity 6) |
| `unity_asset_extended` | `asset-extended-operation` | `create`, `delete`, `copy`, `move`, `deps`, `guid`, `folder-create`, `folder-list`, `export`, `import-package` | Extended asset operations |
| `unity_player_settings` | `player-settings-operation` | `get`, `set`, `defines-list`, `defines-add`, `defines-remove` | Player Settings and scripting defines |

### 3.4 Registration Changes

#### `ClaudeUnityBridge.cs` - Add handler registration

```csharp
// Phase 1: Core Platform APIs
RegisterHandler(new PackageManagerCommandHandler());
RegisterHandler(new BuildProfileCommandHandler());
RegisterHandler(new AssetExtendedCommandHandler());
RegisterHandler(new PlayerSettingsCommandHandler());
```

#### `app.py` - Add command registration

```python
# In _register_optional_commands():
_try_register_group("unity_bridge.commands.package", "package_app", "package")
_try_register_group("unity_bridge.commands.build_profile", "build_profile_app", "profile", parent="build_app")
_try_register_group("unity_bridge.commands.settings", "settings_app", "settings")
# asset.py extensions registered via existing asset_app
```

#### `mcp/tools.py` - Add tool command map entries

```python
# New entries in TOOL_COMMAND_MAP (4 tools, one per command type):
"unity_package_operation": "package-operation",
"unity_build_profile": "build-profile-operation",
"unity_asset_extended": "asset-extended-operation",
"unity_player_settings": "player-settings-operation",
```

### 3.5 Protocol Messages

All messages follow the existing bridge protocol. Python writes a command JSON file to
`.claude/unity/commands/{uuid}-{command-type}.json`. Unity C# reads it, processes it,
and writes a response to `.claude/unity/responses/{uuid}-{command-type}.json`.

**X4: Standardized response fields.** All `dataJson` responses MUST include
`"success": true` or `"success": false` for consistency across all command types.
This applies to both successful results and error cases within dataJson.

---

## 4. Implementation Details

### 4.1 Bridge Command Types (kebab-case)

| Command Type | Operations |
|-------------|-----------|
| `package-operation` | `list`, `search`, `search-all`, `add`, `remove`, `info`, `embed`, `resolve` |
| `build-profile-operation` | `list`, `get-active`, `set-active`, `get-info` |
| `asset-extended-operation` | `create`, `delete`, `copy`, `move`, `deps`, `guid`, `folder-create`, `folder-list`, `export`, `import-package` |
| `player-settings-operation` | `get`, `set`, `defines-list`, `defines-add`, `defines-remove` |

### 4.2 Protocol Message Formats

#### 4.2.1 Package Manager

**`package-operation` / `list`**

Command:
```json
{
  "commandId": "a1b2c3d4-...",
  "commandType": "package-operation",
  "timestamp": "2026-03-19T12:00:00.000Z",
  "parametersJson": "{\"operation\":\"list\",\"source\":\"registry\",\"offlineMode\":false,\"includeIndirectDependencies\":false}"
}
```

Response:
```json
{
  "commandId": "a1b2c3d4-...",
  "commandType": "package-operation",
  "status": "success",
  "timestamp": "2026-03-19T12:00:00.100Z",
  "dataJson": "{\"operation\":\"list\",\"packages\":[{\"name\":\"com.unity.textmeshpro\",\"version\":\"3.0.6\",\"displayName\":\"TextMeshPro\",\"source\":\"registry\",\"status\":\"installed\",\"resolvedPath\":\"/path/to/Library/PackageCache/com.unity.textmeshpro@3.0.6\"}],\"totalCount\":42,\"success\":true,\"message\":\"Listed 42 packages\"}",
  "errorMessage": ""
}
```

**`package-operation` / `search`**

Command parametersJson:
```json
{
  "operation": "search",
  "query": "textmeshpro"
}
```

Response dataJson:
```json
{
  "operation": "search",
  "packages": [
    {
      "name": "com.unity.textmeshpro",
      "version": "3.0.6",
      "displayName": "TextMeshPro",
      "description": "Text rendering package",
      "source": "registry",
      "status": "available"
    }
  ],
  "totalCount": 1,
  "success": true,
  "message": "Found 1 package matching 'textmeshpro'"
}
```

**`package-operation` / `search-all`**

Command parametersJson:
```json
{
  "operation": "search-all"
}
```

Response dataJson:
```json
{
  "operation": "search-all",
  "packages": [
    {
      "name": "com.unity.textmeshpro",
      "version": "3.0.6",
      "displayName": "TextMeshPro",
      "description": "Text rendering package",
      "source": "registry",
      "status": "available"
    }
  ],
  "totalCount": 150,
  "success": true,
  "message": "Found 150 available packages"
}
```

**`package-operation` / `resolve`**

Command parametersJson:
```json
{
  "operation": "resolve"
}
```

Response dataJson:
```json
{
  "operation": "resolve",
  "success": true,
  "message": "Package resolution requested. Client.Resolve() returns void; resolution proceeds asynchronously."
}
```

> **M1 Note:** `Client.Resolve()` returns void, unlike all other `Client` methods.
> Do not attempt to poll it. The command returns success immediately after calling
> `Resolve()`.

**`package-operation` / `add`**

Command parametersJson:
```json
{
  "operation": "add",
  "identifier": "com.unity.textmeshpro@3.0.6"
}
```

Response dataJson:
```json
{
  "operation": "add",
  "package": {
    "name": "com.unity.textmeshpro",
    "version": "3.0.6",
    "displayName": "TextMeshPro",
    "source": "registry",
    "status": "installed",
    "resolvedPath": "/path/to/Library/PackageCache/com.unity.textmeshpro@3.0.6"
  },
  "success": true,
  "message": "Added com.unity.textmeshpro@3.0.6"
}
```

**`package-operation` / `remove`**

Command parametersJson:
```json
{
  "operation": "remove",
  "packageName": "com.unity.textmeshpro"
}
```

Response dataJson:
```json
{
  "operation": "remove",
  "packageName": "com.unity.textmeshpro",
  "success": true,
  "message": "Removed com.unity.textmeshpro"
}
```

**`package-operation` / `info`**

Command parametersJson:
```json
{
  "operation": "info",
  "packageName": "com.unity.textmeshpro"
}
```

Response dataJson:
```json
{
  "operation": "info",
  "package": {
    "name": "com.unity.textmeshpro",
    "version": "3.0.6",
    "displayName": "TextMeshPro",
    "description": "Text rendering with advanced features",
    "source": "registry",
    "status": "installed",
    "resolvedPath": "/path/to/Library/PackageCache/com.unity.textmeshpro@3.0.6",
    "dependencies": [
      {"name": "com.unity.ugui", "version": "1.0.0"}
    ],
    "keywords": ["text", "ui", "font"],
    "author": "Unity Technologies",
    "documentationUrl": "https://docs.unity3d.com/Packages/com.unity.textmeshpro@3.0/manual/index.html"
  },
  "success": true,
  "message": "Retrieved info for com.unity.textmeshpro"
}
```

**`package-operation` / `embed`**

Command parametersJson:
```json
{
  "operation": "embed",
  "packageName": "com.unity.textmeshpro"
}
```

Response dataJson:
```json
{
  "operation": "embed",
  "package": {
    "name": "com.unity.textmeshpro",
    "version": "3.0.6",
    "source": "embedded",
    "resolvedPath": "/path/to/Packages/com.unity.textmeshpro"
  },
  "success": true,
  "message": "Embedded com.unity.textmeshpro to Packages/"
}
```

#### 4.2.2 Build Profiles

**`build-profile-operation` / `list`**

Command parametersJson:
```json
{
  "operation": "list"
}
```

Response dataJson:
```json
{
  "operation": "list",
  "profiles": [
    {
      "assetPath": "Assets/Settings/BuildProfiles/Win64.asset",
      "name": "Win64",
      "platform": "StandaloneWindows64",
      "isActive": true
    },
    {
      "assetPath": "Assets/Settings/BuildProfiles/Android.asset",
      "name": "Android",
      "platform": "Android",
      "isActive": false
    }
  ],
  "totalCount": 2,
  "success": true,
  "message": "Found 2 build profiles"
}
```

**`build-profile-operation` / `get-active`**

Command parametersJson:
```json
{
  "operation": "get-active"
}
```

Response dataJson (active profile exists):
```json
{
  "operation": "get-active",
  "profile": {
    "assetPath": "Assets/Settings/BuildProfiles/Win64.asset",
    "name": "Win64",
    "platform": "StandaloneWindows64",
    "isActive": true,
    "scenes": [
      "Assets/Scenes/Main.unity",
      "Assets/Scenes/Gameplay.unity"
    ],
    "scriptingDefines": "UNITY_POST_PROCESSING;MY_FEATURE",
    "buildTarget": "StandaloneWindows64",
    "subtarget": "Player"
  },
  "success": true,
  "message": "Active profile: Win64 (StandaloneWindows64)"
}
```

Response dataJson (no custom profile active -- `BuildProfile.GetActiveBuildProfile()` returns null):
```json
{
  "operation": "get-active",
  "profile": null,
  "success": true,
  "message": "No custom build profile active; using platform default."
}
```

**`build-profile-operation` / `set-active`**

> **C4 Limitation:** `SetActiveBuildProfile` cannot switch platforms when Unity is
> running in batch mode (`Application.isBatchMode == true`). The C# handler detects
> batch mode and returns an error with guidance to use the `-activeBuildProfile` CLI
> argument when launching Unity instead.

Command parametersJson:
```json
{
  "operation": "set-active",
  "profilePath": "Assets/Settings/BuildProfiles/Android.asset"
}
```

Response dataJson (success):
```json
{
  "operation": "set-active",
  "profile": {
    "assetPath": "Assets/Settings/BuildProfiles/Android.asset",
    "name": "Android",
    "platform": "Android",
    "isActive": true
  },
  "success": true,
  "message": "Activated build profile: Android"
}
```

Response dataJson (batch mode error):
```json
{
  "operation": "set-active",
  "success": false,
  "message": "Cannot switch build profiles in batch mode. Use the -activeBuildProfile CLI argument when launching Unity instead."
}
```

**`build-profile-operation` / `get-info`**

Command parametersJson:
```json
{
  "operation": "get-info",
  "profilePath": "Assets/Settings/BuildProfiles/Win64.asset"
}
```

Response dataJson:
```json
{
  "operation": "get-info",
  "profile": {
    "assetPath": "Assets/Settings/BuildProfiles/Win64.asset",
    "name": "Win64",
    "platform": "StandaloneWindows64",
    "isActive": true,
    "scenes": [
      "Assets/Scenes/Main.unity",
      "Assets/Scenes/Gameplay.unity"
    ],
    "scriptingDefines": "UNITY_POST_PROCESSING;MY_FEATURE",
    "buildTarget": "StandaloneWindows64",
    "subtarget": "Player",
    "il2CppCodeGeneration": "OptimizeSpeed",
    "managedStrippingLevel": "Medium"
  },
  "success": true,
  "message": "Retrieved info for Win64"
}
```

#### 4.2.3 Asset Extended

**`asset-extended-operation` / `create`**

Command parametersJson:
```json
{
  "operation": "create",
  "assetPath": "Assets/Data/MyConfig.asset",
  "assetType": "ScriptableObject"
}
```

Response dataJson:
```json
{
  "operation": "create",
  "asset": {
    "path": "Assets/Data/MyConfig.asset",
    "guid": "abc123def456...",
    "type": "ScriptableObject",
    "fileSize": 1024
  },
  "success": true,
  "message": "Created asset: Assets/Data/MyConfig.asset"
}
```

**`asset-extended-operation` / `delete`**

Command parametersJson:
```json
{
  "operation": "delete",
  "assetPath": "Assets/Data/OldConfig.asset",
  "useTrash": true
}
```

Response dataJson:
```json
{
  "operation": "delete",
  "assetPath": "Assets/Data/OldConfig.asset",
  "usedTrash": true,
  "success": true,
  "message": "Moved to trash: Assets/Data/OldConfig.asset"
}
```

**`asset-extended-operation` / `copy`**

Command parametersJson:
```json
{
  "operation": "copy",
  "sourcePath": "Assets/Prefabs/Player.prefab",
  "destinationPath": "Assets/Prefabs/PlayerCopy.prefab"
}
```

Response dataJson:
```json
{
  "operation": "copy",
  "sourcePath": "Assets/Prefabs/Player.prefab",
  "destinationPath": "Assets/Prefabs/PlayerCopy.prefab",
  "asset": {
    "path": "Assets/Prefabs/PlayerCopy.prefab",
    "guid": "def456abc789...",
    "type": "Prefab",
    "fileSize": 4096
  },
  "success": true,
  "message": "Copied to Assets/Prefabs/PlayerCopy.prefab"
}
```

**`asset-extended-operation` / `move`**

Command parametersJson:
```json
{
  "operation": "move",
  "sourcePath": "Assets/Prefabs/Enemy.prefab",
  "destinationPath": "Assets/Prefabs/Enemies/Enemy.prefab"
}
```

Response dataJson (success):
```json
{
  "operation": "move",
  "sourcePath": "Assets/Prefabs/Enemy.prefab",
  "destinationPath": "Assets/Prefabs/Enemies/Enemy.prefab",
  "errorDetail": "",
  "success": true,
  "message": "Moved to Assets/Prefabs/Enemies/Enemy.prefab"
}
```

Response dataJson (failure -- `AssetDatabase.MoveAsset()` returns a non-empty string on error):
```json
{
  "operation": "move",
  "sourcePath": "Assets/Prefabs/Enemy.prefab",
  "destinationPath": "Assets/Invalid/Enemy.prefab",
  "errorDetail": "Destination path does not exist",
  "success": false,
  "message": "Move failed: Destination path does not exist"
}
```

> **C7 Note:** `AssetDatabase.MoveAsset()` has an unusual return convention: it returns
> an empty string on success and an error message string on failure. The `errorDetail`
> field always contains the raw return value from MoveAsset().

**`asset-extended-operation` / `deps`**

Command parametersJson:
```json
{
  "operation": "deps",
  "assetPath": "Assets/Prefabs/Player.prefab",
  "recursive": true
}
```

Response dataJson:
```json
{
  "operation": "deps",
  "assetPath": "Assets/Prefabs/Player.prefab",
  "dependencies": [
    {
      "path": "Assets/Materials/PlayerMat.mat",
      "guid": "aaa111...",
      "type": "Material",
      "fileSize": 2048
    },
    {
      "path": "Assets/Textures/PlayerTex.png",
      "guid": "bbb222...",
      "type": "Texture2D",
      "fileSize": 102400
    }
  ],
  "totalCount": 2,
  "success": true,
  "message": "Found 2 dependencies for Assets/Prefabs/Player.prefab"
}
```

**`asset-extended-operation` / `guid`**

Command parametersJson (path to GUID):
```json
{
  "operation": "guid",
  "input": "Assets/Prefabs/Player.prefab"
}
```

Response dataJson:
```json
{
  "operation": "guid",
  "input": "Assets/Prefabs/Player.prefab",
  "path": "Assets/Prefabs/Player.prefab",
  "guid": "abc123def456789012345678abcdef01",
  "success": true,
  "message": "GUID: abc123def456789012345678abcdef01"
}
```

Command parametersJson (GUID to path):
```json
{
  "operation": "guid",
  "input": "abc123def456789012345678abcdef01"
}
```

Response dataJson:
```json
{
  "operation": "guid",
  "input": "abc123def456789012345678abcdef01",
  "path": "Assets/Prefabs/Player.prefab",
  "guid": "abc123def456789012345678abcdef01",
  "success": true,
  "message": "Path: Assets/Prefabs/Player.prefab"
}
```

**`asset-extended-operation` / `folder-create`**

Command parametersJson:
```json
{
  "operation": "folder-create",
  "folderPath": "Assets/Data/Configs"
}
```

Response dataJson:
```json
{
  "operation": "folder-create",
  "folderPath": "Assets/Data/Configs",
  "guid": "ccc333...",
  "success": true,
  "message": "Created folder: Assets/Data/Configs"
}
```

**`asset-extended-operation` / `folder-list`**

Command parametersJson:
```json
{
  "operation": "folder-list",
  "folderPath": "Assets/Prefabs"
}
```

Response dataJson:
```json
{
  "operation": "folder-list",
  "folderPath": "Assets/Prefabs",
  "subfolders": [
    "Assets/Prefabs/Characters",
    "Assets/Prefabs/Environment",
    "Assets/Prefabs/UI"
  ],
  "totalCount": 3,
  "success": true,
  "message": "Found 3 subfolders"
}
```

**`asset-extended-operation` / `export`**

Command parametersJson:
```json
{
  "operation": "export",
  "assetPaths": [
    "Assets/Prefabs/Player.prefab",
    "Assets/Materials/PlayerMat.mat"
  ],
  "outputPath": "Exports/player-assets.unitypackage",
  "includeDependencies": true
}
```

Response dataJson:
```json
{
  "operation": "export",
  "outputPath": "Exports/player-assets.unitypackage",
  "exportedAssets": 5,
  "fileSizeBytes": 204800,
  "success": true,
  "message": "Exported 5 assets (including dependencies) to Exports/player-assets.unitypackage"
}
```

**`asset-extended-operation` / `import-package`**

Command parametersJson:
```json
{
  "operation": "import-package",
  "packagePath": "Downloads/ui-kit.unitypackage",
  "interactive": false
}
```

Response dataJson:
```json
{
  "operation": "import-package",
  "packagePath": "Downloads/ui-kit.unitypackage",
  "interactive": false,
  "success": true,
  "message": "Imported package: Downloads/ui-kit.unitypackage"
}
```

#### 4.2.4 Player Settings

**`player-settings-operation` / `get`**

Command parametersJson:
```json
{
  "operation": "get",
  "key": null
}
```

Response dataJson (all settings):
```json
{
  "operation": "get",
  "settings": {
    "companyName": "MyCompany",
    "productName": "MyGame",
    "bundleVersion": "1.0.0",
    "applicationIdentifier": "com.mycompany.mygame",
    "defaultIsFullScreen": true,
    "runInBackground": true,
    "apiCompatibilityLevel": "NET_Standard_2_1",
    "scriptingBackend": "IL2CPP",
    "targetArchitecture": "ARM64"
  },
  "success": true,
  "message": "Retrieved 9 player settings"
}
```

Command parametersJson (specific key):
```json
{
  "operation": "get",
  "key": "companyName"
}
```

Response dataJson:
```json
{
  "operation": "get",
  "key": "companyName",
  "value": "MyCompany",
  "success": true,
  "message": "companyName = MyCompany"
}
```

**`player-settings-operation` / `set`**

Command parametersJson:
```json
{
  "operation": "set",
  "key": "companyName",
  "value": "NewCompany"
}
```

Response dataJson:
```json
{
  "operation": "set",
  "key": "companyName",
  "previousValue": "MyCompany",
  "newValue": "NewCompany",
  "success": true,
  "message": "Set companyName = NewCompany (was: MyCompany)"
}
```

**`player-settings-operation` / `defines-list`**

Command parametersJson:
```json
{
  "operation": "defines-list",
  "platform": "Standalone"
}
```

Response dataJson:
```json
{
  "operation": "defines-list",
  "platform": "Standalone",
  "defines": ["UNITY_POST_PROCESSING", "MY_FEATURE", "DEBUG_MODE"],
  "totalCount": 3,
  "success": true,
  "message": "3 scripting defines for Standalone"
}
```

**`player-settings-operation` / `defines-add`**

Command parametersJson:
```json
{
  "operation": "defines-add",
  "platform": "Standalone",
  "symbol": "MY_NEW_FEATURE"
}
```

Response dataJson:
```json
{
  "operation": "defines-add",
  "platform": "Standalone",
  "symbol": "MY_NEW_FEATURE",
  "defines": ["UNITY_POST_PROCESSING", "MY_FEATURE", "DEBUG_MODE", "MY_NEW_FEATURE"],
  "triggeredRecompilation": true,
  "domainReloadPending": true,
  "success": true,
  "message": "Added MY_NEW_FEATURE to Standalone defines (recompilation triggered). Domain reload in progress. Wait for bridge heartbeat to resume before sending further commands."
}
```

**`player-settings-operation` / `defines-remove`**

Command parametersJson:
```json
{
  "operation": "defines-remove",
  "platform": "Standalone",
  "symbol": "DEBUG_MODE"
}
```

Response dataJson:
```json
{
  "operation": "defines-remove",
  "platform": "Standalone",
  "symbol": "DEBUG_MODE",
  "defines": ["UNITY_POST_PROCESSING", "MY_FEATURE"],
  "triggeredRecompilation": true,
  "domainReloadPending": true,
  "success": true,
  "message": "Removed DEBUG_MODE from Standalone defines (recompilation triggered). Domain reload in progress. Wait for bridge heartbeat to resume before sending further commands."
}
```

### 4.3 Parameter Naming Conventions

Per project convention, bridge protocol parameters use **camelCase** (matching C#), while
Python CLI flags use **snake_case**. The Python command modules perform the translation.

| CLI Flag | Bridge Parameter |
|----------|-----------------|
| `--source` | `source` |
| `--package-name` / `<name>` | `packageName` |
| `--identifier` / `<identifier>` | `identifier` |
| `--profile-path` / `<path>` | `profilePath` |
| `--asset-path` / `<path>` | `assetPath` |
| `--source-path` / `<source>` | `sourcePath` |
| `--destination-path` / `<dest>` | `destinationPath` |
| `--use-trash` / `--trash` | `useTrash` |
| `--include-deps` | `includeDependencies` |
| `--interactive` | `interactive` |
| `--recursive` | `recursive` |
| `--platform` | `platform` |
| `--symbol` / `<symbol>` | `symbol` |
| `--output` / `-o` | `outputPath` |
| `--asset-type` / `--type` | `assetType` |
| `--folder-path` / `<path>` | `folderPath` |

### 4.4 Error Handling

All handlers follow the existing error pattern:

1. **Invalid operation**: Return `BridgeResponse.Success()` with `success: false` in
   the dataJson, listing valid operations.
2. **Missing required parameter**: Return `BridgeResponse.Error()` with a descriptive
   message identifying the missing parameter.
3. **Unity API exception**: Catch at handler level, return `BridgeResponse.Error()` with
   the exception message and stack trace.
4. **Async operation timeout**: For PackageManager polling, if `request.IsCompleted`
   is not true within the handler's internal timeout, write an error response.

Python-side error mapping:

| Bridge Error | CLI Exit Code | Description |
|-------------|---------------|-------------|
| `success: false` in dataJson | 1 | Command failed (Unity error) |
| `status: "error"` in response | 1 | Handler-level error |
| Response timeout | 4 | No response within timeout |
| Bridge unhealthy | 2 | Unity not running / heartbeat stale |
| Invalid CLI input | 3 | Bad arguments |

### 4.5 Timeout Defaults

New entries for `core/protocol.py` `TIMEOUT_DEFAULTS`:

```python
# Package Manager
"package-operation": 60,        # Registry lookups can be slow

# Build Profiles
"build-profile-operation": 15,  # Fast local operations

# Asset Extended
"asset-extended-operation": 60, # Export/import can be slow

# Player Settings
"player-settings-operation": 15, # Fast local operations
```

### 4.6 Parallel Safety

New entries for `core/protocol.py` `PARALLEL_SAFE_COMMANDS`:

```python
# These are read-only and safe for batch parallel execution:
# "build-profile-operation" with operations: list, get-active, get-info
# "player-settings-operation" with operations: get, defines-list
# "asset-extended-operation" with operations: deps, guid, folder-list
```

Since the parallel safety check is at the command-type level (not operation level), and
these command types include both read and write operations, they should **NOT** be added
to `PARALLEL_SAFE_COMMANDS`. The batch system would need operation-level granularity to
safely parallelize these, which is out of scope.

---

## 5. C# Implementation Notes

### 5.1 New Files

| File | LOC Estimate | Description |
|------|-------------|-------------|
| `ClaudeCodeBridge/PackageManagerCommandHandler.cs` | ~300 | Package Manager operations with async polling |
| `ClaudeCodeBridge/BuildProfileCommandHandler.cs` | ~200 | Build Profile CRUD operations |
| `ClaudeCodeBridge/AssetExtendedCommandHandler.cs` | ~350 | Extended AssetDatabase operations |
| `ClaudeCodeBridge/PlayerSettingsCommandHandler.cs` | ~250 | Player Settings get/set and scripting defines |

Each file includes its own `[Serializable]` parameter and result classes (following
the pattern in `BridgeModels.cs`). If `BridgeModels.cs` approaches 500 LOC, the new
model classes should live in a separate `BridgeModelsPhase1.cs` file.

### 5.2 Unity API Usage Patterns

#### PackageManager Async Polling

`UnityEditor.PackageManager.Client` methods (`List`, `Add`, `Remove`, `Embed`, `Search`)
return `Request<T>` objects that must be polled. **Exception:** `Client.Resolve()`
returns void, unlike all other Client methods. Do not attempt to poll it; return
success immediately after calling it. Since `ICommandHandler.Execute()` runs
on the main thread in `EditorApplication.update`, the handler must use a deferred
completion pattern:

```csharp
public class PackageManagerCommandHandler : ICommandHandler
{
    public string CommandType => "package-operation";

    // Track pending async requests
    private static Dictionary<string, PendingRequest> _pending
        = new Dictionary<string, PendingRequest>();

    public BridgeResponse Execute(BridgeCommand command)
    {
        var parameters = JsonUtility.FromJson<PackageOperationParams>(
            command.parametersJson ?? "{}");

        switch (parameters.operation?.ToLower())
        {
            case "list":
                return StartListRequest(command);
            case "add":
                return StartAddRequest(command, parameters);
            // ... etc
        }
    }

    private BridgeResponse StartListRequest(BridgeCommand command)
    {
        var request = UnityEditor.PackageManager.Client.List();
        _pending[command.commandId] = new PendingRequest
        {
            CommandId = command.commandId,
            Request = request,
            StartTime = DateTime.UtcNow
        };

        // Register update callback to poll
        EditorApplication.update += PollPendingRequests;

        // Return "running" status immediately
        return BridgeResponse.Running(command.commandId, CommandType,
            "{\"operation\":\"list\",\"message\":\"Listing packages...\"}");
    }

    private static void PollPendingRequests()
    {
        var completed = new List<string>();

        foreach (var kvp in _pending)
        {
            var pending = kvp.Value;
            if (pending.Request.IsCompleted)
            {
                // Write final response
                WriteFinalResponse(pending);
                completed.Add(kvp.Key);
            }
            else if ((DateTime.UtcNow - pending.StartTime).TotalSeconds > 60)
            {
                // Timeout
                WriteTimeoutResponse(pending);
                completed.Add(kvp.Key);
            }
        }

        foreach (var id in completed)
            _pending.Remove(id);

        if (_pending.Count == 0)
            EditorApplication.update -= PollPendingRequests;
    }
}
```

This pattern is similar to `BuildOperationCommandHandler` which uses
`BridgeResponse.Running()` for deferred completion.

**Serialization constraint**: `PackageManager.Client` methods are **serial** -- calling
a second method before the first completes produces undefined behavior. The handler must
queue requests and process them one at a time.

#### Build Profiles (Unity 6)

```csharp
using UnityEditor.Build.Profile;

// List all profiles
// C5 Note: FindAssets() returns GUID strings. Always convert with
// GUIDToAssetPath() before returning paths to Python.
var guids = AssetDatabase.FindAssets("t:BuildProfile");
var profiles = new List<BuildProfileInfo>();
foreach (var guid in guids)
{
    var path = AssetDatabase.GUIDToAssetPath(guid);
    var profile = AssetDatabase.LoadAssetAtPath<BuildProfile>(path);
    // ... populate profile info
}

// Get active profile -- C3: handle null return
var active = BuildProfile.GetActiveBuildProfile();
if (active is null)
{
    // Return success with profile: null
    // message: "No custom build profile active; using platform default."
}

// Set active profile -- C4: check batch mode first
if (Application.isBatchMode)
{
    // Return error: "Cannot switch build profiles in batch mode.
    // Use the -activeBuildProfile CLI argument when launching Unity instead."
}
var profileToSet = AssetDatabase.LoadAssetAtPath<BuildProfile>(profilePath);
BuildProfile.SetActiveBuildProfile(profileToSet);
```

Key constraint: `SetActiveBuildProfile` may trigger platform switching, which causes
asset reimport. The handler should return a `"running"` status and poll for completion
if a platform switch is detected.

#### Asset Extended Operations

```csharp
// Create asset -- C6: Cannot create prefabs via CreateAsset
// Check for prefab types and return a clear error directing to PrefabUtility
if (assetType.ToLower().Contains("prefab"))
{
    // Return error: "CreateAsset cannot create prefabs. Use the prefab command
    // group with PrefabUtility.SaveAsPrefabAsset() instead."
}
AssetDatabase.CreateAsset(asset, path);

// Delete vs trash
AssetDatabase.DeleteAsset(path);          // Permanent
AssetDatabase.MoveAssetToTrash(path);     // Recoverable

// Copy and move
AssetDatabase.CopyAsset(source, dest);
// C7: MoveAsset returns "" on success, error message string on failure
string error = AssetDatabase.MoveAsset(source, dest);
if (!string.IsNullOrEmpty(error))
{
    // Return success: false with errorDetail containing the raw error string
}

// GUID operations
string guid = AssetDatabase.AssetPathToGUID(path);
string path = AssetDatabase.GUIDToAssetPath(guid);

// Folder operations
string guid = AssetDatabase.CreateFolder(parentFolder, folderName);
string[] subfolders = AssetDatabase.GetSubFolders(folderPath);

// Export/Import
AssetDatabase.ExportPackage(assetPaths, outputPath, exportFlags);
AssetDatabase.ImportPackage(packagePath, interactive);
```

#### Player Settings

```csharp
// Get/set common properties
string company = PlayerSettings.companyName;
PlayerSettings.companyName = "NewCompany";

// Scripting defines (Unity 6 API -- uses NamedBuildTarget)
// M2: Use NamedBuildTarget static properties directly, not FromBuildTargetGroup
var target = NamedBuildTarget.Standalone; // or .Android, .iOS, .WebGL, etc.
PlayerSettings.GetScriptingDefineSymbols(target, out string[] defines);
PlayerSettings.SetScriptingDefineSymbols(target, newDefines);
// M3: SetScriptingDefineSymbols triggers domain reload. Response includes
// "domainReloadPending": true. Python side should wait for bridge heartbeat
// to resume before sending further commands.
```

**Recompilation handling**: `SetScriptingDefineSymbols` triggers domain reload. The
handler should log a warning that recompilation will occur. The response is written
before recompilation starts (synchronous call), so the Python side receives the response
before Unity reloads. The response includes `"domainReloadPending": true`.

**M3 Python-side handling:** When the Python command receives a response with
`domainReloadPending: true`, it should:
1. Return the result to the caller with a warning in the message.
2. The caller (CLI or MCP) should wait for the bridge heartbeat to resume before
   sending further commands, as the bridge C# side restarts after domain reload.

### 5.3 NamedBuildTarget Mapping

Unity 6 deprecates `BuildTargetGroup` in favor of `NamedBuildTarget`. The handler must
accept user-friendly platform names and map them using `NamedBuildTarget` static
properties directly (M2: do NOT use `NamedBuildTarget.FromBuildTargetGroup()`).

```csharp
// M2: Use static properties directly, not FromBuildTargetGroup
private static readonly Dictionary<string, NamedBuildTarget> PLATFORM_MAP
    = new Dictionary<string, NamedBuildTarget>(StringComparer.OrdinalIgnoreCase)
{
    { "Standalone", NamedBuildTarget.Standalone },
    { "Android", NamedBuildTarget.Android },
    { "iOS", NamedBuildTarget.iOS },
    { "WebGL", NamedBuildTarget.WebGL },
    { "Server", NamedBuildTarget.Server },
    { "WindowsStoreApps", NamedBuildTarget.WindowsStoreApps },
    // Default to active platform if not specified
};
```

> **M15:** This map is the C# handler's source of truth for platform validation. The MCP
> schema does NOT constrain platform to an enum -- it uses a free-form string with common
> values listed in the description. This avoids the Python/MCP side going stale when Unity
> adds new platforms.

### 5.4 Thread Safety

- **PackageManager requests**: Serial by design. Queue requests and process one at a time.
- **AssetDatabase operations**: Must run on main thread (enforced by `EditorApplication.update`).
- **PlayerSettings writes**: Must run on main thread. Writes to `ProjectSettings/ProjectSettings.asset`.
- **Build Profile switch**: May trigger async operations (platform switch, reimport). Use
  deferred completion pattern.

### 5.5 Common Guards

All new handlers MUST include these guards at the top of `Execute()`:

```csharp
// Guard: reject commands while compiling
if (EditorApplication.isCompiling)
{
    return BridgeResponse.Error(command.commandId, CommandType,
        "Unity is compiling. Wait for compilation to finish before sending commands.");
}

// Guard: reject mutating operations during play mode
if (EditorApplication.isPlaying && IsMutatingOperation(parameters.operation))
{
    return BridgeResponse.Error(command.commandId, CommandType,
        "Cannot perform mutating operations during play mode. Exit play mode first.");
}
```

**Asset path validation:** All handlers that accept asset paths MUST validate they start
with `"Assets/"` (or `"Packages/"` for read-only operations). Return a clear error if
the path is invalid:

```csharp
if (!assetPath.StartsWith("Assets/"))
{
    return BridgeResponse.Error(command.commandId, CommandType,
        $"Invalid asset path: '{assetPath}'. Asset paths must start with 'Assets/'.");
}
```

---

## 6. Testing Strategy

### 6.1 Unit Tests (Mock Bridge)

All unit tests mock `DirectBridge` and verify parameter construction and result handling.
No Unity instance required.

**New test files:**

| File | Tests |
|------|-------|
| `tests/unit/test_package.py` | All 6 package operations, parameter validation, error cases |
| `tests/unit/test_build_profile.py` | All 4 build profile operations |
| `tests/unit/test_asset_extended.py` | All 10 asset extended operations, GUID detection |
| `tests/unit/test_settings.py` | All 5 player settings operations |

**Test patterns:**

```python
async def test_package_list_sends_correct_command(mock_bridge):
    """Verify package list sends the right command type and parameters."""
    mock_bridge.send_command_with_retry.return_value = CommandResult(
        success=True,
        data={"operation": "list", "packages": [], "totalCount": 0}
    )
    result = await package_operation(mock_bridge, action="list")
    mock_bridge.send_command_with_retry.assert_called_once_with(
        command_type="package-operation",
        parameters={"operation": "list"},
        timeout=60.0,
    )
    assert result.success is True


async def test_package_add_includes_identifier(mock_bridge):
    """Verify package add passes the identifier parameter."""
    mock_bridge.send_command_with_retry.return_value = CommandResult(success=True)
    result = await package_operation(
        mock_bridge, action="add", identifier="com.unity.textmeshpro@3.0.6"
    )
    call_params = mock_bridge.send_command_with_retry.call_args.kwargs["parameters"]
    assert call_params["identifier"] == "com.unity.textmeshpro@3.0.6"


async def test_asset_guid_detects_guid_format(mock_bridge):
    """Verify GUID input is detected and forwarded correctly."""
    mock_bridge.send_command_with_retry.return_value = CommandResult(success=True)
    result = await asset_extended_operation(
        mock_bridge, action="guid", input_value="abc123def456789012345678abcdef01"
    )
    call_params = mock_bridge.send_command_with_retry.call_args.kwargs["parameters"]
    assert call_params["input"] == "abc123def456789012345678abcdef01"


async def test_settings_defines_add_triggers_recompilation_timeout(mock_bridge):
    """Verify defines-add uses extended timeout for recompilation."""
    mock_bridge.send_command_with_retry.return_value = CommandResult(success=True)
    result = await player_settings_operation(
        mock_bridge, action="defines-add", symbol="MY_FLAG"
    )
    call_timeout = mock_bridge.send_command_with_retry.call_args.kwargs["timeout"]
    assert call_timeout >= 120.0
```

**Edge cases to test:**

- Invalid operation name raises `ValueError`
- Missing required parameters (identifier for add, symbol for defines-add)
- Empty package list response
- GUID format detection (32 hex chars vs asset path)
- Platform name normalization
- Timeout override propagation

### 6.2 Integration Tests

Integration tests require Unity running with the C# bridge installed. Marked with
`@pytest.mark.integration`.

```python
@pytest.mark.integration
async def test_package_list_returns_packages(live_bridge):
    """Unity returns at least the built-in packages."""
    result = await package_operation(live_bridge, action="list")
    assert result.success is True
    assert result.data["totalCount"] > 0


@pytest.mark.integration
async def test_settings_get_returns_company_name(live_bridge):
    """Unity returns a non-empty company name."""
    result = await player_settings_operation(live_bridge, action="get")
    assert result.success is True
    assert "companyName" in result.data["settings"]
```

### 6.3 Coverage Targets

| Module | Target |
|--------|--------|
| `commands/package.py` | 90% |
| `commands/build_profile.py` | 90% |
| `commands/asset.py` (extended) | 85% |
| `commands/settings.py` | 90% |
| `mcp/schemas.py` (new schemas) | 100% |
| `mcp/tools.py` (new entries) | 100% |

---

## 7. Migration & Compatibility

### 7.1 Backward Compatibility

- **No breaking changes** to existing commands or MCP tools. All 26 existing tools
  continue to work identically.
- The existing `asset-operation` command type and handler are unchanged. The new
  `asset-extended-operation` is a separate command type to avoid making the existing
  handler more complex.
- The existing `build-operation` command type is unchanged. Build Profiles are a new
  command type (`build-profile-operation`).

### 7.2 Unity Version Requirements

| Feature | Minimum Unity Version | Notes |
|---------|----------------------|-------|
| Package Manager | Unity 2019.1+ | `Client.List()`, `Client.Add()`, etc. |
| Build Profiles | Unity 6 (6000.0) | `UnityEditor.Build.Profile` namespace |
| AssetDatabase extended | Unity 2017.1+ | All APIs long-established |
| Player Settings (NamedBuildTarget) | Unity 2021.2+ / Unity 6 | Replaces deprecated `BuildTargetGroup` |

The Build Profiles handler must include a compile-time check:

```csharp
#if UNITY_6000_0_OR_NEWER
    RegisterHandler(new BuildProfileCommandHandler());
#endif
```

Player Settings handler should use `NamedBuildTarget` static properties (M2) with a fallback:

```csharp
#if UNITY_6000_0_OR_NEWER
    // M2: Use static properties directly, not FromBuildTargetGroup
    var target = PLATFORM_MAP.GetValueOrDefault(platformName, NamedBuildTarget.Standalone);
    PlayerSettings.GetScriptingDefineSymbols(target, out string[] defines);
#else
    var defines = PlayerSettings.GetScriptingDefineSymbolsForGroup(group).Split(';');
#endif
```

### 7.3 Installation

The new C# files follow the existing lifecycle pattern. Running `unity-bridge install` or
starting the MCP server (which auto-installs) will copy the new `.cs` files into the
Unity project at `Assets/Scripts/Editor/ClaudeCodeBridge/`.

Each new `.cs` file needs a corresponding `.meta` file with a stable GUID, committed
alongside the source in the `ClaudeCodeBridge/` directory of this repository.

---

## 8. Risks & Open Questions

### Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| PackageManager serial constraint causes request queuing complexity | Medium | Implement simple FIFO queue with single-active-request guard |
| Build Profile API changes between Unity 6 preview versions | Medium | Use `#if UNITY_6000_0_OR_NEWER` guards; test against latest stable |
| `SetScriptingDefineSymbols` domain reload drops pending bridge responses | High | Write response synchronously before reload triggers; include `domainReloadPending: true` in response; document that bridge restarts after reload |
| `SetActiveBuildProfile` cannot switch platforms in batch mode (C4) | Medium | Detect `Application.isBatchMode` and return error with guidance to use `-activeBuildProfile` CLI arg |
| ExportPackage with large dependency trees causes timeout | Low | Use 120s default timeout; allow user override |
| `MoveAssetToTrash` behavior differs between OS (Windows recycling bin vs macOS trash) | Low | Document OS-dependent behavior; both are recoverable |

### Open Questions

1. **Q: Should `package search` hit the Unity registry directly or use the PackageManager API?**
   The `Client.SearchAll()` API was added in Unity 2020.1 but has been unstable. May need
   to fall back to `Client.List(offlineMode: false)` with client-side filtering.
   **Recommendation:** Use `Client.SearchAll()` with fallback to filtered `Client.List()`.

2. **Q: Should `asset create` support arbitrary ScriptableObject subclasses?**
   Creating a `ScriptableObject.CreateInstance<T>()` requires knowing the type at compile
   time. The handler could use `ScriptableObject.CreateInstance(typeName)` with reflection.
   **Recommendation:** Support generic `ScriptableObject` creation and common built-in types
   (Material, AnimatorController). User scripts require the full type name.

3. **Q: Should `build profile set` wait for platform switch completion?**
   Platform switching can take 30+ seconds for large projects. The handler could return
   immediately or wait.
   **Recommendation:** Return `"running"` status immediately, poll for completion, write
   final response when platform switch finishes (same pattern as build handler).

4. **Q: Should `settings set` support nested/complex values (e.g., Android signing config)?**
   **Recommendation:** Phase 1 supports string, int, float, and bool values only.
   Complex settings (keystore, splash screens) are deferred to a future phase.

5. **Q: How to handle `defines-add` when the symbol already exists?**
   **Recommendation:** Return success with `triggeredRecompilation: false` and a message
   indicating the symbol was already present. Do not treat as an error.

---

## Appendix A: MCP Schema Definitions

New schemas to add in `mcp/schemas.py` (or a new `mcp/schemas_phase1.py` if the file
exceeds 500 LOC). Consolidated to 4 schemas (one per tool, X1):

```python
def unity_package_operation() -> dict[str, Any]:
    """Schema for unity_package_operation MCP tool."""
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": [
                    "list", "search", "search-all", "add", "remove",
                    "info", "embed", "resolve",
                ],
                "description": "Package manager operation to perform",
            },
            "identifier": {
                "type": "string",
                "description": "Package identifier (name@version or git URL) for add",
            },
            "packageName": {
                "type": "string",
                "description": "Package name for remove/embed/info",
            },
            "query": {
                "type": "string",
                "description": (
                    "Package ID or name to search for (search operation). "
                    "Searches by package ID/name, not free-text keywords."
                ),
            },
            "source": {
                "type": "string",
                "enum": ["registry", "git", "embedded", "local"],
                "description": "Filter by package source type (list operation)",
            },
            "offlineMode": {
                "type": "boolean",
                "description": "Use offline mode for list (cached data only)",
                "default": false,
            },
            "includeIndirectDependencies": {
                "type": "boolean",
                "description": "Include indirect (transitive) dependencies in list results",
                "default": false,
            },
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds",
                "default": 60,
            },
        },
        "required": ["operation"],
    }


def unity_build_profile() -> dict[str, Any]:
    """Schema for unity_build_profile MCP tool."""
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["list", "get-active", "set-active", "get-info"],
                "description": "Build profile operation to perform",
            },
            "profilePath": {
                "type": "string",
                "description": "Asset path to build profile (for set-active, get-info)",
            },
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds",
                "default": 30,
            },
        },
        "required": ["operation"],
    }


def unity_asset_extended() -> dict[str, Any]:
    """Schema for unity_asset_extended MCP tool."""
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": [
                    "create", "delete", "copy", "move", "deps",
                    "guid", "folder-create", "folder-list",
                    "export", "import-package",
                ],
                "description": "Extended asset operation to perform",
            },
            "assetPath": {
                "type": "string",
                "description": "Primary asset path (must start with Assets/)",
            },
            "sourcePath": {
                "type": "string",
                "description": "Source path for copy/move (must start with Assets/)",
            },
            "destinationPath": {
                "type": "string",
                "description": "Destination path for copy/move (must start with Assets/)",
            },
            "assetType": {
                "type": "string",
                "description": (
                    "Asset type for create operation (ScriptableObject, Material, "
                    "AnimatorController, etc.). Cannot create prefabs -- use prefab "
                    "command group instead."
                ),
            },
            "useTrash": {
                "type": "boolean",
                "description": "Move to trash instead of permanent delete",
                "default": false,
            },
            "recursive": {
                "type": "boolean",
                "description": "Include transitive dependencies (for deps operation)",
                "default": true,
            },
            "assetPaths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Multiple asset paths (for export)",
            },
            "outputPath": {
                "type": "string",
                "description": "Output file path (for export)",
            },
            "includeDependencies": {
                "type": "boolean",
                "description": "Include dependencies in export",
                "default": true,
            },
            "interactive": {
                "type": "boolean",
                "description": "Show import dialog (for import-package)",
                "default": false,
            },
            "input": {
                "type": "string",
                "description": "Path or GUID input (for guid operation)",
            },
            "folderPath": {
                "type": "string",
                "description": "Folder path (for folder operations)",
            },
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds",
                "default": 60,
            },
        },
        "required": ["operation"],
    }


def unity_player_settings() -> dict[str, Any]:
    """Schema for unity_player_settings MCP tool."""
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": [
                    "get", "set", "defines-list", "defines-add", "defines-remove",
                ],
                "description": "Player settings operation to perform",
            },
            "key": {
                "type": "string",
                "description": "Setting key for get/set (e.g. companyName, productName, bundleVersion)",
            },
            "value": {
                "type": "string",
                "description": "New value for set operation",
            },
            "symbol": {
                "type": "string",
                "description": "Define symbol (required for defines-add/defines-remove)",
            },
            "platform": {
                "type": "string",
                "description": (
                    "Named build target (default: active platform). "
                    "Common values: Standalone, Android, iOS, WebGL, Server, "
                    "WindowsStoreApps. The C# handler's platform map is the "
                    "source of truth for validation."
                ),
            },
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds",
                "default": 15,
            },
        },
        "required": ["operation"],
    }
```

## Appendix B: C# Model Classes

New serializable model classes for `BridgeModels.cs` (or `BridgeModelsPhase1.cs`):

```csharp
#region Package Manager

[Serializable]
public class PackageOperationParams
{
    public string operation;       // "list", "search", "add", "remove", "info", "embed"
    public string packageName;     // For remove, info, embed
    public string identifier;      // For add (name@version or git URL)
    public string query;           // For search
    public string source;          // For list filter
    public bool offlineMode;       // m2: For list (cached data only)
    public bool includeIndirectDependencies; // m2: For list (include transitive deps)
}

[Serializable]
public class PackageOperationResult
{
    public string operation;
    public List<PackageInfoData> packages = new List<PackageInfoData>();
    public PackageInfoData package;  // Single package result (add, remove, info, embed)
    public string packageName;
    public int totalCount;
    public bool success;
    public string message;
}

[Serializable]
public class PackageInfoData
{
    public string name;
    public string version;
    public string displayName;
    public string description;
    public string source;          // "registry", "git", "embedded", "local"
    public string status;          // "installed", "available"
    public string resolvedPath;
    public List<PackageDependency> dependencies = new List<PackageDependency>();
    public List<string> keywords = new List<string>();
    public string author;
    public string documentationUrl;
}

[Serializable]
public class PackageDependency
{
    public string name;
    public string version;
}

#endregion

#region Build Profiles

[Serializable]
public class BuildProfileOperationParams
{
    public string operation;       // "list", "get-active", "set-active", "get-info"
    public string profilePath;     // Asset path to build profile
}

[Serializable]
public class BuildProfileOperationResult
{
    public string operation;
    public List<BuildProfileInfo> profiles = new List<BuildProfileInfo>();
    public BuildProfileInfo profile;  // Single profile result
    public int totalCount;
    public bool success;
    public string message;
}

[Serializable]
public class BuildProfileInfo
{
    public string assetPath;
    public string name;
    public string platform;
    public bool isActive;
    public List<string> scenes = new List<string>();
    public string scriptingDefines;
    public string buildTarget;
    public string subtarget;
    public string il2CppCodeGeneration;
    public string managedStrippingLevel;
}

#endregion

#region Asset Extended

[Serializable]
public class AssetExtendedOperationParams
{
    public string operation;           // See command list
    public string assetPath;
    public string sourcePath;
    public string destinationPath;
    public string assetType;
    public bool useTrash = false;
    public bool recursive = true;
    public string input;               // For guid operation
    public string folderPath;
    public List<string> assetPaths = new List<string>();  // For export
    public string outputPath;
    public bool includeDependencies = true;
    public bool interactive = false;
    public string packagePath;         // For import-package
}

[Serializable]
public class AssetExtendedOperationResult
{
    public string operation;
    public AssetInfo asset;            // Single asset result
    public List<AssetInfo> dependencies = new List<AssetInfo>();
    public string assetPath;
    public string sourcePath;
    public string destinationPath;
    public string folderPath;
    public List<string> subfolders = new List<string>();
    public string path;                // For guid result
    public string guid;                // For guid result
    public string input;               // For guid input echo
    public string outputPath;
    public int exportedAssets;
    public long fileSizeBytes;
    public bool usedTrash;
    public string errorDetail;     // C7: Raw return value from MoveAsset()
    public int totalCount;
    public bool success;
    public string message;
}

#endregion

#region Player Settings

[Serializable]
public class PlayerSettingsOperationParams
{
    public string operation;       // "get", "set", "defines-list", "defines-add", "defines-remove"
    public string key;
    public string value;
    public string symbol;
    public string platform;        // NamedBuildTarget name (default: active)
}

[Serializable]
public class PlayerSettingsOperationResult
{
    public string operation;
    public string key;
    public string value;
    public string previousValue;
    public string newValue;
    public string platform;
    public string symbol;
    public List<string> defines = new List<string>();
    public bool triggeredRecompilation;
    public bool domainReloadPending;   // M3: true when recompilation is triggered
    public int totalCount;
    public PlayerSettingsData settings;
    public bool success;
    public string message;
}

[Serializable]
public class PlayerSettingsData
{
    public string companyName;
    public string productName;
    public string bundleVersion;
    public string applicationIdentifier;
    public bool defaultIsFullScreen;
    public bool runInBackground;
    public string apiCompatibilityLevel;
    public string scriptingBackend;
    public string targetArchitecture;
}

#endregion
```

## Appendix C: Implementation Order

Recommended implementation sequence to minimize dependencies and enable incremental
testing:

1. **Player Settings** (simplest, synchronous Unity APIs, no async polling)
   - C#: `PlayerSettingsCommandHandler.cs`
   - Python: `commands/settings.py`
   - Tests: `tests/unit/test_settings.py`

2. **Asset Extended** (builds on existing asset handler pattern)
   - C#: `AssetExtendedCommandHandler.cs`
   - Python: extend `commands/asset.py`
   - Tests: `tests/unit/test_asset_extended.py`

3. **Build Profiles** (Unity 6 specific, needs conditional compilation)
   - C#: `BuildProfileCommandHandler.cs`
   - Python: `commands/build_profile.py`
   - Tests: `tests/unit/test_build_profile.py`

4. **Package Manager** (most complex, async polling pattern)
   - C#: `PackageManagerCommandHandler.cs`
   - Python: `commands/package.py`
   - Tests: `tests/unit/test_package.py`

After all four are implemented:
5. MCP schema and tool registration updates
6. Integration tests
7. Documentation updates (CLAUDE.md, CHANGELOG.md)
