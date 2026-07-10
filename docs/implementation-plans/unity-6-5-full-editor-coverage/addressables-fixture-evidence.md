# Unity 6.5 Addressables Fixture Evidence

Last updated: 2026-07-10

## Proven negative build

An isolated Unity `6000.5.1f1` project loaded the exact Addressables `3.1.0`,
Scriptable Build Pipeline `3.1.1`, and Profiling Core `1.0.3` assemblies. It did
not contain `Assets/AddressableAssetsData`.

The live public-API outcomes were:

- `addressables list-groups` failed with `Addressable settings not initialized`,
  proving the package API was present rather than absent.
- `addressables build` called `BuildPlayerContent` and returned nonzero with
  `Addressables content build failed: Addressable Asset Settings does not
  exist. Failed to create.`
- The guarded
  `test_addressables_build_delivers_true_failure` integration scenario passed
  and also asserted that the error was not a package-missing result.

This closes the intentional-failure scenario. It does not prove a successful
content build.

## Unproven positive build

Two isolated success-fixture strategies were exercised without editing or
launching a user project.

### Copied resolution-cache attempt

A disposable project initially restored the copied package list and reported
Addressables `3.1.0`, Scriptable Build Pipeline `3.1.1`, Profiling Core `1.0.3`,
and Test Framework `1.7.0`. Package resolution then emitted three instances of:

```text
The "path" argument must be of type string. Received undefined
```

Unity terminated package loading with `No packages loaded`, so the bridge never
produced a heartbeat and no Addressables build was dispatched. The copied
metadata also contained absolute paths to its source project, so it is not an
acceptable reusable fixture.

### Clean embedded-package attempt

A second disposable project contained only final-path, project-local package
copies. No user-project manifest, lock, `ProjectCache`, or
`projectResolution.json` was copied. Full-tree SHA-256 values were:

| Package | Version | Full-tree SHA-256 |
|---|---:|---|
| Addressables | 3.1.0 | `a6c280f5f96258594c0eea26e3816a74e39a3d41d2101686311339b94e5b234a` |
| Scriptable Build Pipeline | 3.1.1 | `064ffb2c2e419f305f6aa3ef86a4c4b3e43d55ccb0ebf5e47eeb714d0d4387d0` |
| Profiling Core | 1.0.3 | `2ef544db5d6c0d260fba02dacfac58130881edfdec1d01b60616183c51de866d` |
| Test Framework | 1.7.0 | `69ce6d576cacebba089e4f9a7568a2e556a4f045540b508fd57c4122374d3e58` |
| NUnit | 2.1.0 | `74d759d5895603aa987ae3c2d92c0ec8361ac33aa1580641eb1d8d4b73165ba5` |

Each copied tree matched its read-only source. Unity connected to UPM, but UPM
reported the same undefined `path` error three times before package
registration or C# compilation, again ending with `No packages loaded`. No
heartbeat, settings creation, content build, or guarded success test was
attempted after that prerequisite failed.

## Accepted packaging limitation

The positive scenario remains non-coverage until a Unity `6000.5.1f1` Editor
can register the exact package set, create real settings plus an addressable
asset, and return `operation == "build"` with `success == true` from
`addressables build`.

The project owner authorized packaging on 2026-07-10 without converting this
missing proof into coverage. The scenario remains a release limitation and a
future validation target.

Compliant next steps are to repair or replace this Editor/UPM installation, or
provision the same final-path fixture on a clean machine/profile where package
resolution works. `-noUpm`, manually loaded DLLs, vendor patches, fake
`PackageInfo`, and user-project mutation are not valid positive-build proof.
