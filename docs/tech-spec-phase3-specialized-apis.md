# Tech Spec: Phase 3 - Specialized Workflow APIs

**Status:** Draft (Revised)
**Author:** Claude Code
**Last Updated:** 2026-03-19
**Version:** 0.2.0

---

## 1. Overview

### Problem Statement

The unity-bridge currently provides 26 MCP tools covering core editing operations (hierarchy, components, scenes, materials, prefabs, builds, etc.). However, several specialized Unity workflows remain inaccessible through the bridge:

- **Shader inspection** -- Debugging pink/error materials, validating shader compatibility, and auditing property usage all require manual Inspector interaction. There is no programmatic way to enumerate shaders, read their properties, or check compilation errors.
- **Lightmap baking** -- CI/CD pipelines and automated lighting validation have no way to trigger, monitor, or cancel lightmap bakes. This long-running operation requires special async handling.
- **Asset import settings** -- Enforcing project-wide import standards (texture sizes, compression formats, model import options) currently requires manual asset-by-asset inspection. Bulk changes and template-based workflows are impossible.
- **Multi-scene management** -- Large projects use multi-scene editing extensively, but there is no way to save/restore scene layouts, detect cross-scene references, or control which scene starts on Play.

### Goals

1. Add 4 new command groups with 22 new commands covering shader inspection, lightmap baking, asset import settings, and extended scene management (including preview scenes and bulk import).
2. Follow the established dual-interface pattern (async core functions shared by CLI and MCP).
3. Handle long-running operations (lightmap baking) with async monitoring and appropriate timeouts.
4. Provide unified JSON representations for heterogeneous data (different importer types, shader property types).
5. Store persistent data (scene setups, import templates) in well-defined locations under `.claude/unity/`.
6. Consolidate MCP tools to 4 (one per command type with operation dispatch) to minimize tool proliferation.

### Non-Goals

- Shader authoring or modification (read-only inspection only).
- Lightmap settings modification (read current settings, do not change them -- that is a future phase).
- Custom importer support (only built-in importer types: Texture, Model, Audio, and generic fallback).
- Runtime scene management (all operations are Editor-only via `EditorSceneManager`).
- Shader variant stripping or build-time shader optimization.

---

## 2. Command Reference

### Command Tree

```
unity-bridge
├── shader
│   ├── list                           # List all available shaders
│   ├── info <name>                    # Get shader details
│   ├── errors <name>                  # Get shader compilation errors
│   ├── properties <name>              # Enumerate shader properties
│   ├── find-by-property <property>    # Find shaders with a specific property
│   └── keywords <name>               # List shader keywords and variants
├── lightmap
│   ├── bake [--run-async]             # Bake lightmaps
│   ├── cancel                         # Cancel in-progress bake
│   ├── clear                          # Clear all baked lightmap data
│   ├── status                         # Get bake status
│   └── settings                       # Get current lightmap settings
├── asset
│   └── import-settings
│       ├── get <path>                 # Get import settings for asset
│       ├── set <path> --setting K:V   # Modify import settings
│       ├── reimport <path> [--force]  # Reimport asset
│       ├── bulk-set <folder> --setting K:V [--filter <pattern>]  # Bulk modify import settings
│       ├── template save <name> <path>  # Save settings as template
│       └── template apply <name> <path> # Apply template to asset
└── scene
    ├── setup save <name>              # Save multi-scene layout
    ├── setup restore <name>           # Restore saved layout
    ├── setup list                     # List saved layouts
    ├── play-start [--set <path>] [--clear]  # Get/set play mode start scene
    ├── cross-refs                     # Detect cross-scene references
    ├── list-loaded                    # List all loaded scenes with status
    ├── preview-create                 # Create an empty preview scene
    └── preview-close                  # Close a preview scene
```

### Detailed Command Signatures

#### 2.1 Shader Commands

| Command | Arguments | Options | Description |
|---------|-----------|---------|-------------|
| `shader list` | -- | `--errors-only` | List all shaders. Optionally filter to only those with errors. |
| `shader info <name>` | `name`: Shader name (e.g. `Universal Render Pipeline/Lit`) | -- | Full shader details: pass count, property count, supported status, error status. |
| `shader errors <name>` | `name`: Shader name | -- | Compilation errors/warnings for the shader. |
| `shader properties <name>` | `name`: Shader name | -- | All shader properties with name, type, description, default value, range. |
| `shader find-by-property <property>` | `property`: Property name (e.g. `_MainTex`) | -- | All shaders that declare the given property. |
| `shader keywords <name>` | `name`: Shader name | `--global`, `--local` | List all shader keywords (global and local). |

#### 2.2 Lightmap Commands

| Command | Arguments | Options | Description |
|---------|-----------|---------|-------------|
| `lightmap bake` | -- | `--run-async` (default: true) | Start lightmap bake. Async returns immediately with status. |
| `lightmap cancel` | -- | -- | Cancel in-progress lightmap bake. |
| `lightmap clear` | -- | -- | Clear all baked lightmap data from disk. |
| `lightmap status` | -- | -- | Get current bake status: running, progress, ETA. |
| `lightmap settings` | -- | -- | Get current Lightmapping settings (read-only). |

#### 2.3 Asset Import Settings Commands

| Command | Arguments | Options | Description |
|---------|-----------|---------|-------------|
| `asset import-settings get <path>` | `path`: Asset path | -- | Get current import settings. Response varies by importer type. |
| `asset import-settings set <path>` | `path`: Asset path | `--setting key:value` (repeatable) | Modify one or more import settings. |
| `asset import-settings reimport <path>` | `path`: Asset path | `--force` | Reimport asset with current settings. Force skips unchanged check. |
| `asset import-settings bulk-set <folder>` | `folder`: Folder path | `--setting key:value` (repeatable), `--filter <pattern>` | Apply settings to all matching assets in a folder. |
| `asset import-settings template save <name> <path>` | `name`: Template name, `path`: Source asset | -- | Save current import settings of asset as a named template. |
| `asset import-settings template apply <name> <path>` | `name`: Template name, `path`: Target asset | -- | Apply saved template to target asset. |

#### 2.4 Scene Extended Commands

| Command | Arguments | Options | Description |
|---------|-----------|---------|-------------|
| `scene setup save <name>` | `name`: Setup name | -- | Save current multi-scene layout to JSON file. |
| `scene setup restore <name>` | `name`: Setup name | -- | Restore a previously saved multi-scene layout. |
| `scene setup list` | -- | -- | List all saved scene setups. |
| `scene play-start` | -- | `--set <path>`, `--clear` | Get, set, or clear the play mode start scene. |
| `scene cross-refs` | -- | -- | Detect cross-scene references across all loaded scenes. |
| `scene list-loaded` | -- | -- | List all loaded scenes with status (active, loaded, dirty, path). |
| `scene preview-create` | -- | -- | Create an empty preview scene for isolated testing. |
| `scene preview-close` | -- | `--handle <handle>` | Close a previously created preview scene. |

---

## 3. Architecture

### 3.1 C# Command Handlers

Four new command handler classes, each implementing `ICommandHandler`:

| Handler Class | Command Type | File |
|---------------|-------------|------|
| `ShaderInspectionCommandHandler` | `shader-inspection` | `ShaderInspectionCommandHandler.cs` |
| `LightmapOperationCommandHandler` | `lightmap-operation` | `LightmapOperationCommandHandler.cs` |
| `ImportSettingsCommandHandler` | `import-settings-operation` | `ImportSettingsCommandHandler.cs` |
| `SceneSetupCommandHandler` | `scene-setup-operation` | `SceneSetupCommandHandler.cs` |

The existing `SceneOperationCommandHandler` remains unchanged. The new `SceneSetupCommandHandler` handles only the extended scene setup commands to keep files under 500 LOC.

### 3.2 Python Command Modules

