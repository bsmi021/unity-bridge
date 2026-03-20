# Adversarial Review: Unity Bridge Expansion Tech Specs

**Reviewer:** Adversarial Agent
**Date:** 2026-03-19
**Specs Reviewed:** Phase 1, Phase 2, Phase 3

## Executive Summary

The three tech specs are well-structured and follow the project's established patterns. However, a thorough comparison against verified Unity 6 API signatures reveals several critical issues that would cause runtime errors or incorrect behavior if implemented as written. The most serious are: Phase 2 uses the obsolete `TestRunnerApi.RetrieveTestList` API (must be `RetrieveTestTree`), Phase 2 uses the obsolete single-parameter `RevertPrefabInstance`, Phase 1 does not document that `AssetDatabase.FindAssets` returns GUIDs (not paths), Phase 1 does not document that `AssetDatabase.CreateAsset` cannot create prefabs, and Phase 1 does not handle the null return from `BuildProfile.GetActiveBuildProfile` or the batch-mode limitation of `SetActiveBuildProfile`.

Beyond API accuracy, the specs have inconsistencies in MCP tool granularity (Phase 3 defines 22 individual MCP tools for 4 command types, while Phase 1 defines 10 for 4 and Phase 2 defines 5 for 5). There are also gaps in edge case handling, particularly around domain reload during scripting define changes, compilation-in-progress guards, and play mode restrictions. The undo history feature in Phase 2 has an acknowledged but unresolved design problem: Unity provides no public API to enumerate undo history.

Overall the specs are a solid foundation, but approximately 8 critical issues and 15 major issues need resolution before implementation begins.

---

## Critical Issues (Must Fix)

