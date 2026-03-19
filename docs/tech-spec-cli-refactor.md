# Tech Spec: Unity Bridge CLI Refactor

**Status:** Draft (Revised)
**Author:** Claude Code
**Last Updated:** 2026-03-17
**Version:** 1.2.0

---

## 1. Overview

### Problem Statement

The Unity Bridge currently exposes its 22+ tools exclusively through an MCP server (`unity_bridge_mcp_server.py`). This creates several problems:

1. **No standalone usage.** Developers cannot run Unity Bridge commands from a terminal without an MCP-aware client.
2. **Debugging friction.** Diagnosing bridge issues requires reading raw JSON files or running ad-hoc Python scripts.
3. **No composability.** Shell scripts, CI pipelines, and other tools cannot integrate with Unity Bridge without MCP.
4. **Monolithic server file.** `unity_bridge_mcp_server.py` is 1,493 lines and growing, containing tool definitions, dispatch logic, help content, config management, and batch execution in a single file.
5. **Duplicated command dispatch.** `scripts/send_command.py` and `scripts/invoke_unity_command.py` duplicate the file-based command protocol already implemented in `DirectBridge`.

### Goals

- **G1:** Provide a first-class CLI (`unity-bridge`) that can be used standalone from any terminal.
- **G2:** Share 100% of core logic between CLI and MCP modes -- no divergent implementations.
- **G3:** Add Tier 1 (Python-side) and Tier 2 (compound/new) commands for developer workflows.
- **G4:** Maintain full backward compatibility via `unity-bridge serve` for MCP mode.
- **G5:** Keep every source file under 500 LOC and every function under 50 LOC.
- **G6:** Make the package installable via `pip install` with a `unity-bridge` entry point.

### Non-Goals

- Replacing the C# bridge in Unity Editor (unchanged).
- Changing the file-based communication protocol (`.claude/unity/commands/` and `.claude/unity/responses/`).
- Building a GUI or TUI dashboard.
- Supporting Unity versions below Unity 6.
- Providing a REST/HTTP API.

---

## 2. CLI Command Reference

### Command Tree

```
unity-bridge
├── status                    # Quick alive/dead check
├── doctor                    # Full diagnostic
├── version                   # Version info
├── install [--project PATH]  # Install/update C# bridge files
├── init [--project PATH]     # Initialize directory structure
├── clean [--all] [--age MIN] # Remove orphaned files
├── serve                     # Start MCP server mode (backward compat)
│
├── compile [--timeout SEC]
├── tdd [--platform PLAT] [--filter PAT]
│
├── hierarchy [--depth N] [--inactive] [--root PATH]
├── component get <object> <type> [--fields F1,F2]
├── component set <object> <type> --update FIELD:JSON [--update FIELD:JSON ...]
│   # Supports multiple --update flags for batch field updates in a single call.
│   # Example: unity-bridge component set Player Transform --update 'position.x:1.5' --update 'position.y:0'
├── component add <object> <type>
│
├── scene load <path> [--save-current]
├── scene save
├── scene create <path>
│
├── prefab validate <path>
├── prefab instantiate <path> [--position X,Y,Z]
├── prefab destroy <instance-path>  # Destroys a prefab instance in the active scene (by GameObject path), NOT the prefab asset on disk
│
├── playmode play|pause|stop
│
├── console read [--types error,warning,log] [--max N] [--pattern PAT]
├── console watch [--types TYPES] [--poll-interval SEC]  # Follow mode (replaces top-level watch and log --follow)
├── console clear
│
├── screenshot <output-path> [--camera NAME] [--width W] [--height H]
├── profiler [--memory] [--rendering] [--cpu]
│
├── material modify|create|duplicate <path> [--properties JSON]
├── asset find|query|import|refresh [--path P] [--type T] [--pattern PAT]
├── build --target TARGET [--validate-only] [--output PATH] [--dev]
├── animator get-state|set-state|get-params|set-param <object> [OPTIONS]
│
├── selection [--components] [--children]
├── refresh [--force]
├── focus <object> [--no-frame]
├── menu <menu-path> [--validate-only]
│
├── batch <file.json> [--stop-on-error] [--parallel]
├── script <expression> [--timeout SEC]
│
├── snapshot save <file> [--depth N] [--max-objects N] [--root PATH]
├── snapshot diff <file1> <file2>
├── test run [--platform PLAT] [--filter PAT] [--timeout SEC]
├── test watch [--platform PLAT] [--filter PAT] [--path DIR]
│
├── config get [KEY]
├── config set KEY VALUE
│
├── help [COMMAND]
```

### Global Flags

| Flag | Short | Type | Default | Description |
|------|-------|------|---------|-------------|
| `--project` | `-p` | `PATH` | auto-detect | Unity project root directory |
| `--pretty` | | `bool` | `false` | Pretty-print JSON output |
| `--human` | `-H` | `bool` | `false` | Human-readable formatted output |
| `--verbose` | `-v` | `bool` | `false` | Verbose logging to stderr |
| `--quiet` | `-q` | `bool` | `false` | Suppress all non-essential output |
| `--timeout` | `-t` | `int` | per-command | Override default timeout (seconds) |
| `--no-color` | | `bool` | `false` | Disable colored output |

> **Output default:** JSON to stdout. Use `--human` for formatted output or `--pretty` for indented JSON. To change the default, set `output_format` in config.

### Example Usage

```bash
# Quick health check
unity-bridge status
# {"healthy": true, "unity_version": "6000.0.23f1", "active_scene": "MainScene"}

# Run tests with human-readable output
unity-bridge test run --platform EditMode --filter CombatTests --human
# PASS  CombatControllerTests.TestDamageCalculation (12ms)
# PASS  CombatControllerTests.TestHealthReduction (8ms)
# FAIL  CombatControllerTests.TestDeathOnZeroHealth (15ms)
#   Expected: isDead = true
#   Actual:   isDead = false
#
# Results: 2 passed, 1 failed (35ms)

# TDD workflow (clear -> compile -> test -> console)
unity-bridge tdd --platform EditMode --filter CombatTests

# Watch console in real-time
unity-bridge console watch --types error,warning

# Execute C# expression in Unity Editor
unity-bridge script "UnityEditor.EditorApplication.isPlaying = true"

# Snapshot and diff scene state
unity-bridge snapshot save before.json --depth 3
# ... make changes ...
unity-bridge snapshot save after.json --depth 3
unity-bridge snapshot diff before.json after.json --human

# Pipe JSON output to jq
unity-bridge hierarchy --depth 2 | jq '.data.children[].name'

# MCP backward compatibility
unity-bridge serve
```

---

## 3. Architecture

### Package Structure

