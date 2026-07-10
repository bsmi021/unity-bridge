# Unity Bridge 3.0.0 Package Evidence

Last updated: 2026-07-10

## Packaging decision

The Unity 6.5 implementation was packaged after the project owner accepted the
unproven positive Addressables content-build fixture as a visible limitation.
That scenario remains non-coverage; see `addressables-fixture-evidence.md`.

The artifacts were built locally and were not uploaded to a package registry.
The repository keeps `dist/` ignored, so these binaries are release outputs,
not source-controlled inputs.

## Artifacts

| Artifact | Size | SHA-256 |
|---|---:|---|
| `unity_bridge-3.0.0-py3-none-any.whl` | 694,369 bytes | `14601a909a4273835927c554659cffd1538963d84324d1b8b0981d55c0314cf8` |
| `unity_bridge-3.0.0.tar.gz` | 921,654 bytes | `7a8f4b5d3733b851574ea4a6174d7272fb4579d9146bb7a6bdcc43939e133dd6` |

Build and metadata validation:

```powershell
uv build --out-dir dist
uvx twine check dist/unity_bridge-3.0.0-py3-none-any.whl `
  dist/unity_bridge-3.0.0.tar.gz
```

Both artifacts passed `twine check`.

## Archive inspection

The wheel contains 480 members, including:

- all 359 managed bridge source/metadata files under
  `unity_bridge/_bundled_bridge/ClaudeCodeBridge/`;
- all nine shipped `unity-bridge-cli` skill files;
- the new exact-assembly probe and cooperative-job CLI modules;
- dependency metadata for `aiofiles>=23.0` and `typer>=0.12.0` without the
  removed Typer `all` extra.

The source distribution contains 729 members, including `pyproject.toml`, the
README, the managed bridge, the canonical skill, and the Unity 6.5 coverage and
accepted-limitation evidence.

## Clean-install proof

The final wheel was installed into a newly created Python 3.12 virtual
environment with dependencies. Validation proved:

- package metadata reported `unity-bridge 3.0.0` from the isolated
  `site-packages` directory;
- `unity-bridge version` reported CLI and bridge version `3.0.0`;
- detached operation commands, `test run --detach`/`--min-tests`, and installer
  `--force`/`--check`/`--include-claude` help were present;
- installing from the wheel into an empty disposable Unity-project shape copied
  359 managed bridge files and nine skill files;
- a second `install --check` reported both the bridge and skill `up_to_date`;
- the prior warning about Typer's removed `all` extra no longer appeared.

Repository validation before packaging remained green at 2,506 passed, 81
environment-selected skips, and 93.34% Python coverage. Command parity remained
complete at 406 classified C# operations with zero gaps.
