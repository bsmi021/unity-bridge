# Phase 2 Generic Host Adversarial Review

Last updated: 2026-07-10

## Scope

Read-only review of the current `execute-script` implementation against Phase
2 of the Unity 6.5 full Editor coverage plan. Determine exactly which public
API shapes are reachable, which mutation/Undo/result guarantees are real, and
whether timeout, cancellation, reload recovery, main-thread scheduling,
assembly selection, and structured serialization claims are truthful.

## Sources

- The implementation plan and coverage evidence in the parent directory.
- `ClaudeCodeBridge/ExecuteScript*.cs` and bridge operation lifecycle code.
- `src/unity_bridge/commands/scripting.py` and related protocol/operation code.
- Focused scripting, bridge, and operation tests.
- Root/nested AGENTS instructions.

## Required output

Return a prioritized, source-cited punch list with the smallest architecture
that can honestly satisfy the phase acceptance criteria. Separate inherent
limits of arbitrary Unity main-thread code from repairable defects. Identify
any parameter or result field that is currently accepted but unused. Recommend
specific Arrange/Act/Assert tests and state whether a cooperative async contract
is needed. Do not edit files, run Unity, deploy, commit, or push.

## Non-goals

- Do not propose private/internal reflection as stable full coverage.
- Do not count caller-side timeout as Unity-side cancellation.
- Do not treat source-string assertions as live proof.
