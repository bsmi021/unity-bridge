# Implementation Brief: Phase 0 CLI Contracts and Reachability

Last updated: 2026-07-10

## Objective

Repair known Python/C# wire drift and expose every already-implemented public
operation through the supported typed CLI.

## Scope

- Fix `menu --validate-only` so Python sends the exact C# field.
- Fix screenshot camera parameter parity between Python and C#.
- Replace stale `health-check` protocol policy entries with `bridge-status`.
- Add typed CLI wrappers for:
  - animation `set-curve`, `add-event`, `set-properties`;
  - terrain `set-heights`, `set-settings`;
  - tilemap `fill-box`, `compress-bounds`;
  - asset-ext `reserialize`.
- Add exact registration/help/serialization tests so these regressions cannot
  pass subset-only assertions.
- Update README/skill references and CHANGELOG only for the changed user-facing
  command surface.

## TDD Gate

Add Arrange/Act/Assert tests first, run them red, then implement. Focus on exact
camelCase parameter names, exact command paths, option parsing, and protocol
membership.

## Ownership

Allowed production files:

- `src/unity_bridge/commands/editor.py`
- `src/unity_bridge/commands/animation.py`
- `src/unity_bridge/commands/terrain.py`
- `src/unity_bridge/commands/tilemap.py`
- `src/unity_bridge/commands/asset_extended.py`
- `src/unity_bridge/core/protocol.py`
- `ClaudeCodeBridge/BridgeModels.cs` only if screenshot parity is best fixed on
  the C# side.
- Relevant focused tests and command docs.

## Non-Goals

- Do not change screenshot Scene View restoration behavior.
- Do not change Build Profile async behavior, profiler capture, path safety,
  result envelopes, or generic script execution.
- Do not edit the API inventory tooling lane.

## Required Output

- Red and green commands/results.
- Exact new CLI paths and fixed wire fields.
- Files changed and docs updated.
- Final `git diff --check` result.

Edits are allowed. Do not commit or push.
