# Implementation Brief: Phase 0 Path Safety

Last updated: 2026-07-10

## Objective

Implement the plan's canonical path-containment, explicit overwrite, and
failed-import rollback requirements for model import, asset hashing, and script
editing.

## Scope

- Work in `ClaudeCodeBridge/` and focused tests only.
- Add a shared public/internal path-safety helper with its paired Unity `.meta`
  file if a new C# source file is needed.
- Canonically prove requested asset paths remain inside the project `Assets`
  directory; reject traversal, sibling-prefix, rooted, and malformed paths.
- Make model-import overwrite behavior explicit and non-destructive.
- Roll back only files created by the current operation; never delete or damage
  pre-existing destinations on importer failure.
- Apply the same containment primitive to asset hashing and script editing.

## TDD Gate

1. Name each behavior change.
2. Add Arrange/Act/Assert tests that fail for the intended reason.
3. Run and report the red output.
4. Edit production C# only after red proof.
5. Run focused tests green.

Use structural tests only where executable C# behavior is not feasible, but
prefer extracting testable pure logic or compiling a small harness when
practical. Do not weaken existing tests.

## Sources

- `ClaudeCodeBridge/AssetExtendedHelpers.cs`
- `ClaudeCodeBridge/AssetExtendedCommandHandler.cs`
- `ClaudeCodeBridge/ScriptEditCommandHandler.cs`
- `ClaudeCodeBridge/AGENTS.md`
- `tests/unit/test_asset_extended.py`
- `tests/unit/test_script_edit.py`
- The Phase 0 section of the parent implementation plan.

## Non-Goals

- Do not change Python CLI wrappers.
- Do not change screenshot, menu, profiler, Build Profile, or generic script
  behavior.
- Do not redesign result envelopes in this lane.
- Do not edit installed bridge copies under another Unity project.

## Required Output

- Implemented files and exact behavior.
- Red and green commands/results.
- Any remaining live-Unity proof requirement.
- Final `git diff --check` result.

Edits are allowed. Do not commit or push.
