# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `app.py` Typer entry point with global flags (`--project`, `--pretty`, `--human`, `--verbose`, `--quiet`, `--timeout`, `--no-color`)
- `mcp/server.py` migrated from monolithic `unity_bridge_mcp_server.py`, uses shared core async functions
- `mcp/tools.py` tool definitions and command map for MCP tool dispatch
- `mcp/schemas.py` JSON Schema definitions for all 26 MCP tools
- Lazy DirectBridge initialization in `AppState.get_bridge()`
- Signal handler for clean Ctrl+C exit (code 130)
- Graceful degradation for optional command modules via `_try_register_command`

## [3.0.0] - 2026-02-21

### BREAKING CHANGES
- Removed all PowerShell dependencies; MCP server now requires DirectBridge (aiofiles)
- `mcp.json` command changed from `python` to `python3` (Ubuntu/WSL default)
- Removed `psutil` dependency from `bridge_utils.py`

### Removed
- Removed PowerShell fallback from `invoke_unity_command()` (~120 lines)
- Removed `import subprocess` from MCP server
- Removed `SCRIPT_DIR` and `INVOKE_SCRIPT` constants
- Deleted 5 PowerShell scripts from `unity/scripts/`: `send-command.ps1`, `Invoke-UnityCommand.ps1`, `BridgeUtilities.ps1`, `cleanup-bridge.ps1`, `test-mcp-diagnostic.ps1`
- Deleted 12 PowerShell scripts from `scripts/`: `run-unity-tests.ps1`, `run-unity-tests-automated.ps1`, `run-tests.ps1`, `analyze-allocations.ps1`, `asset-backup-system.ps1`, `code-formatter.ps1`, `performance-monitor.ps1`, `refactor-checkpoint.ps1`, `scene-validation.ps1`, `test-hook-setup.ps1`, `unity-asset-validator.ps1`, `unity-asset-validator-wrapper.ps1`
- Deleted `unity/scripts/bridge-operator.md` (31KB PowerShell-focused documentation)
- Removed PowerShell permission entries from `.claude/settings.local.json`
- Removed `zen-win` MCP server from enabled servers list

### Changed
- `bridge_utils.py`: Unity detection now uses heartbeat file instead of `psutil` process enumeration (works from WSL)
- `invoke_unity_command()` returns immediate error when DirectBridge unavailable instead of falling through to PowerShell
- Slash commands (`/unity-build`, `/unity-logs`) rewritten to use MCP bridge tools
- Updated all documentation to use Python/WSL paths and examples
- Settings: replaced PowerShell permissions with `Bash(python3:*)`

### Added
- `_check_heartbeat()` function in `bridge_utils.py` for heartbeat-based Unity detection
- `unity/requirements.txt` with runtime dependencies (aiofiles, mcp)
- `test_bridge_utils.py` - unit tests for heartbeat detection and file cleanup
- `test_wsl_compatibility.py` - tests verifying no PowerShell references remain

---

## [2.1.0] - 2026-01-06

### Added

#### Console Log Stack Trace Control
- `includeStackTrace` parameter for `unity_read_console` - toggle stack trace inclusion
- `maxStackTraceLines` parameter - limit stack trace lines per entry (default: 5, 0=unlimited, -1=none)
- `maxMessageLength` parameter - truncate long messages (default: 500 chars, 0=unlimited)
- Intelligent stack trace parsing separates message content from stack trace
- Truncation indicators show when content was trimmed
- Reduces context window usage when reading console logs with many errors

### Changed
- `ReadConsoleCommandHandler.cs` now parses and truncates stack traces
- `ReadConsoleParams` model extended with stack trace control parameters
- MCP tool schema updated with new optional parameters

---

## [2.0.0] - 2026-01-06

### Added

#### Auto-Update System
- Automatic version detection and update on MCP server startup
- SHA256 hash-based file change detection for selective updates
- `bridge_manifest.json` tracks installed version and file hashes
- Support for legacy installations (auto-generates manifest on first update)
- Safe file copying with file locking detection (handles Unity editor locks)
- CLI support: `install_bridge.py --check` to check update status
- Selective updates: only changed files are copied, reducing Unity recompilation

#### Phase 1: Quick Wins
- `unity_clear_console` tool - Clear Unity console logs
- `unity_get_selection` tool - Get currently selected objects in Unity Editor
- `unity_refresh_assets` tool - Force refresh of Unity asset database
- `unity_focus_object` tool - Focus camera on specific GameObject
- `unity_health_check` tool - Check Unity Bridge health status
- Smart timeout defaults per command type (TIMEOUT_DEFAULTS)
- Heartbeat system for health monitoring (HeartbeatGenerator.cs)
- Health monitoring via heartbeat.json (health_monitor.py)
- Retry logic with exponential backoff (retry_handler.py)

#### Phase 2: Architecture Simplification
- DirectBridge class for direct Python-to-file communication (direct_bridge.py)
- `unity_compile` tool - Trigger and monitor C# compilation
- `unity_execute_menu_item` tool - Execute Unity Editor menu items
- CompileCommandHandler.cs - C# handler for compilation commands
- ExecuteMenuItemCommandHandler.cs - C# handler for menu item execution
- Automatic fallback to PowerShell if DirectBridge unavailable

#### Phase 3: Developer Experience
- `unity_batch` tool - Execute multiple commands in single request
- `unity_help` tool - Get help for available tools and usage
- Response caching for read-only operations (response_cache.py)
- Cache integration with MCP server for improved latency
- Scene change detection for automatic cache invalidation

### Changed
- `invoke_unity_command()` now uses DirectBridge by default with PowerShell fallback
- MCP server imports DirectBridge, RetryConfig, and ResponseCache with graceful degradation
- ClaudeUnityBridge.cs now registers Phase 2 handlers (Compile, ExecuteMenuItem)
- Improved error handling with detailed error messages

### Technical Details
- DirectBridge provides ~50% latency reduction compared to PowerShell
- Response cache uses LRU eviction with configurable TTL
- Heartbeat updates every 5 seconds with Unity state information
- Retry handler uses exponential backoff (base_delay=0.1s, max_delay=2.0s)

### Dependencies
- Added: aiofiles (required for DirectBridge async file I/O)
- Python 3.10+ required

## [1.3.1] - Previous Release

- Initial Unity Bridge MCP implementation
- PowerShell-based command execution
- Basic Unity Editor integration
