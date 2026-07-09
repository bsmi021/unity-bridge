# Unity 6.5 Full Editor Coverage Plan

Last updated: 2026-07-09

## Objective

Give Codex the broadest practical control of Unity 6.5 while preserving a
defensible public-API boundary, safe mutations, durable asynchronous behavior,
and live proof.

The program is complete only when every symbol and workflow in a pinned Editor
plus project/package snapshot is classified and every claimed reachable path is
proven at the appropriate layer.

## User Stories

- As Codex, I need to discover every supported public API loaded in the current
  Editor so that I do not guess which capabilities exist.
- As a Unity operator, I need common workflows exposed as typed commands so
  that automation is concise, validated, retry-aware, and observable.
- As Codex, I need a reliable long-tail execution path so that a public API does
  not require a new dedicated command before it can be used.
- As a project owner, I need mutations to be contained, reversible, and
  accurately reported so that expanded control cannot silently damage files or
  claim false success.

## Scope

In scope:

- Unity `6000.5.1f1` core Editor/runtime public APIs on Windows.
- Installed playback modules and build-target/define-specific availability.
- Project-resolved packages, plugins, and project assemblies with provenance.
- CLI/Python/C# command and result contracts.
- Typed workflows, generic execution, unsupported/UI-only classifications, and
  live Unity proof.

Non-goals:

- One CLI leaf per one of the roughly 55,000 core public member endpoints.
- Unsupported reliance on `UnityEditorInternal` or private reflection as a
  stable coverage claim.
- Pretending Shader Graph/VFX Graph internals or other UI-only workflows are
  covered when Unity exposes no public API.
- Treating Python line coverage or source-string assertions as live Editor/API
  coverage.

## Source Evidence

- Human audit:
  `docs/unity-6.5-full-editor-coverage-audit.html`.
- Exact Editor source tag:
  `https://github.com/Unity-Technologies/UnityCsReference/tree/6000.5.1f1`.
- Official API channel:
  `https://docs.unity3d.com/6000.5/Documentation/ScriptReference/index.html`.
- Live bridge baseline: 99 root entries, 79 group nodes, 375 non-group leaves,
  377 invokable paths, 99 Unity 6.5 handlers.
- Local core metadata: 5,354 public types and 54,979 logical public member
  endpoints.
- Builder package/project snapshot: 177 loaded assemblies, 8,318 public types,
  and 60,863 endpoints before provenance filtering.

## Design Options

### Option A: Dedicated command for every member

Rejected. It would produce tens of thousands of commands, duplicate C# type
semantics in schemas, make upgrades unmaintainable, and still fail to express
multi-call workflows or asynchronous lifecycle requirements.

### Option B: Count `script` as universal coverage

Rejected. The current evaluator is synchronous, returns `ToString()`, has no
automatic Undo/change tracking, and failed a live LINQ probe because assembly
references produced duplicate core types and ambiguous extension methods.

### Option C: Layered coverage

Recommended:

1. Generated API inventory and coverage registry.
2. Typed commands for frequent and high-risk workflows.
3. A hardened generic C# execution host for the public long tail.
4. Explicit unsupported/UI-only records.
5. Cross-layer contracts and live Unity fixtures.

This is the smallest design that can be exhaustive without being absurdly
large.

## Coverage Record

Each API/workflow record must include:

- Unity version/revision, host OS, build target, defines, API compatibility,
  extractor version, and capture time.
- Assembly path, MVID, hash, package/asmdef provenance, and package source.
- Canonical assembly-qualified type/member signature and documentation/source
  links.
- Editor/runtime/platform/package constraints and obsolete status.
- Capability-family tags.
- Coverage classification:
  `typed`, `generic`, `public_unwrapped`, `no_public_api`,
  `external_dependency`, `obsolete`, or `explicit_non_goal`.
- Proof state: source, Python contract, C# compile, live positive, live
  negative, install parity, and last verified version.

## Phase 0: Safety and Contract Gate

Purpose: stop false success and unsafe mutation before expanding breadth.

Behavior changes, in required TDD order:

1. Canonically contain all bridge file paths under the intended project root.
2. Make overwrite behavior explicit and rollback failed imports without
   deleting pre-existing content.
