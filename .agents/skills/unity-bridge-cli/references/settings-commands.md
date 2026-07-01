# Settings Commands Reference

Commands for project settings, physics, quality, time, graphics, environment, audio, editor config, tags, layers, and editor preferences.

---

## settings (player settings -- registered)

### `settings get`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `KEY` | positional | no | Specific setting key (omit for all) |

```bash
unity-bridge settings get
unity-bridge settings get companyName
```

### `settings set`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `KEY` | positional | yes | Setting key |
| `VALUE` | positional | yes | Setting value |

```bash
unity-bridge settings set companyName "My Studio"
```

### `settings defines`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `ACTION` | positional | yes | list, add, or remove |
| `--symbol` / `-s` | TEXT | no | Symbol name (required for add/remove) |
| `--platform` | TEXT | no | Target platform |

```bash
unity-bridge settings defines list
unity-bridge settings defines add -s MY_FEATURE
unity-bridge settings defines add -s MY_FEATURE --platform Android
unity-bridge settings defines remove -s OLD_FEATURE
```

---

## physics (registered)

```bash
unity-bridge physics get
unity-bridge physics set -g "0,-9.81,0"
unity-bridge physics set --solver-iterations 12
unity-bridge physics collision get
unity-bridge physics collision set 8 9 --ignore
unity-bridge physics collision set 8 9 --collide
```

---

## quality (registered)

```bash
unity-bridge quality list
unity-bridge quality get
unity-bridge quality set-level 2
```

---

## time-settings

### `time-settings get`

Get current time settings. No arguments.

### `time-settings set`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--fixed-delta` | FLOAT | no | Fixed timestep (e.g. 0.02) |
| `--time-scale` | FLOAT | no | Time scale factor (1.0 = normal) |
| `--max-delta` | FLOAT | no | Maximum allowed timestep |
| `--max-particle-delta` | FLOAT | no | Maximum particle timestep |
| `--capture-delta` | FLOAT | no | Capture framerate timestep |

```bash
unity-bridge time-settings get
unity-bridge time-settings set --time-scale 0.5
unity-bridge time-settings set --fixed-delta 0.01
```

---

## graphics-settings

### `graphics-settings get` / `graphics-settings set`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--render-pipeline` | TEXT | no | Asset path to RenderPipelineAsset, or "none" |
| `--srp-batching/--no-srp-batching` | flag | no | SRP batching |
| `--log-shader/--no-log-shader` | flag | no | Log shader compilations |

```bash
unity-bridge graphics-settings get
unity-bridge graphics-settings set --srp-batching
unity-bridge graphics-settings set --render-pipeline Assets/Settings/URP.asset
```

---

## environment-settings

### `environment-settings get` / `environment-settings set`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--fog/--no-fog` | flag | no | Enable or disable fog |
| `--fog-color` | TEXT | no | Fog color as R,G,B (0-1) |
| `--fog-density` | FLOAT | no | Fog density |
| `--ambient-intensity` | FLOAT | no | Ambient intensity |
| `--skybox` | TEXT | no | Skybox material path or "none" |

```bash
unity-bridge environment-settings get
unity-bridge environment-settings set --fog --fog-density 0.05
unity-bridge environment-settings set --ambient-intensity 1.5
```

---

## audio-settings

### `audio-settings get` / `audio-settings set`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--volume` / `-v` | FLOAT | no | Global volume (0-1) |
| `--speaker-mode` | TEXT | no | AudioSpeakerMode enum |
| `--dsp-buffer` | INT | no | DSP buffer size |

```bash
unity-bridge audio-settings get
unity-bridge audio-settings set --volume 0.8
unity-bridge audio-settings set --speaker-mode Stereo
```

---

## tags / layers / sorting-layers (registered)

```bash
unity-bridge tags list
unity-bridge tags add "Interactable"
unity-bridge layers list
unity-bridge layers add "Interactables"
unity-bridge layers add "Interactables" -i 10
unity-bridge sorting-layers list
unity-bridge sorting-layers add "Foreground"
```

---

## editor-config (registered)

```bash
unity-bridge editor-config get
unity-bridge editor-config set "enterPlayModeOptionsEnabled" "true"
unity-bridge editor-config set "serializationMode" "ForceText"
```

---

## prefs (EditorPrefs/SessionState -- registered)

### `prefs get`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `KEY` | positional | yes | Preference key |
| `--type` / `-t` | TEXT | no | string, int, float, bool |
| `--scope` / `-s` | TEXT | no | prefs or session |

### `prefs set`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `KEY` | positional | yes | Preference key |
| `VALUE` | positional | yes | Value to set |
| `--type` / `-t` | TEXT | no | string, int, float, bool |
| `--scope` / `-s` | TEXT | no | prefs or session |

### `prefs delete` / `prefs has`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `KEY` | positional | yes | Preference key |
| `--scope` / `-s` | TEXT | no | prefs or session |

```bash
unity-bridge prefs get MyPlugin.Setting
unity-bridge prefs get MyPlugin.Setting -t int
unity-bridge prefs get MyKey -s session
unity-bridge prefs set MyPlugin.Count 42 -t int
unity-bridge prefs set MyFlag true -t bool -s session
unity-bridge prefs delete MyPlugin.Setting
unity-bridge prefs has MyKey -s session
```
