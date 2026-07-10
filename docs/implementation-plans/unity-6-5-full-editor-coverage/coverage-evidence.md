# Unity 6.5 API Coverage Evidence

Last updated: 2026-07-10

## Pinned snapshots

The inventory tool was run against Unity `6000.5.1f1` revision
`0d9463e84828` on Windows. The corrected core boundary inventories the exact
`UnityEditor.*Module.dll` and `UnityEngine.*Module.dll` runtime assemblies
rather than Unity's monolithic `UnityEditor.dll` reference facade. That makes
each inventory assembly identity selectable by the live generic host.

Core runtime-module snapshot:

- 146 assemblies inspected; 94 contain public symbol records.
- 60,345 canonical public records.
- Snapshot SHA-256:
  `6f879259ca96f180b03e964a6643bc41d459f2bfb1efa060363b4e47404b4fd8`.
- 57,510 current records classified `generic`.
- 2,835 metadata-obsolete records classified `obsolete`.
- Zero `public_unwrapped` records.

Core plus Builder package/project snapshot:

- 323 assemblies inspected; 199 contain public symbol records.
- 129,615 canonical public records.
- Snapshot SHA-256:
  `dbf3bdecfe8c6b5b2b053c0b3339419b41908546e158ef20b05d561a98a8d768`.
- 173 asmdef/package-mapped Builder assemblies and four predefined project
  assemblies; no unresolved assembly names.
- 126,095 current records classified `generic`.
- 3,520 metadata-obsolete records classified `obsolete`.
- Zero `public_unwrapped`, unclassified, removed, or invalid records.

The earlier reference-facade snapshot is superseded. Its official Unity 6.5
`toc.js` SHA-256 remains
`5bad87a7e197d843d596c231d854c3f6992bb7960cbc64a35b6c991290c01dcd`;
documentation joins are independent from the runtime-identity correction.

## Generic classification proof

`script-probe-assemblies` enumerated the live AppDomain, matched each snapshot
assembly by simple name, MVID, path, and file SHA-256, then submitted a separate
exact-identity compiler probe for every match. The final clean run proved all
199 assemblies that contribute public records. `registry-build
--generic-proof` accepted that proof and `coverage-gate` reported all 129,615
records classified.

This is assembly-scoped reachability proof: a current public symbol can be
referenced through the hardened C# host when its pinned assembly is loaded. It
is not a claim that every member was semantically invoked in every valid Editor
state. High-risk workflows still require typed commands and scenario-specific
live proof.

The generic host now provides:

- deterministic simple-name or exact full-name/MVID/path assembly selection;
- structured scalar, collection, dictionary, Unity object, and DTO results;
- separate compiler diagnostics and Unity logs;
- an explicit non-public-reflection gate;
- declared GlobalObjectId and `Assets/` file mutation transactions;
- verified rollback reporting;
- cooperative jobs with one step per Editor update, deadline, cancellation,
  durable terminal response, and truthful reload interruption.

Arbitrary factory/step code remains full trust and cannot be preempted while it
is executing. Read-only intent is advisory, and a mutating job interrupted by a
domain reload does not carry its in-memory rollback journal across that reload.

## Command and live proof

The independent command parity gate is clean at:

- 101 registered handlers;
- 406 C# operations;
- 100 Python command types and 333 Python operation payloads;
- 394 exact CLI leaves;
- 305 `typed_cli` and 101 reviewed `raw_only` operations;
- zero parity gaps.

A disposable Unity `6000.5.1f1` project accepted 359 managed bridge files and
nine skill files. The installed bundle compiled with zero structured C# errors
or warnings. The expanded 50-scenario guarded headless run returned 47 passed
and three explicit skips; the two headless Scene View skips passed separately
in a normal hidden Editor. The remaining skip is the unproven real
Addressables-success build. Skips remain non-coverage.

The negative glTF case now passes against Unity 6.5's generic `AssetImporter`
fallback and proves that the staged asset and `.meta` are rolled back. The
profiler now drives Editor collection through `ProfilerDriver`, stops at the
requested retained-frame target with explicit overshoot telemetry, cancels a
frame budget when `profiler-control stop` is used, and captures self-authored
timing/allocation markers in a headless Editor. The real Addressables
intentional-failure scenario also passes. The positive Addressables build is
still blocked before package registration by the local UPM `path`-argument
failure; copied-cache and clean embedded-package experiments are documented in
`addressables-fixture-evidence.md`.

Positive live evidence includes LINQ without duplicate core references, exact
assembly replay, cooperative multi-update completion, deadline, cancellation,
declared-file rollback, GlobalObjectId rollback, compiler-error truth,
self-discovered Build Profile platform creation, screenshot and Scene View
restoration contracts, PlayMode enter/stop terminal delivery across real domain
reloads, profiler budget and marker/allocation capture, glTF fallback rollback,
and the real Addressables negative build.

The final repository validation collected 2,587 tests: 2,506 passed, 81 were
explicitly skipped because no live integration environment was selected, and
coverage reached 93.34%, exceeding the required 90% gate.

The disposable project cannot initialize UPM because Unity's local Package
Manager reports `The "path" argument must be of type string. Received
undefined`. Its Test Framework DLLs were therefore supplied as fixture-only
compiler references. This does not affect the exact Builder assembly proof,
which loaded already-resolved DLLs read-only into the disposable AppDomain.

## Packaging disposition

The project owner authorized packaging on 2026-07-10 with the positive
Addressables build retained as a known, explicit limitation. All symbol records
remain classified and all other required live workflows are proven. The
unproven scenario is not counted as coverage and must be rerun when a working
Unity `6000.5.1f1` UPM environment is available.

## Reproduction

```powershell
dotnet run --project tools/UnityApiInventory/UnityApiInventory.csproj -- inventory ...

uv run unity-bridge --project "C:/Path/To/Fixture" `
  script-probe-assemblies SNAPSHOT.jsonl `
  --output GENERIC-PROOF.json

dotnet run --project tools/UnityApiInventory/UnityApiInventory.csproj -- `
  registry-build --snapshot SNAPSHOT.jsonl --summary SUMMARY.json `
  --generic-proof GENERIC-PROOF.json --output REGISTRY.json

dotnet run --project tools/UnityApiInventory/UnityApiInventory.csproj -- `
  coverage-gate --snapshot SNAPSHOT.jsonl --registry REGISTRY.json `
  --output COVERAGE-REPORT.json
```

Machine-local monolithic snapshots and generated per-symbol registries are not
committed. The compact source schemas, commands, hashes, counts, and proof
boundary are durable in this repository.
