# Build Commands Reference

Commands for building, platform switching, build profiles, and build scene management.

---

## build (registered)

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--target` / `-T` | TEXT | none | Platform target |
| `--validate-only` | flag | false | Validate without building |
| `--output` / `-o` | TEXT | none | Build output path |
| `--dev` | flag | false | Development build |
| `--auto-run` | flag | false | Auto-run player after build |
| `--profiler` | flag | false | Connect profiler |
| `--compress` | TEXT | none | Compression: lz4, lz4hc |
| `--scenes` | TEXT | none | Comma-separated scene paths |
| `--subtarget` | TEXT | none | Server or Player |
| `--timeout` | INT | 600 | Build timeout |

**Targets:** StandaloneWindows64, StandaloneWindows, StandaloneLinux64, StandaloneOSX, Android, iOS, WebGL

```bash
unity-bridge build --target StandaloneWindows64 --output builds/win64/
unity-bridge build -T Android --dev
unity-bridge build -T WebGL --validate-only
unity-bridge build -T Android --compress lz4hc --subtarget Player
unity-bridge build -T StandaloneLinux64 --scenes "Assets/Scenes/A.unity,Assets/Scenes/B.unity"
```

---

## profile (Unity 6 Build Profiles -- registered)

### `profile list` / `profile active`

```bash
unity-bridge profile list
unity-bridge profile active
```

### `profile set` / `profile info`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PROFILE_PATH` | positional | yes | Profile asset path |

```bash
unity-bridge profile set Assets/Settings/BuildProfiles/High.asset
unity-bridge profile info Assets/Settings/BuildProfiles/High.asset
```

### `profile scenes` / `profile defines`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PROFILE_PATH` | positional | yes | Profile asset path |

```bash
unity-bridge profile scenes Assets/Settings/BuildProfiles/High.asset
unity-bridge profile defines Assets/Settings/BuildProfiles/High.asset
```

### `profile set-scenes`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PROFILE_PATH` | positional | yes | Profile asset path |
| `--scene` | TEXT (repeatable) | yes | Enabled scene path |
| `--disabled-scene` | TEXT (repeatable) | no | Disabled scene path |

```bash
unity-bridge profile set-scenes Assets/Settings/BuildProfiles/High.asset --scene Assets/Scenes/Main.unity
unity-bridge profile set-scenes Assets/Settings/BuildProfiles/High.asset --scene Assets/Scenes/Main.unity --disabled-scene Assets/Scenes/Debug.unity
```

### `profile set-defines`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PROFILE_PATH` | positional | yes | Profile asset path |
| `--define` | TEXT (repeatable) | yes | Scripting define symbol |

```bash
unity-bridge profile set-defines Assets/Settings/BuildProfiles/High.asset --define USE_ADDRESSABLES --define ENABLE_LOGGING
```

### `profile build`

Build through a Unity 6 build profile. Build output includes structured report data when Unity returns it.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PROFILE_PATH` | positional | yes | Profile asset path |
| `--output` | TEXT | yes | Build output path |
| `--dev` | flag | no | Development build |
| `--run` | flag | no | Auto-run player after build |

```bash
unity-bridge profile build Assets/Settings/BuildProfiles/High.asset --output builds/win64/
unity-bridge profile build Assets/Settings/BuildProfiles/High.asset --output builds/win64/ --dev --run
```

---

## build-scenes (registered)

### `build-scenes list`

List all scenes in Build Settings. No arguments.

### `build-scenes add`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `SCENE_PATH` | positional | yes | Scene asset path |
| `--index` / `-i` | INT | no | Insert position (-1 = append) |

### `build-scenes remove` / `build-scenes enable` / `build-scenes disable`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `SCENE_PATH` | positional | yes | Scene asset path |

```bash
unity-bridge build-scenes list
unity-bridge build-scenes add Assets/Scenes/Main.unity
unity-bridge build-scenes add Assets/Scenes/Main.unity -i 0
unity-bridge build-scenes remove Assets/Scenes/Old.unity
unity-bridge build-scenes enable Assets/Scenes/Main.unity
unity-bridge build-scenes disable Assets/Scenes/Test.unity
```
