# Phase 4 glTF Fixture Closure Brief

Last updated: 2026-07-10

## Objective

Determine the smallest truthful live Unity 6000.5 fixture or scenario that
proves the model-import unsupported-importer failure and rollback contract
without weakening the plan's requirement or counting a skip as coverage.

## Scope

- Inspect the current model import handler, Python command, unit tests, live
  matrix test, disposable fixture, and Unity 6000.5 importer discovery.
- Decide whether a no-glTF-importer project is constructible in this installed
  Editor or whether another supported model extension can reach the same
  product branch.
- Identify exact test and fixture changes needed, with a red/green command.

## Non-goals

- Do not edit source or tests.
- Do not modify Builder, tms-heim, or any non-disposable Unity project.
- Do not replace a product-branch test with CLI validation-only coverage.

## Sources

- `ClaudeCodeBridge/AssetExtendedHelpers.cs`
- `ClaudeCodeBridge/AssetExtendedModels.cs`
- `src/unity_bridge/commands/asset_extended.py`
- `tests/integration/test_unity65_live_matrix.py`
- `tests/fixtures/unity65_model/`
- Unity 6000.5 Editor/package files installed on this machine, read-only

## Required Output

Report the reachable branch, exact fixture recipe, proposed AAA test, commands
to prove red and green, and any irreducible product/version constraint. Cite
paths and line numbers. Distinguish inference from observed evidence.

## Validation And Blockers

Use read-only source inspection and, if useful, read-only Unity/package
metadata inspection. Report the exact error or missing state if no honest
fixture can be built. No edits are allowed.