3. Map inner `success=false` to an outer failed `BridgeResponse` and non-zero
   CLI exit.
4. Fix `menu --validate-only` wire parity (`validate` versus `validateOnly`).
5. Fix screenshot camera field parity and restore Scene View state after
   multi-angle capture.
6. Make Build Profile creation terminal only after its callback completes.
7. Consume profiler `frameCount` or remove the option.
8. Replace stale `health-check` policy entries with the registered
   `bridge-status` contract.

Tests first:

- Arrange traversal, sibling-prefix, existing-destination, and failed-import
  cases; act through the handler; assert no path escapes, no pre-existing file
  is lost, and failure is non-zero.
- Arrange every cross-language command model; act through generated/contract
  serialization; assert exact command type, camelCase fields, defaults, result
  schema, and outer success semantics.
- Arrange Scene View state; act with multi-angle capture; assert state is
  restored in success and exception paths.
- Arrange asynchronous Build Profile callback delay/failure; assert the ledger
  remains running until terminal completion.

Exit criteria:

- All P0/P1 contract defects in the audit are covered by behavioral or
  compilation tests.
- No mutating command can exit zero with `data.success=false`.
- Path containment and rollback helpers are shared rather than reimplemented.

## Phase 1: Versioned API Inventory and Drift Gate

Purpose: establish the closed universe the previous audits lacked.

Tasks:

1. Add a reproducible inventory tool that reads exact Unity reference
   assemblies plus loaded project assemblies with Mono.Cecil.
2. Parse the official `toc.js` type index and join documentation records to
   canonical metadata signatures.
3. Map compiled assemblies back to source files, asmdefs, package manifests,
   and lockfile entries.
4. Emit versioned JSON Lines records and a compact summary. Do not commit a
   monolithic HTML dump of every member.
5. Add snapshot diffs for added, removed, changed, obsolete, and
   availability-changed APIs.
6. Add a coverage registry and fail CI on unclassified additions/removals.

Test criteria:

- Deterministic snapshot from the same assembly hashes.
- Nested accessibility, overloads, properties/events, obsolete attributes, and
  type forwarders are counted correctly.
- Package/project/test/vendor provenance is not conflated.
- Missing platform modules and define variants remain explicit gaps.

Exit criteria:

- Every symbol in the pinned core snapshot is classified.
- Every loaded project assembly has a provenance decision.
- Snapshot drift produces a reviewable, non-silent change set.

## Phase 2: Hardened Generic Execution Host

Purpose: cover the public long tail without a dedicated wrapper per member.

Tasks:

1. Replace the "reference every loaded assembly" behavior with a deterministic,
   de-duplicated reference resolver.
2. Add structured result serialization for primitives, collections, Unity
   object identities, assets, and explicit user DTOs.
3. Capture compiler diagnostics and Unity logs separately from the result.
4. Add an execution manifest: read-only/mutating intent, expected assemblies,
   timeout, Undo label, object/file change set, and requested return schema.
5. Record Undo and dirty/save behavior for mutations.
6. Add cancellation and durable asynchronous completion rather than blocking
   `EditorApplication.update`.
7. Disallow or explicitly gate internal/private reflection.

Acceptance criteria:

- The current LINQ probe compiles without CS1685 duplication or ambiguity.
- A package API can be referenced by exact assembly and returns structured JSON.
- A mutation is undoable and reports changed objects/files.
- Timeout/cancel/domain reload always produce a terminal ledger state.
- Unsupported result types fail explicitly rather than degrading silently to an
  unhelpful string.

## Phase 3: Close Typed Surface Holes

Purpose: keep common tasks ergonomic and safer than generic code.

Immediate wrappers:

- Animation: `set-curve`, `add-event`, `set-properties`.
- Terrain: `set-heights`, `set-settings`.
- Tilemap: `fill-box`, `compress-bounds`.
- Asset extended: `reserialize`.

High-value domain additions after inventory classification:

- Animator Controller/state-machine/override/avatar authoring.
- Renderer features, volume profiles, rendering statistics, shader upload
  statistics, and APV where public APIs are stable.
- Sprite Atlas/slicing and the Unity 6.5 2D profiler.
- Raw AssetBundle/type-tree workflows.
- Project Auditor async/fix, Graph Toolkit connect/disconnect, VFX prewarm, and
  other verified 6.5 additions.