| Module | Typer App | Core Functions |
|--------|-----------|----------------|
| `commands/shader.py` | `shader_app` | `shader_list`, `shader_info`, `shader_errors`, `shader_properties`, `shader_find_by_property`, `shader_keywords` |
| `commands/lightmap.py` | `lightmap_app` | `lightmap_bake`, `lightmap_cancel`, `lightmap_clear`, `lightmap_status`, `lightmap_settings` |
| `commands/import_settings.py` | `import_settings_app` (sub-app of `asset_app`) | `import_settings_get`, `import_settings_set`, `import_settings_reimport`, `import_settings_bulk_set`, `import_settings_template_save`, `import_settings_template_apply` |
| `commands/scene.py` (extended) | `scene_app` (additional sub-commands) | `scene_setup_save`, `scene_setup_restore`, `scene_setup_list`, `scene_play_start`, `scene_cross_refs`, `scene_list_loaded`, `scene_preview_create`, `scene_preview_close` |

The scene module grows with a `setup_app` sub-Typer. If it exceeds 500 LOC, extract `commands/scene_setup.py` as a separate module.

### 3.3 MCP Tool Mappings

Phase 3 consolidates to **4 MCP tools** (one per command type) with an `operation` field for dispatch, reducing tool proliferation:

| MCP Tool Name | Bridge Command Type | Operations |
|---------------|-------------------|------------|
| `unity_shader_inspection` | `shader-inspection` | `list`, `info`, `errors`, `properties`, `find-by-property`, `keywords` |
| `unity_lightmap_operation` | `lightmap-operation` | `bake`, `cancel`, `clear`, `status`, `settings` |
| `unity_import_settings` | `import-settings-operation` | `get`, `set`, `reimport`, `bulk-set`, `template-save`, `template-apply` |
| `unity_scene_extended` | `scene-setup-operation` | `setup-save`, `setup-restore`, `setup-list`, `play-start`, `cross-refs`, `list-loaded`, `preview-create`, `preview-close` |

Each tool accepts a required `operation` string parameter that selects the sub-operation, plus operation-specific parameters. All tools also accept an optional `timeout` parameter (integer, seconds).

Schemas defined in `schemas_phase3.py` to keep existing schema files under 500 LOC.

### 3.4 Protocol Messages

All messages follow the established envelope format. The outer `BridgeCommand` wrapper is shown once; subsequent examples show only `parametersJson` content and response `dataJson` content.

#### Envelope Format (reminder)

**Command file** (`<project>/.claude/unity/commands/{uuid}-{command-type}.json`):
```json
{
  "commandId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "commandType": "shader-inspection",
  "timestamp": "2026-03-19T10:30:00.000Z",
  "parametersJson": "{\"operation\":\"list\",\"errorsOnly\":false}"
}
```

**Response file** (`<project>/.claude/unity/responses/{uuid}-{command-type}.json`):
```json
{
  "commandId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "commandType": "shader-inspection",
  "status": "success",
  "timestamp": "2026-03-19T10:30:00.150Z",
  "dataJson": "{...}",
  "errorMessage": null
}
```

#### 3.4.1 Shader Inspection Protocol

**`shader-inspection` / `list`**

Parameters:
```json
{
  "operation": "list",
  "errorsOnly": false
}
```

Response `dataJson`:
```json
{
  "operation": "list",
  "shaders": [
    {
      "name": "Universal Render Pipeline/Lit",
      "supported": true,
      "hasErrors": false
    },
    {
      "name": "Custom/BrokenShader",
      "supported": false,
      "hasErrors": true
    }
  ],
  "totalCount": 142,
  "success": true,
  "message": "Found 142 shaders"
}
```

**`shader-inspection` / `info`**

Parameters:
```json
{
  "operation": "info",
  "shaderName": "Universal Render Pipeline/Lit"
}
```

Response `dataJson`:
```json
{
  "operation": "info",
  "shaderName": "Universal Render Pipeline/Lit",
  "supported": true,
  "hasErrors": false,
  "isCompiling": false,
  "renderQueue": 2000,
  "passCount": 8,
  "propertyCount": 34,
  "subShaderCount": 1,
  "success": true,
  "message": "Shader info retrieved"
}
```

**`shader-inspection` / `errors`**

Parameters:
```json
{
  "operation": "errors",
  "shaderName": "Custom/BrokenShader"
}
```

Response `dataJson`:
```json
{
  "operation": "errors",
  "shaderName": "Custom/BrokenShader",
  "hasErrors": true,
  "messages": [
    {
      "message": "Syntax error: unexpected token '}'",
      "messageDetails": "at line 42",
      "severity": "error",
      "platform": "d3d11",
      "line": 42,
      "file": "Assets/Shaders/BrokenShader.shader"
    }
  ],
  "messageCount": 1,
  "success": true,
  "message": "Found 1 shader message(s)"
}
```

> **C# implementation note (M13):** The `hasErrors` field uses `ShaderUtil.ShaderHasError(shader)`, which returns true only for compilation errors. The `messages` array uses `ShaderUtil.GetShaderMessages(shader)`, which returns both errors AND warnings. Each message includes a `severity` field (`"error"` or `"warning"`) from `ShaderCompilerMessage.severity` so callers can distinguish between the two.

**`shader-inspection` / `properties`**

Parameters:
```json
{
  "operation": "properties",
  "shaderName": "Universal Render Pipeline/Lit"
}
```

Response `dataJson`:
```json
{
  "operation": "properties",
  "shaderName": "Universal Render Pipeline/Lit",
  "properties": [
    {
      "name": "_BaseColor",
      "displayName": "Base Color",
      "type": "Color",
      "description": "Base color of the surface",
      "flags": ["MainColor"],
      "defaultValue": "{\"r\":1.0,\"g\":1.0,\"b\":1.0,\"a\":1.0}"
    },
    {
      "name": "_Smoothness",
      "displayName": "Smoothness",
      "type": "Range",
      "description": "Surface smoothness",
      "flags": [],
      "rangeMin": 0.0,
      "rangeMax": 1.0,
      "defaultValue": "0.5"
    },
    {
      "name": "_BaseMap",
      "displayName": "Base Map",
      "type": "Texture",
      "description": "Base (albedo) texture",
      "flags": ["MainTexture"],
      "textureDimension": "Tex2D",
      "defaultValue": "white"
    }
  ],
  "propertyCount": 34,
  "success": true,
  "message": "Found 34 properties"
}
```

**`shader-inspection` / `find-by-property`**

Parameters:
```json
{
  "operation": "find-by-property",
  "propertyName": "_MainTex"
}
```

Response `dataJson`:
```json
{
  "operation": "find-by-property",
  "propertyName": "_MainTex",
  "shaders": [
    {
      "name": "Standard",
      "propertyType": "Texture",
      "propertyDescription": "Albedo (RGB) and Transparency (A)"
    },
    {
      "name": "Unlit/Texture",
      "propertyType": "Texture",
      "propertyDescription": ""
    }
  ],
  "matchCount": 47,
  "success": true,
  "message": "Found 47 shaders with property '_MainTex'"
}
```

**`shader-inspection` / `keywords`**

Parameters:
```json
{
  "operation": "keywords",
  "shaderName": "Universal Render Pipeline/Lit",
  "keywordFilter": null
}
```

Response `dataJson`:
```json
{
  "operation": "keywords",
  "shaderName": "Universal Render Pipeline/Lit",
  "globalKeywords": [
    "_MAIN_LIGHT_SHADOWS",
    "_MAIN_LIGHT_SHADOWS_CASCADE",
    "_ADDITIONAL_LIGHTS",
    "_ADDITIONAL_LIGHT_SHADOWS"
  ],
  "localKeywords": [
    "_NORMALMAP",
    "_EMISSION",
    "_METALLICSPECGLOSSMAP",
    "_SMOOTHNESS_TEXTURE_ALBEDO_CHANNEL_A"
  ],
  "globalCount": 12,
  "localCount": 8,
  "success": true,
  "message": "Found 20 keywords (12 global, 8 local)"
}
```

#### 3.4.2 Lightmap Operation Protocol

**`lightmap-operation` / `bake`**

> **Note:** The parameter is named `runAsync` in the bridge protocol (camelCase) because `async` is a reserved word in Python. The Python CLI flag is `--run-async` and the Python parameter name is `run_async`.

Parameters:
```json
{
  "operation": "bake",
  "runAsync": true
}
```

