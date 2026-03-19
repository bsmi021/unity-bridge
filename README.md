# Claude Unity Bridge

A communication bridge that allows Claude Code to interact with Unity Editor programmatically.

## Auto-Installation

**The Unity Bridge automatically installs itself!** When the MCP server starts:

1. **Detects your Unity project** by finding the `Assets/` directory
2. **Copies all C# bridge files** to `Assets/Scripts/Editor/ClaudeCodeBridge/`
3. **Creates required directories** (`.claude/unity/commands/` and `.claude/unity/responses/`)
4. **Skips if already installed** - safe to run multiple times

**No manual setup required!** Just enable the MCP server and the bridge installs itself automatically.

See [AUTO_INSTALL.md](AUTO_INSTALL.md) for detailed installation information.

## Architecture

The bridge uses a file-based RPC system that works across the WSL/Windows boundary:
1. **Commands**: Python (DirectBridge) writes JSON command files to `.claude/unity/commands/`
2. **Execution**: Unity's `EditorApplication.update` detects and processes commands (even in background)
3. **Responses**: Unity writes JSON response files to `.claude/unity/responses/`
4. **Results**: Python reads response files and continues workflow

The file-based IPC works seamlessly across WSL2 and Windows via `/mnt/c/` path mapping.

## Key Components

### Core Scripts
- **BridgeModels.cs** - Command/response JSON schemas for all commands
- **ClaudeUnityBridge.cs** - Main bridge with file watchers and command routing

### Python Bridge Layer
- **direct_bridge.py** - Async file I/O for command/response communication
- **health_monitor.py** - Heartbeat-based health monitoring
- **response_cache.py** - LRU cache for read-only operations
- **retry_handler.py** - Exponential backoff retry logic
- **install_bridge.py** - Auto-installer for Unity C# components

### Command Handlers (C# - runs inside Unity on Windows)
- **RunTestsCommandHandler.cs** - Execute Unity tests (EditMode/PlayMode)
- **QueryHierarchyCommandHandler.cs** - Inspect GameObject hierarchy
- **GetComponentDataCommandHandler.cs** - Read component field values
- **SetComponentDataCommandHandler.cs** - Modify component field values
- **AddComponentCommandHandler.cs** - Add components to GameObjects
- **ValidatePrefabCommandHandler.cs** - Validate prefab integrity
- **ProfilerSampleCommandHandler.cs** - Capture performance snapshots
- And many more (see AUTO_INSTALL.md for full list)

## Available MCP Tools

All commands are accessed via MCP tools. Use `unity_help` for the full list.

### Testing
```
unity_run_tests(testPlatform="EditMode")
unity_run_tests(testPlatform="EditMode", testFilter="CombatTests")
unity_compile(waitForCompletion=true)
```

### Hierarchy & Components
```
unity_query_hierarchy(maxDepth=3, includeInactive=true)
unity_get_component_data(gameObjectPath="Player", componentType="BWS.CharacterStats")
unity_set_component_data(gameObjectPath="Player", componentType="BWS.CharacterStats", fieldUpdates=[...])
```

### Scene & Prefab Operations
```
unity_scene_operation(operation="load", scenePath="Assets/Scenes/Main.unity")
unity_validate_prefab(prefabPath="Assets/Prefabs/Player.prefab")
```

### Editor Control
```
unity_playmode_control(operation="play")
unity_read_console(logTypes=["Error", "Warning"])
unity_execute_menu_item(menuPath="File/Save")
```

### Diagnostics
```
unity_health_check(waitForHealthy=true)
unity_profiler_sample(includeMemory=true)
```

### Batch Operations
```
unity_batch(commands=[
    {"type": "clear-console"},
    {"type": "compile", "parameters": {"waitForCompletion": true}},
    {"type": "run-tests", "parameters": {"testPlatform": "EditMode"}}
])
```

## WSL Setup

### Prerequisites
- WSL2 with Ubuntu
- Python 3.10+
- Unity Editor running on Windows

### Installation
```bash
cd /mnt/c/projects/your-project/unity-plugin
python3 -m venv .venv
source .venv/bin/activate
pip install -r unity/requirements.txt
```

### Verification
```bash
# Check bridge health
python3 unity/unity_bridge_mcp_server.py  # Starts MCP server

# Run tests
cd unity && python3 -m pytest tests/ -v
```

## Unity Menu Items

- **Tools > Claude Code Bridge > Show Status** - Display bridge status in console
- **Tools > Claude Code Bridge > Clean Old Responses** - Remove response files older than 1 hour

## How It Works

1. **Initialization**: `[InitializeOnLoad]` attribute ensures bridge starts when Unity loads
2. **File Watching**: `FileSystemWatcher` monitors commands directory for new JSON files
3. **Main Thread Execution**: `EditorApplication.update` processes commands on Unity's main thread
4. **Async Test Execution**: Uses Unity's `TestRunnerApi` with callbacks for async test execution
5. **Response Writing**: Results written to responses directory for Python to read

## Testing the Bridge

1. **Open Unity** (bridge requires Unity open on Windows)
2. **Check Console** - Should see: `[ClaudeUnityBridge] Initialized - listening for commands...`
3. **Test via MCP**: Use `unity_health_check` to verify the bridge is responsive
4. **Verify Response** - Should see health status with heartbeat information
