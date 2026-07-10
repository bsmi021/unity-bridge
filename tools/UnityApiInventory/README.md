# Unity API Inventory Tool

Last updated: 2026-07-10

This standalone .NET tool uses Mono.Cecil to inventory the public metadata in an
exact Unity installation without adding dependencies to the shipped
`unity-bridge` Python package. It emits deterministic JSON Lines records, a
compact JSON summary, reviewable snapshot diffs, and coverage-registry gate
reports.

## Build

From the repository root in PowerShell:

```powershell
dotnet build tools/UnityApiInventory/UnityApiInventory.csproj --configuration Release
```

The pinned dependency is `Mono.Cecil` 0.11.6. Build output under `tools/**/bin`
and `tools/**/obj` is ignored by Git.

## Inventory

```powershell
$unityRoot = "C:/Program Files/Unity/Hub/Editor/6000.5.1f1"
$revision = (Get-Item "$unityRoot/Editor/Unity.exe").VersionInfo.ProductVersion

dotnet run --project tools/UnityApiInventory/UnityApiInventory.csproj -- `
  inventory `
  --unity-root $unityRoot `
  --unity-version "6000.5.1f1" `
  --unity-revision $revision `
  --capture-time "2026-07-10T12:00:00Z" `
  --build-target "StandaloneWindows64" `
  --api-compatibility "NET_Standard_2_1" `
  --define "UNITY_EDITOR" `
  --toc-js "$env:TEMP/toc.js" `
  --output "$env:TEMP/unity-6000.5.1f1.jsonl" `
  --summary "$env:TEMP/unity-6000.5.1f1-summary.json"
```

The default core boundary uses the exact runtime/editor modules loaded by Unity:
`Managed/UnityEngine/UnityEditor.*Module.dll`,
`Managed/UnityEngine/UnityEngine.*Module.dll`, and `UnityEditor.Graphs.dll`.
It deliberately excludes the monolithic `UnityEditor.dll` reference facade so
coverage records retain the runtime assembly MVID and path that the generic
host can select exactly. Supply loaded project/package or playback-variant
assemblies with repeated `--assembly FILE` or
`--assembly-root DIRECTORY` options. Native DLLs selected through explicit
roots are recorded in `skipped_assemblies` rather than aborting the snapshot.
Use `--project-root PATH` to join assembly names to asmdefs, source files,
package manifests, and `Packages/packages-lock.json`. The summary separately
records physically installed playback modules and their available variations.

`--toc-js FILE` joins the official type index using its top-level
`UnityEngine`, `UnityEditor`, and `Unity` branches. The input hash and unmatched
counts are retained because the version-channel documentation can change after
an Editor patch. Entries under the ambiguous `Other` branch remain explicitly
ignored rather than being guessed.

`--capture-time` is explicit so identical input assemblies and invocation
metadata produce byte-identical output. Defines are sorted before they are
written. Assembly records retain relative path, simple name, MVID, SHA-256,
initial provenance, and availability context.

## Diff and Coverage Gate

```powershell
dotnet run --project tools/UnityApiInventory/UnityApiInventory.csproj -- `
  diff --before before.jsonl --after after.jsonl --output api-diff.json

dotnet run --project tools/UnityApiInventory/UnityApiInventory.csproj -- `
  registry-build `
  --snapshot after.jsonl `
  --summary after-summary.json `
  --overrides reviewed-overrides.json `
  --generic-proof exact-live-assembly-proof.json `
  --output generated-registry.json

dotnet run --project tools/UnityApiInventory/UnityApiInventory.csproj -- `
  coverage-gate `
  --snapshot after.jsonl `
  --registry generated-registry.json `
  --output coverage-report.json
```

Diff output separates `added`, `removed`, `changed`, `obsolete`, and
`availability_changed` records. The coverage gate exits `3` when snapshot
symbols are unclassified, registry symbols disappeared, or registry entries
are invalid. The starter registry is intentionally empty and therefore cannot
be used to claim the current roughly 55,000-member core surface is classified.
`registry-build` creates a pinned, complete registry by conservatively marking
symbols `public_unwrapped` or metadata-backed `obsolete`, then applying reviewed
overrides and exact assembly-scoped generic proof. Generic proof must match the
snapshot SHA-256, Unity version, assembly name, MVID, and file SHA-256; it can
therefore promote every non-obsolete symbol in a proven runtime module without
a monolithic per-symbol override. A `generic` classification is rejected unless
it cites both C# compile and live-positive proof.

## Schemas and Proof Boundary

- `schemas/api-inventory-record.schema.json`
- `schemas/api-inventory-summary.schema.json`
- `schemas/snapshot-diff.schema.json`
- `schemas/coverage-registry.schema.json`
- `schemas/coverage-report.schema.json`

The tool now joins root-aware `toc.js` records, maps project assemblies through
asmdefs/package metadata, records source maps and asmdef variant constraints,
inventories physical playback-module evidence, and can classify every pinned
symbol without claiming reachability. The current remaining provenance gap is
exact evaluated Bee build-input and `.asmref`/vendor `AssetOrigin` ingestion;
without it, complex cross-package or mixed-vendor assemblies remain explicit
unresolved decisions. Full typed/generic reachability still belongs to later
phases and must not be inferred from this inventory. Do not commit
machine-local monolithic snapshots.
