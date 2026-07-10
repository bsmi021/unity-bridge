# Implementation Brief: Phase 1 API Inventory Foundation

Last updated: 2026-07-10

## Objective

Implement a reproducible, tested foundation for the versioned Unity API
inventory and drift gate described in Phase 1.

## Scope

- Inspect current `tools/`, `scripts/`, packaging, and test conventions first.
- Build a Windows/PowerShell-friendly inventory tool that reads an exact Unity
  install's public Editor/runtime assemblies with Mono.Cecil without adding a
  runtime dependency to the shipped CLI.
- Emit deterministic JSON Lines plus a compact JSON summary.
- Capture Unity version/revision, assembly path/name/MVID/hash, canonical public
  type/member signatures, member kind, static/generic metadata, obsolete state,
  and initial provenance classification.
- Enforce nested declaring-type accessibility and exclude property/event
  accessors from method records.
- Support deterministic snapshot diff for added, removed, changed, obsolete,
  and availability-changed records.
- Add tests using small compiled fixture assemblies or equivalent deterministic
  metadata fixtures. Tests must not require Unity to be installed.
- Add a starter coverage-registry schema and a gate that reports unclassified
  symbols without falsely claiming that the entire 55k-member snapshot is
  already classified.

## TDD Gate

Write failing tests for nested accessibility, overload signatures,
properties/events, obsolete attributes, determinism, and diff categories before
implementing tool behavior.

## Ownership

- New files under `tools/` or `scripts/` and their focused tests.
- New generated-schema/sample files under
  `docs/implementation-plans/unity-6-5-full-editor-coverage/` if needed.
- `docs/index.md` or README only if necessary to make the tool discoverable.

## Non-Goals

- Do not change bridge runtime commands or C# handlers.
- Do not download or commit Unity binaries/reference source.
- Do not commit a monolithic generated member snapshot.
- Do not silently classify all public APIs as covered.

## Required Output

- Tool usage and output schema.
- Red and green commands/results.
- Tests proving deterministic extraction/diff behavior.
- Explicit remaining work for official `toc.js`, package/asmdef provenance, and
  full coverage classification.

Edits are allowed. Do not commit or push.
