# Unity Bridge C# Bridge Instructions

Last updated: 2026-07-05

This directory is the managed C# Editor bridge bundle copied into Unity projects
by `unity-bridge install`.

## Managed Bundle Rules

- Treat files here as the source of truth for deployed bridge scripts.
- Do not edit installed copies under a Unity project's
  `Assets/Scripts/Editor/ClaudeCodeBridge/` as the primary source.
- Preserve paired `.meta` files for `.cs` and `.md` assets when adding,
  renaming, or deleting bridge files.
- If bundle contents change, update install/lifecycle expectations and tests.

## Handler Organization

- `*CommandHandler.cs` files own command dispatch and Unity API interaction.
- `*Models.cs` files own serializable request/response shapes.
- `*Helpers.cs` files or partial classes split large handlers by focused
  responsibility.
- Register new handlers in `BridgeCommandRegistry.cs` and cover them with
  inventory or contract tests.

## Unity Editor Boundaries

- Do not block `EditorApplication.update` with long synchronous waits.
- Use `BridgeResponse.Running`, callbacks, `SessionState`, or polling for
  compile, test, package manager, and other long-running operations.
- Source-level correctness and deployed Unity compile correctness are separate
  proof points.

## Historical Activation Docs

- `*_ACTIVATION.md` and `ACTIVATION_INSTRUCTIONS.md` may be historical.
- Do not follow activation instructions unless `BridgeCommandRegistry.cs`,
  README, and current tests confirm they still apply.

## Validation

- For C# bridge structural changes, run relevant inventory/lifecycle tests such
  as:

```powershell
uv run pytest tests/unit/test_bridge_inventory.py tests/unit/test_commands_lifecycle.py
```

- When a Unity project/editor is available, reinstall and compile-check the
  deployed bridge before claiming runtime closure.
