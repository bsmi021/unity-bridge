# Unity Bridge — Audit & Unity 6.x Gap Analysis

> Analysis date: 2026-06-09
> Scope: ~23K Python LOC (`src/unity_bridge/`, 114 files), ~35K C# LOC (`ClaudeCodeBridge/`, 131 files), ~240 command types, 94 live MCP tools, 93 pytest files. Competitive reference: the third-party `unity-mcp` server connected in-session.

---

## Executive Summary

- **Overall verdict: architecturally strong, well-tested at the Python unit layer, but with a cluster of HIGH-severity correctness bugs in the live command path and a near-total absence of executed C#/end-to-end tests.** The foundations (durable ledger, atomic writes, reload recovery) are better than most file-based bridges; the gaps are in enforcement, coverage, and Unity-6-era capabilities.
- **Strength 1 — Durable operation ledger with reload recovery.** A validated state machine on both sides, with C# marking interrupted ops and writing error responses on domain reload so Python never hangs (`operation.py:40-71,147-164`; `BridgeOperationLedger.cs:79-92,116-165`).
- **Strength 2 — Correct atomic writes and BOM-tolerant reads** across Python and C# (`bridge.py:207-217,268-282`; `BridgeOperationLedger.cs:231-286`), plus per-handler exception isolation that keeps the editor loop alive (`ClaudeUnityBridge.cs:249-339`).
- **Strength 3 — Consistent dual-interface + packaging.** No `asyncio.run` in any async path; 94 MCP tools with zero registry inconsistencies; a cross-language inventory contract test; green suite (1661 passed, 33 skipped, ~25s).
- **Risk 1 — `CompileCommandHandler` busy-waits on the Unity main thread**, which can freeze the entire editor for the full timeout (`CompileCommandHandler.cs:159-168`).
- **Risk 2 — Zero executed C# tests and no CI.** ~35K LOC of C# is validated only structurally; "integration" tests never touch Unity; there is no `.github/` workflow, so nothing runs automatically.
- **Risk 3 — Correctness leaks in the live path:** parallel batch mutates state concurrently (`protocol.py:143-144`), the global `--timeout` flag is dead for the whole CLI, and the MCP cache can serve stale reads after a mutation.
- **Top gap 1 (P0) — C# script CRUD + AST-aware edits.** The #1 thing an agent does that the bridge cannot; today it drops to generic file tools with no Unity validation (`script_info.py` / `MonoScriptCommandHandler.cs` are read-only).
- **Top gap 2 (P0) — Inline base64 screenshots + multi-angle capture.** The bridge already renders to PNG but only returns a disk path (`CaptureScreenshotCommandHandler.cs`); returning inline images closes the agent's visual feedback loop.
- **Top gap 3 (P1) — Per-sample profiler drill-down and Adaptive Probe Volumes (APV) baking.** Current profiler captures only aggregate counters; APV (Unity 6's default GI probe system) is entirely absent.
- **Top gap 4 (P1) — `RunCommand`-style escape hatch.** Harden the existing CLI-only `execute-script` with Undo + object-change tracking and expose it as an MCP tool to eliminate "not implemented" dead-ends.
- **Top gap 5 (P1) — Concurrent-edit safety (SHA256 precondition) and `StartAssetEditing` bulk batching** — cheap, high-leverage safety and performance wins.

---

## The Good

**Durable operation ledger with state machine + reload recovery (the standout architecture win).** `OperationRecord`/`OperationStateMachine`/`OperationStore` model the command lifecycle with a validated transition table, terminal-state guards, and atomic temp-file+replace writes; in-flight ops move to `recovering_after_reload` when `domain_generation` changes (`operation.py:40-71,147-164,270-302`). The C# side mirrors this exactly: `BridgeOperationLedger` persists `DomainGeneration` per transition and `RecoverAfterReload` scans startup ops, marking still-pending commands interrupted and writing an error response so Python never waits to timeout (`BridgeOperationLedger.cs:79-92,116-165`; `ClaudeUnityBridge.cs:88-92,307-312`). Most file-based bridges have nothing like this.

**Correct atomic writes on both sides.** Python writes command files and ledger snapshots to `.tmp` then `replace()` (`bridge.py:207-217`; `operation.py:270-276`); C# `WriteAtomic` uses a GUID temp file, `Flush(true)` fsync, then `File.Replace`/`File.Move` with bounded backoff retries (`BridgeOperationLedger.cs:231-286`). Response reads tolerate BOM via `utf-8-sig` with a JSONDecodeError retry loop (`bridge.py:268-282`).

**Per-handler exception isolation keeps the editor loop alive.** `ProcessCommandFile` wraps the full read/parse/dispatch path in try/catch and always `SafeDelete`s the command file, so a poison-pill command produces an error response instead of tearing down `EditorApplication.update` or looping (`ClaudeUnityBridge.cs:249-339`).

**Dual-interface contract is upheld where it matters.** No `asyncio.run` appears in any async path — only in Typer CLI wrappers and the MCP server entrypoint (`server.py:417`), avoiding the documented "event loop already running" crash. ~75 command modules follow a uniform typed-async-core + thin-wrapper shape, making the codebase predictable.

**Health readiness vs. healthiness separation.** `HealthStatus` derives `ready` from `healthy + busy_reason`; `wait_for_ready` treats compiling/importing/reloading as live-but-not-ready (waits through them) while bailing immediately on a dead editor (`health.py:63-68,184-213`).

**Async Unity APIs handled by callback, not blocking.** `RunTestsCommandHandler` returns "running" immediately and writes the terminal response from `RunFinished` via `ICallbacks`, the correct pattern for the async TestRunner (`RunTestsCommandHandler.cs:30-89`). Reflection-based optional-package access (Entities/Addressables) fails soft to a clean error response (`EntitiesArchetypeReflection.cs:15-89`).

**Packaging is genuinely solid.** The wheel force-includes all 131 `.cs` + 134 `.meta` files plus the CLI skill bundle; install resolution handles both source-checkout and packaged layouts (`lifecycle.py:32-53`); `test_bridge_inventory.py` is a cross-language contract test asserting every `.cs` has a unique-GUID `.meta` and every registered handler has a backing file (`test_bridge_inventory.py:19-88`). The MCP tool registry is fully consistent — 94 tools, zero declared-but-unmapped or mapped-but-undeclared, no command-type collisions, every mapped command has a timeout default. Suite is green and Unity-independent (1661 passed, 33 skipped, ~25s).

---

## The Bad

Ordered by severity. HIGH items affect the live command path or core safety guarantees.

**[HIGH] CompileCommandHandler busy-waits on the Unity main thread (deadlock/freeze).** Handlers run synchronously from `EditorApplication.update` (`ClaudeUnityBridge.cs:323`), but `WaitForCompilationComplete` spins `Thread.Sleep(100)` while `EditorApplication.isCompiling` for up to the timeout (default 120s) — `CompileCommandHandler.cs:159-168`. Unity drives compilation on the main thread, so blocking it means `isCompiling` may never clear: the loop runs to full timeout and freezes the whole editor. **Fix:** convert to the across-frames/event model `RunTests` already uses (subscribe to `CompilationPipeline.compilationFinished`, return "running", write the terminal response when it clears).

**[HIGH] Cross-process read-modify-write race on the per-command ledger file.** `OperationStore.transition()` does load → mutate → write with no lock (`operation.py:278-302`), while C# `BridgeOperationLedger` writes the *same* `<command_id>.json` (transitions to accepted/running/terminal — `BridgeOperationLedger.cs:52,128-133,194`). Atomic replace prevents torn files but not lost updates: a last-writer-wins overwrite can drop the C# `accepted` transition that `_response_timeout_result` relies on to decide whether to delete the command file (`bridge.py:286-297,350-364`). **Fix:** enforce single-writer-per-phase (C# owns accepted→terminal, Python owns pre-accept and post-timeout), or re-load inside `transition()` immediately before write and refuse to regress a state the other side already advanced.

**[HIGH] Global `--timeout` flag and `UNITY_BRIDGE_TIMEOUT` are dead for the entire CLI.** `app.py` resolves `config.default_timeout` with full precedence, but no command module reads it — every CLI wrapper hardcodes a literal default or defines its own per-command `--timeout`. Only the MCP path honors timeouts via `get_timeout()`. This directly contradicts the documented global-flags/env-var tables in CLAUDE.md. Evidence: grep for `config.default_timeout` in `commands/` = zero hits; `commands/physics2d.py:117`, `commands/audio_settings.py:17-19`. **Fix:** thread `state.config.default_timeout` into `get_timeout(..., global_override=...)` via a shared helper, or remove the flag from docs.

**[HIGH] Parallel batch executes mutating commands concurrently.** `_execute_parallel` classifies purely by `command_type` membership in `PARALLEL_SAFE_COMMANDS`, but `transform-operation` and `serialized-property` are in that set despite also performing set-position/parent/set-property *mutations* (`protocol.py:143-144`; `transform.py:36-104`). A parallel batch of `transform-operation` "set" commands mutates Unity state concurrently via `asyncio.gather`, violating the read-only guarantee. **Fix:** inspect `parameters.operation` when classifying — only get/list ops are parallel-safe — or gate on an explicit per-command `read_only` flag.

**[HIGH] ~35K LOC of C# has zero executed tests, and "integration" tests never touch Unity.** No EditMode/PlayMode tests, no test `.asmdef`; C# is validated only by the structural inventory test, which never compiles or runs a handler. Both `tests/integration/` files are mislabeled — `test_cli_smoke.py` only runs `--help`/`version`/`status`, `test_mcp_compat.py` introspects in-process dicts. There is no reachable test proving the end-to-end file round-trip — the tool's central value proposition. Compounding this, **there is no CI configuration at all** (no `.github/`), so the 1661-test suite, ruff, and the contract test run only if a dev remembers. **Fix:** add a minimal EditMode test `.asmdef` for the highest-risk handlers (ledger atomic write, BOM-free JSON emit) run in batchmode CI, plus a GitHub Actions workflow running pytest + ruff + a wheel-build that asserts `.meta` inclusion.

**[HIGH] Cache `invalidate(pattern)` cannot match command types — silent no-op.** Cache keys are 16-char SHA-256 hashes (`cache.py:71-75`), but `invalidate(pattern)` filters `pattern in k` against those hashes (`cache.py:160`). Any human pattern like `query-hierarchy` matches nothing and silently invalidates zero entries. Combined with `check_scene_change()` and `invalidate()` having **no callers in `src/`** and `_invoke_command` never invalidating after a mutation, the MCP path can serve stale `query-hierarchy`/`get-component-data` reads for up to the 5s TTL after a mutation — a divergence the CLI (which bypasses the cache entirely) never exhibits. **Fix:** key the cache by `f"{command_type}:{hash}"` so prefix matching works, and invalidate on every successful mutating command in `_invoke_command`.

**[MEDIUM] HeartbeatGenerator write is non-atomic, contradicting its own doc comment.** `WriteHeartbeat` claims "write to .tmp then rename" but does `WriteAllText(tmp)` → `Delete(target)` → `Move(tmp,target)` (`HeartbeatGenerator.cs:216-225`). A health-monitor stat in the delete/move window sees no file and may declare the bridge dead; a crash there loses the heartbeat. **Fix:** reuse `BridgeOperationLedger.WriteAtomic`.

**[MEDIUM] `_processedCommandFiles` grows unbounded for the editor session.** Every processed file path is added to the HashSet and never removed even though the file is deleted immediately (`ClaudeUnityBridge.cs:36,253-261`), leaking memory and making the per-tick `Where(!Contains)` filter progressively slower. The ledger's terminal check already prevents reprocessing, so the set is largely redundant. **Fix:** drop it and rely on `SafeDelete` + ledger terminal check.

**[MEDIUM] Common command timeout returns exit_code 1, not the documented 4.** `_response_timeout_result` (the ordinary "no response" case) returns `exit_code=1` while the busy-timeout paths return 4 (`bridge.py:365-376` vs `391-402`). Callers that branch on exit code 4 = Timeout cannot distinguish a plain timeout from a Unity-side error. **Fix:** return 4 from `_response_timeout_result`.

**[MEDIUM] Timeout marks `retryable:false` and orphans the response while Unity may still be running.** For an accepted/running op, `_response_timeout_result` returns `retryable=False`, transitions to INTERRUPTED, and leaves the command file in place (only unlinked for queued/None). If Unity later writes a response it is never consumed or reconciled (`bridge.py:341-376`). **Fix:** surface a reconcilable state so recovery can adopt the in-flight op, or unlink the orphaned response on next poll.

**[MEDIUM] Non-idempotent retry policy is computed but never enforced.** `retry_policy_for_command` classifies mutations as `RETRY_NON_IDEMPOTENT` and stores it in the ledger, but `retry_async` retries purely on `is_retryable_error` and ignores the policy (`operation.py:336-344`; `retry.py:133-143`). An accepted-then-timed-out mutation can be re-sent, risking duplicate side effects. **Fix:** pass the `OperationRecord`/policy into the retry path and refuse non-idempotent retries past QUEUED without an idempotency key.

**[MEDIUM] Cross-reload static state silently lost.** Assembly-reload lock depth (`AssemblyReloadLockCommandHandler.cs:31-32`) and in-memory test-run contexts (`RunTestsCommandHandler.cs:28`) are plain statics cleared on domain reload — unlike `HeartbeatGenerator.DomainGeneration` which is SessionState-backed. PlayMode test runs (which trigger a reload) become unreportable through the callback path, falling back to a generic "interrupted". **Fix:** back both with SessionState and re-attach after `afterAssemblyReload`, or document EditMode-only result reporting.

**[MEDIUM] Version is stale; up-to-date check is string-equality.** `pyproject`/`__init__` pin 3.0.0 while the CHANGELOG Unreleased section has accumulated 5+ phases; `git tag` is empty. `unity-bridge install` decides `up_to_date` by version string-equality (`lifecycle.py:286-287`), so a user upgrading the package after new `.cs` files land but before the version bumps is told the bridge is up to date when it isn't. **Fix:** bump/tag, and compare file checksums (already in the manifest) rather than the version string.

**[LOW] MCP exception path emits an inconsistent shape.** When `DirectBridge` raises, `_invoke_command` returns `{success, status, error}` with no `exit_code`/`command_id` and a `status` key the normal `to_dict()` never emits (`server.py:151-152` vs `bridge.py:63-73`). **Fix:** return `CommandResult(success=False, error=str(exc), exit_code=5).to_dict()`.

**[LOW] `_check_result_error` treats unknown result types as success.** `retry.py:91` returns `(True, '', None)` for any non-dict result lacking `.success`, so a stray `None` masks a failure with no retry and no error. **Fix:** default unknown shapes to failure.

**[LOW] Command files processed in filesystem order, not FIFO.** `Directory.GetFiles` ordering is unspecified (`ClaudeUnityBridge.cs:253-261`), so order-dependent sequences (add-component then set-component-data) can execute out of submission order. **Fix:** `OrderBy` creation time or an embedded timestamp.

**[LOW / defensive] Busy-accounting can over-subtract → negative `active_elapsed`** (`bridge.py:243-244`). Real but contingent on health states flapping within sub-poll windows (unlikely, and bounded by the hard grace ceiling). Treat as defensive: clamp `active_elapsed >= 0` and add a flap test.

---

## The Ugly

Structural debt and consistency problems — not correctness bugs, but they erode maintainability and will cause future drift.

**ResponseCache is mislabeled and its read-only command lists are triplicated.** `_evict_oldest` evicts by creation timestamp and `get()` never updates it, so it's least-recently-*created*, not LRU, despite the docs (`cache.py:39-62,133-142`). Separately, `CACHEABLE_COMMANDS`, `PARALLEL_SAFE_COMMANDS`, and `TIMEOUT_DEFAULTS` are three overlapping read-only command lists kept in sync by hand.

**MCP bypasses per-domain core functions, so the param contract is duplicated.** CLAUDE.md says MCP awaits the same core fns as the CLI, but `server.py` imports only 4 — the other ~80 tools go through generic `_invoke_command(command_type, raw_camelCase_args)`. Param-shaping (e.g. `transform_set` packing `{x,y,z,isSet}`) and validation (`testing.py:74-78` mode checks) are CLI-only and hand-mirrored in the JSON schemas, so the contract lives in two places and will drift, and per-domain validation is never exercised over MCP.

**Massive get/set-with-flags boilerplate across ~30 settings modules.** physics2d/audio/physics/time/graphics/environment/quality all repeat the identical `if x is not None: params[setX]=True; params[x]=value` plus parallel get fn, Typer wrapper, and re-declared schema (`physics2d.py:42-64`, `audio_settings.py:54-70`). A shared field→(setFlag, valueKey) helper plus a generic get/set core would collapse hundreds of near-identical lines.

**Dead and duplicated C#.** The `FileSystemWatcher` watches but only logs — all processing is poll-driven from `Update()`, yet `GetBridgeStatus` reports `isHealthy` partly on this no-op watcher (`ClaudeUnityBridge.cs:162-188`). `Update()` also calls `Directory.GetFiles` + LINQ on every tick even when fully idle. Project-root path construction and atomic-write logic are recomputed independently across `ClaudeUnityBridge`, `BridgeOperationLedger`, and `HeartbeatGenerator` — drift already realized in the heartbeat's broken write. `BridgeCommandRegistry.RegisterAll` is a hand-maintained ~130-line list with no compile-time guarantee a declared handler is registered; `WriteDiagnostic` appends to `bridge-log.jsonl` with no rotation.

**Silent `except (ImportError, AttributeError): pass` on CLI registration.** A genuine ImportError, attr typo, or syntax failure deep in a command module makes an entire CLI group silently vanish with no warning (`app.py:362-383`) — very hard to diagnose.

**Config merge relies on default-equality sentinels.** `_merge_config` distinguishes "set" from "unset" by comparing each field to `BridgeConfig()` defaults, so explicitly setting a value equal to the default is indistinguishable from not setting it, silently breaking env-over-file precedence for default-valued overrides; `from_env` parses `UNITY_BRIDGE_TIMEOUT` via `str.isdigit()`, rejecting `'30 '` and negatives (`config.py:58-60,188-207`).

**Docs and counts have drifted ~5 phases.** CLAUDE.md still says "48 MCP tools"/"83 tool definitions" and stops at Phase 7, while the live surface is 94 tools and the CHANGELOG documents Unity 6.4 Phases 1-5 plus phases 8/9. `docs/index.md` (last updated 2026-06-08) and the tech-specs stop at phase4-critical-gaps — no spec for the shipped 6.4 groups. The README is the only accurate count.

**Test hygiene wrinkles.** Tests are grouped by dev-phase (`test_phase6b_gaps.py`, `test_phase8_unity64.py`) alongside domain files, contradicting the project's own "group by domain" rule and making the canonical test for a command group hard to find. The MCP count assertion is a loose floor (`assert >= 65` vs 94 live), so a bulk drop of ~30 newer tools would pass. Duplicated timestamp/int-parse helpers (`_parse_datetime`/`_parse_optional_datetime`, `_optional_int`) live in both `health.py` and `operation.py`. An unaddressed `asyncio_default_fixture_loop_scope` deprecation warning fires every run.

---

## Unity 6.x Capability Gaps

Each gap was verified absent (or only partial) by grepping `ClaudeCodeBridge/*` and `src/unity_bridge/commands/*`. Candidates already covered under non-obvious names were dropped (see "Verified non-gaps" at the end).

### Scripting / Code Authoring (highest competitive gap)

| Gap | Unity API entry point | Why it matters for AI automation | Effort | Priority |
|---|---|---|---|---|
| **C# script CRUD + structured/AST-aware edits** (create/read/update/delete `.cs`; replace_method, insert_method before/after, anchor insert). Verified: `script_info.py` + `MonoScriptCommandHandler.cs` are **read-only** (info/list/find-component only); `AssetExtendedCreate` writes `.asset/.mat/.prefab` natives via `File.WriteAllText`, never gameplay scripts. | File I/O + `AssetDatabase.ImportAsset` + Roslyn/`Microsoft.CodeAnalysis` for AST ops; `MonoImporter` to rebind | The #1 thing an agent does that the bridge cannot: it must drop to generic file tools with no Unity validation, no compile coordination, no domain-reload awareness. Competitors' `ManageScript`/`ScriptApplyEdits` is their headline feature. | L | **P0** |
| **Concurrent-edit safety: SHA256 precondition + validate-before-write** for script/asset files. Verified: no `GetSha`/precondition logic anywhere. | SHA over file bytes + `CompilationPipeline` validation pass before write | Prevents the agent clobbering human/other-agent edits; lets it detect stale reads. Cheap safety win, especially paired with script-CRUD. | S | **P1** |

### Visual Feedback (biggest competitive gap)

| Gap | Unity API entry point | Why it matters | Effort | Priority |
|---|---|---|---|---|
| **Inline-image / base64 screenshot return + multi-angle composited capture.** Verified PARTIAL: `CaptureScreenshotCommandHandler.cs` renders scene-view cam + a named camera to PNG but **only writes to disk and returns a path** (`File.WriteAllBytes` → path); no base64 payload, no 2x2 Iso/Front/Top/Right grid, no `focusObjectIds` framing. | Existing `Camera.Render` + `RenderTexture` + `EncodeToPNG` → add `Convert.ToBase64String`; loop 4 framing angles into one composited texture | Closes the agent feedback loop — the agent can *see* the result of its edits and self-correct. Every leading competitor returns multi-angle inline images. Bridge can already render; this is a return-payload + framing extension, not architectural. | M | **P0** |

### Profiling / Diagnostics

| Gap | Unity API entry point | Why it matters | Effort | Priority |
|---|---|---|---|---|
| **Per-frame / per-sample profiler drill-down** (top time samples, self time, related samples, bottom-up, per-sample GC alloc, frame-range summaries). Verified PARTIAL: `profiler-sample` captures only aggregate counters; `profiler-control` only does save/load/`ProfilerDriver`. No `FrameDataView`/`HierarchyFrameDataView`/`RawFrameDataView`. | `UnityEditorInternal.ProfilerDriver` + `UnityEditor.Profiling.HierarchyFrameDataView`/`RawFrameDataView`; `GetFrameData(frameIndex)` | Aggregate counters say *that* a frame is slow; per-sample drill-down says *why* (which method, GC source). This is the actionable layer for optimization loops. | M | **P1** |
| **Memory snapshot capture** for offline analysis. Verified absent: no `MemoryProfiler`/`TakeSnapshot`. | `Unity.Profiling.Memory.MemoryProfiler.TakeSnapshot(path, cb, CaptureFlags)` | Deterministic, headless-friendly, produces a structured artifact — exactly the agent-loop shape. Maps cleanly to the durable ledger (async finish callback). | M | **P2** |
| **Code coverage report generation tied to test runs.** Verified absent in `RunTestsCommandHandler.cs`/`testing.py` (no `coverage`/`-enableCodeCoverage`). | `com.unity.testtools.codecoverage` Coverage API + `-enableCodeCoverage`/`-coverageOptions` | Lets an agent prove a change is tested and find untested paths — structured artifact, high CI value. The test runner is already wrapped, so this is an extension. | M | **P2** |

### Lighting / Rendering (Unity 6-specific)

| Gap | Unity API entry point | Why it matters | Effort | Priority |
|---|---|---|---|---|
| **Adaptive Probe Volumes (APV) baking + lighting scenarios.** Verified absent: no `AdaptiveProbeVolume`/`ProbeReferenceVolume`/`ProbeVolumeBakingSet`; `lightmap.py`/`LightmapOperationCommandHandler.cs` cover legacy `Lightmapping.Bake` only. | `UnityEditor.Rendering.AdaptiveProbeVolumes.BakeAsync`/`BakeAdditionalRequests`; `ProbeVolumeBakingSet` scenario APIs | APV is the default GI probe system in Unity 6 URP/HDRP. Long-running bake → maps to the operation ledger with progress polling. High-value Unity-6 gap not addressable via existing lightmap commands. | M | **P1** |

### Bulk Asset Performance (internal, not exposed)

| Gap | Unity API entry point | Why it matters | Effort | Priority |
|---|---|---|---|---|
| **`StartAssetEditing`/`StopAssetEditing` batching around bulk asset ops.** Verify inside `asset_extended.py`/`AssetExtendedHelpers.cs` whether bulk create/move/delete wrap import batching — likely not. | `AssetDatabase.StartAssetEditing`/`StopAssetEditing` | Order-of-magnitude speedup when an agent does many asset edits in one batch; reduces per-op reimport stalls. Pairs with the existing `batch` multiplexer. | S | **P1** |

### Asset Authoring (niche)

| Gap | Unity API entry point | Why it matters | Effort | Priority |
|---|---|---|---|---|
| **Sprite Atlas packing.** Verified absent: no `SpriteAtlas`/`PackAtlases`. | `UnityEditor.U2D.SpriteAtlasUtility.PackAtlases`; `SpriteAtlasAsset` create | 2D build step for sprite-heavy projects; deterministic. | S | **P2** |
| **Localization table/locale authoring.** Verified absent: no `Localization`/`StringTable`. | `LocalizationEditorSettings.CreateStringTableCollection`/`AddLocale`; `StringTable.AddEntry` | Common content-pipeline task; niche unless project uses `com.unity.localization`. | M | **P2** |
| **Timeline asset / track authoring.** Verified absent: no `Timeline`/`TimelineAsset`. | `UnityEngine.Timeline.TimelineAsset.CreateTrack<T>`/`CreateClip` | Cutscene/sequencing; niche, only if project uses Timeline. | M | **P2** |

### Verified non-gaps (dropped after codebase check)

- **Enter Play Mode options / fast script reload** — covered: `EditorConfigCommandHandler.cs:75-77,130-135,168-178`.
- **Build Profiles (Unity 6) — build/scenes/defines/activate** — fully covered: `BuildProfileCommandHandler.cs`.
- **Addressables analyze rules / profiles / labels** — covered: `AddressablesCommandHandler.cs:93,155` + profile/label ops.
- **Menu-item execute / exists** — covered: `ExecuteMenuItemCommandHandler.cs` (only "list all menu items" is thin; no clean public Unity API exists).
- **Search via SearchService** — covered (`query` + `providers`); only *semantic/visual* search is residual (see Opportunities).
- **GraphicsStateCollection/PSO warmup, Project Auditor, occlusion, navmesh, reflection probes, render pipeline, entities, input system, tilemap, terrain, quality, animator/animation-clip** — all have dedicated handlers + modules.

---

## Opportunities & Better Ideas

1. **Harden `execute-script` into a structured "RunCommand" escape hatch (P0-adjacent).** Current `ExecuteScriptCommandHandler.cs` uses `Mono.CSharp.Evaluator` and returns only `{result, resultType, executionTimeMs}`, and is **CLI-only — not an MCP tool**. Add Undo registration, object create/modify/destroy tracking, and a typed `ExecutionResult` with captured logs, then **expose it as an MCP tool**. This is the cheapest way to eliminate "capability not implemented" dead-ends, since any unwrapped editor API becomes reachable safely.

2. **AI asset generation — integrate, don't reimplement.** The bridge has zero generative capability and shouldn't grow cloud-model calls in a deterministic file-bridge. Instead wrap Unity 6.2's native **AI Generators** (`com.unity.ai.generators`) via menu-item/execute-script invocation. Low priority, high marketing optics.

3. **Semantic/visual asset search.** `search-query` already wraps `SearchService` (string/provider-based). Layer in an optional embedding-based index for visual-content semantic match. Medium value.

4. **MCP Resources model.** Expose console logs and key artifacts (ledger entries, last screenshot, last test/coverage report) as MCP **resources** (`unity://logs`, `unity://operations/{id}`) rather than only as tool calls. The `ListMcpResources`/`ReadMcpResource` plumbing already exists in-session. Improves agent grounding without new bridge commands.

5. **Editor toast / notify-to-human.** A `notify-message` command surfacing `EditorUtility.DisplayDialog`/`ShowNotification` so an agent can flag the human mid-run. S effort, low value.

6. **Reflection-based "any C# method → tool" registration (DX, P2).** A `[BridgeCommand]`-attribute auto-registration path would cut the cost of every future command and eliminate the hand-maintained ~130-line `BridgeCommandRegistry.RegisterAll`. Architectural investment.

---

## Recommended Roadmap

### P0 — correctness & feedback loop (do first)

1. **Fix `CompileCommandHandler` main-thread busy-wait** → convert to the `CompilationPipeline.compilationFinished` event model (`CompileCommandHandler.cs:159-168`). Editor-freeze bug.
2. **Stop parallel batch from mutating concurrently** → classify by `parameters.operation`, not just `command_type` (`protocol.py:143-144`). Data-safety bug.
3. **Resolve the ledger read-modify-write race** → single-writer-per-phase or reload-before-write-with-no-regression (`operation.py:278-302`).
4. **Add base64 / multi-angle screenshot return** (`CaptureScreenshotCommandHandler.cs`) — closes the agent visual feedback loop; the renderer already exists.
5. **Ship C# script CRUD + AST edits** (new handler + Roslyn) — the headline capability gap. SHA256 precondition (P1 item below) should land with it.
6. **Stand up CI** (`.github/` workflow: pytest + ruff + wheel-build asserting `.meta` inclusion) + a minimal EditMode `.asmdef` for ledger atomic-write and BOM-free JSON. Without this, every other fix is unverified.

### P1 — enforcement, parity & high-value capabilities

7. **Make the global `--timeout`/`UNITY_BRIDGE_TIMEOUT` actually work** across the CLI, or remove from docs (`app.py` resolves it; no command reads it).
8. **Fix the MCP cache** → key by `command_type:hash`, invalidate after every successful mutation in `_invoke_command` (`cache.py:71-75,160`).
9. **Harden + MCP-expose `execute-script`** as `RunCommand` (Undo, change tracking, captured logs).
10. **Add SHA256 concurrent-edit precondition** (pairs with script CRUD).
11. **Add `StartAssetEditing`/`StopAssetEditing` batching** to bulk asset ops.
12. **Per-sample profiler drill-down** (`HierarchyFrameDataView`/`RawFrameDataView`) and **Adaptive Probe Volume baking** (Unity-6 default GI).
13. **Enforce the non-idempotent retry policy** and return exit_code 4 for plain timeouts; reconcile orphaned post-timeout responses.
14. **Fix HeartbeatGenerator atomic write** (reuse `WriteAtomic`) and back reload-sensitive statics with SessionState.

### P2 — debt reduction & niche capabilities

15. **Collapse the get/set-with-flags boilerplate** (~30 settings modules) behind a shared field-spec helper + generic get/set core.
16. **Consolidate the triplicated read-only command lists** and the duplicated datetime/int-parse helpers; fix the LRU/eviction mislabel.
17. **Reconcile docs/counts** (CLAUDE.md tool counts, phase coverage, version bump + git tag; checksum-based up-to-date check).
18. **Remove dead C#** (no-op FileSystemWatcher, unbounded `_processedCommandFiles`), add FIFO command ordering, and add log rotation to `bridge-log.jsonl`.
19. **Surface CLI-registration import failures** instead of silently swallowing them (`app.py:362-383`).
20. **Niche capabilities & DX:** memory snapshots, code-coverage reports, sprite atlas / localization / timeline authoring, MCP Resources, and the `[BridgeCommand]` auto-registration path.

---
*Evidence citations use `file:line` against the repository state on the analysis date. The third-party `unity-mcp` server (in-session) is referenced only as a competitive capability baseline.*
