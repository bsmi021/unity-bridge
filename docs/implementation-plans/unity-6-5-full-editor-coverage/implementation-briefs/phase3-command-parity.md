# Phase 3 Command Surface Parity Brief

Last updated: 2026-07-10

## Scope

Build a reproducible command-surface/parity gate for every C# handler operation,
Python core wrapper, and exact Typer CLI leaf. Own a new focused tool outside
`tools/UnityApiInventory/`, its registry/report artifacts under `docs/` or a
small versioned data directory, and focused tests. Do not add new domain
capabilities in this lane.

## Required behavior

- Discover all registered C# command types and operation literals from handler
  dispatch code without relying on a hard-coded count floor.
- Discover exact invokable CLI paths and Python command types/operation payloads.
- Join the surfaces and require each C# operation intended for users to be
  classified as `typed_cli`, `raw_only`, `internal`, or `unreachable` with a
  rationale and proof pointer.
- Fail on an unclassified new/removed handler, operation, command type, or CLI
  leaf; produce deterministic machine-readable output and a compact summary.
- Explicitly flag field-name mismatches and registered command types that no
  Python path can send.
- Seed the registry from current source, but do not mark gaps typed unless an
  exact runnable path exists.

## Tests

Strict TDD with synthetic fixtures plus the real repository. Assert exact sets,
deterministic output, overload/subcommand handling, and a failing unclassified
fixture. Keep generated bulk data compact.

## Non-goals

- Do not commit/push, deploy Unity, edit production handlers/commands, revive
  MCP, or modify the API-inventory tool directory.