```
unity-plugin/unity/
├── pyproject.toml                    # Package definition, entry points
├── requirements.txt                  # Runtime dependencies (kept for backward compat)
├── unity_bridge_mcp_server.py        # DEPRECATED: thin wrapper, calls `unity-bridge serve`
│
├── src/
│   └── unity_bridge/
│       ├── __init__.py               # Package metadata, __version__
│       ├── __main__.py               # `python -m unity_bridge` entry point
│       ├── app.py                    # Typer app definition, global options
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── bridge.py             # DirectBridge (migrated from direct_bridge.py)
│       │   ├── health.py             # HealthMonitor, HealthStatus (from health_monitor.py)
│       │   ├── cache.py              # ResponseCache (from response_cache.py)
│       │   ├── retry.py              # RetryConfig, retry_async (from retry_handler.py)
│       │   ├── config.py             # Configuration loading, defaults, precedence
│       │   ├── project.py            # Unity project detection, path resolution
│       │   ├── protocol.py           # Command/response types, timeout defaults
│       │   └── output.py             # Output formatting (JSON, human, pretty)
│       │
│       ├── commands/
│       │   ├── __init__.py
│       │   ├── testing.py            # run-tests, compile, tdd
│       │   ├── hierarchy.py          # hierarchy, component get/set/add
│       │   ├── scene.py              # scene load/save/create
│       │   ├── prefab.py             # prefab validate/instantiate/delete
│       │   ├── playmode.py           # playmode play/pause/stop
│       │   ├── console.py            # console read/clear, watch, log
│       │   ├── editor.py             # selection, refresh, focus, menu, screenshot
│       │   ├── asset.py              # asset find/query/import/refresh
│       │   ├── material.py           # material modify/create/duplicate
│       │   ├── build.py              # build, validate
│       │   ├── animator.py           # animator state/parameter operations
│       │   ├── diagnostics.py        # status, doctor, health-check, profiler
│       │   ├── lifecycle.py          # install, init, clean, version
│       │   ├── workflow.py           # tdd, snapshot, diff, test-watch
│       │   ├── scripting.py          # script (C# expression execution)
│       │   ├── batch.py              # batch command execution
│       │   └── serve.py              # MCP server mode
│       │
│       │   # Formatters start as functions in core/output.py.
│       │   # Extract to a formatters/ package later if they grow beyond 100 LOC.
│       │
│       └── mcp/
│           ├── __init__.py
│           ├── server.py             # MCP server (migrated from unity_bridge_mcp_server.py)
│           └── tools.py              # MCP tool definitions and dispatch
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_bridge.py
│   │   ├── test_health.py
│   │   ├── test_cache.py
│   │   ├── test_retry.py
│   │   ├── test_config.py
│   │   ├── test_project.py
│   │   ├── test_protocol.py
│   │   ├── test_output.py
│   │   ├── test_commands_testing.py
│   │   ├── test_commands_lifecycle.py
│   │   ├── test_commands_workflow.py
│   │   └── test_commands_scripting.py
│   ├── integration/
│   │   ├── test_cli_smoke.py
│   │   ├── test_mcp_compat.py
│   │   └── test_bridge_roundtrip.py
│   └── fixtures/
│       ├── heartbeat.json
│       ├── sample_hierarchy.json
│       ├── sample_test_results.json
│       └── sample_snapshot.json
│
├── ClaudeCodeBridge/                  # C# bridge files (unchanged)
├── scripts/                           # DEPRECATED: kept for backward compat, not developed
├── direct_bridge.py                   # DEPRECATED: use src/unity_bridge/core/bridge.py
├── health_monitor.py                  # DEPRECATED: use src/unity_bridge/core/health.py
├── response_cache.py                  # DEPRECATED: use src/unity_bridge/core/cache.py
├── retry_handler.py                   # DEPRECATED: use src/unity_bridge/core/retry.py
├── install_bridge.py                  # DEPRECATED: use src/unity_bridge/commands/lifecycle.py
└── docs/
    └── tech-spec-cli-refactor.md      # This document
```

### Data Flow

```
CLI Entry Point                   MCP Entry Point
     │                                 │
     ▼                                 ▼
  app.py (Typer)                 mcp/server.py
     │                                 │
     ▼                                 ▼
  commands/*.py ◄──────────────► mcp/tools.py
     │              (shared)           │
     ├─── Python-only logic            │
     │    (status, doctor, clean,      │
     │     install, config, etc.)      │
     │                                 │
     └─── Unity Bridge commands ───────┘
          │
          ▼
     core/bridge.py (DirectBridge)
          │
          ▼
     core/retry.py + core/cache.py
          │
          ▼
     File I/O (.claude/unity/commands/*.json)
          │
          ▼
     Unity C# Bridge (ClaudeUnityBridge.cs)
          │
          ▼
     File I/O (.claude/unity/responses/*.json)
          │
          ▼
     core/bridge.py (response parsing)
          │
          ▼
     core/output.py (formatting)
          │
          ▼
     stdout (JSON or human-readable)
```

---

## 4. Module Design

### 4.1 `core/bridge.py` — DirectBridge

Migrated from `direct_bridge.py`. The async file-based communication layer.

**Public API:**

```python
@dataclass
class CommandResult:
    """Standardized result from any bridge command."""
    success: bool
    data: Any | None = None
    error: str | None = None
    command_id: str | None = None
    execution_time_ms: int = 0
    exit_code: int = 0
    cached: bool = False

class DirectBridge:
    def __init__(self, project_root: Path) -> None: ...
    async def send_command(
        self,
        command_type: str,
        parameters: dict[str, Any] | None = None,
        timeout: float = 30.0,
        check_health: bool = True,
    ) -> CommandResult: ...
    async def send_command_with_retry(
        self,
        command_type: str,
        parameters: dict[str, Any] | None = None,
        timeout: float = 30.0,
        retry_config: RetryConfig | None = None,
    ) -> CommandResult: ...
```

**Changes from current:**
- Return `CommandResult` dataclass instead of raw dict.
- Move `CommandResult` from `invoke_unity_command.py` here as the canonical result type.
- Remove duplicate `send_command` implementations in `scripts/`.

### 4.2 `core/health.py` — HealthMonitor

Migrated from `health_monitor.py`. No API changes.

```python
@dataclass
class HealthStatus:
    healthy: bool
    reason: str | None = None
    unity_version: str | None = None
    is_compiling: bool = False
    is_playing: bool = False
    is_paused: bool = False
    active_scene: str | None = None
    commands_processed: int = 0
    uptime_seconds: int = 0
    heartbeat_age_seconds: float = 0.0
    def to_dict(self) -> dict[str, Any]: ...

class HealthMonitor:
    MAX_HEARTBEAT_AGE_SECONDS: float = 15.0
    def __init__(self, project_root: Path) -> None: ...
    def check_health(self) -> HealthStatus: ...
    def wait_for_healthy(self, timeout_seconds: float = 30.0, poll_interval: float = 0.5) -> HealthStatus: ...
```

### 4.3 `core/config.py` — Configuration

```python
from dataclasses import dataclass, field

@dataclass
class BridgeConfig:
    """Unified configuration with precedence: CLI flags > env vars > config file > defaults."""
    project_root: Path | None = None          # --project or UNITY_BRIDGE_PROJECT
    log_level: str = "ERROR"                  # --verbose → DEBUG, or UNITY_BRIDGE_LOG_LEVEL
    output_format: str = "json"               # --human → "human", --pretty → "pretty"
    default_timeout: int = 30                  # --timeout or UNITY_BRIDGE_TIMEOUT
    color: bool = True                        # --no-color → False
    config_file: Path | None = None           # Auto-detected or UNITY_BRIDGE_CONFIG

    @classmethod
    def from_env(cls) -> "BridgeConfig": ...

    @classmethod
    def from_file(cls, path: Path) -> "BridgeConfig": ...

    @classmethod
    def resolve(
        cls,
        cli_project: Path | None = None,
        cli_format: str | None = None,
        cli_verbose: bool = False,
        cli_quiet: bool = False,
        cli_timeout: int | None = None,
        cli_no_color: bool = False,
    ) -> "BridgeConfig": ...

def load_config_file(path: Path | None = None) -> dict[str, Any]: ...
def save_config_file(config: dict[str, Any], path: Path | None = None) -> bool: ...
```

**Config file format** (`unity_bridge_config.json`):

```json
{
  "log_level": "ERROR",
  "default_timeout": 30,
  "color": true,
  "version": "1.0.0"
}
```

**Precedence:** CLI flags > environment variables > config file > defaults.

**Environment variables:**

| Variable | Description |
|----------|-------------|
| `UNITY_BRIDGE_PROJECT` | Unity project root path |
| `UNITY_BRIDGE_LOG_LEVEL` | Logging level |
| `UNITY_BRIDGE_TIMEOUT` | Default command timeout |
| `UNITY_BRIDGE_CONFIG` | Config file path |
| `NO_COLOR` | Disable color (standard) |

### 4.4 `core/project.py` — Project Detection

```python
def detect_unity_project(start_path: Path | None = None) -> Path:
    """Walk up from CWD looking for a directory containing both Assets/ and
    ProjectSettings/. Stop at filesystem root or after 10 levels. If not
    found, raise PROJECT_NOT_FOUND error with exit code 2."""
    ...
def find_unity_project_root(start_path: Path) -> Path | None: ...
def validate_project(project_root: Path) -> list[str]: ...
def get_bridge_paths(project_root: Path) -> BridgePaths: ...

@dataclass
class BridgePaths:
    project_root: Path
    commands_dir: Path      # .claude/unity/commands/
    responses_dir: Path     # .claude/unity/responses/
    heartbeat_file: Path    # .claude/unity/heartbeat.json
    editor_bridge_dir: Path # Assets/Scripts/Editor/ClaudeCodeBridge/
```

