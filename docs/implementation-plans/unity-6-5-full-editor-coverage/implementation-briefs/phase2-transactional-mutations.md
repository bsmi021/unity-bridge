# Phase 2 Transactional Mutations

Last updated: 2026-07-10

## Scope

Implement declared mutation targets and verifiable rollback for generic
execution. A mutating manifest must declare the Unity objects and project files
it may change. Object targets use stable `GlobalObjectId` strings; file targets
use canonical `Assets/` paths resolved through the shared containment helper.

## Sources

- Phase 0 safety invariants and Phase 2 tasks in the parent plan.
- `ClaudeCodeBridge/ExecuteScriptModels.cs`,
  `ExecuteScriptMutationScope.cs`, `AssetFileMutationScope.cs`, and
  `ProjectAssetPath.cs`.
- `src/unity_bridge/commands/scripting.py` and focused tests.
- Root and nested `AGENTS.md` instructions.

## Required workflow and output

Use TDD. First add Arrange/Act/Assert contract tests proving that mutating
execution without declared targets is rejected, traversal/reparse file targets
are rejected, declared objects are pre-recorded with Undo, declared files and
their `.meta` files are backed up before execution, undeclared observable file
changes fail, and `reverted=true` is emitted only after post-rollback
verification succeeds. Record the red failure before implementation.

Implement focused models/helpers rather than growing the handler. Preserve
read-only manifest compatibility, but do not describe it as a sandbox. Add
Python repeatable options for declared object IDs and file paths. Run focused
tests and lint. Report changed files, red/green evidence, and any behavior that
still cannot be verified without live Unity.

## Non-goals

- Do not implement job scheduling/cancellation/reload persistence.
- Do not change assembly resolution.
- Do not run or mutate Unity projects.
- Do not commit or push.
