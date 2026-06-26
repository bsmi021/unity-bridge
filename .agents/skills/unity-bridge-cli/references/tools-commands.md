# Tools Commands Reference

Editor tools: profiler, profiler-control, game view, clipboard, window management,
input system, script info, deep serialize, find references, execution order, and assembly lock.

---

## coverage

Optional Unity Code Coverage package utility. The bridge compiles without
`com.unity.testtools.codecoverage`; availability and report inspection return
structured results even when the package is missing.

```bash
unity-bridge coverage availability
unity-bridge coverage install
unity-bridge coverage install --version 1.3.0
unity-bridge coverage start
unity-bridge coverage pause
unity-bridge coverage resume
unity-bridge coverage stop
unity-bridge coverage find-reports --path CoverageResults --max-results 25
unity-bridge coverage summarize CoverageResults/Report/Summary.json
```

---

## profiler

### Simple snapshot (registered)

```bash
unity-bridge profiler --memory --rendering --cpu
```

## profiler-control

Advanced profiler controls.

### `profiler-control start`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--log-file` | TEXT | no | Path to save profiler data |

### `profiler-control stop`

Stop the Unity Profiler. No arguments.

### `profiler-control save`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `LOG_FILE` | positional | yes | Path to save profiler data |

### `profiler-control memory`

Get detailed memory statistics. No arguments.

```bash
unity-bridge profiler-control start
unity-bridge profiler-control start --log-file profiler.raw
unity-bridge profiler-control stop
unity-bridge profiler-control save profiler-output.raw
unity-bridge profiler-control memory
```

---

## game-view

### `game-view get`

Get the current Game View state. No arguments.

### `game-view set-resolution`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `WIDTH` | positional (INT) | yes | Resolution width |
| `HEIGHT` | positional (INT) | yes | Resolution height |

### `game-view set-scale`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `SCALE` | positional (FLOAT) | yes | Zoom scale (1.0 = 100%) |

```bash
unity-bridge game-view get
unity-bridge game-view set-resolution 1920 1080
unity-bridge game-view set-scale 2.0
```

---

## clipboard

```bash
unity-bridge clipboard read
unity-bridge clipboard write "Hello from CLI"
```

---

## window

```bash
unity-bridge window list
unity-bridge window open Inspector
unity-bridge window focus Console
unity-bridge window close ProfilerWindow
```

---

## input-system

Requires `com.unity.inputsystem` package.

### `input-system list`

List all InputActionAssets. No arguments.

### `input-system get`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | positional | yes | Path to InputActionAsset |

### `input-system export`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | positional | yes | Path to InputActionAsset |
| `--output` / `-o` | TEXT | no | File path to save JSON to |

### `input-system import`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | positional | yes | Path for the InputActionAsset |
| `--from` / `-f` | TEXT | no | JSON file to import from |
| `--json` / `-j` | TEXT | no | Inline JSON data |

```bash
unity-bridge input-system list
unity-bridge input-system get Assets/Input/Controls.inputactions
unity-bridge input-system export Assets/Input/Controls.inputactions -o controls.json
unity-bridge input-system import Assets/Input/Controls.inputactions -f controls.json
```

---

## script-execution-order

### `script-execution-order get`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--non-default` | flag | no | Only scripts with non-zero order |

### `script-execution-order set`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `SCRIPT_PATH` | positional | yes | Asset path to the script |
| `ORDER` | positional (INT) | yes | Execution order value |

```bash
unity-bridge script-execution-order get
unity-bridge script-execution-order get --non-default
unity-bridge script-execution-order set Assets/Scripts/GameManager.cs -100
```

---

## assembly-lock / assembly-unlock / assembly-status

Standalone commands (not a group).

```bash
unity-bridge assembly-lock
unity-bridge assembly-unlock
unity-bridge assembly-status
```

---

## script-info

### `script-info info`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | positional | yes | Asset path to the .cs script |

### `script-info list`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--filter` / `-f` | TEXT | no | Filter by name (partial match) |
| `--max` / `-m` | INT | no | Max results (default: 500) |

### `script-info find-component`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | GameObject path |
| `COMPONENT_TYPE` | positional | yes | Component type name |

```bash
unity-bridge script-info info Assets/Scripts/Player.cs
unity-bridge script-info list
unity-bridge script-info list -f "Combat" -m 50
unity-bridge script-info find-component Player PlayerController
```

---

## deep-serialize

### `deep-serialize get`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | GameObject path |
| `COMPONENT_TYPE` | positional | yes | Component type |
| `--compact` | flag | no | Output compact JSON |

### `deep-serialize set`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | GameObject path |
| `COMPONENT_TYPE` | positional | yes | Component type |
| `JSON_DATA` | positional | yes | JSON data to overwrite with |

```bash
unity-bridge deep-serialize get Player Health
unity-bridge deep-serialize set Player Health '{"maxHp": 200}'
```