Response `dataJson` (immediate, when `runAsync` is true and `BakeAsync()` returns true):
```json
{
  "operation": "bake",
  "started": true,
  "runAsync": true,
  "success": true,
  "message": "Lightmap bake started asynchronously"
}
```

Response `dataJson` (when `BakeAsync()` returns false -- bake failed to start):
```json
{
  "operation": "bake",
  "started": false,
  "runAsync": true,
  "success": false,
  "message": "Lightmap bake failed to start. Check that scenes are loaded and lightmap settings are valid."
}
```

Response `dataJson` (when `runAsync` is false -- blocks until complete):
```json
{
  "operation": "bake",
  "started": true,
  "runAsync": false,
  "completed": true,
  "durationSeconds": 145.3,
  "success": true,
  "message": "Lightmap bake completed in 145.3 seconds"
}
```

> **C# implementation note:** `Lightmapping.BakeAsync()` returns `bool` (not void). The handler MUST check this return value. If it returns `false`, respond immediately with `"started": false` and `"success": false`. Do not subscribe to `bakeCompleted` or write a deferred response.

**`lightmap-operation` / `cancel`**

Parameters:
```json
{
  "operation": "cancel"
}
```

Response `dataJson`:
```json
{
  "operation": "cancel",
  "wasRunning": true,
  "success": true,
  "message": "Lightmap bake cancelled"
}
```

**`lightmap-operation` / `clear`**

Parameters:
```json
{
  "operation": "clear"
}
```

Response `dataJson`:
```json
{
  "operation": "clear",
  "success": true,
  "message": "Lightmap data cleared"
}
```

**`lightmap-operation` / `status`**

Parameters:
```json
{
  "operation": "status"
}
```

Response `dataJson`:
```json
{
  "operation": "status",
  "isRunning": true,
  "progress": 0.42,
  "success": true,
  "message": "Lightmap bake in progress (42%)"
}
```

When not running:
```json
{
  "operation": "status",
  "isRunning": false,
  "progress": 0.0,
  "success": true,
  "message": "No lightmap bake in progress"
}
```

**`lightmap-operation` / `settings`**

Parameters:
```json
{
  "operation": "settings"
}
```

Response `dataJson`:
```json
{
  "operation": "settings",
  "lightmapper": "ProgressiveGPU",
  "bakedGI": true,
  "realtimeGI": false,
  "directSamples": 32,
  "indirectSamples": 512,
  "environmentSamples": 256,
  "bounces": 2,
  "lightmapResolution": 40,
  "lightmapPadding": 2,
  "lightmapMaxSize": 1024,
  "compressLightmaps": true,
  "ambientOcclusion": true,
  "aoMaxDistance": 1.0,
  "directionalMode": "Directional",
  "mixedBakeMode": "ShadowMask",
  "success": true,
  "message": "Lightmap settings retrieved"
}
```

> **C# implementation note (CRITICAL):** Do NOT use the obsolete `Lightmapping.bakedGI` or `Lightmapping.realtimeGI` properties. Instead, use `Lightmapping.lightingSettings` to get the `LightingSettings` asset, then read `bakedGI` and `realtimeGI` from it:
> ```csharp
> var settings = Lightmapping.lightingSettings;
> if (settings is not null)
> {
>     result.bakedGI = settings.bakedGI;
>     result.realtimeGI = settings.realtimeGI;
>     result.lightmapper = settings.lightmapper.ToString();
>     // ... other properties from LightingSettings
> }
> ```
> All lightmap settings should be read from the `LightingSettings` object, not from static `Lightmapping` properties.

#### 3.4.3 Import Settings Operation Protocol

**`import-settings-operation` / `get`**

Parameters:
```json
{
  "operation": "get",
  "assetPath": "Assets/Textures/Character_Albedo.png"
}
```

Response `dataJson` (texture example):
```json
{
  "operation": "get",
  "assetPath": "Assets/Textures/Character_Albedo.png",
  "importerType": "TextureImporter",
  "settings": {
    "textureType": "Default",
    "textureShape": "Texture2D",
    "sRGBTexture": true,
    "alphaSource": "FromInput",
    "alphaIsTransparency": false,
    "maxTextureSize": 2048,
    "textureCompression": "Normal",
    "compressionQuality": 50,
    "filterMode": "Bilinear",
    "anisoLevel": 1,
    "wrapMode": "Repeat",
    "mipmapEnabled": true,
    "mipmapFilter": "BoxFilter",
    "streamingMipmaps": false,
    "readWriteEnabled": false,
    "spriteMode": "None",
    "npotScale": "ToNearest"
  },
  "success": true,
  "message": "Import settings retrieved for TextureImporter"
}
```

Response `dataJson` (model example):
```json
{
  "operation": "get",
  "assetPath": "Assets/Models/Character.fbx",
  "importerType": "ModelImporter",
  "settings": {
    "globalScale": 1.0,
    "useFileScale": true,
    "meshCompression": "Off",
    "isReadable": false,
    "optimizeMeshPolygons": true,
    "optimizeMeshVertices": true,
    "importBlendShapes": true,
    "importNormals": "Import",
    "normalCalculationMode": "AreaAndAngleWeighted",
    "normalSmoothingAngle": 60,
    "importTangents": "CalculateMikk",
    "swapUVChannels": false,
    "generateSecondaryUV": false,
    "importAnimation": true,
    "animationType": "Humanoid",
    "animationCompression": "Optimal",
    "importConstraints": false,
    "importVisibility": true,
    "importCameras": false,
    "importLights": false,
    "materialImportMode": "ImportViaMaterialDescription",
    "materialLocation": "InPrefab"
  },
  "success": true,
  "message": "Import settings retrieved for ModelImporter"
}
```

Response `dataJson` (audio example):
```json
{
  "operation": "get",
  "assetPath": "Assets/Audio/Explosion.wav",
  "importerType": "AudioImporter",
  "settings": {
    "forceToMono": false,
    "normalize": true,
    "loadInBackground": false,
    "ambisonic": false,
    "loadType": "DecompressOnLoad",
    "compressionFormat": "Vorbis",
    "quality": 0.7,
    "sampleRateSetting": "PreserveSampleRate",
    "sampleRateOverride": 44100,
    "preloadAudioData": true
  },
  "success": true,
  "message": "Import settings retrieved for AudioImporter"
}
```

Response `dataJson` (unknown/generic importer):
```json
{
  "operation": "get",
  "assetPath": "Assets/Data/config.json",
  "importerType": "AssetImporter",
  "settings": {
    "userData": "",
    "assetBundleName": "",
    "assetBundleVariant": ""
  },
  "success": true,
  "message": "Import settings retrieved for AssetImporter (generic)"
}
```

**`import-settings-operation` / `set`**

Parameters:
```json
{
  "operation": "set",
  "assetPath": "Assets/Textures/Character_Albedo.png",
  "settings": {
    "maxTextureSize": 1024,
    "textureCompression": "HighQuality",
    "mipmapEnabled": false,
    "filterMode": "Point"
  }
}
```

Response `dataJson`:
```json
{
  "operation": "set",
  "assetPath": "Assets/Textures/Character_Albedo.png",
  "importerType": "TextureImporter",
  "updatedSettings": ["maxTextureSize", "textureCompression", "mipmapEnabled", "filterMode"],
  "updatedCount": 4,
  "reimported": true,
  "success": true,
  "message": "Updated 4 settings and reimported asset"
}
```

**`import-settings-operation` / `reimport`**

Parameters:
```json
{
  "operation": "reimport",
  "assetPath": "Assets/Textures/Character_Albedo.png",
  "force": false
}
```

Response `dataJson`:
```json
{
  "operation": "reimport",
  "assetPath": "Assets/Textures/Character_Albedo.png",
  "importerType": "TextureImporter",
  "success": true,
  "message": "Asset reimported successfully"
}
```

**`import-settings-operation` / `template-save`**

Parameters:
```json
{
  "operation": "template-save",
  "templateName": "character-texture-2k",
  "assetPath": "Assets/Textures/Character_Albedo.png"
}
```

Response `dataJson`:
```json
{
  "operation": "template-save",
  "templateName": "character-texture-2k",
  "importerType": "TextureImporter",
  "templatePath": ".claude/unity/import-templates/character-texture-2k.json",
  "success": true,
  "message": "Template 'character-texture-2k' saved from TextureImporter settings"
}
```

