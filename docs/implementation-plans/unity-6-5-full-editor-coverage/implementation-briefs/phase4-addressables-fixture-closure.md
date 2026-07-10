# Phase 4 Addressables Fixture Closure Brief

Last updated: 2026-07-10

## Objective

Design isolated Unity 6000.5 Addressables success and intentional-failure
fixtures that can run the current live bridge scenarios despite the disposable
project's UPM `path`-argument failure.

## Scope

- Inspect the Addressables handler, CLI, unit/live tests, fixture selection,
  installed package caches, Builder's resolved package metadata read-only, and
  the disposable Unity project's UPM logs/config.
- Determine whether an embedded/local package fixture, copied resolved package
  cache, or a corrected UPM launch/config can provide real public API behavior.
- Specify how to create success and failure settings/content without touching a
  user project.

## Non-goals

- Do not edit source, tests, Builder, tms-heim, or the disposable fixture.
- Do not substitute a mocked Addressables API for live package execution.
- Do not suppress a real package/build error to manufacture success.

## Sources

- `ClaudeCodeBridge/AddressablesCommandHandler.cs` and related helpers/models
- `src/unity_bridge/commands/addressables.py`
- `tests/integration/test_unity65_live_matrix.py`
- `tests/integration/conftest.py`
- `C:/Projects/builder/Packages/` and its package cache metadata, read-only
- disposable fixture manifest, packages-lock, and Unity logs

## Required Output

Return a source-cited fixture recipe for both outcomes, exact package versions
and paths, launch/test commands, expected success/failure assertions, and risks.
State the root cause of the current UPM error when evidence supports it.

## Validation And Blockers

Read-only investigation only. Do not launch or mutate Unity. Report exact
missing packages/files or external-state blockers rather than proposing a skip.
