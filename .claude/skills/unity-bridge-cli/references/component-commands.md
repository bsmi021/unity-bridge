# Component Commands Reference

Commands for inspecting, modifying, and managing components on GameObjects.

---

## component (core -- registered)

### `component get`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | GameObject path |
| `COMPONENT_TYPE` | positional | yes | Component type (e.g., Transform) |
| `--fields` / `-F` | TEXT | no | Comma-separated field names |
| `--deep` | flag | no | Full EditorJsonUtility serialization |

```bash
unity-bridge component get Player Transform
unity-bridge component get Player Health --fields "currentHp,maxHp"
unity-bridge component get Player Health --deep
```

### `component set`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | GameObject path |
| `COMPONENT_TYPE` | positional | yes | Component type |
| `--update` / `-u` | TEXT (repeatable) | yes | `FIELD:JSON_VALUE` pairs |

```bash
unity-bridge component set Player Health -u "currentHp:100"
unity-bridge component set Player Transform -u "position.x:5.0" -u "position.y:0"
```

### `component add`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | GameObject path |
| `COMPONENT_TYPE` | positional | yes | Component type to add |

```bash
unity-bridge component add Player "AudioSource"
```

### `component remove`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | GameObject path |
| `COMPONENT_TYPE` | positional | yes | Component type to remove |

```bash
unity-bridge component remove Player "Rigidbody"
```

### `component enable`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | GameObject path |
| `COMPONENT_TYPE` | positional | yes | Component type to enable |

```bash
unity-bridge component enable Player "AudioSource"
```

### `component disable`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | GameObject path |
| `COMPONENT_TYPE` | positional | yes | Component type to disable |

```bash
unity-bridge component disable Player "AudioSource"
```

---

## component copy/paste/reset (not yet registered -- module exists)

### `component copy`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | Source GameObject path |
| `COMPONENT_TYPE` | positional | yes | Component type to copy |

```bash
unity-bridge component copy Player Health
```

### `component paste`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | Target GameObject path |
| `COMPONENT_TYPE` | positional | yes | Component type to paste onto |
| `--data` | TEXT | no | JSON data to paste (overrides buffer) |

```bash
unity-bridge component paste Enemy Health
unity-bridge component paste Enemy Health --data '{"maxHp": 200}'
```

### `component reset`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | GameObject path |
| `COMPONENT_TYPE` | positional | yes | Component type to reset |

```bash
unity-bridge component reset Player Health
```

---

## property (serialized property access -- registered)

Fine-grained access to ALL serialized fields including `[SerializeField]` private fields.

### `property list`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | GameObject path |
| `COMPONENT_TYPE` | positional | yes | Component type |

```bash
unity-bridge property list Player BoxCollider
```

### `property get`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | GameObject path |
| `COMPONENT_TYPE` | positional | yes | Component type |
| `PROPERTY_PATH` | positional | yes | SerializedProperty path |

```bash
unity-bridge property get Player BoxCollider "m_Size"
```

### `property set`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | GameObject path |
| `COMPONENT_TYPE` | positional | yes | Component type |
| `PROPERTY_PATH` | positional | yes | SerializedProperty path |
| `VALUE` | positional | yes | JSON value to set |

```bash
unity-bridge property set Player BoxCollider "m_Size" '{"x":2,"y":2,"z":2}'
```

---

## deep-serialize (not yet registered -- module exists)

Full EditorJsonUtility serialization including private fields.

### `deep-serialize get`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | GameObject path |
| `COMPONENT_TYPE` | positional | yes | Component type |
| `--compact` | flag | no | Output compact JSON |

```bash
unity-bridge deep-serialize get Player Health
```

### `deep-serialize set`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | GameObject path |
| `COMPONENT_TYPE` | positional | yes | Component type |
| `JSON_DATA` | positional | yes | JSON data to overwrite with |

```bash
unity-bridge deep-serialize set Player Health '{"maxHp": 200, "currentHp": 200}'
```

---

## script-info (not yet registered -- module exists)

MonoScript inspection.

### `script-info info`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | positional | yes | Asset path to the .cs script |

```bash
unity-bridge script-info info Assets/Scripts/Player.cs
```

### `script-info list`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--filter` / `-f` | TEXT | no | Filter by name (partial match) |
| `--max` / `-m` | INTEGER | no | Max results (default: 500) |

```bash
unity-bridge script-info list
unity-bridge script-info list -f "Combat" -m 50
```

### `script-info find-component`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | GameObject path |
| `COMPONENT_TYPE` | positional | yes | Component type name |

```bash
unity-bridge script-info find-component Player PlayerController
```