**`import-settings-operation` / `template-apply`**

Parameters:
```json
{
  "operation": "template-apply",
  "templateName": "character-texture-2k",
  "assetPath": "Assets/Textures/Enemy_Albedo.png"
}
```

Response `dataJson`:
```json
{
  "operation": "template-apply",
  "templateName": "character-texture-2k",
  "assetPath": "Assets/Textures/Enemy_Albedo.png",
  "importerType": "TextureImporter",
  "appliedSettings": ["maxTextureSize", "textureCompression", "mipmapEnabled", "filterMode", "sRGBTexture"],
  "appliedCount": 5,
  "reimported": true,
  "success": true,
  "message": "Template 'character-texture-2k' applied to asset and reimported"
}
```

**`import-settings-operation` / `bulk-set`**

Parameters:
```json
{
  "operation": "bulk-set",
  "folderPath": "Assets/Textures",
  "settings": {
    "maxTextureSize": 1024,
    "textureCompression": "Normal"
  },
  "filter": "*.png"
}
```

Response `dataJson`:
```json
{
  "operation": "bulk-set",
  "folderPath": "Assets/Textures",
  "filter": "*.png",
  "updatedAssets": [
    "Assets/Textures/Character_Albedo.png",
    "Assets/Textures/Enemy_Albedo.png"
  ],
  "updatedCount": 2,
  "skippedCount": 0,
  "skippedAssets": [],
  "success": true,
  "message": "Updated 2 assets in Assets/Textures matching *.png"
}
```

> **C# implementation note:** Use `AssetDatabase.FindAssets()` with the folder path, then filter by the glob pattern. For each matching asset, apply settings using the same logic as the `set` operation. Call `importer.SaveAndReimport()` after applying settings to each asset. Assets whose importer type does not support the given settings are added to `skippedAssets`.

#### 3.4.4 Scene Setup Operation Protocol

**`scene-setup-operation` / `save`**

Parameters:
```json
{
  "operation": "save",
  "setupName": "gameplay-editing"
}
```

Response `dataJson`:
```json
{
  "operation": "save",
  "setupName": "gameplay-editing",
  "setupPath": ".claude/unity/scene-setups/gameplay-editing.json",
  "scenes": [
    {
      "path": "Assets/Scenes/Gameplay.unity",
      "isLoaded": true,
      "isActive": true,
      "isSubScene": false
    },
    {
      "path": "Assets/Scenes/UI_Overlay.unity",
      "isLoaded": true,
      "isActive": false,
      "isSubScene": false
    },
    {
      "path": "Assets/Scenes/Audio.unity",
      "isLoaded": false,
      "isActive": false,
      "isSubScene": false
    }
  ],
  "sceneCount": 3,
  "success": true,
  "message": "Scene setup 'gameplay-editing' saved with 3 scenes"
}
```

**`scene-setup-operation` / `restore`**

Parameters:
```json
{
  "operation": "restore",
  "setupName": "gameplay-editing"
}
```

Response `dataJson`:
```json
{
  "operation": "restore",
  "setupName": "gameplay-editing",
  "scenes": [
    {
      "path": "Assets/Scenes/Gameplay.unity",
      "isLoaded": true,
      "isActive": true,
      "isSubScene": false
    },
    {
      "path": "Assets/Scenes/UI_Overlay.unity",
      "isLoaded": true,
      "isActive": false,
      "isSubScene": false
    }
  ],
  "sceneCount": 3,
  "success": true,
  "message": "Scene setup 'gameplay-editing' restored"
}
```

