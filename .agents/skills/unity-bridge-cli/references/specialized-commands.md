# Specialized Commands Reference

Domain-specific commands: NavMesh, animation, terrain, tilemap, addressables,
reflection probes, occlusion culling, Project Auditor, Graph Toolkit, Entities,
Adaptive Performance, Multiplayer Play Mode, Timeline, Cinemachine,
Localization, Memory Profiler, and VFX asset inspection.

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

### `animation set-curve`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `CLIP_PATH` | positional | yes | Asset path to the AnimationClip |
| `PROPERTY_NAME` | positional | yes | Serialized property to animate |
| `--keyframes` | JSON | yes | Non-empty array of `{time, value}` objects |
| `--relative-path` | TEXT | no | Path relative to the animated root |
| `--component-type` | TEXT | no | Animated component type (default: Transform) |

### `animation add-event`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `CLIP_PATH` | positional | yes | Asset path to the AnimationClip |
| `--time` | FLOAT | yes | Event time in seconds |
| `--function` | TEXT | no | Function name (default: OnAnimationEvent) |
| `--string-param` | TEXT | no | String event parameter |
| `--int-param` | INT | no | Integer event parameter |
| `--float-param` | FLOAT | no | Float event parameter |

### `animation set-properties`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `CLIP_PATH` | positional | yes | Asset path to the AnimationClip |
| `--loop/--no-loop` | flag pair | no | Set clip looping |
| `--wrap-mode` | TEXT | no | Unity WrapMode name |
| `--frame-rate` | FLOAT | no | Clip frame rate |

```bash
unity-bridge animation create Assets/Animations/Walk.anim
unity-bridge animation create Assets/Animations/Walk.anim --frame-rate 30
unity-bridge animation info Assets/Animations/Walk.anim
unity-bridge animation curves Assets/Animations/Walk.anim
unity-bridge animation set-curve Assets/Animations/Walk.anim m_LocalPosition.y --keyframes '[{"time":0,"value":0},{"time":1,"value":1}]'
unity-bridge animation add-event Assets/Animations/Walk.anim --time 0.5 --function FootStep
unity-bridge animation set-properties Assets/Animations/Walk.anim --loop --wrap-mode Loop
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

### `terrain heights get`

Read a rectangular heightmap region with `--x`, `--y`, `--width`, and
`--height` options.

### `terrain set-heights`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--heights` | JSON | yes | Non-empty rectangular 2D numeric array |
| `--x` | INT | no | Start X coordinate (default: 0) |
| `--y` | INT | no | Start Y coordinate (default: 0) |
| `--terrain-name` | TEXT | no | Terrain name; defaults to active terrain |

### `terrain set-settings`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--size` / `-s` | TEXT | no | Terrain size as X,Y,Z |
| `--heightmap-resolution` | INT | no | Heightmap resolution |
| `--terrain-name` | TEXT | no | Terrain name; defaults to active terrain |

```bash
unity-bridge terrain create
unity-bridge terrain create -n "Island" -s 500,100,500
unity-bridge terrain info
unity-bridge terrain info "Island"
unity-bridge terrain set-heights --heights '[[0.1,0.2],[0.3,0.4]]' --x 4 --y 6
unity-bridge terrain set-settings --terrain-name Island --size 500,100,500
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

### `tilemap fill-box`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `TILEMAP_PATH` | positional | yes | Hierarchy path to Tilemap |
| `TILE_PATH` | positional | yes | Asset path to tile |
| `--start-x` / `--start-y` | INT | yes | Inclusive start cell |
| `--end-x` / `--end-y` | INT | yes | Inclusive end cell |

### `tilemap compress-bounds`

Compress used bounds. Takes TILEMAP_PATH as a positional argument.

```bash
unity-bridge tilemap set-tile "Grid/Tilemap" Assets/Tiles/Grass.asset --x 5 --y 3
unity-bridge tilemap get-tile "Grid/Tilemap" --x 5 --y 3
unity-bridge tilemap fill-box "Grid/Tilemap" Assets/Tiles/Grass.asset --start-x 0 --start-y 0 --end-x 5 --end-y 5
unity-bridge tilemap clear "Grid/Tilemap"
unity-bridge tilemap bounds "Grid/Tilemap"
unity-bridge tilemap compress-bounds "Grid/Tilemap"
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

### `addressables profiles` / `addressables labels` / `addressables schemas`