**Path handling:** All paths are normalized using `pathlib.Path` which handles both `/` and `\` on Windows. Unity asset paths (scene, prefab, material) use forward-slash relative paths from the project root (e.g., `Assets/Scenes/Main.unity`). The CLI accepts either slash style and normalizes internally.

### 4.5 `core/protocol.py` — Command Protocol Types

```python
from dataclasses import dataclass

TIMEOUT_DEFAULTS: dict[str, int] = {
    "query-hierarchy": 10,
    "get-component-data": 10,
    "read-console": 10,
    "playmode-control": 10,
    "clear-console": 5,
    "get-selection": 5,
    "refresh-assets": 15,
    "focus-object": 5,
    "health-check": 5,
    "set-component-data": 30,
    "add-component": 30,
    "scene-operation": 30,
    "prefab-operation": 30,
    "validate-prefab": 30,
    "material-operation": 30,
    "animator-operation": 30,
    "execute-menu-item": 30,
    "run-tests": 300,
    "compile": 120,
    "asset-operation": 60,
    "build-operation": 600,
    "execute-script": 30,
}

PARALLEL_SAFE_COMMANDS: set[str] = {
    "query-hierarchy",
    "get-component-data",
    "get-selection",
    "read-console",
    "validate-prefab",
    "health-check",
}

def get_timeout(
    command_type: str,
    command_override: int | None = None,
    global_override: int | None = None,
) -> int:
    """Resolve timeout with precedence: command-specific > global > per-command default.

    Args:
        command_type: Bridge command type for TIMEOUT_DEFAULTS lookup.
        command_override: --timeout on the command itself (highest priority).
        global_override: --timeout on the global flags (middle priority).

    Returns:
        Resolved timeout in seconds.
    """
    if command_override is not None:
        return command_override
    if global_override is not None:
        return global_override
    return TIMEOUT_DEFAULTS.get(command_type, 30)
```

### 4.6 `core/output.py` — Output Formatting

```python
import json
from typing import Any

class OutputFormatter:
    """Routes output to the correct format based on config."""

    def __init__(self, format: str = "json", color: bool = True) -> None: ...

    def success(self, data: Any, human_formatter: callable | None = None) -> str:
        """Format a successful result."""
        ...

    def error(self, message: str, details: dict | None = None) -> str:
        """Format an error result."""
        ...

    def json_output(self, data: Any, pretty: bool = False) -> str: ...
    def human_output(self, data: Any, formatter: callable) -> str: ...

def print_result(result: CommandResult, formatter: OutputFormatter) -> None:
    """Print a CommandResult to stdout, exit with appropriate code."""
    ...
```

### 4.7 `app.py` — Typer Application

```python
import typer

