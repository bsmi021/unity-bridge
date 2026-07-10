# Phase 2 Generic Host Brief

Last updated: 2026-07-10

## Scope

Implement the hardened generic `execute-script` host from Phase 2 of the parent
plan. Own `ClaudeCodeBridge/ExecuteScriptCommandHandler.cs`, new focused
`ExecuteScript*` helpers/models and paired `.meta` files, the Python
`src/unity_bridge/commands/scripting.py` wrapper, and focused tests.

## Required behavior

- Resolve loaded assembly references deterministically and de-duplicate Unity
  core facade/implementation collisions so the audited LINQ probe compiles
  without CS1685 or ambiguous extension methods.
- Accept an execution manifest containing intent, exact expected assembly
  names, timeout, Undo label, requested return schema, and an explicit
  allow-internal-reflection gate.
- Serialize primitives, enums, collections, dictionaries, Unity object
  identities/assets, and explicit DTOs into structured JSON. Reject unsupported
  values explicitly instead of silently using only `ToString()`.
- Capture compiler diagnostics separately from Unity logs.
- For mutating intent, create/collapse an Undo group and report changed Unity
  objects plus changed project files where observable.
- Preserve truthful terminal errors. Do not weaken the central response
  envelope or path-containment rules.

## Tests and proof

Use strict red/green/refactor with Arrange/Act/Assert. Unit/source-contract tests
must cover deterministic reference selection, manifest validation, structured
result kinds, log/diagnostic separation, mutation governance, and reflection
gating. Run the focused suite and all scripting/bridge-related unit tests.

Live Unity compilation and behavioral probes remain an integration proof owned
by the main agent; report exact source-only proof boundaries.

## Non-goals

- Do not commit, push, install into another project, or edit audit/plan status.
- Do not add a new MCP server or revive retired MCP interfaces.
- Do not touch unrelated Phase 0, API-inventory, or typed-wrapper files.
