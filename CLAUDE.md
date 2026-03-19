# Unity Bridge

CLI and MCP server for Unity Editor automation via file-based bridge protocol.

## Commands

```bash
# Install
pip install -e "."              # Core only (CLI + bridge)
pip install -e ".[mcp]"         # With MCP server
pip install -e ".[dev]"         # With test/lint tools
pip install -e ".[all]"         # Everything (mcp + watch + dev)

# CLI
unity-bridge --help             # All commands and flags
unity-bridge version            # Check installed version
unity-bridge serve              # Start MCP server mode

# Test
python3 -m pytest tests/                    # All tests (integration skipped without Unity)
python3 -m pytest tests/unit/               # Unit tests only
python3 -m pytest tests/unit/test_bridge.py  # Single file
python3 -m pytest -x --tb=short             # Stop on first failure
python3 -m pytest --cov=unity_bridge        # With coverage

# Lint
ruff check src/ tests/          # Lint
ruff format src/ tests/         # Format
```

## Global CLI Flags

All commands accept these flags via `AppState` (defined in `app.py`):

| Flag | Default | Effect |
|------|---------|--------|
| `--project PATH` | auto-detect | Unity project root |
| `--pretty` | off | Indented JSON output |
| `--human` | off | Human-readable formatted output |
| `--verbose` | off | Set log level to DEBUG |
| `--quiet` | off | Set log level to CRITICAL |
| `--timeout N` | 30 | Default command timeout (seconds) |
| `--no-color` | off | Disable colored output |

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `UNITY_BRIDGE_PROJECT` | Override project root path |
| `UNITY_BRIDGE_LOG_LEVEL` | Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL, OFF) |
| `UNITY_BRIDGE_TIMEOUT` | Default timeout in seconds |
| `UNITY_BRIDGE_CONFIG` | Path to config JSON file |
| `NO_COLOR` | Disable colored output (any value) |

## Configuration Precedence

CLI flags > environment variables > config file > defaults.

Config file search order:
1. `$UNITY_BRIDGE_CONFIG`
2. `<project_root>/unity_bridge_config.json`
3. `<project_root>/.claude/unity_bridge_config.json`

## Project Structure

```
unity-bridge/
├── src/unity_bridge/
│   ├── app.py                 # Typer entry point, AppState, global flags
│   ├── core/                  # Shared modules
│   │   ├── bridge.py          # DirectBridge, CommandResult
│   │   ├── config.py          # BridgeConfig with precedence resolution
│   │   ├── health.py          # Heartbeat-based health monitoring
│   │   ├── cache.py           # LRU cache for read-only operations
│   │   ├── retry.py           # Exponential backoff retry logic
│   │   ├── protocol.py        # Timeout defaults, parallel-safe commands
│   │   ├── project.py         # Unity project auto-detection
│   │   └── output.py          # OutputFormatter (json/pretty/human)
│   ├── commands/              # 18 command groups (one per domain)
│   └── mcp/                   # MCP server layer
│       ├── server.py          # MCP server using shared core functions
│       ├── tools.py           # Tool definitions and command dispatch map
│       └── schemas.py         # JSON Schema definitions for 26 MCP tools
├── ClaudeCodeBridge/          # C# scripts installed into Unity Editor
├── tests/                     # pytest suite
│   ├── unit/                  # Mock-based, no Unity required
│   ├── integration/           # Requires Unity running
│   ├── fixtures/              # JSON test data
│   └── conftest.py            # Shared fixtures (mock_bridge, fake_project, etc.)
└── docs/                      # Tech specs
```

## Architecture

### Communication Protocol

Python writes JSON command files to `<project>/.claude/unity/commands/`. The Unity C# bridge (`ClaudeUnityBridge.cs`, running via `EditorApplication.update`) picks them up, processes them, and writes responses to `<project>/.claude/unity/responses/`. Each command has a unique UUID.

### Project Auto-Detection

`core/project.py` walks up from cwd looking for `Assets/` + `ProjectSettings/` directories. Override with `--project` flag or `UNITY_BRIDGE_PROJECT` env var.

### Dual Interface Pattern

CLI and MCP share 100% of core logic. Each command module in `commands/` exposes:

1. **Async core functions** — accept typed params, return `CommandResult`. Called by both CLI and MCP.
2. **Typer CLI wrappers** — thin sync wrappers that call `asyncio.run()` on the core functions.

MCP handlers in `mcp/server.py` `await` the same core functions directly. Never use `asyncio.run()` inside MCP handlers — it crashes with `RuntimeError: This event loop is already running`.

### Key Types

- `CommandResult` (`core/bridge.py`) — canonical return type for all commands
- `DirectBridge` (`core/bridge.py`) — async file-based Unity communication
- `BridgeConfig` (`core/config.py`) — unified config with precedence resolution
- `AppState` (`app.py`) — shared state passed to commands via `ctx.obj`, lazy-inits bridge

### Command Groups

animator, asset, batch, build, console, diagnostics, editor, hierarchy, component, lifecycle, material, playmode, prefab, scene, script, serve, test, workflow, snapshot

## C# Bridge Installation

The `lifecycle` command copies `ClaudeCodeBridge/*.cs` into the Unity project at `Assets/Scripts/Editor/ClaudeCodeBridge/`. The MCP server auto-installs on first run. Files include `.meta` files for Unity asset tracking.

## Code Conventions

- Python 3.10+ syntax: use `X | Y` unions, not `Optional[X]` or `Union[X, Y]`
- Use `datetime.now(timezone.utc)` — never `datetime.utcnow()`
- Use `asyncio.get_running_loop()` inside async — never `asyncio.get_event_loop()`
- Type hints on all public function signatures; avoid `Any` where specific types are possible
- Use dataclasses for structured data
- One public class per file when practical
- All source files under 500 LOC, all functions under 50 LOC
- Line length: 100 (configured in `pyproject.toml` via ruff)

## Command Module Pattern

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

## Output Rules

- JSON to stdout by default (no `--json` flag needed)
- `--human` for formatted output, `--pretty` for indented JSON
- CLI output uses `snake_case` keys; bridge protocol uses `camelCase`
- Errors in human mode go to stderr; JSON errors go to stdout with `"success": false`
- Logging to stderr via `logging.getLogger("unity_bridge")`

## Bridge Protocol

- Command types use kebab-case: `run-tests`, `query-hierarchy`, `set-component-data`
- Parameters use camelCase (matching C# conventions): `testPlatform`, `waitForCompletion`
- Timeout defaults are in `core/protocol.py` — use `get_timeout()` with 3-level precedence
- `PARALLEL_SAFE_COMMANDS` in `core/protocol.py` is the single source of truth for batch parallelism

## Testing

- Unit tests mock `DirectBridge` — never require Unity running
- Integration tests marked `@pytest.mark.integration`, skipped without Unity
- Use `tmp_path` fixture for file system tests
- Shared fixtures in `conftest.py`: `mock_bridge`, `healthy_bridge`, `failing_bridge`, `fake_project`, `fake_heartbeat`
- Coverage targets: core/ 90%+, commands/ 85%+, mcp/ 80%+

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Command failure (Unity error, tests failed) |
| 2 | Bridge unavailable (Unity not running, heartbeat stale) |
| 3 | Invalid input |
| 4 | Timeout |
| 5 | Internal error |
| 130 | Interrupted (Ctrl+C) |