No arguments.

```bash
unity-bridge addressables profiles
unity-bridge addressables labels
unity-bridge addressables schemas
```

### `addressables set-profile`

Set the active Addressables profile by id or by name.

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--id` | TEXT | no | Addressables profile id |
| `--name` | TEXT | no | Addressables profile name |

```bash
unity-bridge addressables set-profile --name Default
unity-bridge addressables set-profile --id 0123456789abcdef
```

### `addressables set-label`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `ASSET_PATH` | positional | yes | Addressable asset path |
| `LABEL` | positional | yes | Label name |
| `--enable/--disable` | flag pair | no | Add or remove the label |
| `--force` | flag | no | Create missing label when supported |

```bash
unity-bridge addressables set-label Assets/Prefabs/Enemy.prefab Enemy --enable --force
unity-bridge addressables set-label Assets/Prefabs/Enemy.prefab Deprecated --disable
```

### `addressables analyze`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--rule` | TEXT | no | Analyze rule to run |
| `--output` | TEXT | no | Output report path |

```bash
unity-bridge addressables analyze
unity-bridge addressables analyze --rule "Check Duplicate Bundle Dependencies" --output Reports/addressables-analyze.json
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

---

## timeline

Requires `com.unity.timeline`. Uses reflection internally (no compile-time
dependency), so it degrades to a clean error if the package is absent.
Parent-track grouping is not supported in v1 — only top-level tracks.
Clips are addressed by `(TRACK_INDEX, CLIP_INDEX)`; both are positions at
query time, not stable ids — re-run `get-clips` after any mutation before
addressing a clip again.

### `timeline create-track`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `TIMELINE_ASSET_PATH` | positional | yes | Asset path to the TimelineAsset |
| `TRACK_TYPE` | positional | yes | Short type name, e.g. `AnimationTrack`, `AudioTrack` |
| `--track-name` | TEXT | no | Display name for the new track |

### `timeline create-clip`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `TIMELINE_ASSET_PATH` | positional | yes | Asset path to the TimelineAsset |
| `TRACK_INDEX` | positional | yes | Target track index |
| `--clip-asset-path` | TEXT | no | Asset path to a PlayableAsset to wrap (default clip if omitted) |

### `timeline get-clips`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `TIMELINE_ASSET_PATH` | positional | yes | Asset path to the TimelineAsset |
| `TRACK_INDEX` | positional | yes | Target track index |

### `timeline delete-clip`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `TIMELINE_ASSET_PATH` | positional | yes | Asset path to the TimelineAsset |
| `TRACK_INDEX` | positional | yes | Target track index |
| `CLIP_INDEX` | positional | yes | Clip index within that track |

### `timeline get-info`

List tracks on a TimelineAsset. Takes `TIMELINE_ASSET_PATH` positional arg.

### `timeline evaluate`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `DIRECTOR_PATH` | positional | yes | Hierarchy path to a GameObject with a PlayableDirector |
| `--time` | FLOAT | no | Time in seconds to scrub to before evaluating |
| `--timeline-asset-path` | TEXT | no | Rebind the director's TimelineAsset before evaluating |

```bash
unity-bridge timeline create-track Assets/Timelines/Intro.playable AnimationTrack --track-name "Camera"
unity-bridge timeline create-clip Assets/Timelines/Intro.playable 0
unity-bridge timeline get-clips Assets/Timelines/Intro.playable 0
unity-bridge timeline delete-clip Assets/Timelines/Intro.playable 0 1
unity-bridge timeline get-info Assets/Timelines/Intro.playable
unity-bridge timeline evaluate "Directors/IntroDirector" --time 2.5
```

---

## cinemachine

Requires `com.unity.cinemachine` 3.x (`Unity.Cinemachine.CinemachineCamera`,
not the 2.x `CinemachineVirtualCamera`). Uses reflection internally.
`list-cameras` walks the full scene (including inactive cameras) rather than
relying on `CinemachineCore`, which only tracks currently-active cameras.

### `cinemachine list-cameras`

No arguments. Lists every CinemachineCamera in the scene.

### `cinemachine info`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `CAMERA_PATH` | positional | yes | Hierarchy path to a CinemachineCamera |

### `cinemachine set-priority`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `CAMERA_PATH` | positional | yes | Hierarchy path to a CinemachineCamera |
| `PRIORITY` | positional | yes | New priority value |

### `cinemachine set-lens`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `CAMERA_PATH` | positional | yes | Hierarchy path to a CinemachineCamera |
| `--fov` | FLOAT | no | Vertical field of view in degrees |
| `--ortho-size` | FLOAT | no | Orthographic camera half-size |
| `--near-clip` | FLOAT | no | Near clip plane distance |
| `--far-clip` | FLOAT | no | Far clip plane distance |
| `--dutch` | FLOAT | no | Dutch (roll) angle in degrees |

### `cinemachine set-follow` / `cinemachine set-lookat`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `CAMERA_PATH` | positional | yes | Hierarchy path to a CinemachineCamera |
| `TARGET_PATH` | positional | yes | Hierarchy path to the Follow/LookAt target (`""` clears it) |

### `cinemachine active`

No arguments. Reads the live/blended camera via `CinemachineBrain`.

```bash
unity-bridge cinemachine list-cameras
unity-bridge cinemachine info "Cameras/MainVCam"
unity-bridge cinemachine set-priority "Cameras/MainVCam" 20
unity-bridge cinemachine set-lens "Cameras/MainVCam" --fov 50 --near-clip 0.3
unity-bridge cinemachine set-follow "Cameras/MainVCam" "Player"
unity-bridge cinemachine active
```

---

## localization

Requires `com.unity.localization`. Editor-only API — not available in player
builds, which is fine since this only runs through the bridge.

### `localization list-locales` / `localization get-selected-locale`

No arguments.

### `localization add-locale` / `localization remove-locale` / `localization set-selected-locale`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `LOCALE_CODE` | positional | yes | Locale code, e.g. `fr`, `de` |

### `localization create-string-table-collection` / `localization get-string-table-collection`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `TABLE_COLLECTION_NAME` | positional | yes | String table collection name |

### `localization add-entry`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `TABLE_COLLECTION_NAME` | positional | yes | String table collection name |
| `KEY` | positional | yes | Entry key |
| `VALUE` | positional | yes | Entry value |

### `localization export-csv` / `localization import-csv` / `localization export-xliff` / `localization import-xliff`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `TABLE_COLLECTION_NAME` | positional | yes | String table collection name |
| `FILE_PATH` | positional | yes | Source/destination file path |

```bash
unity-bridge localization list-locales
unity-bridge localization add-locale fr
unity-bridge localization set-selected-locale de
unity-bridge localization create-string-table-collection MyStrings
unity-bridge localization add-entry MyStrings greeting "Hello"
unity-bridge localization export-csv MyStrings Reports/strings.csv
unity-bridge localization import-csv MyStrings Reports/strings.csv
```

---

## memory-profiler

Wraps the core Unity `Unity.Profiling.Memory.MemoryProfiler.TakeSnapshot` API
(ships with the Editor, no package install needed). Capture only — loading
or diffing an existing `.snap` file has no public Unity API and is out of
scope. Async/callback-based on the Unity side; the CLI call blocks until the
snapshot write completes or the command times out (default 120s).

### `memory-profiler take-snapshot`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--path` | TEXT | no | Destination `.snap` path (defaults to a bridge-managed path under `.claude/unity/memory-snapshots/`) |
| `--capture-flags` | TEXT | no | Comma-separated `CaptureFlags` names, e.g. `ManagedObjects,NativeObjects` (defaults to `ManagedObjects,NativeObjects,NativeAllocations`) |

```bash
unity-bridge memory-profiler take-snapshot
unity-bridge memory-profiler take-snapshot --path Reports/heap.snap --capture-flags ManagedObjects,NativeObjects
```

---

## vfx

Requires `com.unity.visualeffectgraph`. Read-only asset inspection only —
`VisualEffectAsset.GetEvents`/`GetExposedProperties` are the only public API
for this; full graph authoring (add/remove nodes, systems, blocks) has no
public Unity API and is out of scope, do not attempt it via other commands.

### `vfx get-info`

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--asset-path` | TEXT | no | Asset path to the VisualEffectAsset (exactly one of `--asset-path`/`--guid` required) |
| `--guid` | TEXT | no | GUID of the VisualEffectAsset (exactly one of `--asset-path`/`--guid` required) |

```bash
unity-bridge vfx get-info --asset-path Assets/VFX/Explosion.vfx
unity-bridge vfx get-info --guid 0123456789abcdef0123456789abcdef
```