app = typer.Typer(
    name="unity-bridge",
    help="CLI for Unity Editor automation via file-based bridge.",
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

# Global state passed to subcommands via typer.Context
@dataclass
class AppState:
    config: BridgeConfig
    formatter: OutputFormatter
    bridge: DirectBridge | None = None

@app.callback()
def main(
    ctx: typer.Context,
    project: Annotated[Path | None, typer.Option("--project", "-p")] = None,
    pretty: Annotated[bool, typer.Option("--pretty")] = False,
    human: Annotated[bool, typer.Option("--human", "-H")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
    quiet: Annotated[bool, typer.Option("--quiet", "-q")] = False,
    timeout: Annotated[int | None, typer.Option("--timeout", "-t")] = None,
    no_color: Annotated[bool, typer.Option("--no-color")] = False,
) -> None:
    """Configure global state from flags."""
    ...

# Register command groups
app.add_typer(component_app, name="component")
app.add_typer(scene_app, name="scene")
app.add_typer(prefab_app, name="prefab")
app.add_typer(console_app, name="console")
app.add_typer(snapshot_app, name="snapshot")
app.add_typer(config_app, name="config")
app.add_typer(test_app, name="test")
```

---

## 5. Command Dispatcher

The key architectural constraint: CLI and MCP must use identical core logic. This is achieved by having both entry points call the same functions in `commands/*.py`.

### Dispatcher Pattern

Each command module exposes **async functions** that accept typed parameters and return `CommandResult`:

```python
# commands/testing.py
async def run_tests(
    bridge: DirectBridge,
    platform: str = "EditMode",
    filter_pattern: str | None = None,
    timeout: int = 300,
) -> CommandResult:
    """Core logic for run-tests. Called by both CLI and MCP."""
    return await bridge.send_command_with_retry(
        command_type="run-tests",
        parameters={
            "testPlatform": platform,
            **({"testFilter": filter_pattern} if filter_pattern else {}),
        },
        timeout=float(timeout),
    )
```

### CLI Binding

```python
# commands/testing.py (continued)
@app.command()
def run_tests_cli(
    ctx: typer.Context,
    platform: Annotated[str, typer.Option("--platform", "-P")] = "EditMode",
    filter_pattern: Annotated[str | None, typer.Option("--filter", "-f")] = None,
    timeout: Annotated[int, typer.Option("--timeout", "-t")] = 300,
) -> None:
    state: AppState = ctx.obj
    result = asyncio.run(run_tests(state.bridge, platform, filter_pattern, timeout))
    print_result(result, state.formatter, human_formatter=format_test_results)
```

### MCP Binding

```python
# mcp/tools.py
async def handle_unity_run_tests(arguments: dict) -> CommandResult:
    bridge = get_direct_bridge()
    return await run_tests(
        bridge=bridge,
        platform=arguments.get("testPlatform", "EditMode"),
        filter_pattern=arguments.get("testFilter"),
        timeout=arguments.get("timeout", 300),
    )
```

> **IMPORTANT:** CLI bindings use `asyncio.run()` because Typer commands are synchronous entry points. MCP bindings `await` the same async functions directly because they execute within an existing event loop. **Never use `asyncio.run()` inside MCP handlers** -- it will crash with `RuntimeError: cannot call asyncio.run() inside a running event loop`.

### Registration Table

Both CLI and MCP register the same core functions. The MCP tool definitions (name, description, input schema) live in `mcp/tools.py`. The CLI command registration lives in each `commands/*.py` module using Typer decorators.

### Concurrency Model

Commands are processed sequentially by Unity's `EditorApplication.update` loop. Multiple concurrent CLI invocations are safe at the file level (each command has a unique UUID), but may produce interleaved results for compound commands like `tdd`. Avoid running multiple `tdd` or `batch` commands simultaneously.

---

## 6. Output Formatting

### JSON Output (Default)

All commands output valid JSON to stdout. Errors go to stderr.

> **Key casing:** All CLI output uses `snake_case` keys (Python convention, `jq`-friendly). The internal bridge protocol uses `camelCase` (C# convention). Translation happens in `core/output.py`.

**Success:**
```json
{
  "success": true,
  "data": { "passed": 5, "failed": 1, "duration_ms": 234 },
  "command_id": "a1b2c3d4-...",
  "execution_time_ms": 1523
}
```

**Error:**
```json
{
  "success": false,
  "error": "Unity Bridge not healthy: Heartbeat is stale (45.2s old)",
  "exit_code": 2
}
```

### Pretty JSON (`--pretty`)

Same structure, indented with 2 spaces.

### Human-Readable (`--human` or `-H`)

Each command type has a dedicated formatter function in `core/output.py`. Examples:

**Test Results:**
```
PASS  CombatControllerTests.TestDamage (12ms)
FAIL  CombatControllerTests.TestDeath (15ms)
  Expected: isDead = true
  Actual:   isDead = false

Results: 1 passed, 1 failed (27ms total)
```

**Hierarchy:**
```
Scene: MainScene
├── Main Camera
│   └── [Camera, AudioListener]
├── Directional Light
│   └── [Light]
├── Player
│   ├── [Transform, PlayerController, Rigidbody]
│   └── Weapon
│       └── [Transform, WeaponSystem]
└── Environment
    ├── Ground [Transform, MeshRenderer]
    └── Trees [Transform]
```

**Console Logs:**
```
[ERR] NullReferenceException: Object reference not set...
      at PlayerController.Update() in PlayerController.cs:42
[WRN] Shader 'Custom/Water' is not supported on this GPU
[LOG] Game initialized successfully
```

### Error Output

Errors always go to stderr. In `--human` mode, errors are prefixed with `ERROR:` and colored red. In JSON mode, errors are structured JSON on stdout with `"success": false`.

---

## 7. Configuration

### Config File Location

Searched in order:
1. `$UNITY_BRIDGE_CONFIG` (explicit path)
2. `<project_root>/unity_bridge_config.json`
3. `<project_root>/.claude/unity_bridge_config.json`

### Config File Schema

```json
{
  "log_level": "ERROR",
  "default_timeout": 30,
  "color": true,
  "output_format": "json"
}
```

### Precedence

```
CLI flags (highest priority)
  └── Environment variables
        └── Config file
              └── Hardcoded defaults (lowest priority)
```

Example: `unity-bridge --timeout 60 status` uses 60s regardless of `UNITY_BRIDGE_TIMEOUT` or config file.

**Timeout precedence:** command-specific `--timeout` > global `--timeout` > per-command default from `TIMEOUT_DEFAULTS`.

Example: `unity-bridge --timeout 60 test run --timeout 300` uses 300s (command-specific wins).

---

## 8. New Feature Specs

### 8.1 `status` (Tier 1)

Quick alive/dead check. Returns within 1 second.

```python
async def status(bridge: DirectBridge) -> CommandResult:
    """Check if Unity Bridge is responsive."""
    monitor = HealthMonitor(bridge.project_root)
    health = monitor.check_health()
    return CommandResult(
        success=health.healthy,
        data=health.to_dict(),
        error=health.reason if not health.healthy else None,
    )
```

**Exit code:** 0 if healthy, 1 if unhealthy.

**Human output:**
```
Unity Bridge: ONLINE
  Unity 6000.0.23f1 | Scene: MainScene | Uptime: 2h 15m
  Heartbeat: 1.2s ago | Commands processed: 142
```
or
```
Unity Bridge: OFFLINE
  No heartbeat file found. Unity Editor may not be running.
```

### 8.2 `doctor` (Tier 1)

Full diagnostic check. Runs all health checks and reports results.

```python
async def doctor(project_root: Path) -> CommandResult:
    """Run full diagnostic suite."""
    checks: list[DiagnosticCheck] = []

    # 1. Project structure
    checks.append(check_project_structure(project_root))
    # 2. C# bridge installed
    checks.append(check_bridge_installed(project_root))
    # 3. Bridge version
    checks.append(check_bridge_version(project_root))
    # 4. Heartbeat
    checks.append(check_heartbeat(project_root))
    # 5. Directory permissions
    checks.append(check_directory_permissions(project_root))
    # 6. Orphaned files
    checks.append(check_orphaned_files(project_root))
    # 7. Python dependencies
    checks.append(check_dependencies())
    # 8. Unity Editor process running (Windows: tasklist)
    checks.append(check_unity_process())
    # 9. Bridge version compatibility
    checks.append(check_version_compatibility(project_root))

    all_pass = all(c.passed for c in checks)
    return CommandResult(success=all_pass, data=[c.to_dict() for c in checks])

@dataclass
class DiagnosticCheck:
    name: str
    passed: bool
    message: str
    suggestion: str | None = None
```

**Human output:**
```
Unity Bridge Doctor
===================
[PASS] Project structure: Assets/ directory found
[PASS] C# bridge installed: v2.0.0 at Assets/Scripts/Editor/ClaudeCodeBridge/
[PASS] Bridge version: up to date (v2.0.0)
[PASS] Heartbeat: fresh (1.2s old)
[PASS] Directory permissions: commands/ and responses/ writable
[WARN] Orphaned files: 3 stale files found (run `unity-bridge clean`)
[PASS] Python dependencies: aiofiles, typer installed

6 passed, 1 warning, 0 failed
```

### 8.3 `install` (Tier 1)

Wraps existing `install_bridge.py` logic.

```bash
unity-bridge install                  # Auto-detect project, install/update
unity-bridge install --project /path  # Explicit project path
unity-bridge install --check          # Check status without changes
unity-bridge install --force          # Force reinstall
```

### 8.4 `init` (Tier 1)

Creates the `.claude/unity/` directory structure without installing C# files. Useful when setting up a new project before opening Unity.

```python
async def init(project_root: Path) -> CommandResult:
    paths = get_bridge_paths(project_root)
    created = []
    for name, path in [
        ("commands", paths.commands_dir),
        ("responses", paths.responses_dir),
    ]:
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(name)
    return CommandResult(success=True, data={"created": created, "project_root": str(project_root)})
```

### 8.5 `clean` (Tier 1)

Wraps `clear_orphaned_bridge_files()` from `bridge_utils.py`.

```bash
unity-bridge clean              # Remove files older than 5 minutes
unity-bridge clean --age 0      # Remove all orphaned files
unity-bridge clean --all        # Alias for --age 0
unity-bridge clean --dry-run    # Show what would be deleted
```

### 8.6 `version` (Tier 1)

```bash
unity-bridge version
# unity-bridge 3.0.0
# C# bridge: 2.0.0
# Python: 3.12.1
# Platform: win32
```

### 8.7 `console watch` (Tier 1)

Tail console logs in real-time by polling `read-console` at intervals. Replaces the former top-level `watch` and `log --follow` commands.

```python
async def watch(
    bridge: DirectBridge,
    types: list[str] | None = None,
    poll_interval: float = 1.0,
) -> None:
    """Stream console output. Runs until Ctrl+C."""
    from collections import deque
    # Dedup key format: "timestamp|logType|message_hash" — uses hash to avoid
    # collisions from truncation while keeping memory bounded. Repeated identical
    # messages (same timestamp + type + content) are suppressed.
    seen_entries: deque[str] = deque(maxlen=10_000)

    def _entry_key(entry: dict) -> str:
        msg = entry.get("message", "")
        msg_hash = hashlib.md5(msg.encode(), usedforsecurity=False).hexdigest()[:12]
        return f"{entry.get('timestamp', '')}|{entry.get('type', '')}|{msg_hash}"

    try:
        while True:
            result = await bridge.send_command(
                "read-console",
                {"logTypes": types or ["Error", "Warning", "Log"], "maxEntries": 50},
                timeout=10.0,
                check_health=False,
            )
            if result.success and result.data:
                for entry in result.data.get("entries", []):
                    key = _entry_key(entry)
                    if key not in seen_entries:
                        seen_entries.append(key)
                        print_console_entry(entry)
            await asyncio.sleep(poll_interval)
    except KeyboardInterrupt:
        pass
```

### 8.8 `tdd` (Tier 2)

Compound workflow: clear console -> compile -> run tests -> read console (if failures).

```python
async def tdd(
    bridge: DirectBridge,
    platform: str = "EditMode",
    filter_pattern: str | None = None,
    strict: bool = False,
) -> CommandResult:
    """TDD workflow: clear → compile → test → console."""
    steps: list[dict] = []

    # Step 1: Clear console
    clear_result = await bridge.send_command("clear-console", timeout=5.0)
    steps.append({"step": "clear-console", "success": clear_result.success})

    # Step 2: Compile
    compile_result = await bridge.send_command(
        "compile", {"waitForCompletion": True}, timeout=120.0
    )
    steps.append({"step": "compile", "success": compile_result.success})
    if not compile_result.success:
        return CommandResult(
            success=False,
            data={"steps": steps, "failed_at": "compile", "compile_errors": compile_result.data},
            error="Compilation failed",
        )

    # Step 3: Run tests
    test_params = {"testPlatform": platform}
    if filter_pattern:
        test_params["testFilter"] = filter_pattern
    test_result = await bridge.send_command("run-tests", test_params, timeout=300.0)
    steps.append({"step": "run-tests", "success": test_result.success})

    # Step 4: Read console if tests failed
    if not test_result.success:
        console_result = await bridge.send_command(
            "read-console",
            {"logTypes": ["Error"], "maxEntries": 20, "maxStackTraceLines": 3},
            timeout=10.0,
        )
        steps.append({"step": "read-console", "success": console_result.success})
        return CommandResult(
            success=False,
            data={"steps": steps, "test_results": test_result.data, "console": console_result.data},
            error="Tests failed",
        )

    return CommandResult(success=True, data={"steps": steps, "test_results": test_result.data})
```

`--strict` treats compilation warnings as failures. When `strict=True`, warnings in `compile_result.data` cause the workflow to halt with a compilation failure.

### 8.9 `test watch` (Tier 2)

File watcher that re-runs tests on `.cs` file changes.

```python
async def test_watch(
    bridge: DirectBridge,
    platform: str = "EditMode",
    filter_pattern: str | None = None,
    watch_path: Path | None = None,
    debounce_seconds: float = 2.0,
) -> None:
    """Watch for file changes and re-run tests."""
    try:
        from watchfiles import awatch
    except ImportError:
        raise typer.BadParameter(
            "watchfiles package required for test watch. "
            "Install with: pip install unity-bridge[watch]"
        )

    path = watch_path or bridge.project_root / "Assets"
    print(f"Watching {path} for .cs file changes...")

    async for changes in awatch(path):
        cs_changes = [c for c in changes if c[1].endswith(".cs")]
        if cs_changes:
            changed_files = [Path(c[1]).name for c in cs_changes]
            print(f"\nChanged: {', '.join(changed_files)}")
            result = await tdd(bridge, platform, filter_pattern)
            print_result(result, ...)
```

### 8.10 `snapshot save` and `snapshot diff` (Tier 2)

**Snapshot save:** Captures hierarchy + component state to a JSON file.

```python
async def snapshot_save(
    bridge: DirectBridge,
    output_file: Path,
    depth: int = 5,
    max_objects: int = 1000,
) -> CommandResult:
    """Save scene state snapshot."""
    hierarchy_result = await bridge.send_command(
        "query-hierarchy", {"maxDepth": depth, "includeInactive": True}
    )
    if not hierarchy_result.success:
        return hierarchy_result

    # Truncate large hierarchies
    object_count = count_objects(hierarchy_result.data)
    truncated = object_count > max_objects
    if truncated:
        hierarchy_result.data = truncate_hierarchy(hierarchy_result.data, max_objects)

    snapshot = {
        "version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "project_root": str(bridge.project_root),
        "hierarchy": hierarchy_result.data,
    }

    output_file.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    return CommandResult(success=True, data={"file": str(output_file), "objects": count_objects(snapshot)})
```

**Helper functions for hierarchy traversal:**

```python
def count_objects(hierarchy: dict) -> int:
    """Recursively count all GameObjects in a hierarchy tree.

    Expects the Unity bridge hierarchy format: each node has a "children" list.
    Returns total count including the root nodes.
    """
    count = 0
    nodes = hierarchy.get("children", hierarchy.get("roots", []))
    for node in nodes:
        count += 1
        count += count_objects(node)
    return count


def truncate_hierarchy(hierarchy: dict, max_objects: int) -> dict:
    """Breadth-first truncation of hierarchy tree to max_objects.

    Preserves structure up to the limit. Adds a sentinel node
    {"name": "... truncated ...", "truncated_count": N} at the cut point.
    Returns a shallow copy — does not mutate the original.
    """
    import copy
    result = copy.deepcopy(hierarchy)
    seen = 0
    queue = result.get("children", result.get("roots", []))
    # BFS: keep nodes until limit, then prune remaining children
    for node in queue:
        seen += 1
        if seen >= max_objects:
            node["children"] = [{"name": "... truncated ...", "truncated_count": count_objects(node)}]
            break
        queue.extend(node.get("children", []))
    return result
```

**Snapshot diff:** Compares two snapshots and highlights differences.

```python
@dataclass
class HierarchyDiff:
    """Result of comparing two hierarchy snapshots."""
    added: list[str]      # GameObject paths present in snap2 but not snap1
    removed: list[str]    # GameObject paths present in snap1 but not snap2
    modified: list[dict]  # Objects with same path but different components/properties


def _collect_paths(node: dict, prefix: str = "") -> dict[str, dict]:
    """Flatten hierarchy tree into {path: node_data} map."""
    path = f"{prefix}/{node['name']}" if prefix else node["name"]
    result = {path: node}
    for child in node.get("children", []):
        result.update(_collect_paths(child, path))
    return result


def compute_hierarchy_diff(hierarchy1: dict, hierarchy2: dict) -> HierarchyDiff:
    """Compare two hierarchy trees by flattening to path maps and diffing.

    Compares: presence/absence of GameObjects (added/removed) and
    component lists per object (modified). Does NOT compare component
    field values — that would require component data snapshots.
    """
    paths1 = {}
    for root in hierarchy1.get("children", hierarchy1.get("roots", [])):
        paths1.update(_collect_paths(root))

    paths2 = {}
    for root in hierarchy2.get("children", hierarchy2.get("roots", [])):
        paths2.update(_collect_paths(root))

    added = sorted(set(paths2.keys()) - set(paths1.keys()))
    removed = sorted(set(paths1.keys()) - set(paths2.keys()))

    modified = []
    for path in sorted(set(paths1.keys()) & set(paths2.keys())):
        comps1 = set(paths1[path].get("components", []))
        comps2 = set(paths2[path].get("components", []))
        if comps1 != comps2:
            modified.append({
                "path": path,
                "components_added": sorted(comps2 - comps1),
                "components_removed": sorted(comps1 - comps2),
            })

    return HierarchyDiff(added=added, removed=removed, modified=modified)


async def snapshot_diff(file1: Path, file2: Path) -> CommandResult:
    """Compare two scene snapshots."""
    snap1 = json.loads(file1.read_text(encoding="utf-8"))
    snap2 = json.loads(file2.read_text(encoding="utf-8"))

    diffs = compute_hierarchy_diff(snap1["hierarchy"], snap2["hierarchy"])
    return CommandResult(
        success=True,
        data={"added": diffs.added, "removed": diffs.removed, "modified": diffs.modified},
    )
```

### 8.11 `script` (Tier 2)

Execute arbitrary C# expressions in Unity Editor. See section 9 for protocol details.

```bash
# Simple expression
unity-bridge script "Debug.Log(\"Hello from CLI\")"

# Return a value
unity-bridge script "EditorApplication.isPlaying"
# {"success": true, "data": {"result": "False", "type": "System.Boolean"}}

# Multi-statement (semicolon-separated)
unity-bridge script "var go = new GameObject(\"TestObj\"); go.transform.position = Vector3.up;"

# From file
unity-bridge script --file setup.cs
```

### 8.12 Shell Completions

Shell completions use Typer's built-in `--install-completion` and `--show-completion` flags. No custom `completions` subcommand needed.

### 8.13 `serve` (Backward Compat)

Starts the MCP server using stdio transport.

```python
@app.command()
def serve(ctx: typer.Context) -> None:
    """Start MCP server mode for Claude Code integration."""
    state: AppState = ctx.obj
    from unity_bridge.mcp.server import run_mcp_server
    asyncio.run(run_mcp_server(config=state.config))
```

### 8.14 `batch` (Existing, Enhanced)

Execute multiple commands from a JSON file.

**File format:**
```json
{
  "commands": [
    {"type": "clear-console"},
    {"type": "compile", "parameters": {"waitForCompletion": true}},
    {"type": "run-tests", "parameters": {"testPlatform": "EditMode"}}
  ]
}
```

**Flags:**
- `--stop-on-error` (default: true) -- halt on first failure
- `--parallel` (default: false) -- send read-only commands concurrently from Python side (Unity still processes sequentially via `EditorApplication.update`)

**Output:** Array of results with per-command status, plus aggregate summary.

---

## 9. C# Bridge Protocol Extension

### `execute-script` Command Type

The `script` command requires a new command type in the C# bridge protocol.

**Command JSON:**

```json
{
  "commandId": "uuid",
  "commandType": "execute-script",
  "timestamp": "2026-03-17T10:00:00Z",
  "parametersJson": "{\"expression\": \"EditorApplication.isPlaying\", \"returnValue\": true}"
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `expression` | `string` | yes | C# expression or statements to execute |
| `returnValue` | `bool` | no | Whether to capture and return the expression value (default: true) |
| `timeout_ms` | `int` | no | Maximum execution time in milliseconds (default: 10000) |

**Response JSON (success):**

```json
{
  "commandId": "uuid",
  "commandType": "execute-script",
  "status": "success",
  "timestamp": "2026-03-17T10:00:01Z",
  "dataJson": "{\"result\": \"False\", \"resultType\": \"System.Boolean\", \"executionTimeMs\": 12}"
}
```

**Response JSON (error):**

```json
{
  "commandId": "uuid",
  "commandType": "execute-script",
  "status": "error",
  "timestamp": "2026-03-17T10:00:01Z",
  "errorMessage": "CS0103: The name 'foo' does not exist in the current context"
}
```

### C# Handler: `ExecuteScriptCommandHandler.cs`

New file in `ClaudeCodeBridge/`. Uses `Mono.CSharp.Evaluator` (available in Unity's Mono runtime). `Evaluator.Evaluate()` for expressions, `Evaluator.Run()` for statements.

```csharp
// ClaudeCodeBridge/ExecuteScriptCommandHandler.cs
// Uses Mono.CSharp.Evaluator (available in Unity's Mono runtime)
// Evaluator.Evaluate() for expressions, Evaluator.Run() for statements
namespace BWS.Editor.ClaudeCodeBridge
{
    [Serializable]
    public class ExecuteScriptParams
    {
        public string expression;
        public bool returnValue = true;
        public int timeout_ms = 10000;
    }

    [Serializable]
    public class ExecuteScriptResult
    {
        public string result;
        public string resultType;
        public int executionTimeMs;
    }

    public class ExecuteScriptCommandHandler : ICommandHandler
    {
        public string CommandType => "execute-script";

        public BridgeResponse Handle(BridgeCommand command)
        {
            var parameters = JsonUtility.FromJson<ExecuteScriptParams>(command.parametersJson);
            // Initialize Mono.CSharp.Evaluator with Unity's default assemblies
            // Call Evaluator.Evaluate() for expressions, Evaluator.Run() for statements
            // Return result as string representation
        }
    }
}
```

**Note:** `Mono.CSharp.Evaluator` is available in Unity's Mono runtime. Roslyn and `CSharpCodeProvider` are NOT available in Unity Editor. A feasibility spike should validate this approach before implementation begins.
```

**Security considerations:**
- This command provides arbitrary code execution within Unity Editor. This is by design -- the bridge already allows arbitrary modifications via component data, menu items, and prefab operations.
- The C# handler should log all executed expressions.
- A configurable allowlist/blocklist of namespaces could be added later as a non-goal for v1.

### Registration

In `ClaudeUnityBridge.cs`, register the new handler:

```csharp
RegisterHandler(new ExecuteScriptCommandHandler());
```

---

## 10. Migration Plan

### Phase 1: Package Scaffold (no behavior change)

1. Create `src/unity_bridge/` package structure.
2. Create `pyproject.toml` with entry points.
3. Move core modules into `core/` (bridge, health, cache, retry, config, project, protocol).
4. Add `__init__.py` with version and public exports.
5. Existing `unity_bridge_mcp_server.py` continues to work as-is.

### Phase 2: CLI Implementation

1. Implement `app.py` with Typer and global flags.
2. Implement Tier 1 commands (status, doctor, install, init, clean, version).
3. Implement command groups (component, scene, prefab, console, config).
4. Implement formatter functions in `core/output.py` for human-readable output.
5. Wire up all existing bridge commands to CLI.

### Phase 3: MCP Migration

1. Create `mcp/server.py` and `mcp/tools.py` using shared command functions.
2. Implement `unity-bridge serve` command.
3. Update `unity_bridge_mcp_server.py` to be a thin wrapper:

```python
#!/usr/bin/env python3
"""Legacy MCP server entry point. Use `unity-bridge serve` instead."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from unity_bridge.mcp.server import run_mcp_server
import asyncio
asyncio.run(run_mcp_server())
```

4. Update `mcp.json` to use `unity-bridge serve` as the command.

### Phase 4: Tier 2 Features

1. Implement `tdd`, `test watch`, `snapshot`, `diff`, `console watch`, `script`.
2. Create `ExecuteScriptCommandHandler.cs` in C# bridge.
3. Implement `batch` with file input support.

### Phase 5: Cleanup

1. Mark deprecated files with deprecation notices.
2. Update `README.md` with CLI documentation.
3. Update `CHANGELOG.md`.
4. Remove `scripts/send_command.py` and `scripts/invoke_unity_command.py`.

### Backward Compatibility

- `unity_bridge_mcp_server.py` continues to exist as a thin wrapper.
- `mcp.json` configuration can point to either `python3 unity_bridge_mcp_server.py` (legacy) or `unity-bridge serve` (new).
- All MCP tool names (`unity_run_tests`, `unity_query_hierarchy`, etc.) remain unchanged.
- All MCP tool input schemas remain unchanged.
- Response format from MCP tools remains unchanged.

---

## 11. Testing Strategy

### Unit Tests

Every module in `core/` and `commands/` gets a corresponding test file. Tests use `pytest` with `pytest-asyncio`.

**Test doubles for DirectBridge:**

```python
# tests/conftest.py
from dataclasses import dataclass
from unittest.mock import AsyncMock

@pytest.fixture
def mock_bridge(tmp_path: Path) -> DirectBridge:
    """DirectBridge with mocked file I/O."""
    bridge = DirectBridge(tmp_path)
    bridge.send_command = AsyncMock()
    bridge.send_command_with_retry = AsyncMock()
    return bridge

@pytest.fixture
def healthy_bridge(mock_bridge: DirectBridge) -> DirectBridge:
    """Bridge that returns healthy status."""
    mock_bridge.send_command.return_value = CommandResult(
        success=True,
        data={"healthy": True},
    )
    return mock_bridge

@pytest.fixture
def fake_heartbeat(tmp_path: Path) -> Path:
    """Create a fresh heartbeat file."""
    heartbeat_dir = tmp_path / ".claude" / "unity"
    heartbeat_dir.mkdir(parents=True)
    heartbeat_file = heartbeat_dir / "heartbeat.json"
    heartbeat_file.write_text(json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "unityVersion": "6000.0.23f1",
        "isCompiling": False,
        "isPlaying": False,
        "activeScene": "TestScene",
        "commandsProcessed": 0,
        "uptimeSeconds": 100,
    }))
    return heartbeat_file
```

**Key test areas:**

| Module | Tests |
|--------|-------|
| `core/bridge.py` | Command serialization, response parsing, timeout, atomic writes |
| `core/health.py` | Fresh heartbeat, stale heartbeat, missing file, invalid JSON |
| `core/cache.py` | Cache hit/miss, TTL expiry, LRU eviction, scene invalidation |
| `core/retry.py` | Retry on transient errors, no retry on permanent errors, backoff |
| `core/config.py` | Precedence resolution, env var loading, file loading, defaults |
| `core/project.py` | Project detection from various starting paths |
| `core/output.py` | JSON formatting, pretty printing, human dispatch |
| `commands/testing.py` | run_tests parameter mapping, tdd workflow sequencing |
| `commands/lifecycle.py` | Install detection, version comparison, directory creation |
| `commands/workflow.py` | Snapshot serialization, diff computation |
| `commands/scripting.py` | Expression escaping, parameter building |

### Integration Tests

Integration tests require Unity running and are marked with `@pytest.mark.integration`.

```python
@pytest.mark.integration
async def test_cli_run_tests_roundtrip():
    """Test full CLI → bridge → Unity → response flow."""
    result = subprocess.run(
        ["unity-bridge", "test", "run", "--platform", "EditMode"],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["success"] is True
```

### CLI Smoke Tests

Test that all commands produce valid output without Unity running:

```python
def test_version_output():
    result = subprocess.run(["unity-bridge", "version"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "unity-bridge" in result.stdout

def test_status_without_unity():
    result = subprocess.run(
        ["unity-bridge", "status"],
        capture_output=True, text=True,
    )
    data = json.loads(result.stdout)
    assert data["success"] is False  # No Unity running
```

### Test Coverage Targets

- `core/`: 90%+ line coverage
- `commands/`: 85%+ line coverage
- `mcp/`: 80%+ line coverage

---

## 12. Dependencies

### Required

| Package | Version | Purpose |
|---------|---------|---------|
| `typer[all]` | `>=0.12.0` | CLI framework with rich integration |
| `aiofiles` | `>=23.0` | Async file I/O for bridge communication |
| `rich` | `>=13.0` | Terminal formatting (installed via `typer[all]`) |

### Optional

| Package | Version | Purpose |
|---------|---------|---------|
| `mcp` | `>=1.0` | MCP SDK for `unity-bridge serve` |
| `watchfiles` | `>=0.21` | File watching for `unity-bridge test watch` |

### Development

| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | `>=7.0` | Test runner |
| `pytest-asyncio` | `>=0.23` | Async test support |
| `pytest-cov` | `>=4.0` | Coverage reporting |

### Python Version

- **Minimum:** Python 3.10 (for `X | Y` union syntax in type annotations)
- **Recommended:** Python 3.12+

---

## 13. Error Handling

### Exit Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| `0` | Success | Command completed successfully |
| `1` | Command failure | Unity command returned error, tests failed |
| `2` | Bridge unavailable | Unity not running, heartbeat stale, bridge not installed |
| `3` | Invalid input | Bad arguments, missing required parameters |
| `4` | Timeout | Command timed out waiting for response |
| `5` | Internal error | Unexpected Python exception |

### Error Output Format (JSON mode)

```json
{
  "success": false,
  "error": "Human-readable error message",
  "error_code": "BRIDGE_UNAVAILABLE",
  "exit_code": 2,
  "details": {
    "heartbeat_age_seconds": 45.2,
    "heartbeat_path": "/path/to/.claude/unity/heartbeat.json"
  }
}
```

### Error Output Format (Human mode)

```
ERROR: Unity Bridge not available
  Heartbeat file is stale (45.2s old). Unity may be frozen or closed.

  Try:
    1. Check that Unity Editor is open
    2. Run `unity-bridge doctor` for full diagnostics
    3. Run `unity-bridge install` to reinstall the C# bridge
```

### Error Codes

| Code | Constant | Description |
|------|----------|-------------|
| `BRIDGE_UNAVAILABLE` | Bridge not responding | Heartbeat stale or missing |
| `BRIDGE_NOT_INSTALLED` | C# bridge not found | No ClaudeUnityBridge.cs in project |
| `PROJECT_NOT_FOUND` | No Unity project detected | No Assets/ directory found |
| `COMMAND_TIMEOUT` | Command timed out | Response not received within timeout |
| `COMMAND_FAILED` | Unity returned error | C# handler reported failure |
| `INVALID_ARGUMENTS` | Bad CLI arguments | Missing required args, invalid values |
| `COMPILATION_FAILED` | C# compilation error | Unity compilation had errors |
| `DEPENDENCY_MISSING` | Required package missing | aiofiles, mcp, watchfiles not installed |

### Retry Behavior

Inherited from `core/retry.py`. Retries occur automatically for:
- File I/O errors (locking, access denied)
- Transient bridge unavailability
- Sharing violations (Windows)

Default: 3 retries with exponential backoff (0.1s, 0.2s, 0.4s, capped at 2.0s).

Commands that mutate state (set-component-data, scene-operation, prefab-operation) are retried only for I/O failures, not for command-level errors.

### Signal Handling (Ctrl+C)

When interrupted during a long-running command:
1. Print to stderr: `"Interrupted. Command may still be running in Unity."`
2. Exit with code 130 (standard SIGINT exit code)
3. The orphaned response file will be cleaned by `unity-bridge clean`

The C# bridge does not currently support command cancellation. A cancellation protocol may be added in a future version.

**Registration pattern** (in `app.py` or `__main__.py`):

```python
import signal
import sys

def _handle_sigint(signum: int, frame: Any) -> None:
    print("\nInterrupted. Command may still be running in Unity.", file=sys.stderr)
    sys.exit(130)

signal.signal(signal.SIGINT, _handle_sigint)
```

> **Note:** This handler is registered at CLI startup. Long-running async commands (`watch`, `test watch`) use `KeyboardInterrupt` catch blocks instead, allowing graceful cleanup before exit.

### Destructive Command Safety (v1)

The following commands mutate Unity state and are **not idempotent**:
- `component set` — overwrites field values
- `prefab destroy` — removes a scene instance permanently
- `scene load` — replaces active scene (unsaved changes lost unless `--save-current`)
- `set-component-data` — modifies live data

**v1 behavior:** These commands execute immediately with no confirmation prompt. Users are expected to understand the consequences.

**Planned for v2:** `--dry-run` flag for mutating commands and confirmation prompts in `--human` mode.

---

## 14. Packaging

### `pyproject.toml`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "unity-bridge"
version = "3.0.0"
description = "CLI and MCP server for Unity Editor automation"
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
authors = [
    { name = "Claude Code" },
]
dependencies = [
    "typer[all]>=0.12.0",
    "aiofiles>=23.0",
]

[project.optional-dependencies]
mcp = ["mcp>=1.0"]
watch = ["watchfiles>=0.21"]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=4.0",
]
all = ["unity-bridge[mcp,watch]"]

[project.scripts]
unity-bridge = "unity_bridge.app:app"

[tool.hatch.build.targets.wheel]
packages = ["src/unity_bridge"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = [
    "integration: requires Unity Editor running",
    "slow: long-running tests",
]

[tool.ruff]
line-length = 120
target-version = "py310"
```

### Installation

```bash
# From project directory
pip install -e .

# With MCP support
pip install -e ".[mcp]"

# With file watching
pip install -e ".[watch]"

# Everything
pip install -e ".[all]"

# Development
pip install -e ".[all,dev]"
```

### Entry Points

After installation, `unity-bridge` is available as a shell command:

```bash
unity-bridge --help
unity-bridge status
unity-bridge test run --platform EditMode
unity-bridge serve  # MCP mode
```

Also runnable as a module:

```bash
python -m unity_bridge --help
python -m unity_bridge serve
```

### MCP Configuration (`mcp.json`)

Updated config for Claude Code:

```json
{
  "mcpServers": {
    "unity-bridge": {
      "command": "unity-bridge",
      "args": ["serve"],
      "env": {}
    }
  }
}
```

Legacy config (still works):

```json
{
  "mcpServers": {
    "unity-bridge": {
      "command": "python3",
      "args": ["unity_bridge_mcp_server.py"],
      "env": {}
    }
  }
}
```

---

## Appendix A: MCP Tool to CLI Mapping

| MCP Tool Name | CLI Command | Bridge Command Type |
|---------------|-------------|---------------------|
| `unity_run_tests` | `unity-bridge test run` | `run-tests` |
| `unity_compile` | `unity-bridge compile` | `compile` |
| `unity_query_hierarchy` | `unity-bridge hierarchy` | `query-hierarchy` |
| `unity_get_component_data` | `unity-bridge component get` | `get-component-data` |
| `unity_set_component_data` | `unity-bridge component set` | `set-component-data` |
| `unity_add_component` | `unity-bridge component add` | `add-component` |
| `unity_validate_prefab` | `unity-bridge prefab validate` | `validate-prefab` |
| `unity_prefab_operation` | `unity-bridge prefab instantiate/destroy` | `prefab-operation` |
| `unity_scene_operation` | `unity-bridge scene load/save/create` | `scene-operation` |
| `unity_playmode_control` | `unity-bridge playmode` | `playmode-control` |
| `unity_read_console` | `unity-bridge console read` | `read-console` |
| `unity_clear_console` | `unity-bridge console clear` | `clear-console` |
| `unity_capture_screenshot` | `unity-bridge screenshot` | `capture-screenshot` |
| `unity_profiler_sample` | `unity-bridge profiler` | `profiler-sample` |
| `unity_material_operation` | `unity-bridge material` | `material-operation` |
| `unity_asset_operation` | `unity-bridge asset` | `asset-operation` |
| `unity_build_operation` | `unity-bridge build` | `build-operation` |
| `unity_animator_operation` | `unity-bridge animator` | `animator-operation` |
| `unity_get_selection` | `unity-bridge selection` | `get-selection` |
| `unity_refresh_assets` | `unity-bridge refresh` | `refresh-assets` |
| `unity_focus_object` | `unity-bridge focus` | `focus-object` |
| `unity_execute_menu_item` | `unity-bridge menu` | `execute-menu-item` |
| `unity_health_check` | `unity-bridge status` | (Python-side) |
| `unity_batch` | `unity-bridge batch` | (Python-side) |
| `unity_help` | `unity-bridge help` | (Python-side) |
| `unity_bridge_config` | `unity-bridge config` | (Python-side) |
| (new) | `unity-bridge script` | `execute-script` |

## Appendix B: File Migration Map

| Current File | New Location | Action |
|---|---|---|
| `direct_bridge.py` | `src/unity_bridge/core/bridge.py` | Migrate, refactor to return `CommandResult` |
| `health_monitor.py` | `src/unity_bridge/core/health.py` | Migrate, no API changes |
| `response_cache.py` | `src/unity_bridge/core/cache.py` | Migrate, no API changes |
| `retry_handler.py` | `src/unity_bridge/core/retry.py` | Migrate, no API changes |
| `install_bridge.py` | `src/unity_bridge/commands/lifecycle.py` | Migrate, wrap in Typer commands |
| `scripts/bridge_utils.py` | `src/unity_bridge/core/project.py` + `core/protocol.py` | Split and migrate |
| `scripts/invoke_unity_command.py` | (deleted) | Replaced by `core/bridge.py` |
| `scripts/send_command.py` | (deleted) | Replaced by CLI |
| `unity_bridge_mcp_server.py` | `src/unity_bridge/mcp/server.py` + thin wrapper | Split: server logic migrates, file stays as wrapper |

---

## Appendix C: Missing Sections (from review)

### Logging Architecture
- All log output goes to stderr via `logging.getLogger("unity_bridge")`
- `--verbose` sets log level to DEBUG; `--quiet` suppresses INFO and below
- stdout is reserved exclusively for command output (JSON or human-formatted)
- stderr carries: log messages, progress indicators, error context

### Multiple Unity Instances
- Bridge paths are per-project (`.claude/unity/` inside the project root)
- Auto-detection picks the nearest ancestor with `Assets/` + `ProjectSettings/`
- If ambiguous, use `--project` to specify explicitly
- Running commands against the wrong project is a user error; `unity-bridge doctor` reports the detected project path

### Upgrade Path
1. Install the new package: `pip install -e .`
2. Verify: `unity-bridge version`
3. Update `mcp.json` to use `unity-bridge serve` (optional -- legacy wrapper still works)
4. Old `scripts/` and root-level `.py` files remain as deprecated wrappers

### Performance Targets
- `status`: < 100ms (local file check, no Unity round-trip)
- `doctor`: < 2s (all checks sequential)
- Passthrough commands: < 50ms overhead on top of Unity processing time

---

## Appendix D: Review Response Matrix

| # | Severity | Finding | Action | Notes |
|---|----------|---------|--------|-------|
| 1.1 | CRITICAL | `script` C# impl uses unavailable APIs | **Fixed** | Switched to `Mono.CSharp.Evaluator`, added spike requirement |
| 1.2 | CRITICAL | `--json` flag contradicts JSON-default design | **Fixed** | Removed `--json` flag entirely; JSON is implicit default |
| 1.3 | CRITICAL | `asyncio.run()` pattern dangerous in MCP context | **Fixed** | Added explicit warning in Section 5 |
| 2.1 | HIGH | `watch` unbounded memory growth | **Fixed** | Bounded deque with maxlen=10,000 |
| 2.2 | HIGH | No concurrent CLI specification | **Fixed** | Added Concurrency Model subsection |
| 2.3 | HIGH | `snapshot` unspecified for large scenes | **Fixed** | Added `--max-objects` flag with default 1000 |
| 2.4 | HIGH | `watchfiles` import error unhandled | **Fixed** | Added try/except with actionable error message |
| 2.5 | HIGH | `--timeout` precedence ambiguous | **Fixed** | Documented: command-specific > global > default |
| 2.6 | HIGH | `component set` capability regression | **Fixed** | Changed to repeatable `--update FIELD:JSON` flag |
| 2.7 | HIGH | Windows path handling unaddressed | **Fixed** | Added path normalization note in Section 4.4 |
| 3.1 | MEDIUM | `tdd` doesn't handle warnings | **Fixed** | Added `--strict` flag |
| 3.2 | MEDIUM | `doctor` checks incomplete | **Fixed** | Added Unity process + version compat checks |
| 3.3 | MEDIUM | `serve` doesn't pass global config | **Fixed** | Passes `state.config` to `run_mcp_server()` |
| 3.4 | MEDIUM | `batch` lacks specification | **Fixed** | Added Section 8.14 with file format and semantics |
| 3.5 | MEDIUM | `prefab delete` ambiguous | **Fixed** | Renamed to `prefab destroy <instance-path>` with clarification |
| 3.6 | MEDIUM | `output.py` exit code mapping unclear | **Fixed** | Added `exit_code` field to `CommandResult` |
| 3.7 | MEDIUM | No Ctrl+C signal handling | **Fixed** | Added signal handling section with exit code 130 |
| 3.8 | MEDIUM | Project detection algorithm unspecified | **Fixed** | Documented walk-up algorithm with `Assets/` + `ProjectSettings/` |
| 4.1 | LOW | Version jump to 4.0.0 unexplained | **Fixed** | Changed to 3.0.0 |
| 4.2 | LOW | `datetime.utcnow()` deprecated | **Fixed** | Replaced with `datetime.now(timezone.utc)` |
| 4.3 | LOW | `watch`/`log`/`console read` overlap | **Fixed** | Merged into `console read` + `console watch` |
| 4.4 | LOW | `build build` awkward | **Fixed** | Default action is build, added `--validate-only` |
| 4.5 | LOW | Test fixtures use deprecated datetime | **Fixed** | Updated to `datetime.now(timezone.utc)` |
| 4.6 | LOW | `match` statement mention incorrect | **Fixed** | Removed; reason is `X | Y` union syntax |
| 4.7 | LOW | Missing `--dry-run` on destructive commands | **Deferred** | v2 consideration; `--human` mode will add confirmation prompts |
| 4.8 | LOW | `completions` duplicates Typer built-in | **Fixed** | Removed custom command; use Typer's `--install-completion` |
| 5.1 | CONSISTENCY | `run-tests` vs `test watch` naming | **Fixed** | Renamed to `test run` + `test watch` |
| 5.2 | CONSISTENCY | `-p` short flag conflict | **Fixed** | `--platform` uses `-P` (capital) |
| 5.3 | CONSISTENCY | Mixed key casing in output | **Fixed** | CLI output uses `snake_case`; bridge protocol stays `camelCase` |
| 6.1 | ARCH | `assets.py` will exceed 500 LOC | **Fixed** | Split into asset.py, material.py, build.py, animator.py |
| 6.2 | ARCH | `formatters/` directory premature | **Fixed** | Start in `core/output.py`, extract later |
| 6.3 | ARCH | `mcp/tools.py` will be large | **Deferred** | Will split by domain if it exceeds 500 LOC during implementation |

### QA Review Resolutions (v1.2.0)

| # | Finding | Action |
|---|---------|--------|
| QA-1 | `truncate_hierarchy()`, `count_objects()`, `compute_hierarchy_diff()` undefined | **Fixed** | Full implementations added to Section 8.10 with docstrings |
| QA-2 | Watch dedup key format unclear, collision-prone | **Fixed** | Replaced with `timestamp\|logType\|md5_hash` format in Section 8.7 |
| QA-3 | Signal handler registration pattern missing | **Fixed** | Added `_handle_sigint` registration code in Section 13 |
| QA-4 | `get_timeout()` precedence implementation missing | **Fixed** | Full function body with docstring added in Section 4.5 |
| QA-5 | Destructive commands lack safety documentation | **Fixed** | Added "Destructive Command Safety (v1)" subsection in Section 13 |