**`scene-setup-operation` / `list`**

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
  "setups": [
    {
      "name": "gameplay-editing",
      "sceneCount": 3,
      "createdAt": "2026-03-19T10:30:00.000Z",
      "activeScene": "Assets/Scenes/Gameplay.unity"
    },
    {
      "name": "ui-work",
      "sceneCount": 2,
      "createdAt": "2026-03-18T14:00:00.000Z",
      "activeScene": "Assets/Scenes/MainMenu.unity"
    }
  ],
  "setupCount": 2,
  "success": true,
  "message": "Found 2 saved scene setups"
}
```

**`scene-setup-operation` / `play-start`**

Get current play mode start scene:
```json
{
  "operation": "play-start"
}
```

Response:
```json
{
  "operation": "play-start",
  "playModeStartScene": "Assets/Scenes/Bootstrap.unity",
  "isSet": true,
  "success": true,
  "message": "Play mode start scene: Assets/Scenes/Bootstrap.unity"
}
```

Set play mode start scene:
```json
{
  "operation": "play-start",
  "scenePath": "Assets/Scenes/MainMenu.unity"
}
```

Clear play mode start scene (use active scene on play):
```json
{
  "operation": "play-start",
  "clear": true
}
```

**`scene-setup-operation` / `cross-refs`**

Parameters:
```json
{
  "operation": "cross-refs"
}
```

Response `dataJson`:
```json
{
  "operation": "cross-refs",
  "loadedScenes": [
    "Assets/Scenes/Gameplay.unity",
    "Assets/Scenes/UI_Overlay.unity"
  ],
  "crossReferences": [
    {
      "scenePath": "Assets/Scenes/Gameplay.unity",
      "hasCrossRefs": false
    },
    {
      "scenePath": "Assets/Scenes/UI_Overlay.unity",
      "hasCrossRefs": true
    }
  ],
  "totalWithCrossRefs": 1,
  "success": true,
  "message": "Detected cross-scene references in 1 of 2 loaded scenes"
}
```

**`scene-setup-operation` / `list-loaded`**

Parameters:
```json
{
  "operation": "list-loaded"
}
```

Response `dataJson`:
```json
{
  "operation": "list-loaded",
  "scenes": [
    {
      "name": "Gameplay",
      "path": "Assets/Scenes/Gameplay.unity",
      "buildIndex": 0,
      "isLoaded": true,
      "isActive": true,
      "isDirty": false,
      "rootCount": 12
    },
    {
      "name": "UI_Overlay",
      "path": "Assets/Scenes/UI_Overlay.unity",
      "buildIndex": 1,
      "isLoaded": true,
      "isActive": false,
      "isDirty": true,
      "rootCount": 5
    }
  ],
  "loadedCount": 2,
  "success": true,
  "message": "2 scenes currently loaded"
}
```

**`scene-setup-operation` / `preview-create`**

Parameters:
```json
{
  "operation": "preview-create"
}
```

Response `dataJson`:
```json
{
  "operation": "preview-create",
  "handle": 1,
  "sceneName": "preview_1",
  "success": true,
  "message": "Preview scene created (handle: 1)"
}
```

> **C# implementation note:** Uses `EditorSceneManager.NewPreviewScene()`. The handle is a sequential integer tracked by the handler to identify preview scenes for closing. Useful for testing prefab/material setups in isolation.

**`scene-setup-operation` / `preview-close`**

Parameters:
```json
{
  "operation": "preview-close",
  "handle": 1
}
```

Response `dataJson`:
```json
{
  "operation": "preview-close",
  "handle": 1,
  "success": true,
  "message": "Preview scene closed (handle: 1)"
}
```

> **C# implementation note:** Uses `EditorSceneManager.ClosePreviewScene()`. Returns an error if the handle does not match a known open preview scene.

---

## 4. Implementation Details

### 4.1 Shader Property Serialization Format

Shader properties use a unified JSON structure regardless of property type. The `type` field discriminates the value format:

```json
{
  "name": "_PropertyName",
  "displayName": "Human Readable Name",
  "type": "Color | Vector | Float | Range | Texture | Int",
  "description": "Property description from ShaderPropertyDescription",
  "flags": ["MainColor", "MainTexture", "Normal", "HDR", "Gamma", "PerRendererData", "NonModifiableTextureData", "HideInInspector"],
  "defaultValue": "<type-dependent>",
  "rangeMin": 0.0,
  "rangeMax": 1.0,
  "textureDimension": "Tex2D | Tex3D | Cube | Any"
}
```

> **C# implementation note (M12):** Unity's `ShaderUtil.ShaderPropertyType` enum uses the name `TexEnv` for texture properties. In bridge responses, this is serialized as `"Texture"` for clarity. The C# handler must map: `ShaderPropertyType.TexEnv` -> `"Texture"` when building the JSON response. Consumers should expect `"Texture"` in responses, not `"TexEnv"`.

Type-dependent `defaultValue` formats:
- **Color**: `"{\"r\":1.0,\"g\":1.0,\"b\":1.0,\"a\":1.0}"` (JSON string of color object)
- **Vector**: `"{\"x\":0.0,\"y\":0.0,\"z\":0.0,\"w\":0.0}"` (JSON string of vector4)
- **Float**: `"0.5"` (numeric string)
- **Range**: `"0.5"` (numeric string, with `rangeMin`/`rangeMax` present)
- **Int**: `"1"` (integer string)
- **Texture**: `"white"` (default texture name: `white`, `black`, `gray`, `bump`, `red`)

Fields `rangeMin` and `rangeMax` are only present when `type` is `Range`. Field `textureDimension` is only present when `type` is `Texture`.

The `flags` array is populated from `ShaderPropertyFlags` via bitwise inspection. Empty array if no flags are set.

### 4.2 Lightmap Async Bake Monitoring Pattern

Lightmap baking is a long-running operation that cannot block the bridge's `EditorApplication.update` loop. The implementation uses this pattern:

1. **`bake` with `runAsync: true` (default)**: Calls `Lightmapping.BakeAsync()`, checks the bool return value. If true, immediately returns a `"started": true` response. If false, returns `"started": false` with an error. The Python side can poll with `lightmap status` to monitor progress.

2. **`bake` with `runAsync: false`**: The C# handler calls `Lightmapping.BakeAsync()`, checks the bool return. If false, returns error immediately. If true, returns a `BridgeResponse.Running()` response (status `"running"`). The bridge writes a running response immediately. On the next `EditorApplication.update` tick, if `Lightmapping.isRunning` is false, it writes the final success/error response. The Python side sees the `"running"` status and continues polling for the final response.

3. **Timeout handling**: The Python `lightmap_bake` function with `run_async=False` uses a long default timeout (3600 seconds). The `lightmap_status` function uses a quick timeout (10 seconds). The CLI exposes `--timeout` to override. On the C# side, a timeout mechanism tracks `_bakeStartTime` -- if `bakeCompleted` does not fire within the configured timeout, the handler writes an error response and resets the pending state.

4. **`cancel`**: Calls `Lightmapping.Cancel()`. Safe to call even when no bake is running.

5. **`status`**: Reads `Lightmapping.isRunning` and the bake progress. Progress is reported as a float 0.0-1.0. Unity does not expose ETA directly, so the Python side can compute ETA from progress delta over time if needed (future enhancement, not in scope).

#### Deferred Response Pattern for Synchronous Bake

The `LightmapOperationCommandHandler` needs to track in-progress synchronous bakes. A static field holds the pending command ID:

```csharp
private static string _pendingBakeCommandId;
private static string _pendingBakeCommandType;
private static DateTime _bakeStartTime;
private static float _bakeTimeoutSeconds = 3600f;
```

When `runAsync: false` is requested:
1. Store `commandId` in `_pendingBakeCommandId`
2. Call `Lightmapping.BakeAsync()` and check the bool return value
3. If `BakeAsync()` returns false, respond immediately with `"started": false, "success": false`
4. If true, subscribe to `Lightmapping.bakeCompleted` event
5. Return `BridgeResponse.Running(commandId, commandType)`
6. On `bakeCompleted` callback, write the final response file directly via `File.WriteAllText`
7. If `bakeCompleted` does not fire within the timeout, write an error response and reset pending state

This is an extension of the existing bridge pattern -- the only command handler that writes responses outside the main `Execute` flow. The `ClaudeUnityBridge` already writes responses to the filesystem, so the handler reuses the same `RESPONSES_PATH`.

### 4.3 Import Settings Unified JSON Schema

Different importer types expose different properties. The unified approach:

1. **C# side**: Detect the importer subclass using `is` pattern matching:
   ```
   AssetImporter.GetAtPath(path) is TextureImporter ti -> extract texture settings
   AssetImporter.GetAtPath(path) is ModelImporter mi -> extract model settings
   AssetImporter.GetAtPath(path) is AudioImporter ai -> extract audio settings
   fallback -> extract generic AssetImporter settings
   ```

2. **Response format**: Always includes `importerType` discriminator field and a flat `settings` dictionary. The Python side does not need to know about C# class hierarchies -- it receives and sends the same flat key-value structure.

3. **Setting a value**: The C# handler maps setting keys to the appropriate importer property. Unknown keys are ignored with a warning in the response. Type conversion is handled in C# (string to enum, string to int, etc.). After applying all settings, the handler MUST call `importer.SaveAndReimport()` (which both persists the settings to disk and triggers reimport). Do not call `SaveAndReimport()` and `AssetDatabase.ImportAsset()` separately.

4. **Supported settings per importer type**:

   **TextureImporter** (21 settings):
   `textureType`, `textureShape`, `sRGBTexture`, `alphaSource`, `alphaIsTransparency`, `maxTextureSize`, `textureCompression`, `compressionQuality`, `filterMode`, `anisoLevel`, `wrapMode`, `mipmapEnabled`, `mipmapFilter`, `streamingMipmaps`, `readWriteEnabled`, `spriteMode`, `spritePixelsPerUnit`, `spritePivot`, `npotScale`, `generatePhysicsShape`, `crunchedCompression`

   **ModelImporter** (24 settings):
   `globalScale`, `useFileScale`, `meshCompression`, `isReadable`, `optimizeMeshPolygons`, `optimizeMeshVertices`, `importBlendShapes`, `importNormals`, `normalCalculationMode`, `normalSmoothingAngle`, `importTangents`, `swapUVChannels`, `generateSecondaryUV`, `importAnimation`, `animationType`, `animationCompression`, `importConstraints`, `importVisibility`, `importCameras`, `importLights`, `materialImportMode`, `materialLocation`, `addCollider`, `keepQuads`

   **AudioImporter** (10 settings):
   `forceToMono`, `normalize`, `loadInBackground`, `ambisonic`, `loadType`, `compressionFormat`, `quality`, `sampleRateSetting`, `sampleRateOverride`, `preloadAudioData`

   **Generic AssetImporter** (3 settings):
   `userData`, `assetBundleName`, `assetBundleVariant`

### 4.4 Scene Setup Storage Format and Location

Scene setups are stored as JSON files in `<project>/.claude/unity/scene-setups/`. This directory is created on first save if it does not exist.

**File path**: `.claude/unity/scene-setups/{setup-name}.json`

**File format**:
```json
{
  "name": "gameplay-editing",
  "createdAt": "2026-03-19T10:30:00.000Z",
  "updatedAt": "2026-03-19T10:30:00.000Z",
  "scenes": [
    {
      "path": "Assets/Scenes/Gameplay.unity",
      "isLoaded": true,
      "isActive": true,
      "isSubScene": false
    },
    {
      "path": "Assets/Scenes/UI_Overlay.unity",
      "isLoaded": true,
      "isActive": false,
      "isSubScene": false
    },
    {
      "path": "Assets/Scenes/Audio.unity",
      "isLoaded": false,
      "isActive": false,
      "isSubScene": false
    }
  ]
}
```

The scene setup save/restore is handled **on the C# side** using `EditorSceneManager.GetSceneManagerSetup()` and `RestoreSceneManagerSetup()`. The C# handler reads/writes JSON files directly to the `.claude/unity/scene-setups/` directory.

**Restore pre-validation (REQUIRED):** Before calling `RestoreSceneManagerSetup`, the C# handler MUST:
1. Verify at least one scene is present in the setup (empty setups are invalid -- `RestoreSceneManagerSetup` requires at least one scene).
2. Check that all scene paths in the setup exist on disk using `File.Exists()`.
3. If any scenes are missing, return an error listing the missing scene paths:
```json
{
  "operation": "restore",
  "setupName": "gameplay-editing",
  "success": false,
  "missingScenes": ["Assets/Scenes/DeletedScene.unity"],
  "message": "Cannot restore setup: 1 scene(s) not found on disk"
}
```

**Setup name validation**: Alphanumeric characters, hyphens, and underscores only. Max 64 characters. The name is used as the filename (sanitized).

### 4.5 Import Template Storage Format and Location

Import templates are stored in `<project>/.claude/unity/import-templates/`.

**File path**: `.claude/unity/import-templates/{template-name}.json`

**File format**:
```json
{
  "name": "character-texture-2k",
  "importerType": "TextureImporter",
  "createdAt": "2026-03-19T10:30:00.000Z",
  "sourceAsset": "Assets/Textures/Character_Albedo.png",
  "settings": {
    "textureType": "Default",
    "maxTextureSize": 2048,
    "textureCompression": "Normal",
    "filterMode": "Bilinear",
    "mipmapEnabled": true,
    "sRGBTexture": true
  }
}
```

**Template validation**: When applying a template, the handler verifies that the target asset's importer type matches the template's `importerType`. A type mismatch (e.g., applying a `TextureImporter` template to a `ModelImporter` asset) returns an error response:
```json
{
  "operation": "template-apply",
  "templateName": "character-texture-2k",
  "assetPath": "Assets/Models/Character.fbx",
  "success": false,
  "message": "Template type mismatch: template is TextureImporter but asset uses ModelImporter"
}
```

---

## 5. C# Implementation Notes

### 5.1 New Files

All files go in `ClaudeCodeBridge/` with corresponding `.meta` files:

| File | LOC Estimate | Description |
|------|-------------|-------------|
| `ShaderInspectionCommandHandler.cs` | ~350 | All 6 shader operations |
| `ShaderInspectionModels.cs` | ~120 | Params/result model classes for shader inspection |
| `LightmapOperationCommandHandler.cs` | ~280 | All 5 lightmap operations + deferred bake pattern |
| `LightmapOperationModels.cs` | ~100 | Params/result model classes for lightmap operations |
| `ImportSettingsCommandHandler.cs` | ~480 | 6 import-settings operations (incl. bulk-set) + importer type detection |
| `ImportSettingsModels.cs` | ~150 | Params/result model classes for import settings |
| `SceneSetupCommandHandler.cs` | ~400 | 8 scene-setup operations (incl. preview scenes) + file I/O for setups |
| `SceneSetupModels.cs` | ~130 | Params/result model classes for scene setup |

Model classes are split into separate files to keep handlers under 500 LOC. Each model file contains the `[Serializable]` parameter and result classes for that command group, following the pattern established in `BridgeModels.cs`.

> **Cross-spec note (X3):** Phase 3 establishes separate model files per handler (e.g., `ShaderInspectionModels.cs` alongside `ShaderInspectionCommandHandler.cs`) as the standard pattern. This approach is recommended for Phase 1 and Phase 2 handlers as well -- existing monolithic model files (like `BridgeModels.cs`) should be split into per-handler model files during future refactoring.

### 5.2 Handler Registration

Each handler registers itself in `ClaudeUnityBridge.InitializeHandlers()`. Add 4 new registrations:

```csharp
RegisterHandler(new ShaderInspectionCommandHandler());
RegisterHandler(new LightmapOperationCommandHandler());
RegisterHandler(new ImportSettingsCommandHandler());
RegisterHandler(new SceneSetupCommandHandler());
```

### 5.3 Importer Type Detection and Property Extraction

The `ImportSettingsCommandHandler` uses a dispatch pattern based on importer subclass:

```csharp
var importer = AssetImporter.GetAtPath(assetPath);