### C1. Phase 2: `TestRunnerApi.RetrieveTestList` is OBSOLETE
**Location:** Phase 2, Section 3 (C# handler table), Section 5.3 (callback pattern)
**Problem:** The spec explicitly uses `testRunnerApi.RetrieveTestList(new ExecutionSettings(filter))` in the code sample and references `RetrieveTestList` in the handler table. This API is obsolete in Unity 6.
**Fix:** Replace all references with `RetrieveTestTree`. The callback pattern also changes -- `RetrieveTestTree` populates an `ITestAdaptor` tree, not through `RunStarted`. The `ICallbacks` interface pattern shown in Section 5.3 is wrong for `RetrieveTestTree`; it uses a separate `Action<ITestAdaptor>` callback.

### C2. Phase 2: `RevertPrefabInstance(GameObject)` single-param is OBSOLETE
**Location:** Phase 2, Section 5.2 (prefab override serialization), implied by `revert` operation
**Problem:** The spec does not show the `RevertPrefabInstance` call explicitly, but the revert operation must use `PrefabUtility.RevertPrefabInstance(GameObject, InteractionMode)` -- the two-parameter version. The single-parameter overload is obsolete.
**Fix:** Ensure all apply/revert calls use `InteractionMode.AutomatedAction` as the second parameter. The spec mentions `InteractionMode.AutomatedAction` for `ApplyAddedComponent` etc. but must explicitly require it for `RevertPrefabInstance` as well.

### C3. Phase 1: `BuildProfile.GetActiveBuildProfile()` returns null not handled
**Location:** Phase 1, Section 5.2 (Build Profiles C# code)
**Problem:** The spec shows `var active = BuildProfile.GetActiveBuildProfile()` but does not document or handle the null case. `GetActiveBuildProfile()` returns null when a platform profile (not a custom Build Profile) is active. The `get-active` operation response assumes a profile object is always returned.
**Fix:** The `get-active` response must handle null by returning `success: true` with `profile: null` and a message like "No custom build profile active; using platform default." The response schema in Section 4.2.2 needs a null-profile variant.

### C4. Phase 1: `SetActiveBuildProfile` cannot switch platforms in batch mode
**Location:** Phase 1, Section 5.2, Section 8 (Risks)
**Problem:** The spec does not document that `BuildProfile.SetActiveBuildProfile` cannot switch platforms in batch mode. Users running Unity in batch mode (common in CI/CD) will get silent failures.
**Fix:** Add a documented limitation: "In batch mode, use the `-activeBuildProfile` CLI argument instead of `SetActiveBuildProfile`. The handler should detect `Application.isBatchMode` and return an error with guidance."

### C5. Phase 1: `AssetDatabase.FindAssets` returns GUIDs, not paths
**Location:** Phase 1, Section 5.2 (Build Profiles code), where `AssetDatabase.FindAssets("t:BuildProfile")` is used
**Problem:** The code sample `var guids = AssetDatabase.FindAssets("t:BuildProfile")` correctly assigns to `guids`, but this is only correct by coincidence of the variable name. The spec never explicitly documents that `FindAssets` returns GUID strings that must be converted with `AssetDatabase.GUIDToAssetPath()`. Since the existing `asset-operation` handler likely uses `FindAssets`, and the new `asset-extended-operation` adds GUID operations, this conversion step must be explicit.
**Fix:** Add a note in the C# implementation notes: "`FindAssets()` returns GUID strings. Always convert with `GUIDToAssetPath()` before returning paths to Python."

### C6. Phase 1: `AssetDatabase.CreateAsset` cannot create prefabs
**Location:** Phase 1, Section 4.2.3 (asset create operation), Section 2 (command reference lists `--type` options)
**Problem:** The spec lists `create` as a general asset creation command with `assetType` parameter, but does not document that `AssetDatabase.CreateAsset` cannot create prefabs. A user calling `asset create Assets/Prefabs/New.prefab --type Prefab` would get an unclear Unity error.
**Fix:** Document this limitation explicitly. The C# handler should check for prefab types and return a clear error: "Cannot create prefabs with AssetDatabase.CreateAsset. Use the prefab-operation command with PrefabUtility instead."

### C7. Phase 1: `AssetDatabase.MoveAsset` unusual return convention not documented
**Location:** Phase 1, Section 5.2 (Asset Extended code)
**Problem:** The spec shows `string error = AssetDatabase.MoveAsset(source, dest); // Returns "" on success` in a code comment, which is correct. However, the response protocol in Section 4.2.3 for the `move` operation does not include an `error` field. If MoveAsset fails, the error message from the return value would be lost.
**Fix:** Add an `errorDetail` field to the move response for when MoveAsset returns a non-empty string. The C# handler should check `if (!string.IsNullOrEmpty(error))` and return it in the response.

### C8. Phase 3: `Lightmapping.bakedGI` / `realtimeGI` are OBSOLETE
**Location:** Phase 3, Section 3.4.2 (lightmap settings response)
**Problem:** The spec's lightmap settings response does not reference these properties, but the C# implementation will need to read lighting settings. If the implementation uses `Lightmapping.bakedGI` or `Lightmapping.realtimeGI`, it will trigger obsolete warnings or errors. The spec should specify using `LightingSettings` object instead.
**Fix:** Add explicit guidance in C# implementation notes: "Use `Lightmapping.lightingSettings` to get the `LightingSettings` asset, then read `bakedGI`/`realtimeGI` from it. Do NOT use the obsolete `Lightmapping.bakedGI`/`Lightmapping.realtimeGI` properties."

---

## Major Issues (Should Fix)

### M1. Phase 1: `PackageManager.Client.Resolve()` returns void, not a Request
**Location:** Phase 1, Section 5.2
**Problem:** While the spec does not explicitly propose a `resolve` operation, it describes the async polling pattern for all `Client` methods. If a `resolve` operation is ever added or if implementation code assumes all Client methods return Request objects, it will fail for `Resolve()` which returns void.
**Fix:** Add a note in the C# implementation notes: "`Client.Resolve()` returns void, unlike all other Client methods. Do not attempt to poll it."

### M2. Phase 1: `PlayerSettings` uses `NamedBuildTarget.FromBuildTargetGroup` -- wrong approach
**Location:** Phase 1, Section 5.2 and 5.3
**Problem:** The spec shows `var target = NamedBuildTarget.FromBuildTargetGroup(BuildTargetGroup.Standalone)`. This uses the deprecated `BuildTargetGroup` enum as an intermediary. The verified API shows that `NamedBuildTarget` has predefined static properties (`NamedBuildTarget.Standalone`, `NamedBuildTarget.Android`, etc.) that should be used directly.
**Fix:** The platform map in Section 5.3 correctly maps to `NamedBuildTarget.Standalone` etc., but the code sample in Section 5.2 should be updated to use the map directly, not go through `FromBuildTargetGroup`.

### M3. Phase 1: `SetScriptingDefineSymbols` recompilation timing not fully addressed
**Location:** Phase 1, Section 5.2
**Problem:** The spec says "The response is written before recompilation starts (synchronous call), so the Python side receives the response before Unity reloads." This is correct for the C# side, but the spec does not address what happens if the Python side sends another command while Unity is recompiling. The bridge's heartbeat would go stale during domain reload, and queued commands would time out.
**Fix:** Document in the response: include a `"note": "Domain reload in progress. Wait for bridge heartbeat to resume before sending further commands."` The Python side should detect this and provide guidance to the user.

### M4. Phase 2: `HasPrefabInstanceAnyOverrides` with `includeDefaultOverrides=true` caveat
**Location:** Phase 2, Section 3.3 (prefab override list response)
**Problem:** The `hasOverrides` field in the `list` response does not specify whether it uses `includeDefaultOverrides=true` or `false`. With `true`, it almost always returns true because position/rotation are default overrides. This would make the field useless for practical purposes.
**Fix:** Use `includeDefaultOverrides: false` as the default behavior. Document that the field excludes default overrides (position/rotation) to be practically useful. Optionally add an `includeDefaultOverrides` parameter to the command.

### M5. Phase 2: `FindAllInstancesOfPrefab` does NOT return nested prefab instances
**Location:** Phase 2, Section 3.3 (find-instances operation)
**Problem:** The spec does not document this limitation. Users searching for instances of a prefab that is used as a nested prefab inside other prefabs will get incomplete results.
**Fix:** Add a note to the `find-instances` response: `"note": "Does not include nested prefab instances. Only root-level instances of this prefab are returned."`

### M6. Phase 2: `Undo.isProcessing` not checked before undo operations
**Location:** Phase 2, Section 5.1
**Problem:** The spec does not mention checking `Undo.isProcessing` before performing undo/redo. If an undo operation is already in progress, calling `PerformUndo()` again could cause undefined behavior.
**Fix:** Add a guard: `if (Undo.isProcessing) return BridgeResponse.Error(...)` with a message "Undo operation already in progress."

### M7. Phase 2: `CompilationPipeline.GetDefinesFromAssemblyName` can return null
**Location:** Phase 2, Section 5.1 (CompilationPipelineCommandHandler)
**Problem:** The verified API states `GetDefinesFromAssemblyName(string)` returns `string[]` or null. The spec does not handle the null case.
**Fix:** Check for null and return an error: "Assembly not found or has no defines: {assemblyName}".

### M8. Phase 2: `CompilationPipeline.GetAssemblyNameFromScriptPath` can return null
**Location:** Phase 2, Section 5.1
**Problem:** Same null-return issue as M7. If the script path is invalid or outside any assembly definition, this returns null.
**Fix:** Check for null and return an appropriate error response.

### M9. Phase 2: `compilation-pipeline` marked as parallel-safe despite `optimization` write operation
**Location:** Phase 2, Section 4.2
**Problem:** The spec acknowledges this is a write operation but adds the command type to `PARALLEL_SAFE_COMMANDS` anyway with a hedge: "If this causes issues, remove it from the set." This violates the principle that parallel-safe means ALL operations are safe.
**Fix:** Do NOT add `compilation-pipeline` to `PARALLEL_SAFE_COMMANDS`. The spec's own reasoning explains why.

### M10. Phase 2: Undo history is not implementable as specified
**Location:** Phase 2, Section 5.1
**Problem:** The spec acknowledges that Unity provides no public API to enumerate undo history, then proposes Option 3 (maintain own history via `undoRedoPerformed` callback). However, this only captures undo/redo events that happen AFTER the bridge initializes. The history command would return nothing until bridge operations start creating undo records. This is a significantly degraded experience from what the command reference promises.
**Fix:** Either (a) document this limitation clearly in the command reference and response, or (b) downscope `undo history` to return only the current group name and explicitly state "full history enumeration is not supported by Unity's public API."

### M11. Phase 3: `Lightmapping.BakeAsync()` returns bool, not void
**Location:** Phase 3, Section 4.2 and 5.4
**Problem:** The verified API states `BakeAsync()` returns `bool` (false if it cannot start, e.g., already running). The spec does not check this return value.
**Fix:** Check the return value and set `started: false` with an appropriate error message if `BakeAsync()` returns false.

### M12. Phase 3: Shader property type enum incomplete
**Location:** Phase 3, Section 4.1
**Problem:** The spec lists `"type": "Color | Vector | Float | Range | Texture | Int"`. The verified `ShaderPropertyType` enum is: Color, Vector, Float, Range, TexEnv, Int. The spec uses "Texture" instead of "TexEnv". While "Texture" is more user-friendly, it does not match the Unity API enum name.
**Fix:** Either use the exact enum name `TexEnv` for fidelity, or document the mapping: `TexEnv` -> `"Texture"` in the serialization notes.

### M13. Phase 3: `ShaderHasError` vs `GetShaderMessages` distinction not clarified
**Location:** Phase 3, Section 3.4.1 (shader errors operation)
**Problem:** The `errors` command uses the field name `hasErrors` and `messages`. The verified API distinguishes: `ShaderHasError(Shader)` returns errors only (ignores warnings), while `GetShaderMessages(Shader)` returns both errors AND warnings. The spec should clarify which API is used for each field.
**Fix:** Document: `hasErrors` uses `ShaderUtil.ShaderHasError()` (errors only), `messages` uses `ShaderUtil.GetShaderMessages()` (errors and warnings). The `severity` field in each message distinguishes between them.

### M14. Phase 2: Prefab status response uses wrong enum values
**Location:** Phase 2, Section 3.3
**Problem:** The response shows `"prefabType": "PrefabInstance"`. The verified `GetPrefabAssetType()` enum values are: NotAPrefab, Regular, Model, Variant, MissingAsset. And `GetPrefabInstanceStatus()` enum values are: NotAPrefab, Connected, MissingAsset. "PrefabInstance" is not a valid value from either enum.
**Fix:** Use correct enum values. The `prefabType` field should map to `GetPrefabAssetType()` values, and a separate `instanceStatus` field should use `GetPrefabInstanceStatus()` values.

### M15. Phase 1: `scripting_defines` schema has hardcoded platform enum that will go stale
**Location:** Phase 1, Appendix A (scripting_defines schema)
**Problem:** The schema hardcodes `"enum": ["Standalone", "Android", "iOS", "WebGL", "Server", "WindowsStoreApps"]`. This is missing PS4, PS5, XboxOne, etc. from the verified `NamedBuildTarget` list. Hardcoding platform lists in schemas means they go stale as Unity adds platforms.
**Fix:** Remove the enum constraint and use a free-form string with a description listing common values. The C# handler's platform map is the source of truth for validation.

---

## Minor Issues (Nice to Fix)

### m1. Phase 1: `package search` uses `Client.Search(query)` but API searches by package ID, not keyword
**Problem:** `Client.Search(string packageIdOrName)` searches for a specific package by ID or name. It does not perform keyword search across all packages. The `Client.SearchAll()` method returns all available packages. The spec's `package search <query>` command implies keyword search but the underlying API is ID-based lookup.
**Fix:** Clarify the command: either rename to `package info-remote <name>` or document that the search is by package ID/name, not free-text keyword search.

### m2. Phase 1: `package list` response uses `Client.List()` without specifying `offlineMode` and `includeIndirectDependencies` parameters
**Problem:** The verified API shows `List()` / `List(bool offlineMode)` / `List(bool offlineMode, bool includeIndirectDependencies)`. The spec does not expose these options.
**Fix:** Consider adding `--offline` and `--include-indirect` flags for completeness.

### m3. Phase 2: `CodeOptimization` enum has 3 values, not 2
**Problem:** The compilation pipeline schema allows `"enum": ["Debug", "Release"]`. The verified enum is `CodeOptimization.None`, `CodeOptimization.Debug`, `CodeOptimization.Release`. The `None` value is missing.
**Fix:** Add `None` to the enum or document why it is excluded.

### m4. Phase 3: MCP tool proliferation -- 22 tools for 4 command types
**Problem:** Phase 3 creates 22 MCP tools, most of which are thin wrappers that just set the `operation` field differently. This contrasts with Phase 1 (10 tools for 4 types) and Phase 2 (5 tools for 5 types). The inconsistency adds cognitive load for MCP clients.
**Fix:** Consider consolidating. For example, `unity_shader_inspection` with an `operation` parameter covers all 6 shader operations in one tool, matching the Phase 2 pattern.

### m5. Phase 1: `asset_extended` schema uses Python `False`/`True` instead of JSON `false`/`true`
**Location:** Appendix A, `asset_extended()` function
**Problem:** `"default": False` and `"default": True` are Python booleans written in JSON Schema context. While Python's JSON serializer handles this correctly (`False` -> `false`), it is misleading in documentation.
**Fix:** Use lowercase `false`/`true` in the spec's JSON Schema examples for clarity (the actual Python code can keep `False`/`True`).

### m6. Phase 3: `async` is a Python reserved word used as a parameter name
**Location:** Phase 3, lightmap bake parameters
**Problem:** The parameter `"async": true` in the protocol and the C# field name `async_field` suggest awareness of the issue, but the Python-side handling is not specified. `async` cannot be used as a Python variable name.
**Fix:** Document the Python parameter name as `async_mode` or `run_async` and map it to `"async"` in the bridge protocol JSON.

### m7. Phase 1: `build-profile` CLI registration uses hyphen
**Location:** Phase 1, Section 3.4
**Problem:** `_try_register_group("...", "build_profile_app", "build-profile")` registers as a hyphenated subcommand. Check that this is consistent with existing subcommand naming (existing uses: `build`, `asset`, `scene` -- all single words).
**Fix:** Since this is a sub-subcommand (`build profile`), it should be registered as a subcommand under the existing `build` group, not as a top-level `build-profile` group.

### m8. Phase 2/3: Missing `timeout` parameters in several MCP schemas
**Problem:** Phase 2 schemas (undo_operation, compilation_pipeline, prefab_overrides, etc.) do not include a `timeout` property, unlike Phase 1 schemas which consistently include it.
**Fix:** Add `timeout` to all Phase 2 and Phase 3 schemas for consistency.

---

## Missing Capabilities

### MC1. No `package resolve` command
The verified API shows `Client.Resolve()` is available (returns void, forces package resolution). This is useful after manual edits to `manifest.json`. Phase 1 should add a `package resolve` subcommand.

### MC2. No `Undo.CollapseUndoOperations` exposed
Phase 2 adds undo commands but omits `CollapseUndoOperations(int groupIndex)`. This is useful for AI workflows that perform multiple atomic changes that should be collapsed into a single undo step.

### MC3. No shader variant count or compilation status
Phase 3 adds shader inspection but omits variant count information. While the spec explicitly defers this, even a simple `isCompiling` global check would be valuable.

### MC4. No `EditorSceneManager.NewPreviewScene()` / `ClosePreviewScene()`
Phase 3 adds scene management but misses preview scenes, which are useful for testing prefab/material setups in isolation without modifying the main scene.

### MC5. No bulk import settings operations
Phase 3's import settings commands operate on single assets. A `bulk-set` operation that applies settings to all assets matching a pattern (e.g., all textures in a folder) would be high-value for project standardization workflows.

### MC6. No `Undo.RecordObject` before missing script removal
Phase 2, Section 5.4 calls `GameObjectUtility.RemoveMonoBehavioursWithMissingScript(go)` but calls `Undo.SetCurrentGroupName` without a corresponding `Undo.RecordObject`. The `RemoveMonoBehavioursWithMissingScript` may not be automatically undo-aware.

---

## Cross-Spec Consistency Issues

### X1. MCP tool granularity is wildly inconsistent
- Phase 1: 10 MCP tools for 4 command types (2-3 tools per type)
- Phase 2: 5 MCP tools for 5 command types (1 tool per type)
- Phase 3: 22 MCP tools for 4 command types (4-6 tools per type)

Phase 2 uses the most consolidated pattern (one tool per command type with `operation` field), while Phase 3 goes the opposite direction with individual tools per operation. This inconsistency means MCP clients see three different patterns.

**Recommendation:** Standardize on Phase 2's approach (one tool per command type). This keeps the tool list manageable and is consistent with the existing `unity_asset_operation`, `unity_prefab_operation` patterns.

### X2. MCP tool naming convention inconsistency
- Phase 1: `unity_package_list`, `unity_package_manage`, `unity_asset_extended` (mixed verb/noun)
- Phase 2: `unity_undo_operation`, `unity_compilation_pipeline` (noun-based)
- Phase 3: `unity_shader_list`, `unity_lightmap_bake` (verb-based)

Existing tools use: `unity_run_tests`, `unity_query_hierarchy`, `unity_scene_operation` (mixed).

**Recommendation:** At minimum, be consistent within each phase. Prefer `unity_{domain}_{operation}` pattern.

### X3. Model class organization differs between phases
- Phase 1: All models in `BridgeModels.cs` or `BridgeModelsPhase1.cs`
- Phase 2: All models appended to `BridgeModels.cs`
- Phase 3: Separate model files per handler (`ShaderInspectionModels.cs`, etc.)

Phase 3's approach is better (separation of concerns, easier to stay under 500 LOC), but the specs should agree on a single strategy.

### X4. `success` field in response `dataJson` is inconsistent
Phase 1 includes `"success": true` inside every `dataJson` response. Phase 2 does NOT include a `success` field in `dataJson` (relying on the envelope's `status` field). Phase 3 includes `"success": true` in all responses.

The existing bridge protocol uses the envelope `status` field. Including `success` in `dataJson` is redundant. Either all phases should include it (for convenience) or none should.

### X5. Tool count discrepancy
- Phase 1 claims to add 10 new MCP tools (bringing total from 26 to 36)
- Phase 2 claims to add 5 tools (bringing total to 31, but this should be 41 if Phase 1 is done first)
- Phase 3 claims "All existing 26 MCP tools remain unchanged" but does not state the total

The phases do not appear to account for each other's additions to the total count.

### X6. Existing `asset-operation` uses `find` which already calls `FindAssets`
Phase 1 adds a `guid` operation under `asset-extended-operation`. But the existing `asset-operation` `find` action likely already calls `FindAssets` and may already need GUID-to-path conversion. The existing handler's behavior should be verified and documented.

---

## Phase 1 Detailed Review

### API Accuracy
- **PackageManager**: Signatures match verified API. Async polling pattern is correct. Serial constraint is documented.
- **BuildProfile**: Missing null handling for `GetActiveBuildProfile()` (C1). Missing batch mode limitation (C4). `#if UNITY_6000_0_OR_NEWER` guards are correctly specified.
- **AssetDatabase extended**: `MoveAsset` return convention mentioned in code but not in protocol (C7). `CreateAsset` prefab limitation not documented (C6). `FindAssets` GUID return not emphasized (C5).
- **PlayerSettings**: Uses deprecated `FromBuildTargetGroup` intermediary (M2). `SetScriptingDefineSymbols` recompilation acknowledged but not fully handled (M3). Platform enum in schema is incomplete (M15).

### Protocol Design
- Command types are correctly kebab-case.
- Parameters are correctly camelCase.
- Response schemas are generally complete but missing null-profile variant for build profile get-active.
- Error cases follow existing pattern.

### Edge Cases
- No handling for commands sent during domain reload (after `SetScriptingDefineSymbols`).
- No play mode restriction checks (some AssetDatabase operations fail in play mode).
- No validation that asset paths start with "Assets/" (Unity requirement).
- Export operation does not validate output path directory exists.

---

## Phase 2 Detailed Review

### API Accuracy
- **TestRunnerApi**: Uses obsolete `RetrieveTestList` (C1). The callback pattern shown is incorrect for `RetrieveTestTree`.
- **PrefabUtility**: Uses obsolete single-param `RevertPrefabInstance` (C2). Status response uses invalid enum values (M14). `FindAllInstancesOfPrefab` nested limitation not documented (M5). `HasPrefabInstanceAnyOverrides` default override caveat missing (M4).
- **Undo**: `isProcessing` guard missing (M6). History enumeration not feasible as designed (M10).
- **CompilationPipeline**: Null returns from `GetDefinesFromAssemblyName` and `GetAssemblyNameFromScriptPath` not handled (M7, M8). `CodeOptimization.None` enum value omitted (m3). Incorrectly classified as parallel-safe (M9).

### Protocol Design
- Command types are correctly kebab-case.
- Parameters correctly use camelCase.
- Missing `timeout` in MCP schemas (m8).
- Missing `operation` field echo in some responses (undo perform/redo responses do not include `"operation": "perform"`).

### Edge Cases
- `undo clear` calls `Undo.ClearAll()` which removes ALL history including non-bridge operations. This is destructive and should have a confirmation mechanism or at minimum a warning in the response.
- `missing-scripts` with `--fix` removes components permanently. Should require undo recording BEFORE removal, but the spec only shows `Undo.SetCurrentGroupName` without `Undo.RecordObject`.
- `set-layer --recursive` does not specify whether it affects inactive children.
- No guard against calling undo/redo operations during play mode (some operations behave differently).

---

## Phase 3 Detailed Review

### API Accuracy
- **ShaderUtil**: Property type enum uses "Texture" instead of "TexEnv" (M12). `ShaderHasError` vs `GetShaderMessages` distinction unclear (M13). `GetAllShaderInfo()` return type is correct.
- **Lightmapping**: `bakedGI`/`realtimeGI` obsolescence not documented (C8). `BakeAsync()` return value not checked (M11). `buildProgress` property (0.0-1.0) is correctly used as `progress` in response.
- **EditorSceneManager**: `DetectCrossSceneReferences` behavior correctly documented. `playModeStartScene` get/set/clear pattern is correct. `RestoreSceneManagerSetup` requirement for at least one loaded scene not documented.
- **AssetImporter**: Importer type detection pattern is correct. Per-platform TextureImporter settings explicitly deferred.

### Protocol Design
- Too many MCP tools (22 for 4 command types) -- inconsistent with other phases (X1).
- `async` parameter name conflicts with Python reserved word (m6).
- Scene setup storage in `.claude/unity/scene-setups/` is reasonable but should be validated against `.gitignore`.

### Edge Cases
- Lightmap `bake` with `async: false` blocks indefinitely if `bakeCompleted` never fires (e.g., Unity crashes during bake). Need a timeout mechanism on the C# side for the deferred response.
- `scene setup restore` with missing scenes: spec mentions this risk but does not specify pre-validation behavior in the handler code.
- Import settings `set` does not call `AssetDatabase.WriteImportSettingsIfDirty()` or `SaveAssets()` -- settings may not persist.
- Import settings `template-apply` to an asset with a different importer type returns an error, but what about a TextureImporter template applied to a different texture format (e.g., EXR vs PNG)? Some settings may not apply.
- `lightmap settings` response does not mention how to access `LightingSettings` (via `Lightmapping.lightingSettings` property).

---

## Recommendations

Ordered by priority (critical first, then major):

1. **Fix all 8 critical issues (C1-C8) before implementation begins.** These would cause compile errors, runtime exceptions, or silently wrong behavior.

2. **Standardize MCP tool granularity across all three phases.** Adopt Phase 2's one-tool-per-command-type pattern. This affects Phase 1 (reduce from 10 to 4 tools) and Phase 3 (reduce from 22 to 4 tools).

3. **Add null-return handling for all Unity APIs that can return null.** This affects BuildProfile.GetActiveBuildProfile, CompilationPipeline.GetDefinesFromAssemblyName, CompilationPipeline.GetAssemblyNameFromScriptPath.

4. **Remove `compilation-pipeline` from PARALLEL_SAFE_COMMANDS (M9).** The spec's own rationale explains why this is unsafe.

5. **Fix the prefab status enum values (M14)** to match actual `GetPrefabAssetType()` and `GetPrefabInstanceStatus()` return values.

6. **Add `timeout` parameter to all Phase 2 and Phase 3 MCP schemas (m8)** for consistency with Phase 1.

7. **Standardize model class organization.** Adopt Phase 3's approach (separate model files per handler) retroactively for Phase 1 and Phase 2 specs.

8. **Add domain reload / compilation-in-progress guards** to all handlers. Check `EditorApplication.isCompiling` before executing non-trivial operations.

9. **Add play mode guards** to mutating operations that are invalid during play mode (AssetDatabase operations, BuildProfile changes, PlayerSettings changes).

10. **Downscope `undo history` (M10)** to return only current/pending group names, and explicitly document the limitation.

11. **Add `package resolve` command (MC1)** -- simple to implement and practically useful.

12. **Add `Undo.CollapseUndoOperations` exposure (MC2)** -- high value for AI agent workflows that make multiple changes.

13. **Standardize the `success` field in `dataJson` (X4).** Either include it everywhere or remove it everywhere. Recommend including it for convenience since MCP clients may not always inspect the envelope.

14. **Fix tool count arithmetic (X5)** so each phase correctly states the cumulative tool total.

15. **Validate asset paths start with "Assets/"** in all handlers that accept asset paths, returning a clear error for invalid paths.
