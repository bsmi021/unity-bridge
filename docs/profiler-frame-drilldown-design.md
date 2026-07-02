# Design Proposal: Per-Frame Profiler Drill-Down

**Status:** Implemented in `profiler-frame`
**Author:** Claude Code
**Last Updated:** 2026-07-02
**Tracks:** Unity 6.5 capability gap audit item 2 ("Per-sample/per-frame profiler drill-down")

---

## 1. Overview

### Problem Statement

`profiler-control` and `profiler-sample` only expose **aggregate** counters
(total/mono/graphics memory, draw calls, triangle count, one frame's delta
time). Neither can answer "why was frame 412 slow" or "what's allocating
GC this session" — the actionable layer an optimization loop needs. This
gap is already tracked in `docs/phase7-new-gaps-report.md:126,195` as P1.

The sibling `unity-mcp` server (connected in this session, not part of this
repo) exposes the equivalent capability via `RawFrameDataView`/
`HierarchyFrameDataView` — used here only as a reference for what the
underlying Unity API surface supports, not as something to copy verbatim.

### Goals

- **G1:** Query recorded profiler frames for per-sample timing (top total
  time, top self time) without leaving the CLI.
- **G2:** Retrieve a bottom-up call tree for a given sample so an agent can
  see *what* called the expensive marker.
- **G3:** Retrieve GC allocation broken down per-frame, per-frame-range,
  and per-sample.
- **G4:** Keep this usable from a live (non-batch) Unity Editor session
  driven by the CLI — the bridge's actual operating model. Headless
  `-batchmode` CI capture is a non-goal for this iteration (see §5 Risks).
- **G5 (companion, small):** Let the agent enable/disable specific
  profiler areas (`Physics`, `Audio`, `GC`, etc.) and allocation
  callstacks before capturing, since default capture is too coarse to
  attribute allocations to call sites.

### Non-Goals

- GPU profiling — Unity's own docs state the GPU Profiler cannot profile
  the Editor at all (Play Mode or builds only). Out of scope regardless
  of this feature; matches existing profiler commands, which are
  CPU/memory-only already.
- Headless `-batchmode` CI profiling — Unity's docs do not confirm CPU
  frame capture works under `-batchmode`; needs an empirical spike before
  it's promised as a CI feature. Tracked as a follow-up, not blocking G1-G5.
- Replacing `memory-profiler take-snapshot` (heap snapshots) — orthogonal;
  `.snap` diff is a separate proposal.

---

## 2. Unity API Surface

| Capability | API |
|---|---|
| Enumerate retained frame range | `ProfilerDriver.firstFrameIndex` / `lastFrameIndex` |
| Per-frame flat sample data | `ProfilerDriver.GetRawFrameDataView(frameIndex, threadIndex)` → `RawFrameDataView` |
| Per-frame hierarchical call tree | `ProfilerDriver.GetHierarchyFrameDataView(frameIndex, threadIndex, viewMode, sortType, descending)` → `HierarchyFrameDataView` |
| Bottom-up tree | `HierarchyFrameDataView` with `HierarchyFrameDataView.ViewModes.MergeSamplesWithTheSameName`, walking `GetItemChildren`/parent links |
| Per-sample GC alloc | `HierarchyFrameDataView.GetItemColumnData(id, HierarchyFrameDataView.columnGcMemory)` |
| Clear retained history | `ProfilerDriver.ClearAllFrames()` |
| Area/category toggle | `UnityEditorInternal.ProfilerDriver.SetAreaEnabled(area, enabled)` (areas: CPU, GPU, Rendering, Memory, Audio, Physics, Physics2D, NetworkMessages, NetworkOperations, UI, UIDetails, GlobalIllumination, VirtualTexturing, Video) |
| Allocation callstacks | `UnityEngine.Profiling.Profiler.enableAllocationCallstacks` |

---

## 3. Proposed Bridge Surface

### New command type: `profiler-frame`

New handler `ProfilerFrameCommandHandler.cs` (+ `ProfilerFrameModels.cs`,
kept under 500 LOC per project convention). Operations:

| Operation | Params | Returns |
|---|---|---|
| `capture-start` | `frameCount?`, `logFile?` | begins recording; enables `Profiler.enabled` |
| `capture-stop` | — | stops recording; reports `firstFrameIndex`/`lastFrameIndex` captured |
| `frame-range` | — | current `firstFrameIndex`/`lastFrameIndex` (no capture side effect) |
| `top-time-samples` | `frameIndex`, `count?`, `threadIndex?` | top-N samples by total time in the frame |
| `self-time-samples` | `frameIndex`, `count?`, `threadIndex?` | top-N samples by self time |
| `sample-time-summary` | `markerName`, `frameIndexStart`, `frameIndexEnd` | aggregated total/self/count for a marker across a frame range |
| `bottom-up-tree` | `frameIndex`, `markerName`, `depth?` | call-tree entries leading into the marker |
| `gc-alloc` | `frameIndex` **or** `frameIndexStart`+`frameIndexEnd` | GC bytes for the frame / frame range |
| `sample-gc-alloc` | `frameIndex`, `markerName` | GC bytes attributed to a specific sample |
| `clear` | — | `ProfilerDriver.ClearAllFrames()` |