switch (importer)
{
    case TextureImporter ti:
        return ExtractTextureSettings(ti);
    case ModelImporter mi:
        return ExtractModelSettings(mi);
    case AudioImporter ai:
        return ExtractAudioSettings(ai);
    default:
        return ExtractGenericSettings(importer);
}
```

Each `Extract*Settings` method returns a `Dictionary<string, string>` of setting key-value pairs. Values are serialized as JSON strings (enums as their string names, booleans as `"true"`/`"false"`, numbers as string representation).

For the `set` operation, the inverse `Apply*Settings` methods use a similar switch, mapping string keys to typed property assignments:

```csharp
case "maxTextureSize":
    ti.maxTextureSize = int.Parse(value);
    break;
case "textureCompression":
    ti.textureCompression = Enum.Parse<TextureImporterCompression>(value);
    break;
```

Unknown keys are collected into a `skippedSettings` list in the response for debugging.

### 5.4 Handling Long-Running Lightmap Bakes

The `LightmapOperationCommandHandler` subscribes to bake lifecycle events in its constructor and registers an update callback for timeout monitoring:

```csharp
public LightmapOperationCommandHandler()
{
    Lightmapping.bakeCompleted += OnBakeCompleted;
    EditorApplication.update += CheckBakeTimeout;
}
```

The `OnBakeCompleted` callback checks if there is a pending synchronous bake command and writes the final response:

```csharp
private void OnBakeCompleted()
{
    if (_pendingBakeCommandId is null) return;

    var elapsed = (DateTime.UtcNow - _bakeStartTime).TotalSeconds;
    var result = new LightmapBakeResult
    {
        operation = "bake",
        started = true,
        runAsync = false,
        completed = true,
        durationSeconds = elapsed,
        success = true,
        message = $"Lightmap bake completed in {elapsed:F1} seconds"
    };

    var response = BridgeResponse.Success(
        _pendingBakeCommandId,
        _pendingBakeCommandType,
        JsonUtility.ToJson(result)
    );

    // Write response directly to filesystem
    var responsePath = Path.Combine(RESPONSES_PATH,
        $"{_pendingBakeCommandId}-{_pendingBakeCommandType}.json");
    File.WriteAllText(responsePath, JsonUtility.ToJson(response));

    _pendingBakeCommandId = null;
}

private void CheckBakeTimeout()
{
    if (_pendingBakeCommandId is null) return;

    var elapsed = (DateTime.UtcNow - _bakeStartTime).TotalSeconds;
    if (elapsed < _bakeTimeoutSeconds) return;

    // Timeout reached -- cancel the bake and write error response
    Lightmapping.Cancel();

    var result = new LightmapBakeResult
    {
        operation = "bake",
        started = true,
        runAsync = false,
        completed = false,
        durationSeconds = elapsed,
        success = false,
        message = $"Lightmap bake timed out after {elapsed:F0} seconds"
    };

    var response = BridgeResponse.Error(
        _pendingBakeCommandId,
        _pendingBakeCommandType,
        JsonUtility.ToJson(result)
    );

    var responsePath = Path.Combine(RESPONSES_PATH,
        $"{_pendingBakeCommandId}-{_pendingBakeCommandType}.json");
    File.WriteAllText(responsePath, JsonUtility.ToJson(response));

    _pendingBakeCommandId = null;
}
```

### 5.5 Cross-Scene Reference Detection

Uses `EditorSceneManager.DetectCrossSceneReferences(Scene)` for each loaded scene. This method is available in Unity 2021.2+ and iterates all GameObjects in the scene looking for references to objects in other scenes.

```csharp
for (int i = 0; i < SceneManager.sceneCount; i++)
{
    var scene = SceneManager.GetSceneAt(i);
    if (!scene.isLoaded) continue;

    var hasCrossRefs = EditorSceneManager.DetectCrossSceneReferences(scene);
    result.crossReferences.Add(new CrossRefInfo
    {
        scenePath = scene.path,
        hasCrossRefs = hasCrossRefs
    });
}
```

Note: `DetectCrossSceneReferences` returns a boolean only. It does not enumerate which specific objects have cross-references. Enumerating specific cross-references would require walking the full hierarchy and checking every serialized reference, which is a potential future enhancement (not in scope for Phase 3).

### 5.6 Play Mode Start Scene

Uses `EditorSceneManager.playModeStartScene`:

```csharp
// Get
var startScene = EditorSceneManager.playModeStartScene;
var path = startScene != null ? AssetDatabase.GetAssetPath(startScene) : null;

// Set
var sceneAsset = AssetDatabase.LoadAssetAtPath<SceneAsset>(scenePath);
EditorSceneManager.playModeStartScene = sceneAsset;

