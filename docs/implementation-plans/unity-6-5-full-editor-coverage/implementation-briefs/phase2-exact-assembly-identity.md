# Phase 2 Exact Assembly Identity

Last updated: 2026-07-10

## Scope

Implement exact, unambiguous assembly selection for the governed generic
execution path. Replace silent simple-name tie-breaking with an explicit
identity contract that can select by simple name only when unique, or by full
assembly name, MVID, and normalized loaded path when duplicates exist.

## Sources

- Phase 2 tasks and acceptance criteria in the parent implementation plan.
- `ClaudeCodeBridge/ExecuteScriptAssemblyResolver.cs` and related models.
- `src/unity_bridge/commands/scripting.py`.
- `tests/unit/test_execute_script_hardening.py` and scripting tests.
- Root and nested `AGENTS.md` instructions.

## Required workflow and output

Use TDD. First add Arrange/Act/Assert coverage for duplicate simple-name
assemblies with different identities: simple-name selection must fail with a
structured ambiguity report, while an exact full-name/MVID/path request selects
one deterministic loaded assembly. Record the red failure, then implement the
smallest data contract and resolver changes. Preserve the existing simple-name
CLI option as the unique-name convenience path. Ensure result metadata reports
the resolved full identities, not only simple names. Run focused tests and any
format/lint checks. Report changed files and red/green evidence.

## Non-goals

- Do not implement the cooperative job state machine or cancellation.
- Do not modify mutation/Undo/file transaction behavior.
- Do not run or mutate Unity projects.
- Do not commit or push.