Response payloads are flat DTOs (`JsonUtility`-serializable, matching the
existing `ProfilerControlResult` pattern) — no nested polymorphic trees;
`bottom-up-tree` returns a flat list of `{depth, markerName, totalTimeMs,
selfTimeMs, callCount}` rows rather than a recursive object, consistent
with how the rest of the bridge avoids deep JSON nesting.

### Companion: extend `profiler-control`

Add `set-areas` operation: `{"operation": "set-areas", "areas": "Physics,Audio", "enabled": true, "allocationCallstacks": true}`.
No new command type — this is a natural extension of the existing
start/stop/save/memory operations.

### Python: `commands/profiler_frame.py`

Follows the existing module pattern exactly (async core fn + Typer
wrapper). CLI group `profiler-frame`:

```
unity-bridge profiler-frame capture-start [--frame-count N]
unity-bridge profiler-frame capture-stop
unity-bridge profiler-frame top-time-samples <frame-index> [--count N]
unity-bridge profiler-frame self-time-samples <frame-index> [--count N]
unity-bridge profiler-frame sample-time-summary <marker-name> --start N --end N
unity-bridge profiler-frame bottom-up-tree <frame-index> <marker-name>
unity-bridge profiler-frame gc-alloc [--frame N | --start N --end N]
unity-bridge profiler-frame sample-gc-alloc <frame-index> <marker-name>
unity-bridge profiler-frame clear
unity-bridge profiler-control set-areas --areas Physics,Audio [--disable] [--allocation-callstacks]
```

---

## 4. Acceptance Criteria

1. `profiler-frame capture-start --frame-count 60` followed by advancing
   Play Mode 60 frames, then `capture-stop`, reports a `lastFrameIndex -
   firstFrameIndex` consistent with frames actually elapsed (±buffer
   eviction if `maxUsedMemory` was exceeded — documented, not a failure).
2. `top-time-samples` for a known-synthetic slow frame (e.g. a test scene
   with a scripted `Thread.Sleep`-equivalent heavy `Update`) surfaces that
   marker in the top 5 by total time.
3. `sample-time-summary` for a marker present in every frame of a 10-frame
   range returns `callCount == 10` (or the correct multiple if the marker
   fires more than once per frame).
4. `gc-alloc` for a frame range with a known allocation (e.g. a test
   script that allocates a fixed-size array every frame) returns a
   non-zero, monotonically-plausible byte count.
5. `set-areas` disabling `Audio` causes subsequent `top-time-samples` to
   omit Audio-category markers; re-enabling restores them.
6. All operations return `success: false` with a clear message (not a
   silent empty array) when `frameIndex` is outside `[firstFrameIndex,
   lastFrameIndex]`.

## 5. Risks / Open Questions

- **Batchmode CPU capture is unverified by Unity's docs** (checked
  `ProfilerDriver`, `Profiler.maxUsedMemory`, `ProfilerGPU.html`,
  `profiler-command-line-arguments.html`, `desktop-headless-mode.html` —
  none confirm or deny `-batchmode` CPU frame recording). Recommend a
  30-minute empirical spike (`-batchmode -profiler-enable`, poll
  `ProfilerDriver.lastFrameIndex`) before advertising this as CI-safe.
  Does not block the live-Editor use case this proposal targets.
- **Frame retention after `Profiler.enabled = false`** is not explicitly
  documented either way. Mitigation: the proposed workflow always queries
  *before* `capture-stop` disables the profiler, or immediately after —
  never assumes long-lived post-stop querying.
- Unity 6000.3 deprecates `HierarchyFrameDataView.GetItemInstanceID` in
  favor of EntityId-based equivalents — implementation should target the
  non-deprecated overloads from the start.

## 6. Test Plan (TDD)

- Unit tests (`tests/unit/test_profiler_frame.py`): mock `DirectBridge`,
  cover every operation's parameter marshalling and `CommandResult`
  handling — no Unity required, matching existing `test_profiler.py`
  conventions.
- Integration tests (`@pytest.mark.integration`, skipped without Unity):
  drive a real capture window against a minimal test scene with a
  deliberately expensive `Update()` and a deliberate per-frame GC
  allocation, asserting against Acceptance Criteria 2 and 4 above.
- C# side: no existing EditMode test harness for handlers in this repo
  (verified — handlers are tested only via the Python integration suite);
  this proposal does not introduce one, consistent with current practice.

## 7. Effort Estimate

- C# handler + models: ~1 day (M, per original gap-report estimate).
- Python module + CLI wiring + unit tests: ~0.5 day.
- Integration test scene + tests: ~0.5 day.
- `set-areas` companion: ~2 hours (S, bundles into `profiler-control`).

Implemented with Python payload/CLI tests and C# source-contract tests.
Live Unity profiler acceptance remains the next validation step when a
target Unity project is available.
