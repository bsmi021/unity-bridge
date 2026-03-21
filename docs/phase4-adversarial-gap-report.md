# Phase 4+ Adversarial Gap Report: Unity Editor Parity Analysis

**Date:** 2026-03-21
**Branch:** `feature/expansion-phases-1-3`
**Standard:** If a human can do it through the Unity Editor UI, the CLI should be able to do it too.
**Method:** Systematic walk-through of every Unity Editor window, menu, and workflow against the 39 MCP tools and 32 C# command handlers.

---

## Table of Contents

1. [Still Missing After Phase 4](#1-still-missing-after-phase-4)
2. [Partially Covered](#2-partially-covered)
3. [Edge Cases in Existing Commands](#3-edge-cases-in-existing-commands)
4. [Recommended Phase 5 Priorities](#4-recommended-phase-5-priorities)

---

## Phase 4 Scope (Already Being Implemented)

For reference, Phase 4 covers:
- Set Selection, Transform manipulation, SerializedProperty, EditorPrefs
- Build Settings Scene list management, Duplicate GameObjects
- Physics config, Quality settings, Editor settings, Tags/Layers management
- Bugfixes: ObjectFactory, SerializedProperty for private fields, Undo-aware destroy

---

## 1. Still Missing After Phase 4

### 1.1 Hierarchy Window: Primitive and Object Creation

**Gap:** The `gameobject-operation` handler only supports `create` (empty GameObject), `delete`, and `rename`. A human can right-click the Hierarchy and create dozens of object types.

| Missing Operation | Frequency | Automation Value | Complexity |
|---|---|---|---|
| Create primitives (Cube, Sphere, Capsule, Cylinder, Plane, Quad) | daily | high | simple |
| Create Light types (Directional, Point, Spot, Area) | weekly | high | simple |
| Create Camera | weekly | high | simple |
| Create Audio Source | weekly | medium | simple |
| Create Particle System | weekly | medium | simple |
| Create UI elements (Canvas, Button, Text, Image, ScrollView, Panel, Slider, Toggle, Dropdown, InputField) | daily | high | medium |
| Create 2D objects (Sprite, SpriteMask, Tilemap, TilemapGrid) | weekly | medium | medium |
| Create empty child (shortcut alt+shift+N) | daily | high | simple |
| Create Volumes (Global/Local for URP/HDRP post-processing) | weekly | medium | medium |

**Why this matters:** Scene setup automation is one of the top use cases. Without primitive creation, users must use `execute-menu-item` with paths like `GameObject/3D Object/Cube`, which is fragile and undiscoverable.

**Implementation:** Add a `primitiveType` parameter to `gameobject-operation create` that calls `ObjectFactory.CreatePrimitive()` or `new GameObject().AddComponent<T>()` for non-primitives.

---

### 1.2 Inspector: Remove Component

**Gap:** `add-component` exists but there is no `remove-component` command.

| Missing Operation | Frequency | Automation Value | Complexity |
|---|---|---|---|
| Remove component from GameObject | daily | high | simple |

**Why this matters:** Automated refactoring and scene cleanup require the ability to remove components, not just add them.

**Implementation:** Add `remove-component` command type. C# side: `Undo.DestroyObjectImmediate(component)`.

---

### 1.3 Inspector: Enable/Disable Components

**Gap:** No way to enable or disable a component (the checkbox in the Inspector). `set-component-data` only writes to fields, not to `Behaviour.enabled`.

| Missing Operation | Frequency | Automation Value | Complexity |
|---|---|---|---|
| Enable/disable component | daily | high | simple |

**Implementation:** Either add a `component-enabled` operation or extend `set-component-data` to recognize `enabled` as a special pseudo-field that maps to `Behaviour.enabled` or `Renderer.enabled`.

---

### 1.4 Inspector: Enable/Disable GameObject

**Gap:** No way to toggle `GameObject.activeSelf` (the checkbox next to the name in the Inspector). Phase 4 mentions transform manipulation but not active state.

| Missing Operation | Frequency | Automation Value | Complexity |
|---|---|---|---|
| Enable/disable (activate/deactivate) GameObject | daily | high | simple |

**Implementation:** Add `set-active` operation to `gameobject-operation`, calling `go.SetActive(bool)` with Undo support.

---

### 1.5 Inspector: Copy/Paste Component Values

**Gap:** In the Editor, users can right-click a component header to Copy Component, Paste Component Values, or Paste Component As New.

| Missing Operation | Frequency | Automation Value | Complexity |
|---|---|---|---|
| Copy component values | weekly | medium | medium |
| Paste component values (to same type on different GO) | weekly | medium | medium |
| Paste component as new | rarely | low | medium |

**Implementation:** Serialize all component fields to JSON (like `get-component-data` output), then apply them to a target component via `set-component-data`.

---

### 1.6 Inspector: Reset Component to Defaults

**Gap:** The Inspector's Reset option restores a component to its default values.

| Missing Operation | Frequency | Automation Value | Complexity |
|---|---|---|---|
| Reset component to defaults | weekly | medium | medium |

**Implementation:** C# side: `Undo.RecordObject(component, "Reset"); var newComp = go.AddComponent(type); CopyValues(newComp, component); DestroyImmediate(newComp);` or use `EditorUtility.SetObjectEnabled`.

---

### 1.7 Project Window: Create ScriptableObject Instances (Custom Types)

**Gap:** `asset-extended-operation create` supports `ScriptableObject`, `Material`, and `AnimatorController` only. In the Editor, users can right-click > Create and choose any `[CreateAssetMenu]`-attributed ScriptableObject subclass.

| Missing Operation | Frequency | Automation Value | Complexity |
|---|---|---|---|
| Create ScriptableObject instance of custom subtype | daily | high | medium |
| Create Shader Graph / Shader file | weekly | medium | medium |
| Create Assembly Definition (.asmdef) | weekly | high | simple |
| Create Assembly Definition Reference (.asmref) | weekly | medium | simple |
| Create TextAsset / JSON file | weekly | medium | simple |
| Create RenderTexture | weekly | medium | simple |
| Create PhysicsMaterial / PhysicsMaterial2D | weekly | medium | simple |
| Create AnimationClip | weekly | medium | simple |
| Create Timeline asset | rarely | low | medium |
| Create ComputeShader | rarely | low | simple |

**Implementation:** Extend `CreateAssetByType()` in `AssetExtendedHelpers.cs` to support more types. For custom ScriptableObjects, use `ScriptableObject.CreateInstance(typeName)` with `System.Type.GetType()` resolution.

---

### 1.8 Project Window: Reimport All

**Gap:** `refresh-assets` calls `AssetDatabase.Refresh()`. The Editor's "Assets > Reimport All" calls `AssetDatabase.ImportAsset("Assets", ImportAssetOptions.ImportRecursive)`, which is more aggressive.

| Missing Operation | Frequency | Automation Value | Complexity |
|---|---|---|---|
| Reimport All (recursive full reimport) | rarely | medium | simple |

**Implementation:** Add `reimport-all` operation to `asset-extended-operation` or `refresh-assets`.

---

### 1.9 Project Window: Find References in Scene

**Gap:** No command to find which scene GameObjects reference a given asset. This is a core debugging workflow in Unity.

| Missing Operation | Frequency | Automation Value | Complexity |
|---|---|---|---|
| Find references to asset in loaded scenes | daily | high | complex |

**Implementation:** Iterate all components in loaded scenes, check their serialized fields for references to the target asset via `SerializedObject`/`SerializedProperty` traversal.

---

### 1.10 Project Settings: Missing Settings Windows

Phase 4 covers Physics, Quality, Editor Settings, Tags/Layers. Still missing:

| Missing Settings | Frequency | Automation Value | Complexity |
|---|---|---|---|
| **Time Settings** (fixed timestep, time scale, max delta time) | weekly | high | simple |
| **Audio Settings** (global volume, spatializer plugin, DSP buffer size) | rarely | low | simple |
| **Graphics Settings** (scriptable render pipeline asset, transparency sort, default render pipeline) | weekly | high | medium |
| **Input Manager** (legacy input axes definition) | rarely | low | medium |
| **Preset Manager** (default presets per type) | rarely | low | complex |
| **Script Execution Order** (`MonoScript` execution ordering) | weekly | medium | medium |
| **TextMeshPro Settings** (default font, SDF atlas resolution) | rarely | low | simple |
| **Version Control Settings** (VCS mode, visible meta files) | rarely | low | simple |
| **Memory Settings** (player memory allocator config) | rarely | low | simple |
| **Adaptive Performance** (Unity 6 thermal/performance management) | rarely | low | medium |

---

### 1.11 Build Settings: Platform Switching

**Gap:** The build handler can trigger builds and get settings, but cannot switch the active build target platform. This requires `EditorUserBuildSettings.SwitchActiveBuildTarget()`.

| Missing Operation | Frequency | Automation Value | Complexity |
|---|---|---|---|
| Switch active build target/platform | weekly | high | medium |
| Get list of installed build targets | weekly | medium | simple |
| Set build options (development, autoconnect profiler, deep profiling, script debugging, compression) | weekly | high | simple |

**Implementation:** Add `switch-platform` operation to `build-operation`. Must handle the async domain reload that follows platform switching.

---

### 1.12 Animation Window Operations

**Gap:** The Animator controller handler is comprehensive (22 operations), but there is no way to work with individual Animation Clips at the keyframe level.

| Missing Operation | Frequency | Automation Value | Complexity |
|---|---|---|---|
| Create AnimationClip asset | weekly | medium | simple |
| Add/edit keyframes on AnimationClip | weekly | medium | complex |
| Edit animation curves (AnimationCurve) | weekly | medium | complex |
| Add animation events | rarely | low | medium |
| Set animation clip properties (loop, root motion, wrap mode) | weekly | medium | simple |

---

### 1.13 Lighting Window: Advanced Operations

**Gap:** Lightmap baking exists but several Lighting window features are missing.

| Missing Operation | Frequency | Automation Value | Complexity |
|---|---|---|---|
| **Set lightmap settings** (currently read-only) | weekly | high | medium |
| Place/configure Light Probes | weekly | medium | complex |
| Bake Reflection Probes | weekly | medium | medium |
| Set environment lighting (skybox material, ambient color, ambient mode) | weekly | high | medium |
| Set fog settings (enable, mode, density, color) | weekly | medium | simple |
| Generate lighting for specific scenes in multi-scene setup | rarely | low | medium |

**Implementation for settings:** Extend `lightmap-operation` with a `set-settings` operation that writes to `Lightmapping.lightingSettings` properties.

---

### 1.14 Navigation/NavMesh Window

**Gap:** Entire navigation system is uncovered.

| Missing Operation | Frequency | Automation Value | Complexity |
|---|---|---|---|
| Bake NavMesh | weekly | medium | medium |
| Clear NavMesh | weekly | medium | simple |
| Get NavMesh settings | weekly | medium | simple |
| Set NavMesh agent parameters | weekly | medium | simple |
| Set NavMesh area costs | rarely | low | simple |
| Add/configure OffMeshLinks | rarely | low | medium |

---

### 1.15 Occlusion Culling Window

| Missing Operation | Frequency | Automation Value | Complexity |
|---|---|---|---|
| Bake occlusion culling | rarely | low | medium |
| Clear occlusion data | rarely | low | simple |
| Get occlusion settings | rarely | low | simple |

---

### 1.16 Console: Log Custom Messages

**Gap:** Can read and clear the console, but cannot write custom log messages from the CLI into the Unity Console.

| Missing Operation | Frequency | Automation Value | Complexity |
|---|---|---|---|
| Log message to Unity Console (Info/Warning/Error) | weekly | medium | simple |

**Implementation:** Call `Debug.Log()`, `Debug.LogWarning()`, `Debug.LogError()` in a new operation.

---

### 1.17 Scene View: Manipulation

**Gap:** `focus-object` frames a GameObject, but many Scene View controls are inaccessible.

| Missing Operation | Frequency | Automation Value | Complexity |
|---|---|---|---|
| Set Scene View camera position/rotation | weekly | medium | simple |
| Toggle 2D/3D scene view mode | rarely | low | simple |
| Set scene view gizmo visibility | rarely | low | simple |
| Toggle scene view overlays (grid, skybox, fog, effects) | rarely | low | simple |
| Lock Scene View to specific camera | rarely | low | simple |
| Set Scene View draw mode (wireframe, shaded, etc.) | rarely | low | simple |

---

### 1.18 Game View: Configuration

| Missing Operation | Frequency | Automation Value | Complexity |
|---|---|---|---|
| Set game view resolution/aspect ratio | weekly | medium | medium |
| Toggle maximize on play | rarely | low | simple |
| Set target display index | rarely | low | simple |
| Get current game view resolution | weekly | medium | simple |

---

### 1.19 Profiler: Advanced Controls

**Gap:** `profiler-sample` captures a single snapshot. The Profiler window offers much more.

| Missing Operation | Frequency | Automation Value | Complexity |
|---|---|---|---|
| Start/stop profiler recording | weekly | medium | simple |
| Save profiler data to file | weekly | medium | simple |
| Load profiler data from file | rarely | low | simple |
| Enable/disable specific profiler modules | weekly | medium | simple |
| Deep profiling toggle | rarely | low | simple |
| Memory profiler snapshot | weekly | medium | medium |

---

### 1.20 Addressables System

**Gap:** Unity Addressables is widely used but has zero coverage.

| Missing Operation | Frequency | Automation Value | Complexity |
|---|---|---|---|
| List Addressable groups | weekly | medium | medium |
| Build Addressable content | weekly | high | medium |
| Mark asset as Addressable | weekly | medium | medium |
| Set Addressable address/label | weekly | medium | medium |
| Clean Addressable build cache | weekly | medium | simple |

---

### 1.21 Sprite Editor / 2D Workflows

| Missing Operation | Frequency | Automation Value | Complexity |
|---|---|---|---|
| Set sprite import mode (single/multiple/polygon) | weekly | medium | simple |
| Define sprite slicing (grid, automatic, manual) | weekly | medium | complex |
| Set sprite pivot point | weekly | medium | simple |
| Create Sprite Atlas | weekly | medium | medium |
| Configure Sprite Atlas packing settings | rarely | low | medium |

---

### 1.22 Terrain Operations

| Missing Operation | Frequency | Automation Value | Complexity |
|---|---|---|---|
| Create Terrain | rarely | medium | medium |
| Import/export heightmap | rarely | medium | medium |
| Set terrain layers (texture painting data) | rarely | medium | complex |
| Get terrain settings | rarely | low | simple |
| Place trees/details programmatically | rarely | medium | complex |

---

### 1.23 Window Management

| Missing Operation | Frequency | Automation Value | Complexity |
|---|---|---|---|
| Open/close Editor windows | rarely | low | simple |
| List open Editor windows | rarely | low | simple |
| Dock/undock windows | rarely | low | complex |

---

## 2. Partially Covered

### 2.1 PlayerSettings: Very Limited Property Set

**Current:** Only 3 settable properties: `companyName`, `productName`, `bundleVersion`. The `get` operation returns 9 properties.

**Missing from PlayerSettings that a human can set in the Inspector:**

| Missing Property | Frequency | Automation Value | Complexity |
|---|---|---|---|
| `applicationIdentifier` (bundle ID) | weekly | high | simple |
| `defaultIsFullScreen` | weekly | medium | simple |
| `runInBackground` | weekly | medium | simple |
| `apiCompatibilityLevel` (per platform) | weekly | high | simple |
| `scriptingBackend` (IL2CPP/Mono) | weekly | high | simple |
| `targetArchitecture` (ARM64, etc.) | weekly | high | simple |
| Icon settings (default icon, platform icons) | rarely | medium | medium |
| Splash screen settings | rarely | low | medium |
| Resolution and presentation settings | weekly | medium | simple |
| Android-specific (minSdkVersion, targetSdkVersion, keystoreSettings) | weekly | high | medium |
| iOS-specific (cameraUsageDescription, locationUsageDescription) | weekly | high | simple |
| WebGL-specific (template, memory size, compression) | rarely | medium | simple |
| Color space (linear/gamma) | rarely | high | simple |
| Auto Graphics API settings | rarely | medium | simple |
| Managed Stripping Level | rarely | medium | simple |
| Incremental GC | rarely | low | simple |
| Allow unsafe code | weekly | medium | simple |

**Recommendation:** Expand `GETTERS` and `SETTERS` dictionaries in `PlayerSettingsCommandHandler.cs` to cover at least the top 10 most-used properties. This is pure dictionary expansion, no new architecture needed.

---

### 2.2 GetComponentData / SetComponentData: Public Fields Only

**Current:** Both handlers use `BindingFlags.Public | BindingFlags.Instance` for field access. This means:
- `[SerializeField] private` fields (Unity best practice) are invisible
- Properties (e.g., `Transform.position`, `Rigidbody.mass`) are inaccessible
- No support for `[SerializeField]` on private fields

**Phase 4 notes mention** SerializedProperty for private fields, which is the correct fix.

| Gap Detail | Frequency | Automation Value | Complexity |
|---|---|---|---|
| Read `[SerializeField] private` fields | daily | high | medium |
| Read/write Unity properties (not just fields) | daily | high | medium |
| Support for arrays/lists in component data | weekly | high | medium |
| Support for enum fields (currently serialize as int) | weekly | medium | simple |
| Support for UnityEngine.Object references (show path/GUID instead of InstanceID) | weekly | high | medium |

**Note:** Phase 4's SerializedProperty work should address most of these, but the scope should explicitly include properties, arrays, and Object references.

---

### 2.3 Material Operations: Missing Common Properties

**Current:** Material handler supports create, modify, get-properties, set-shader. But:

| Gap Detail | Frequency | Automation Value | Complexity |
|---|---|---|---|
| Enable/disable material keywords (e.g., `_EMISSION`) | weekly | high | simple |
| Get/set render queue value | weekly | medium | simple |
| Get/set material pass enable/disable | rarely | low | simple |
| Material variant support (Unity 6 feature) | rarely | medium | medium |
| Copy material properties between materials | weekly | medium | simple |

---

### 2.4 Build Operations: Missing Options

**Current:** Build handler supports `build`, `get-settings`, `validate`, `get-target` with only `development` as a build option.

| Missing Build Option | Frequency | Automation Value | Complexity |
|---|---|---|---|
| `BuildOptions.AutoRunPlayer` | weekly | medium | simple |
| `BuildOptions.ShowBuiltPlayer` | rarely | low | simple |
| `BuildOptions.ConnectWithProfiler` | weekly | medium | simple |
| `BuildOptions.AllowDebugging` | weekly | medium | simple |
| `BuildOptions.CompressWithLz4` / `Lz4HC` | weekly | medium | simple |
| `BuildOptions.CleanBuildCache` | weekly | medium | simple |
| `BuildOptions.DetailedBuildReport` | weekly | medium | simple |
| Custom scene list (not just build settings scenes) | weekly | high | simple |
| Incremental build support | rarely | medium | medium |
| Sub-target (e.g., Server) | rarely | medium | simple |

---

### 2.5 Scene Operations: Missing Additive Loading

**Current:** `scene-operation load` always uses `OpenSceneMode.Single`. In the Editor, users routinely use additive scene loading.

| Gap Detail | Frequency | Automation Value | Complexity |
|---|---|---|---|
| Load scene additively (`OpenSceneMode.Additive`) | daily | high | simple |
| Load scene additively without loading (`OpenSceneMode.AdditiveWithoutLoading`) | weekly | medium | simple |
| Unload specific scene (from multi-scene setup) | weekly | medium | simple |
| Set active scene (when multiple loaded) | weekly | medium | simple |
| Move GameObject between loaded scenes | weekly | medium | simple |

**Note:** The `scene-setup-operation` handler has `list-loaded` and `preview-create/close`, but lacks basic additive load/unload. The gap is in `scene-operation` not supporting `mode: "additive"`.

---

### 2.6 Animator: Missing Blend Tree Operations

**Current:** 22 operations cover layers, states, transitions, parameters. Missing:

| Gap Detail | Frequency | Automation Value | Complexity |
|---|---|---|---|
| Create/edit Blend Trees | weekly | medium | complex |
| Set state machine behaviours | weekly | medium | medium |
| Animator Override Controllers | weekly | medium | medium |
| Sub-state machines | rarely | low | complex |
| Avatar Mask creation/editing | rarely | low | medium |
| IK settings per layer | rarely | low | simple |

---

### 2.7 Prefab Editing Mode

**Current:** Prefab operations work on instances in scenes and prefab assets. But:

| Gap Detail | Frequency | Automation Value | Complexity |
|---|---|---|---|
| Enter/exit prefab editing mode (`PrefabStageUtility.OpenPrefab`) | weekly | medium | medium |
| Make changes inside prefab editing context | weekly | medium | medium |
| Nested prefab manipulation | weekly | medium | complex |
| Prefab variant creation | weekly | medium | medium |

---

### 2.8 Test Runner: Missing Features

**Current:** `run-tests` and `list-tests` cover the basics.

| Gap Detail | Frequency | Automation Value | Complexity |
|---|---|---|---|
| Run specific test by full name (not just filter) | weekly | high | simple |
| Get test results after a run | daily | high | simple |
| Cancel running tests | rarely | medium | medium |
| Run tests with custom arguments | rarely | low | medium |
| Code coverage integration | rarely | medium | complex |

---

## 3. Edge Cases in Existing Commands

### 3.1 `SetComponentDataCommandHandler` Does Not Use Undo

**Severity:** Major

The `SetComponentDataCommandHandler.cs` modifies component fields directly via reflection (`field.SetValue`) without calling `Undo.RecordObject()` first. This means:
- Changes cannot be undone
- Inconsistent with other handlers that properly use Undo
- Phase 4's "undo-aware destroy" bugfix should be expanded to cover this

**Fix:** Add `Undo.RecordObject(component, "Set Component Data")` before the field update loop.

---

### 3.2 `GameObjectOperationCommandHandler` Rename Does Not Use Undo

**Severity:** Minor

The rename operation does `gameObject.name = parameters.newName` without `Undo.RecordObject()`. Delete correctly uses `Undo.DestroyObjectImmediate()`.

---

### 3.3 GetComponentData Only Searches Active Scene Root Objects

**Severity:** Medium

Both `GetComponentDataCommandHandler` and `SetComponentDataCommandHandler` use `SceneManager.GetActiveScene().GetRootGameObjects()` to find GameObjects. This means:
- Objects in additively loaded scenes (non-active) are invisible
- Objects inside prefab stages are invisible

**Contrast:** `GameObjectUtilityCommandHandler` uses `GameObject.Find()` (searches all loaded scenes).

---

### 3.4 `AssetExtendedCommandHandler.CreateAssetByType` Returns Null for Most Types

**Severity:** Medium

`CreateAssetByType()` only handles 3 types: `ScriptableObject`, `Material`, `AnimatorController`. Everything else returns null. This makes the `create` operation fail silently for valid types like `RenderTexture`, `Cubemap`, `AnimationClip`, etc.

---

### 3.5 Scene Load Does Not Support Additive Mode

**Severity:** Medium

`SceneOperationCommandHandler.LoadScene()` hardcodes `OpenSceneMode.Single`. There is no `mode` parameter in `SceneOperationParams`.

---

### 3.6 Build Operation Does Not Support Custom Scene Lists

**Severity:** Medium

`BuildOperationCommandHandler.ExecuteBuild()` always reads scenes from `EditorBuildSettings.scenes`. There is no way to specify a custom scene list for a build, which is common for build automation.

---

### 3.7 `PlayerSettingsCommandHandler` Active Platform Detection is Fragile

**Severity:** Minor

`GetActiveNamedBuildTarget()` does string containment matching (`activeBuildTarget.ToString().Contains(kvp.Key)`) which could false-match if platform names overlap (e.g., "Windows" matching "WindowsStoreApps" before "StandaloneWindows64").

---

### 3.8 `ReadConsoleCommandHandler` May Miss Logs During Domain Reload

**Severity:** Minor

Console logs captured before domain reload may not persist in the bridge's tracked log buffer. The Unity Console retains them, but the bridge handler's in-memory tracking does not survive serialization.

---

### 3.9 Multiple Handlers Duplicate FindGameObjectByPath Logic

**Severity:** Code quality

`FindGameObjectByPath()` is duplicated in: `GameObjectOperationCommandHandler`, `GetComponentDataCommandHandler`, `SetComponentDataCommandHandler`, `PrefabOperationHelpers`, and `QueryHierarchyCommandHandler`. Some use `SceneManager.GetActiveScene()` (active scene only), others use `GameObject.Find()` (all scenes). This inconsistency means the same path resolves differently depending on which command you use.

**Fix:** Extract to a shared `GameObjectPathResolver` utility class with options for active-scene-only vs all-scenes.

---

### 3.10 No Command Timeout for Lightmap Sync Bake

**Severity:** Minor

The lightmap bake has a C#-side timeout of 3600 seconds but the Python timeout default is 30 seconds. A synchronous bake will almost always time out on the Python side. Users must manually specify `--timeout 3600` or use `runAsync: true`.

---

## 4. Recommended Phase 5 Priorities

Ranked by combined automation value, developer frequency, and implementation simplicity.

### Tier 1: High Priority (Daily use, high automation value)

| # | Feature | Scope | Complexity |
|---|---|---|---|
| 1 | **Create primitives/lights/cameras** in gameobject-operation | Extend existing handler | simple |
| 2 | **Remove component** command | New command type | simple |
| 3 | **Enable/disable component** | Extend set-component-data or new op | simple |
| 4 | **Enable/disable (activate) GameObject** | Extend gameobject-operation | simple |
| 5 | **Additive scene loading** (load/unload with mode parameter) | Extend scene-operation | simple |
| 6 | **Expand PlayerSettings** to cover 15+ common properties | Extend GETTERS/SETTERS dictionaries | simple |
| 7 | **Find references in scene** (which GOs reference an asset) | New command type | complex |
| 8 | **Create custom ScriptableObject instances** by type name | Extend CreateAssetByType | medium |
| 9 | **Set lightmap settings** (not just read) | Extend lightmap-operation | medium |
| 10 | **Platform switching** (SwitchActiveBuildTarget) | Extend build-operation | medium |

### Tier 2: Medium Priority (Weekly use, medium automation value)

| # | Feature | Scope | Complexity |
|---|---|---|---|
| 11 | **Time Settings** (fixed timestep, time scale) | New handler or extend project-settings | simple |
| 12 | **Graphics Settings** (SRP asset, render pipeline) | New handler | medium |
| 13 | **Script Execution Order** | New handler | medium |
| 14 | **Build options expansion** (all BuildOptions flags, custom scene list) | Extend build-operation | simple |
| 15 | **NavMesh baking** (bake, clear, settings) | New handler | medium |
| 16 | **Environment lighting** (skybox, ambient, fog) | Extend lightmap-operation or new | medium |
| 17 | **Reflection Probe baking** | New handler or extend lightmap | medium |
| 18 | **Material keyword enable/disable** | Extend material-operation | simple |
| 19 | **Scene View camera control** | Extend focus-object or new | simple |
| 20 | **Game view resolution control** | New handler | medium |
| 21 | **Profiler start/stop recording** | Extend profiler-sample | simple |
| 22 | **Log custom messages to Console** | Extend clear-console or new | simple |
| 23 | **Blend Tree operations** | Extend animator-operation | complex |
| 24 | **Prefab editing mode** (enter/exit) | Extend prefab-operation | medium |
| 25 | **Create .asmdef / .asmref files** | Extend asset-extended | simple |

### Tier 3: Lower Priority (Rarely used, or specialized)

| # | Feature | Scope | Complexity |
|---|---|---|---|
| 26 | Animation clip keyframe editing | New handler | complex |
| 27 | Addressables integration | New handler | medium |
| 28 | Sprite slicing and atlas | Extend import-settings | complex |
| 29 | Terrain operations | New handler | complex |
| 30 | Occlusion culling | New handler | medium |
| 31 | Memory profiler snapshot | Extend profiler | medium |
| 32 | Preset Manager | New handler | complex |
| 33 | Audio Settings | New handler | simple |
| 34 | Input Manager (legacy) | New handler | medium |
| 35 | Editor window management | New handler | complex |
| 36 | UI element creation (Canvas/Button/etc) | Extend gameobject-operation | medium |

### Bugfixes to Include in Phase 5

| # | Fix | Location |
|---|---|---|
| B1 | Add `Undo.RecordObject` to `SetComponentDataCommandHandler` | `SetComponentDataCommandHandler.cs` |
| B2 | Add `Undo.RecordObject` to `GameObjectOperationCommandHandler.RenameGameObject` | `GameObjectOperationCommandHandler.cs` |
| B3 | Unify `FindGameObjectByPath` into shared utility with configurable scene scope | All handlers |
| B4 | Expand `CreateAssetByType` to handle 10+ common types | `AssetExtendedHelpers.cs` |
| B5 | Add `mode` parameter to `scene-operation load` for additive support | `SceneOperationCommandHandler.cs` |
| B6 | Add custom scene list parameter to build-operation | `BuildOperationCommandHandler.cs` |
| B7 | Fix fragile platform detection in `PlayerSettingsCommandHandler` | `PlayerSettingsCommandHandler.cs` |
| B8 | Align Python lightmap timeout default with actual bake time (or document workaround) | `protocol.py` |

---

## Appendix A: Complete Capability Matrix

### Legend
- **Full**: CLI can do everything the Editor UI can
- **Partial**: CLI covers common operations but not all
- **None**: No CLI coverage at all

| Unity Editor Area | Coverage | Notes |
|---|---|---|
| Hierarchy: Query | Full | query-hierarchy with depth, inactive, root filter |
| Hierarchy: Create empty GO | Full | gameobject-operation create |
| Hierarchy: Create primitives/lights | None | Must use execute-menu-item workaround |
| Hierarchy: Delete GO | Full | gameobject-operation delete |
| Hierarchy: Rename GO | Full | gameobject-operation rename (no undo) |
| Hierarchy: Reparent GO | None | No set-parent operation |
| Hierarchy: Reorder siblings | None | No sibling index control |
| Inspector: Get component data | Partial | Public fields only, no private/properties |
| Inspector: Set component data | Partial | Public fields only, no undo |
| Inspector: Add component | Full | add-component |
| Inspector: Remove component | None | |
| Inspector: Enable/disable component | None | |
| Inspector: Enable/disable GO | None | |
| Inspector: Tag/Layer | Full | gameobject-utility set-tag, set-layer |
| Inspector: Static flags | Full | gameobject-utility static-flags |
| Scene: Load/Save/Create | Partial | No additive load, no unload |
| Scene: Multi-scene editing | Partial | scene-setup save/restore but no additive load |
| Scene: Build settings list | Full | scene-operation list + build-operation get-settings |
| Project: Find assets | Full | asset-operation find with type/path filters |
| Project: Create assets | Partial | Only Material, SO, AnimatorController |
| Project: Delete/Copy/Move | Full | asset-extended-operation |
| Project: Dependencies | Full | asset-operation get-dependencies |
| Project: GUID lookup | Full | asset-extended-operation guid |
| Project: Export/Import package | Full | asset-extended-operation export/import-package |
| Project: Folders | Full | asset-extended-operation folder-create/folder-list |
| Project: Reimport | Full | import-settings-operation reimport |
| Build: Trigger build | Full | build-operation build |
| Build: Get settings | Full | build-operation get-settings |
| Build: Platform switch | None | |
| Build: Build options | Partial | Only development flag |
| Build: Build Profiles (Unity 6) | Full | build-profile-operation |
| Player Settings | Partial | 3 settable properties of 50+ |
| Package Manager | Full | 8 operations covering all UPM actions |
| Animator Controller | Full | 22 operations across all categories |
| Animator: Blend Trees | None | |
| Materials | Partial | CRUD + properties, missing keywords |
| Shaders | Full | 6 read-only inspection operations |
| Lightmaps | Partial | Bake/cancel/clear/status/settings (read-only) |
| Import Settings | Full | Get/set/reimport/bulk/templates |
| Prefabs | Full | Create/instantiate/apply/revert/overrides/unpack |
| Play Mode | Full | Play/pause/stop/step/status |
| Console | Partial | Read/clear but no write |
| Editor Selection | Full (Phase 4) | Get + set selection |
| Screenshots | Full | Scene view and camera capture |
| Profiler | Partial | Single snapshot only |
| Tests | Full | Run + list + filter |
| Undo/Redo | Full | 6 operations including history |
| Compilation | Full | Assemblies/defines/which/optimization |
| Menu Items | Full | Execute any menu path |
| C# Scripting | Full | Execute arbitrary expressions |
| Transform | Full (Phase 4) | Position/rotation/scale manipulation |
| EditorPrefs | Full (Phase 4) | Get/set/delete editor preferences |
| Physics Settings | Full (Phase 4) | Read/write physics config |
| Quality Settings | Full (Phase 4) | Read/write quality levels |
| Editor Settings | Full (Phase 4) | Read/write editor configuration |
| Tags/Layers | Full (Phase 4) | Manage custom tags and layers |
| Time Settings | None | |
| Audio Settings | None | |
| Graphics Settings | None | |
| Navigation/NavMesh | None | |
| Occlusion Culling | None | |
| Addressables | None | |
| Terrain | None | |
| Animation Clips (keyframes) | None | |
| Sprite Editor | None | |
| Scene View controls | Partial | Focus only |
| Game View controls | None | |

---

*Last updated: 2026-03-21*
