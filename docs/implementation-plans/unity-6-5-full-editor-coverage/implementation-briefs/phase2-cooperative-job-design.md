# Phase 2 Cooperative Job Design Review

Last updated: 2026-07-10

## Scope

Perform a read-only, repo-grounded design pass for a cooperative generic
execution job that returns `running`, advances bounded steps from
`EditorApplication.update`, supports cancellation/deadline checks between
steps, survives or truthfully terminates on domain reload, and writes exactly
one terminal response.

## Sources

- Phase 2 tasks and Definition of Done in the parent plan.
- Existing compile, Build Profile, test-run, operation-ledger, heartbeat, and
  command processing lifecycle code.
- Current `ExecuteScript*` implementation and focused tests.
- Root/nested `AGENTS.md` instructions.

## Required output

Return a source-cited proposed state machine, ownership boundaries, persisted
fields, command/result contracts, cancellation race handling, and the smallest
tests that prove heartbeat continuity, timeout, cancel, reload, and one-terminal
writer behavior. Identify any Unity API or C# runtime constraint that prevents
arbitrary code preemption and make the cooperative boundary explicit. Do not
edit files, run Unity, commit, or push.

## Non-goals

- Do not treat `Task.Run` as valid for Unity main-thread APIs.
- Do not promise preemption inside a single user step.
- Do not redesign unrelated command handlers.
