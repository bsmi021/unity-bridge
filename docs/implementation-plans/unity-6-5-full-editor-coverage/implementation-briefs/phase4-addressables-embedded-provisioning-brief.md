# Phase 4 Addressables Embedded-Package Provisioning Brief

Last updated: 2026-07-10

## Scope

Attempt the smallest self-contained, disposable Unity 6000.5.1f1 Addressables
fixture at its final Temp path by provisioning exact, unmodified embedded
package sources locally instead of copying path-bound Package Manager state.

## Required Package Sources

Read-only sources:

- `C:\Projects\tms-heim\Library\PackageCache\com.unity.addressables@9bffe1a216ce`
- `C:\Projects\tms-heim\Library\PackageCache\com.unity.scriptablebuildpipeline@ea93f1084040`
- `C:\Projects\tms-heim\Library\PackageCache\com.unity.profiling.core@8a49f7027d06`

Copy them unmodified into a new final-path disposable project's `Packages/`
directory under their package names without hash suffixes. Do not copy
tms-heim's manifest, lock, ProjectCache, or projectResolution metadata.

## Allowed Actions

- Mutate only a newly named project beneath
  `C:\Users\bsmi0\AppData\Local\Temp`.
- Reuse the disposable bridge/test-runner fixture files already present under
  `unity-bridge-6000.5-current-compile` when needed.
- Launch/stop Unity only for the new disposable project.
- If package registration and compilation succeed, create settings plus one
  real addressable asset through public Addressables APIs and run
  `unity-bridge addressables build`.

## Required Output

- Exact fixture path, package hashes/versions, launch command, and process IDs.
- Whether UPM registers the embedded package set without path-bound metadata.
- Exact compile/heartbeat/list-groups/build results and log evidence.
- Whether the guarded success test can run honestly against the result.
- Cleanup confirmation.

## Non-Goals

- Do not edit repository files or any user project.
- Do not copy path-bound Package Manager cache/lock state from a user project.
- Do not patch vendor sources or DLLs, fake `PackageInfo`, or count a bridge
  precondition failure as an Addressables build result.
- Do not commit or publish.