// Clear
EditorSceneManager.playModeStartScene = null;
```

---

## 6. Testing Strategy

### 6.1 Unit Tests (no Unity required)

All unit tests mock `DirectBridge` and verify that Python command modules send correct protocol messages and handle responses properly.

**New test files:**

| File | Tests |
|------|-------|
| `tests/unit/test_shader.py` | 6 core functions, input validation, response parsing |
| `tests/unit/test_lightmap.py` | 5 core functions, async/sync bake params, timeout handling |
| `tests/unit/test_import_settings.py` | 5 core functions, template save/apply, importer type validation |
| `tests/unit/test_scene_setup.py` | 6 core functions, setup name validation |

**Key test scenarios per group:**

Shader:
- `shader_list` sends correct parameters with `errorsOnly` flag
- `shader_info` validates shader name is required
- `shader_properties` response parsing with all property types
- `shader_find_by_property` validates property name is required
- `shader_errors` response with empty messages list (no errors)

Lightmap:
- `lightmap_bake` sends `runAsync: true` by default
- `lightmap_bake` with `run_async=False` uses extended timeout (3600s)
- `lightmap_bake` handles `started: false` response (BakeAsync returns false)
- `lightmap_status` uses quick timeout (10s)
- `lightmap_cancel` sends correct operation
- `lightmap_settings` response parsing of all settings fields

Import Settings:
- `import_settings_get` sends correct asset path
- `import_settings_set` serializes settings dict correctly
- `import_settings_set` validates at least one setting provided
- `import_settings_bulk_set` sends folder path, settings, and optional filter
- `import_settings_bulk_set` validates folder path is required
- `import_settings_template_save` validates template name format
- `import_settings_template_apply` sends both template name and target path
- `import_settings_template_apply` handles type mismatch error response

Scene Setup:
- `scene_setup_save` validates setup name (alphanumeric + hyphen + underscore)
- `scene_setup_restore` sends correct operation and name
- `scene_setup_list` expects no required parameters
- `scene_play_start` with no args returns current setting
- `scene_play_start` with `--set` sends scene path
- `scene_play_start` with `--clear` sends `clear: true`
- `scene_cross_refs` and `scene_list_loaded` send correct operations
- `scene_preview_create` sends correct operation
- `scene_preview_close` validates handle is required
- `scene_setup_restore` handles missing scenes error response

### 6.2 Integration Tests (requires Unity running)

Marked with `@pytest.mark.integration`. These verify end-to-end behavior.

| Test | Verification |
|------|-------------|
| `test_shader_list_returns_shaders` | At least 1 shader returned, all have `name` field |
| `test_shader_info_standard` | Info for `Standard` shader returns valid property/pass counts |
| `test_lightmap_status_when_idle` | Status returns `isRunning: false` |
| `test_import_settings_get_texture` | Get settings for a known texture returns `TextureImporter` type |
| `test_scene_list_loaded` | At least 1 loaded scene, active scene is set |
| `test_scene_setup_save_restore_roundtrip` | Save setup, restore it, verify scene layout matches |

### 6.3 MCP Schema Tests

Verify that all new schemas are valid JSON Schema and that `TOOL_DEFINITIONS` includes all new tools:

```python
def test_all_phase3_tools_registered():
    tool_names = {t["name"] for t in TOOL_DEFINITIONS}
    expected = {
        "unity_shader_inspection",
        "unity_lightmap_operation",
        "unity_import_settings",
        "unity_scene_extended",
    }
    assert expected.issubset(tool_names)

def test_phase3_tools_have_operation_field():
    """All Phase 3 tools require an 'operation' parameter."""
    phase3_tools = {
        "unity_shader_inspection",
        "unity_lightmap_operation",
        "unity_import_settings",
        "unity_scene_extended",
    }
    for tool in TOOL_DEFINITIONS:
        if tool["name"] in phase3_tools:
            schema = tool["inputSchema"]
            assert "operation" in schema["properties"]
            assert "operation" in schema.get("required", [])

def test_phase3_tools_have_timeout():
    """All Phase 3 tools accept an optional timeout parameter."""
    phase3_tools = {
        "unity_shader_inspection",
        "unity_lightmap_operation",
        "unity_import_settings",
        "unity_scene_extended",
    }
    for tool in TOOL_DEFINITIONS:
        if tool["name"] in phase3_tools:
            schema = tool["inputSchema"]
            assert "timeout" in schema["properties"]
```

### 6.4 Coverage Targets

| Module | Target |
|--------|--------|
| `commands/shader.py` | 90%+ |
| `commands/lightmap.py` | 85%+ |
| `commands/import_settings.py` | 85%+ |
| `commands/scene.py` (new functions) | 90%+ |
| `mcp/schemas_phase3.py` | 100% |

---

## 7. Migration and Compatibility

### 7.1 Backward Compatibility

- All existing MCP tools remain unchanged (Phase 1: 4 tools + Phase 2: 5 tools = 26 existing tools prior to Phase 3).
- Phase 3 adds 4 new consolidated MCP tools, bringing the cumulative total to 30 tools (down from the original 22-tool proposal).
- No modifications to existing C# handlers or Python command modules.
- The `scene-operation` command type is untouched; new scene commands use `scene-setup-operation`.
- The `asset-operation` command type is untouched; import settings use `import-settings-operation`.

### 7.2 Protocol Additions

Four new command types are added to the bridge protocol:

| Command Type | Category |
|-------------|----------|
| `shader-inspection` | Read-only |
| `lightmap-operation` | Read-write + long-running |
| `import-settings-operation` | Read-write |
| `scene-setup-operation` | Read-write |

### 7.3 Timeout Defaults

New entries for `core/protocol.py` `TIMEOUT_DEFAULTS`:

```python
# Shader inspection - read-only, fast
"shader-inspection": 15,

# Lightmap operations - varies widely
"lightmap-operation": 30,  # Default for status/cancel/clear/settings
# lightmap bake (run_async=False) overrides this per-command to 3600

# Import settings - medium (reimport can take time)
"import-settings-operation": 60,

# Scene setup - medium (restore loads scenes)
"scene-setup-operation": 30,
```

### 7.4 Parallel-Safe Commands

New entries for `core/protocol.py` `PARALLEL_SAFE_COMMANDS`:

```python
"shader-inspection",  # All shader operations are read-only
# lightmap-operation is NOT parallel-safe (bake/cancel/clear mutate state)
# import-settings-operation is NOT parallel-safe (set/reimport mutate state)
# scene-setup-operation is NOT parallel-safe (restore changes loaded scenes)
```

Note: Individual operations within `shader-inspection` are all read-only. For the other command types, even though `status` and `get` operations are read-only, the command type as a whole is not marked parallel-safe because the C# handler does not distinguish operations for parallelism purposes.

### 7.5 C# Bridge Installation

The `lifecycle` command copies C# files into the Unity project. The new handler and model files must be added to the file list in `ClaudeCodeBridge/`. The 8 new `.cs` files (4 handlers + 4 model files) and their 8 `.meta` files must be included (16 new files total).

### 7.6 New Filesystem Directories

Two new directories under `.claude/unity/`:

| Directory | Purpose | Created By |
|-----------|---------|------------|
| `.claude/unity/scene-setups/` | Saved multi-scene layouts | C# `SceneSetupCommandHandler` on first save |
| `.claude/unity/import-templates/` | Saved import settings templates | C# `ImportSettingsCommandHandler` on first save |

These directories should be added to `.gitignore` recommendations in documentation (they contain workspace-specific data, not project data).

---

## 8. Risks and Open Questions

### 8.1 Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Lightmap bake blocks editor** | High | Always use `BakeAsync()`, never `Bake()`. The synchronous-from-Python-perspective mode still uses `BakeAsync()` internally with deferred response. |
| **ShaderUtil API changes across Unity versions** | Medium | `ShaderUtil` is an internal API that has changed between Unity versions. Use `#if UNITY_2021_2_OR_NEWER` preprocessor directives for version-specific methods. Target Unity 2021.3 LTS as minimum. |
| **Large shader list performance** | Medium | Projects can have 500+ shaders. The `list` command should be fast (< 1 second) since `GetAllShaderInfo()` is a single call. The `find-by-property` command iterates all shaders and all their properties, which could be slow. Add a warning in the response if iteration takes > 5 seconds. |
| **Import settings serialization edge cases** | Medium | Some importer settings are complex objects (e.g., `TextureImporterPlatformSettings` per-platform overrides). Phase 3 covers only the main settings, not per-platform overrides. Document this limitation. |
| **Deferred response file write race condition** | Low | The `bakeCompleted` callback writes a response file that the Python side is polling for. The bridge's existing robust file read logic (retry with stability wait) handles this. |
| **Scene setup restoration with missing scenes** | Medium | If a saved setup references a scene that no longer exists, `RestoreSceneManagerSetup` will fail. The handler MUST pre-validate all scene paths exist on disk before calling `RestoreSceneManagerSetup`, and verify at least one scene is in the setup. Return a clear error listing missing scenes. See section 4.4 for the required validation. |

