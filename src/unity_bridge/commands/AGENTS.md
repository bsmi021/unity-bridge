# Unity Bridge Command Module Instructions

Last updated: 2026-07-05

This directory owns Python CLI command groups and their async bridge-facing
operations.

## Command Shape

- Keep async core functions separate from Typer wrappers.
- Core functions return `CommandResult` and accept explicit typed parameters.
- Typer wrappers should stay thin: read `AppState`, call the async core through
  `asyncio.run()`, and print through the configured formatter.
- Do not put Unity file-protocol polling, config loading, or output formatting
  policy directly in wrappers when shared core helpers already exist.

## Protocol Mapping

- CLI option and output keys use `snake_case`.
- Bridge parameters sent to Unity use `camelCase`.
- Bridge command types use kebab-case.
- Timeout behavior must route through `src/unity_bridge/core/protocol.py` when a
  command has command-specific defaults or batch behavior.
- Update `PARALLEL_SAFE_COMMANDS` only for read-only commands that are safe to
  batch concurrently.

## Registration And Parity

- Register new command modules in `src/unity_bridge/app.py`.
- Verify new or renamed commands with `uv run unity-bridge --help` and targeted
  command help.
- For Unity-executed operations, keep Python command types aligned with
  `ClaudeCodeBridge/BridgeCommandRegistry.cs`.
- Do not carry stale `CLI + MCP` comments forward. The internal MCP interface is
  retired; correct that wording when touching command files.

## Tests

- Add or update focused unit tests for command serialization, option handling,
  error output, and bridge dispatch.
- Prefer `DirectBridge` mocks and existing fixtures over a real Unity project for
  unit tests.
- For command-surface changes, include CLI registration/help coverage when
  practical.