- Package scoped registries, lockfile/outdated views, and package provenance.
- Richer Localization, UI Toolkit/USS, accessibility, player connection, device
  simulator, and platform workflows as demanded by real projects.

Tests:

- Exact CLI tree assertions, not subset floors.
- Every typed leaf must map to a registered command type and a C# operation.
- Every C# operation intended for users must have a typed leaf or an explicit
  "raw-only" classification.
- Package-absent and older-version failures must be structured and non-mutating.

## Phase 4: Live Unity 6.5 Fixture Matrix

Purpose: replace source-token confidence with behavior proof.

Fixture projects:

- Clean core Unity 6000.5.1f1 project.
- Package-rich project pinned to the supported package matrix.
- At least one project per required playback module/build target.

Required live scenarios:

- Model import success, unsupported importer rollback, overwrite refusal, and
  traversal rejection.
- Script edit stale hash, compile success, compile failure, and reload recovery.
- Menu validation never executes.
- Screenshot camera selection, base64 output, multi-angle output, and state
  restoration.
- Build Profile asynchronous creation success/failure.
- Profiler known slow marker and known allocation.
- Addressables build true success/failure.
- PlayMode reload terminal delivery, cancellation, timeout, and recovery.
- Package missing/version mismatch behavior for every optional adapter.

Exit criteria:

- Source, package, compile, EditMode, PlayMode, and install proof are recorded
  separately.
- No skipped live test is counted as coverage.

## Phase 5: Continuous Coverage Operations

- Run API and command-contract diffs for every Unity or package upgrade.
- Require a classification decision for every changed public symbol.
- Keep the full Python suite above 90% and add C# EditMode/PlayMode coverage
  where Unity tooling permits.
- Publish a compact generated coverage dashboard with source hashes and proof
  timestamps.
- Keep README, skill references, CHANGELOG, and `docs/index.md` generated or
  checked against the live CLI tree.

## Adversarial Review

### Finding: member presence is not workflow coverage

A callable method may require callback lifetime, Editor state, scene/save
coordination, package installation, or multiple calls. The registry therefore
tracks symbols and workflows separately.

### Finding: a generic host can become an unsafe bypass

If it ignores Undo, containment, retries, or internal API boundaries, it
invalidates typed-command safety. Phase 0 and the execution manifest are hard
prerequisites for generic-host expansion.

### Finding: package coverage is unbounded without provenance

The phrase "all package APIs" is meaningless without names, versions, sources,
targets, defines, and time. The inventory pins these inputs and treats new
project packages as a new snapshot, not as silently covered.

### Finding: source-string tests can pass broken behavior

They already missed menu, screenshot, profiler, Build Profile, and result
envelope defects. Contract and live tests are mandatory closure evidence.

## Validation Commands

Repository gates:

```powershell
uv run ruff check src tests
uv run pytest tests/
uv run pytest tests --cov=unity_bridge --cov-report=term-missing --cov-fail-under=90
```

Unity gates:

```powershell
uv run unity-bridge --project "C:/Path/To/Fixture" status
uv run unity-bridge --project "C:/Path/To/Fixture" doctor
uv run unity-bridge --project "C:/Path/To/Fixture" test compile --wait --timeout 600
uv run unity-bridge --project "C:/Path/To/Fixture" test run --platform EditMode --min-tests 1
uv run unity-bridge --project "C:/Path/To/Fixture" test run --platform PlayMode --min-tests 1
uv run unity-bridge install --project "C:/Path/To/Fixture" --check
```

## Definition of Done

1. Every API/workflow in each pinned snapshot has one explicit coverage class.
2. Every typed and generic path has cross-language contract proof.
3. Every mutating path has containment, overwrite, conflict, rollback,
   idempotence, and state-restoration proof.
4. Every asynchronous path reaches terminal ledger state only on real
   completion.
5. Required live Unity positive and negative fixtures pass.
6. Full Python tests pass above 90% coverage; C# and live proof remain distinct.
7. Packaged install parity is clean on Unity 6.5 fixture projects.
8. Documentation and skill text match the generated live command surface.
9. Unsupported/UI-only capabilities remain visible and are never called
   covered.
