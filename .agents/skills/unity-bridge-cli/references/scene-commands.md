# Scene Commands Reference

Commands for scene loading, saving, multi-scene editing, and scene view control.

---

## modal-safe scene replacement

As of Unity 6.5, `EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo`
still opens an interactive Save/Don't Save/Cancel dialog, and `OpenScene`,
`NewScene`, `CloseScene`, and `RestoreSceneManagerSetup` are the scene APIs that
can close or replace loaded scene state. The bridge must prevent that modal
instead of trying to recover after it appears.

References checked 2026-07-05:
`SaveCurrentModifiedScenesIfUserWantsTo`
(https://docs.unity3d.com/ScriptReference/SceneManagement.EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo.html),
`OpenScene`
(https://docs.unity3d.com/ScriptReference/SceneManagement.EditorSceneManager.OpenScene.html),
`NewScene`
(https://docs.unity3d.com/ScriptReference/SceneManagement.EditorSceneManager.NewScene.html),
`CloseScene`
(https://docs.unity3d.com/ScriptReference/SceneManagement.EditorSceneManager.CloseScene.html),
and `RestoreSceneManagerSetup`
(https://docs.unity3d.com/ScriptReference/SceneManagement.EditorSceneManager.RestoreSceneManagerSetup.html).

Before single-scene `scene load`, `scene create`, `scene-ext setup restore`, or
playmode target-scene launch, the bridge discards only blank untitled scenes
left by test cleanup. A blank scene is not dirty and has no roots, or only clean
default `Main Camera` and `Directional Light` roots. If real unsaved content or
dirty scene state remains, the command returns a structured error telling the
user to save or discard the scene manually.

Use `--save-current` only when the current scene should be explicitly saved.
The CLI sends the C# field `saveCurrentScene`; omitting the flag does not imply
an automatic save.

## scene (core)

### `scene load`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | positional | yes | Scene asset path |
| `--save-current` | flag | no | Explicitly save current scene before loading |

```bash
unity-bridge scene load Assets/Scenes/Main.unity
unity-bridge scene load Assets/Scenes/Test.unity --save-current
```

### `scene save`

Save the current scene. No arguments.

```bash
unity-bridge scene save
```

### `scene create`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | positional | yes | Path for the new scene |

```bash
unity-bridge scene create Assets/Scenes/NewLevel.unity
```

`scene create` also preflights the current scene state before replacing it. It
will discard blank untitled test scenes, but refuses to proceed if real unsaved
scene content would trigger Unity's save modal.

### `scene load-additive`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | positional | yes | Scene to load additively |
| `--save-current` | flag | no | Save current scene first |

```bash
unity-bridge scene load-additive Assets/Scenes/UI.unity
unity-bridge scene load-additive Assets/Scenes/UI.unity --save-current
```

### `scene unload`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | positional | yes | Scene to unload |
| `--keep` | flag | no | Keep objects in scene |

```bash
unity-bridge scene unload Assets/Scenes/UI.unity
```

### `scene set-active`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | positional | yes | Scene to set as active |

```bash
unity-bridge scene set-active Assets/Scenes/Main.unity
```

### `scene move-object`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OBJECT_PATH` | positional | yes | Root GameObject to move |
| `--target-scene` | TEXT | yes | Target scene path |

```bash
unity-bridge scene move-object "Player" --target-scene Assets/Scenes/Gameplay.unity
```

---

## scene-ext (extended scene management)

### `scene-ext setup save`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `NAME` | positional | yes | Layout name |

```bash
unity-bridge scene-ext setup save my-layout
```

### `scene-ext setup restore`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `NAME` | positional | yes | Layout name |

```bash
unity-bridge scene-ext setup restore my-layout
```

Restore replaces the active scene setup. It uses the same modal preflight as
single-scene load/create: blank untitled test scenes are discarded, real unsaved
content becomes a structured error.

### `scene-ext setup list`

List all saved scene setups. No arguments.

```bash
unity-bridge scene-ext setup list
```

### `scene-ext play-start`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--set` | PATH | no | Scene path for play start |
| `--clear` | flag | no | Clear play start scene |

```bash
unity-bridge scene-ext play-start                       # Get current
unity-bridge scene-ext play-start --set Assets/Scenes/Boot.unity
unity-bridge scene-ext play-start --clear
```

### `scene-ext cross-refs`

Detect cross-scene references. No arguments.

```bash
unity-bridge scene-ext cross-refs
```

### `scene-ext list-loaded`

List all loaded scenes. No arguments.

```bash
unity-bridge scene-ext list-loaded
```

### `scene-ext preview-create`

Create an empty preview scene. No arguments.

```bash
unity-bridge scene-ext preview-create
```

### `scene-ext preview-close`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `HANDLE` | positional (INT) | yes | Preview scene handle |

```bash
unity-bridge scene-ext preview-close 12345
```

---

## scene-view

Scene View camera control.

### `scene-view get`

Get the current Scene View camera state. No arguments.

```bash
unity-bridge scene-view get
```

### `scene-view set`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--pivot` | TEXT | no | Pivot position as X,Y,Z |
| `--rotation` | TEXT | no | Euler rotation as X,Y,Z |
| `--size` | FLOAT | no | Camera orbit size |
| `--ortho/--perspective` | flag | no | Projection mode |

```bash
unity-bridge scene-view set --pivot 0,5,0 --rotation 45,0,0 --size 10
unity-bridge scene-view set --ortho
```

### `scene-view toggle-2d`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--enable/--disable` | flag | no | Enable or disable 2D mode (default: enable) |

```bash
unity-bridge scene-view toggle-2d --enable
unity-bridge scene-view toggle-2d --disable
```

### `scene-view set-draw-mode`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `DRAW_MODE` | positional | yes | Textured, Wireframe, TexturedWire, etc. |

```bash
unity-bridge scene-view set-draw-mode Wireframe
```

---

## scene-template

### `scene-template list`

List available scene templates. No arguments.

```bash
unity-bridge scene-template list
```

### `scene-template create`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `SCENE_PATH` | positional | yes | Source scene path (.unity) |
| `OUTPUT` | positional | yes | Output template path |

```bash
unity-bridge scene-template create Assets/Scenes/Main.unity Assets/Templates/MainTemplate.asset
```

### `scene-template instantiate`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `TEMPLATE` | positional | yes | Template asset path |
| `--output` / `-o` | TEXT | no | Output scene path |

```bash
unity-bridge scene-template instantiate Assets/Templates/MainTemplate.asset
unity-bridge scene-template instantiate Assets/Templates/MainTemplate.asset -o Assets/Scenes/New.unity
```
