# Phase 4 Addressables Cached-Project Retry Brief

Last updated: 2026-07-10

## Scope

Determine whether the disposable Unity 6000.5.1f1 project at
`C:\Users\bsmi0\AppData\Local\Temp\unity-bridge-addressables-cache-success`
can register the exact locally cached Addressables 3.1.0 package set and execute
a real Addressables content build without modifying any user project.

## Sources To Inspect

- The disposable project's `Packages/`, `Library/PackageManager/`, bridge status,
  and Editor log.
- Read-only package/cache evidence from `C:\Projects\tms-heim` when necessary.
- `tests/integration/test_unity65_live_matrix.py` and its Addressables fixtures.
- Unity 6000.5 package registration and Addressables build behavior.

## Allowed Actions

- Read repository and user-project evidence.
- Mutate only the named disposable Temp project.
- Launch or stop Unity only for that disposable project.
- Run read-only bridge/status commands and the real Addressables build in the
  disposable project.

## Required Output

- Exact launch, registration, and build result with log-backed root cause.
- Whether the result is sufficient for the guarded success integration test.
- The smallest honest next step if it is not sufficient.
- Any disposable process IDs started, so the coordinator can clean them up.

## Non-Goals

- Do not edit repository files.
- Do not edit, import into, or launch `C:\Projects\tms-heim` or
  `C:\Projects\builder`.
- Do not patch vendor DLLs, fake package registration, or reinterpret a failed
  build as success.
- Do not commit or publish.
