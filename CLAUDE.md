# Unity Bridge

CLI for Unity Editor automation via file-based bridge protocol.

## Commands

```bash
# Install
pip install -e "."              # Core only (CLI + bridge)
pip install -e ".[dev]"         # With test/lint tools
pip install -e ".[all]"         # Everything (watch + dev)

# CLI
unity-bridge --help             # All commands and flags
unity-bridge version            # Check installed version

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
│   └── commands/              # 84 command modules (one per domain)
│       ├── hierarchy.py       # hierarchy + component groups
│       ├── workflow.py        # workflow + snapshot groups
│       ├── settings.py        # Phase 1: PlayerSettings
│       ├── asset_extended.py  # Phase 1: extended asset ops
│       ├── build_profile.py   # Phase 1: Unity 6 Build Profiles
│       ├── package.py         # Phase 1: UPM package manager
│       ├── compile_extended.py # Phase 2: compilation pipeline
│       ├── undo.py            # Phase 2: undo/redo management
│       ├── lightmap.py        # Phase 3: lightmap baking
│       ├── shader.py          # Phase 3: shader inspection
│       ├── scene_setup.py     # Phase 3: multi-scene setups
│       ├── import_settings.py # Phase 3: asset import templates
│       ├── navmesh.py         # Phase 4-ext: NavMesh bake/query
│       ├── preset.py          # Phase 6: Unity Preset asset API
│       ├── timeline.py, cinemachine.py, localization.py, memory_profiler.py, vfx.py  # package-provided systems
│       └── ...                # animator, asset, batch, build, console, addressables, terrain, tilemap, profiler, etc.
├── ClaudeCodeBridge/          # C# scripts installed into Unity Editor (100+ files)
│   ├── ClaudeUnityBridge.cs   # Main bridge loop (EditorApplication.update)
│   ├── BridgeCommandRegistry.cs # Command handler registration
│   ├── BridgeModels.cs        # Core request/response models
│   ├── BridgeModelsPhase2.cs  # Phase 2 models (undo, compile, prefab overrides)
│   ├── BridgeModelsPhase3.cs  # Phase 3 models (lightmap, shader, scene setup, import)
│   ├── *CommandHandler.cs     # One handler per command type
│   ├── *Models.cs             # Per-domain model classes
│   └── *Helpers.cs            # Split helpers for large handlers (500 LOC limit)
├── tests/                     # pytest suite
│   ├── unit/                  # Mock-based, no Unity required
│   ├── integration/           # Requires Unity running
│   ├── fixtures/              # JSON test data
│   └── conftest.py            # Shared fixtures (mock_bridge, fake_project, etc.)
└── docs/                      # Tech specs (phase 1-3 + adversarial review)
```

## Architecture

### Communication Protocol

Python writes JSON command files to `<project>/.claude/unity/commands/`. The Unity C# bridge (`ClaudeUnityBridge.cs`, running via `EditorApplication.update`) picks them up, processes them, and writes responses to `<project>/.claude/unity/responses/`. Each command has a unique UUID.

Additional bridge directories created by Phase 3 handlers:
- `<project>/.claude/unity/scene-setups/` — saved multi-scene layouts (scene-setup-operation)
- `<project>/.claude/unity/import-templates/` — saved import setting templates (import-settings-operation)

### Project Auto-Detection

`core/project.py` walks up from cwd looking for `Assets/` + `ProjectSettings/` directories. Override with `--project` flag or `UNITY_BRIDGE_PROJECT` env var.

### Single Interface — MCP Retired

The MCP server has been **fully removed** (was `mcp/`, `serve` command,
`[mcp]` extra — all deleted). The `unity-bridge` CLI (driven by the
`unity-bridge-cli` skill) is the only interface. Do not reintroduce an
`mcp/` package, a `serve` command, or MCP tool schemas — new capability
work targets the CLI + core async functions only.

### Command Module Pattern (architecture)

Each command module in `commands/` exposes:

1. **Async core functions** — accept typed params, return `CommandResult`.
2. **Typer CLI wrappers** — thin sync wrappers that call `asyncio.run()` on the core functions.

This split is kept even without MCP: it keeps Unity-communication logic
testable (mock `DirectBridge`, no Typer/argv involved) independent of the
CLI plumbing.

### Key Types

- `CommandResult` (`core/bridge.py`) — canonical return type for all commands
- `DirectBridge` (`core/bridge.py`) — async file-based Unity communication
- `BridgeConfig` (`core/config.py`) — unified config with precedence resolution
- `AppState` (`app.py`) — shared state passed to commands via `ctx.obj`, lazy-inits bridge

### Command Groups (40+ CLI groups)

**Core:** animator, asset, batch, build, component, console, diagnostics, editor, hierarchy, lifecycle, material, playmode, prefab, scene, script, snapshot, test, workflow
**Phase 1:** asset-ext, package, profile, settings
**Phase 2:** compile, undo (+ prefab overrides/gameobject-utility subcommands)
**Phase 3:** import-settings, lightmap, scene-ext, shader
**Phase 4:** select, prefs, build-scenes, transform, property, physics, quality, tags, layers, sorting-layers, editor-config
**Phase 4 expansion:** navmesh, animation-clip, terrain, reflection-probe, occlusion, script-execution-order, assembly-reload-lock, find-references
**Phase 5 (quick wins):** remove-component, component-toggle, console-log
**Phase 6 / 6b:** component-copy, component-reset, scene-view, game-view, profiler-control, preset, clipboard, deep-serialize, scene-template, tilemap, input-system, audio-settings, environment-settings, graphics-settings, time-settings, window, script-info, addressables
**Package-provided systems (post-6.4 delta):** timeline, cinemachine, localization, memory-profiler, vfx

Note: this list has drifted from the live CLI surface over several phases
(see `docs/unity-bridge-audit-and-gap-analysis.md`) — treat `unity-bridge
--help` as authoritative for the full current group list, not this doc.

## C# Bridge Installation

The `lifecycle` command copies `ClaudeCodeBridge/*.cs` into the Unity project at `Assets/Scripts/Editor/ClaudeCodeBridge/`. Files include `.meta` files for Unity asset tracking.

### C# File Organization

Large C# handlers are split to stay under 500 LOC:
- `*CommandHandler.cs` — main handler with `Execute()` dispatch
- `*Models.cs` — request/response data classes (e.g., `LightmapOperationModels.cs`)
- `*Helpers.cs` — extracted helper methods (e.g., `ImportSettingsHelpers.cs`, `AssetExtendedHelpers.cs`)
- `BridgeModels.cs` / `BridgeModelsPhase2.cs` / `BridgeModelsPhase3.cs` — shared models by phase
- Animator handler split into 5 partial class files by operation category (layer, state, transition, parameter)

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
# 1. Core async function
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
- Current parallel-safe (read-only) commands: `query-hierarchy`, `get-component-data`, `get-selection`, `read-console`, `validate-prefab`, `health-check`, `list-tests`, `shader-inspection`, `transform-operation`, `serialized-property`

## Testing

- Unit tests mock `DirectBridge` — never require Unity running
- Integration tests marked `@pytest.mark.integration`, skipped without Unity
- Use `tmp_path` fixture for file system tests
- Shared fixtures in `conftest.py`: `mock_bridge`, `healthy_bridge`, `failing_bridge`, `fake_project`, `fake_heartbeat`
- Coverage targets: core/ 90%+, commands/ 85%+

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
