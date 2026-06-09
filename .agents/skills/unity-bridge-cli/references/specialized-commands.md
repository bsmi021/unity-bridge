# Specialized Commands Reference

Domain-specific commands: NavMesh, animation, terrain, tilemap, addressables,
reflection probes, occlusion culling, Project Auditor, Graph Toolkit, Entities,
Adaptive Performance, and Multiplayer Play Mode.

---

## navmesh

### `navmesh bake`

Bake NavMesh for the active scene. No arguments.

### `navmesh clear`

Clear all baked NavMesh data. No arguments.

### `navmesh settings`

Get or set NavMesh build settings. Read-only if no options provided.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--agent-radius` | FLOAT | no | Agent radius |
| `--agent-height` | FLOAT | no | Agent height |
| `--max-slope` | FLOAT | no | Maximum slope angle |
| `--step-height` | FLOAT | no | Maximum step height |

### `navmesh areas`

Get NavMesh area names and costs. No arguments.

```bash
unity-bridge navmesh bake
unity-bridge navmesh clear
unity-bridge navmesh settings
unity-bridge navmesh settings --agent-radius 0.5 --agent-height 2.0
unity-bridge navmesh areas
```

---

## animation

### `animation create`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `CLIP_PATH` | positional | yes | Asset path for the new clip |
| `--frame-rate` | FLOAT | no | Frame rate |

### `animation info`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `CLIP_PATH` | positional | yes | Asset path to the AnimationClip |

### `animation curves`

List all curve bindings on a clip. Takes CLIP_PATH positional arg.

```bash
unity-bridge animation create Assets/Animations/Walk.anim
unity-bridge animation create Assets/Animations/Walk.anim --frame-rate 30
unity-bridge animation info Assets/Animations/Walk.anim
unity-bridge animation curves Assets/Animations/Walk.anim
```

---

## terrain

### `terrain create`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--name` / `-n` | TEXT | no | Terrain name |
| `--size` / `-s` | TEXT | no | Terrain size as X,Y,Z |

### `terrain info`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `TERRAIN_NAME` | positional | no | Terrain name (uses active terrain if omitted) |

### `terrain heights` (subgroup)

Height get/set operations.

```bash
unity-bridge terrain create
unity-bridge terrain create -n "Island" -s 500,100,500
unity-bridge terrain info
unity-bridge terrain info "Island"
```

---

## tilemap

### `tilemap set-tile`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `TILEMAP_PATH` | positional | yes | Hierarchy path to Tilemap |
| `TILE_PATH` | positional | yes | Asset path to tile |
| `--x` | INT | no | Cell X (default: 0) |
| `--y` | INT | no | Cell Y (default: 0) |
| `--z` | INT | no | Cell Z (default: 0) |

### `tilemap get-tile`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `TILEMAP_PATH` | positional | yes | Hierarchy path to Tilemap |
| `--x` | INT | no | Cell X (default: 0) |
| `--y` | INT | no | Cell Y (default: 0) |

### `tilemap clear` / `tilemap bounds`

Both take TILEMAP_PATH as positional arg.

```bash
unity-bridge tilemap set-tile "Grid/Tilemap" Assets/Tiles/Grass.asset --x 5 --y 3
unity-bridge tilemap get-tile "Grid/Tilemap" --x 5 --y 3
unity-bridge tilemap clear "Grid/Tilemap"
unity-bridge tilemap bounds "Grid/Tilemap"
```

---

## addressables

Requires `com.unity.addressables` package.

### `addressables list-groups` / `addressables build` / `addressables clean-cache`

No arguments.

### `addressables mark`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `ASSET_PATH` | positional | yes | Asset path to mark as addressable |

### `addressables set-address`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `ASSET_PATH` | positional | yes | Asset path |
| `ADDRESS` | positional | yes | Address key |

```bash
unity-bridge addressables list-groups
unity-bridge addressables build
unity-bridge addressables clean-cache
unity-bridge addressables mark Assets/Prefabs/Enemy.prefab
unity-bridge addressables set-address Assets/Prefabs/Enemy.prefab "enemies/basic"
```

---

## reflection-probe

### `reflection-probe bake`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `GAME_OBJECT_PATH` | positional | no | Hierarchy path (omit with --all) |
| `--all` | flag | no | Bake all probes in scene |

### `reflection-probe list`

List all reflection probes. No arguments.

### `reflection-probe info`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `GAME_OBJECT_PATH` | positional | yes | Hierarchy path to the probe |

```bash
unity-bridge reflection-probe bake "Environment/Probe1"
unity-bridge reflection-probe bake --all
unity-bridge reflection-probe list
unity-bridge reflection-probe info "Environment/Probe1"
```

---

## occlusion

### `occlusion bake` / `occlusion clear` / `occlusion settings`

All no arguments.

```bash
unity-bridge occlusion bake
unity-bridge occlusion clear
unity-bridge occlusion settings
```

---

## project-auditor

Requires Unity Project Auditor package/API availability.

```bash
unity-bridge project-auditor availability
unity-bridge project-auditor run --output Reports/project-audit.json
unity-bridge project-auditor load Reports/project-audit.json
```

---

## graph-toolkit

Read-only Graph Toolkit package and graph asset inspection.

```bash
unity-bridge graph-toolkit availability
unity-bridge graph-toolkit list-assets
unity-bridge graph-toolkit inspect Assets/Graphs/Gameplay.asset
unity-bridge graph-toolkit export Assets/Graphs/Gameplay.asset
```

---

## entities

Read-only Unity Entities package, world, system, and archetype inspection.

```bash
unity-bridge entities availability
unity-bridge entities list-worlds
unity-bridge entities world-summary --world "Default World"
unity-bridge entities list-systems --world "Default World"
unity-bridge entities list-archetypes --max-archetypes 25
```

---

## adaptive-performance

Read-only Adaptive Performance package and scaler profile inspection.

```bash
unity-bridge adaptive-performance availability
unity-bridge adaptive-performance settings
unity-bridge adaptive-performance list-profiles
unity-bridge adaptive-performance inspect-profile Assets/Settings/AdaptivePerformanceProfile.asset
```

---

## multiplayer-playmode

Read-only Multiplayer Play Mode package and current player inspection.

```bash
unity-bridge multiplayer-playmode availability
unity-bridge multiplayer-playmode current-player
unity-bridge multiplayer-playmode packages
```
