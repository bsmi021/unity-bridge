# Phase 3 Command Parity Repairs

Last updated: 2026-07-10

## Scope

Repair the ten gaps reported by the generated command-surface parity gate:

- `focus-object`: `noFrame` versus `frameSelection`.
- `get-component-data`: `fields` versus `fieldNames`.
- `prefab-operation|instantiate`: `position` is ignored by C#.
- `profiler-sample`: `includeCPU` is ignored by C#.
- `read-console`: `filterPattern` and `maxStackLines` do not match C#.
- `refresh-assets`: `forceRefresh` versus `forceUpdate`.
- `set-component-data`: `properties` versus `fieldUpdates`.
- `build-operation|list-platforms` has no C# dispatch.
- `build-operation|switch-platform` has no C# dispatch.
- `prefab-operation|destroy` has no C# dispatch.

## Sources

- Generated report and registry beside this brief.
- Python producers under `src/unity_bridge/commands/`.
- Corresponding handlers/models under `ClaudeCodeBridge/`.
- Existing focused tests under `tests/unit/`.
- Root and nested `AGENTS.md` instructions.

## Required workflow and output

For each gap, determine the intended public behavior from CLI help, tests, and
handler semantics. Add or update an Arrange/Act/Assert regression test, run it
red for the right reason, then make the smallest cross-language production
fix. Preserve behavior rather than merely silencing the parity tool. Regenerate
the registry/report and make the parity check exit zero. Run focused tests and
Ruff. Report changed files, red/green evidence, any capability deliberately
removed instead of implemented, and residual gaps. Do not commit, push, deploy,
or run live Unity.

## Non-goals

- Do not broaden into new capability families beyond these ten gaps.
- Do not weaken discovery or field-contract checks.
- Do not classify a reachable gap as raw-only/internal to make the gate pass.
- Do not edit unrelated user or team changes.