### 8.2 Open Questions

1. **Shader variant enumeration depth**: Should `shader keywords` also return the actual compiled variant count per platform? `ShaderUtil.GetVariantCount()` exists but can be very slow for complex shaders (thousands of variants). **Recommendation**: Omit variant count in Phase 3. Add as a separate `shader variants <name>` command in a future phase.

2. **Lightmap settings modification**: Should Phase 3 include a `lightmap settings set` command to modify lightmap settings before baking? **Recommendation**: Defer to Phase 4. Read-only settings inspection is sufficient for validation workflows. Modification adds significant complexity (many interdependent settings, enum types, validation).

3. **Per-platform import settings**: `TextureImporter` has per-platform override settings (e.g., different max size for Android vs. Standalone). Should `import-settings get` include these? **Recommendation**: Phase 3 returns the default platform settings only. Per-platform overrides are a Phase 4 enhancement. The `get` response should include a `platformOverrides` array listing which platforms have overrides, without the full details.

4. **Import template cross-project portability**: Should templates be stored in a global location (`~/.claude/unity-bridge/templates/`) for sharing across projects? **Recommendation**: Keep project-local in Phase 3. Add global template support in a future phase.

5. **Scene setup auto-save on exit**: Should the bridge automatically save the current scene setup when Unity closes? **Recommendation**: No. Auto-save behavior should be opt-in and is better handled by a separate "workspace" feature in a future phase.

6. **DetectCrossSceneReferences granularity**: The API only returns a boolean per scene. Should we implement custom cross-reference detection that identifies specific GameObjects? **Recommendation**: Use the built-in boolean API in Phase 3. Custom detection is expensive and fragile. If users need more detail, they can use `query-hierarchy` to inspect specific objects.

---

## Appendix A: MCP Schema Definitions

All new schemas go in `src/unity_bridge/mcp/schemas_phase3.py`. Phase 3 uses 4 consolidated tools (one per command type) with an `operation` field for dispatch. All tools include an optional `timeout` parameter.

```python
def unity_shader_inspection() -> dict[str, Any]:
    """Consolidated shader inspection tool with operation dispatch."""
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "Shader operation to perform",
                "enum": ["list", "info", "errors", "properties", "find-by-property", "keywords"],
            },
            "shaderName": {
                "type": "string",
                "description": "Full shader name (e.g. 'Universal Render Pipeline/Lit'). Required for: info, errors, properties, keywords.",
            },
            "propertyName": {
                "type": "string",
                "description": "Shader property name (e.g. '_MainTex'). Required for: find-by-property.",
            },
            "errorsOnly": {
                "type": "boolean",
                "description": "Only return shaders with compilation errors (for 'list' operation)",
                "default": False,
            },
            "keywordFilter": {
                "type": "string",
                "description": "Optional filter: 'global', 'local', or null for both (for 'keywords' operation)",
                "enum": ["global", "local"],
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds",
                "default": 15,
            },
        },
        "required": ["operation"],
    }

def unity_lightmap_operation() -> dict[str, Any]:
    """Consolidated lightmap operation tool with operation dispatch."""
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "Lightmap operation to perform",
                "enum": ["bake", "cancel", "clear", "status", "settings"],
            },
            "runAsync": {
                "type": "boolean",
                "description": "Return immediately (true) or wait for completion (false). Only for 'bake' operation.",
                "default": True,
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds. Defaults to 30 for most operations, 3600 for sync bake.",
            },
        },
        "required": ["operation"],
    }

def unity_import_settings() -> dict[str, Any]:
    """Consolidated import settings tool with operation dispatch."""
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "Import settings operation to perform",
                "enum": ["get", "set", "reimport", "bulk-set", "template-save", "template-apply"],
            },
            "assetPath": {
                "type": "string",
                "description": "Asset path (e.g. 'Assets/Textures/Albedo.png'). Required for: get, set, reimport, template-save, template-apply.",
            },
            "settings": {
                "type": "object",
                "description": "Key-value pairs of settings to modify. Required for: set, bulk-set.",
                "additionalProperties": True,
            },
            "force": {
                "type": "boolean",
                "description": "Force reimport even if unchanged (for 'reimport' operation)",
                "default": False,
            },
            "templateName": {
                "type": "string",
                "description": "Template name (alphanumeric, hyphens, underscores). Required for: template-save, template-apply.",
            },
            "folderPath": {
                "type": "string",
                "description": "Folder path for bulk operations. Required for: bulk-set.",
            },
            "filter": {
                "type": "string",
                "description": "Glob filter pattern for bulk operations (e.g. '*.png'). Optional for: bulk-set.",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds",
                "default": 60,
            },
        },
        "required": ["operation"],
    }

def unity_scene_extended() -> dict[str, Any]:
    """Consolidated extended scene management tool with operation dispatch."""
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "Scene operation to perform",
                "enum": [
                    "setup-save", "setup-restore", "setup-list",
                    "play-start", "cross-refs", "list-loaded",
                    "preview-create", "preview-close",
                ],
            },
            "setupName": {
                "type": "string",
                "description": "Setup name (alphanumeric, hyphens, underscores, max 64 chars). Required for: setup-save, setup-restore.",
            },
            "scenePath": {
                "type": "string",
                "description": "Scene path to set as play mode start scene (for 'play-start' operation).",
            },
            "clear": {
                "type": "boolean",
                "description": "Clear the play mode start scene (for 'play-start' operation)",
                "default": False,
            },
            "handle": {
                "type": "integer",
                "description": "Preview scene handle. Required for: preview-close.",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds",
                "default": 30,
            },
        },
        "required": ["operation"],
    }
```

---

## Appendix B: Implementation Order

Recommended implementation sequence, ordered by dependency and complexity:

1. **Shader Inspection** (simplest, read-only, no state management)
   - C#: `ShaderInspectionModels.cs`, `ShaderInspectionCommandHandler.cs`
   - Python: `commands/shader.py`
   - MCP: Schema + tool definitions
   - Tests: Unit tests for all 6 operations

2. **Scene Setup Extended** (builds on existing scene infrastructure)
   - C#: `SceneSetupModels.cs`, `SceneSetupCommandHandler.cs` (incl. preview scenes)
   - Python: Extend `commands/scene.py` or create `commands/scene_setup.py`
   - MCP: Schema + tool definitions
   - Tests: Unit + integration roundtrip test + preview scene tests

3. **Asset Import Settings** (moderate complexity, multiple importer types)
   - C#: `ImportSettingsModels.cs`, `ImportSettingsCommandHandler.cs` (incl. bulk-set)
   - Python: `commands/import_settings.py` + register as `asset` sub-app
   - MCP: Schema + tool definitions
   - Tests: Unit tests per importer type + bulk-set + template type mismatch

4. **Lightmap Operations** (most complex, async pattern, deferred responses)
   - C#: `LightmapOperationModels.cs`, `LightmapOperationCommandHandler.cs`
   - Python: `commands/lightmap.py`
   - MCP: Schema + tool definitions
   - Tests: Unit tests + careful integration testing of async bake

Each capability area is independently deployable. The C# handlers self-register, Python modules register via `app.py`, and MCP tools register via `tools.py`.
