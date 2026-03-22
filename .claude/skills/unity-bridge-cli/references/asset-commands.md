# Asset Commands Reference

Commands for asset database operations, import settings, materials, and shaders.

---

## asset (core -- registered)

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `ACTION` | positional | yes | `find`, `query`, `import`, or `refresh` |
| `--path` | TEXT | no | Asset path or search directory |
| `--type` | TEXT | no | Asset type filter |
| `--pattern` | TEXT | no | Search pattern |

```bash
unity-bridge asset find --type Prefab --pattern "Enemy*"
unity-bridge asset query --path Assets/Materials/
unity-bridge asset import --path Assets/Models/character.fbx
unity-bridge asset refresh
```

---

## asset-ext (extended -- registered)

### `asset-ext create`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | positional | yes | Asset path to create |
| `--type` | TEXT | yes | Asset type to create |

```bash
unity-bridge asset-ext create Assets/Data/Config.asset --type ScriptableObject
```

### `asset-ext delete`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | positional | yes | Asset path to delete |
| `--trash` | flag | no | Move to trash instead |

```bash
unity-bridge asset-ext delete Assets/Old/unused.mat
unity-bridge asset-ext delete Assets/Old/unused.mat --trash
```

### `asset-ext copy` / `asset-ext move`

Both take SOURCE and DEST as positional arguments.

```bash
unity-bridge asset-ext copy Assets/Materials/Base.mat Assets/Materials/Copy.mat
unity-bridge asset-ext move Assets/Old/file.cs Assets/New/file.cs
```

### `asset-ext deps`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | positional | yes | Asset path |
| `--recursive/--no-recursive` | flag | no | Include transitive deps |

```bash
unity-bridge asset-ext deps Assets/Prefabs/Player.prefab
unity-bridge asset-ext deps Assets/Prefabs/Player.prefab --recursive
```

### `asset-ext guid`

Bidirectional: pass an asset path to get GUID, or a GUID to get the path.

```bash
unity-bridge asset-ext guid Assets/Scenes/Main.unity
unity-bridge asset-ext guid abc123def456
```

### `asset-ext folder-create` / `asset-ext folder-list`

```bash
unity-bridge asset-ext folder-create Assets/NewFolder
unity-bridge asset-ext folder-list Assets/Scripts
```

### `asset-ext export`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATHS` | positional (variadic) | yes | Asset paths to export |
| `--output` / `-o` | TEXT | yes | Output .unitypackage path |
| `--no-deps` | flag | no | Exclude dependencies |

```bash
unity-bridge asset-ext export Assets/Prefabs/ -o export.unitypackage
```

### `asset-ext import-package`

```bash
unity-bridge asset-ext import-package downloaded.unitypackage
```

### `asset-ext reserialize` (not yet registered)

```bash
unity-bridge asset-ext reserialize
unity-bridge asset-ext reserialize --paths "Assets/Prefabs/Player.prefab"
```

---

## import-settings (registered)

### `import-settings get`

```bash
unity-bridge import-settings get Assets/Textures/icon.png
```

### `import-settings set`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | positional | yes | Asset path |
| `--setting` / `-s` | TEXT (repeatable) | yes | KEY:VALUE pairs |

```bash
unity-bridge import-settings set Assets/Textures/icon.png -s "maxTextureSize:512"
unity-bridge import-settings set Assets/Textures/icon.png -s "maxTextureSize:512" -s "mipmapEnabled:false"
```

### `import-settings reimport`

```bash
unity-bridge import-settings reimport Assets/Textures/icon.png
unity-bridge import-settings reimport Assets/Textures/icon.png --force
```

### `import-settings bulk-set`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `FOLDER` | positional | yes | Folder path |
| `--setting` / `-s` | TEXT (repeatable) | yes | KEY:VALUE pairs |
| `--filter` | TEXT | no | File filter pattern |

```bash
unity-bridge import-settings bulk-set Assets/Textures/ -s "maxTextureSize:1024" --filter "*.png"
```

### `import-settings template-save` / `import-settings template-apply`

```bash
unity-bridge import-settings template-save mobile-tex Assets/Textures/icon.png
unity-bridge import-settings template-apply mobile-tex Assets/Textures/other.png
```

---

## material (registered -- positional ACTION)

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `ACTION` | positional | yes | modify, create, duplicate, enable-keyword, disable-keyword, get-keywords, set-render-queue, copy-properties |
| `PATH` | positional | yes | Material asset path |
| `--properties` | JSON | no | JSON property overrides (for modify) |

```bash
unity-bridge material modify Assets/Materials/Player.mat --properties '{"_Color":{"r":1}}'
unity-bridge material create Assets/Materials/New.mat
unity-bridge material duplicate Assets/Materials/Base.mat
unity-bridge material enable-keyword Assets/Materials/Player.mat _EMISSION
unity-bridge material disable-keyword Assets/Materials/Player.mat _EMISSION
unity-bridge material get-keywords Assets/Materials/Player.mat
unity-bridge material set-render-queue Assets/Materials/Player.mat 3000
unity-bridge material copy-properties Assets/Materials/Source.mat Assets/Materials/Target.mat
```

---

## shader (registered)

### `shader list`

```bash
unity-bridge shader list
unity-bridge shader list --errors-only
```

### `shader info` / `shader errors` / `shader properties` / `shader find-by-property`

All take a positional NAME argument.

```bash
unity-bridge shader info "Universal Render Pipeline/Lit"
unity-bridge shader errors "Custom/MyShader"
unity-bridge shader properties "Standard"
unity-bridge shader find-by-property _MainTex
```

### `shader keywords`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `NAME` | positional | yes | Shader name |
| `--global` | flag | no | Global keywords only |
| `--local` | flag | no | Local keywords only |

```bash
unity-bridge shader keywords "Standard" --global
```

---

## find-references (not yet registered)

```bash
unity-bridge find-references Assets/Prefabs/Enemy.prefab
```

---

## preset (not yet registered)

```bash
unity-bridge preset create Assets/Materials/Lit.mat Assets/Presets/LitMat.preset
unity-bridge preset apply Assets/Presets/LitMat.preset Assets/Materials/New.mat
unity-bridge preset can-apply Assets/Presets/LitMat.preset Assets/Materials/New.mat
unity-bridge preset list-defaults
```
