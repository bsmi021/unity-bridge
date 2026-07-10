# Command Surface Parity Gate

Last updated: 2026-07-10

This gate joins the registered C# bridge handlers and their operation dispatch
literals to Python bridge payload producers and exact runtime Typer/Click CLI
leaves. It is independent from `tools/UnityApiInventory/`, deterministic, and
does not require a running Unity Editor.

## Run the gate

From the repository root in PowerShell:

```powershell
uv run python tools/command_surface_parity.py check `
  --root . `
  --registry docs/implementation-plans/unity-6-5-full-editor-coverage/command-surface-registry.json `
  --output docs/implementation-plans/unity-6-5-full-editor-coverage/command-surface-report.json
```

Exit code `0` means the registry matches the discovered source surfaces and no
typed payload field mismatch remains. Exit code `3` means review is required.
The report identifies unclassified/removed C# operations, added/removed
handlers, Python command types and operations, CLI leaves, invalid registry
records, command types with no sender, and typed Python fields that the C#
parameter model cannot deserialize.

Regenerate the registry only while intentionally reviewing a command-surface
change:

```powershell
uv run python tools/command_surface_parity.py seed `
  --root . `
  --registry docs/implementation-plans/unity-6-5-full-editor-coverage/command-surface-registry.json
```

The seed marks an operation `typed_cli` only when an exact runtime CLI leaf can
reach a Python payload producer with the same command type and operation. Other
registered operations are conservatively classified `raw_only`; a reviewer may
change a classification to `internal` or `unreachable` only with a rationale
and proof pointer.

## Current source result

The source snapshot contains 101 registered handlers, 406 C# operations, 100
statically identified Python command types, 333 Python operation payloads, and
394 exact CLI leaves. All 406 C# operations are classified: 305 as `typed_cli`
and 101 as `raw_only`.

The gate currently exits `0` with no unclassified or removed surfaces, field
contract mismatches, Python operations without C# dispatch, or registered
command types without a Python sender. The prior ten gaps are repaired in both
source contracts, and the cooperative job/cancel routes are classified. Unity
deployment and live Editor validation remain separate proof points.

The machine-readable report is
`command-surface-report.json`. These are source-contract findings only; they do
not prove deployed bridge behavior or live Unity Editor execution. Production
fixes, deployment, and live validation are outside this tooling slice.
