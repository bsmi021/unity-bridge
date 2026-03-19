# Unity Bridge

CLI and MCP server for Unity Editor automation via file-based bridge protocol.

## Project Structure

```
unity-bridge/
├── src/unity_bridge/          # CLI package (v3.0.0)
│   ├── app.py                 # Typer entry point, global flags, command registration
│   ├── core/                  # Shared core modules (bridge, health, cache, retry, config, project, protocol, output)
│   ├── commands/              # CLI command modules (one per domain)
│   └── mcp/                   # MCP server layer (server.py, tools.py, schemas.py)
├── ClaudeCodeBridge/          # C# bridge files installed into Unity projects
├── tests/                     # pytest suite (unit/, integration/, fixtures/)
├── docs/                      # Tech specs and reviews
└── pyproject.toml             # Package definition, entry points
```

## Architecture

### Communication Protocol

Python writes JSON command files to `.claude/unity/commands/`, the Unity C# bridge (running in Editor via `EditorApplication.update`) picks them up, processes them, and writes responses to `.claude/unity/responses/`. Each command has a unique UUID to prevent collisions.

### Dual Interface Pattern

CLI and MCP share 100% of core logic. Each command module in `commands/` exposes:

1. **Async core functions** — accept typed params, return `CommandResult`. Called by both CLI and MCP.
2. **Typer CLI wrappers** — thin sync wrappers that call `asyncio.run()` on the core functions.

MCP handlers in `mcp/server.py` `await` the same core functions directly (never use `asyncio.run()` inside MCP handlers — it crashes with `RuntimeError`).

### Key Types

- `CommandResult` (core/bridge.py) — canonical return type for all commands
- `DirectBridge` (core/bridge.py) — async file-based Unity communication
- `BridgeConfig` (core/config.py) — unified config with precedence: CLI flags > env vars > config file > defaults
- `AppState` (app.py) — shared state passed to commands via `ctx.obj`, lazy-inits bridge via property

## Development

```bash
pip install -e ".[all]"        # Install with all extras
python3 -m pytest tests/       # Run tests (293 unit, 31 integration skipped without Unity)
unity-bridge --help             # CLI entry point
unity-bridge serve              # Start MCP server mode
```

## Rules

### Output

- JSON to stdout by default (no `--json` flag needed)
- `--human` flag for formatted output, `--pretty` for indented JSON
- All CLI output uses `snake_case` keys; bridge protocol uses `camelCase`
- Errors in human mode go to stderr; JSON errors go to stdout with `"success": false`
- Logging goes to stderr via `logging.getLogger("unity_bridge")`

### Code Conventions

- All source files under 500 LOC (excluding comments/whitespace)
- All functions under 50 LOC
- Python 3.10+ syntax: use `X | Y` unions, not `Optional[X]` or `Union[X, Y]`
- Use `datetime.now(timezone.utc)` — never `datetime.utcnow()`
- Use `asyncio.get_running_loop()` inside async functions — never `asyncio.get_event_loop()`
- Use type hints on all public function signatures; avoid `Any` where specific types are possible
- Use dataclasses for structured data
- One public class per file when practical

### Command Module Pattern

Every command module follows this pattern:

```python
# 1. Core async function (shared by CLI + MCP)
async def do_thing(bridge: DirectBridge, ...) -> CommandResult:
    return await bridge.send_command_with_retry(...)

# 2. Typer CLI wrapper
@some_app.command()
def do_thing_cli(ctx: typer.Context, ...) -> None:
    state: AppState = ctx.obj
    result = asyncio.run(do_thing(state.bridge, ...))
    print_result(result, state.formatter)
```

### Testing

- Unit tests mock `DirectBridge` — never require Unity running
- Integration tests are marked `@pytest.mark.integration` and skipped without Unity
- Use `tmp_path` fixture for file system tests
- Coverage targets: core/ 90%+, commands/ 85%+, mcp/ 80%+

### Bridge Protocol

- Command types use kebab-case: `run-tests`, `query-hierarchy`, `set-component-data`
- Parameters use camelCase (matching C# conventions): `testPlatform`, `waitForCompletion`, `maxDepth`
- Timeout defaults are in `core/protocol.py` — use `get_timeout()` with 3-level precedence
- `PARALLEL_SAFE_COMMANDS` in `core/protocol.py` is the single source of truth — do not duplicate

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Command failure (Unity error, tests failed) |
| 2 | Bridge unavailable (Unity not running, heartbeat stale) |
| 3 | Invalid input |
| 4 | Timeout |
| 5 | Internal error |
| 130 | Interrupted (Ctrl+C) |

## Known Issues (to fix)

- `mcp/server.py` `_invoke_command` calls `.get()` on `CommandResult` — needs `.success` / `.to_dict()`
- `core/retry.py` `retry_async` only checks `isinstance(result, dict)` — needs `CommandResult` branch
- `commands/testing.py` compile sends `{"wait": ...}` but C# bridge expects `{"waitForCompletion": ...}`
