# BridgeStatusCommandHandler Activation

## Status: READY FOR ACTIVATION

The `BridgeStatusCommandHandler.cs` file has been created and is ready for use. However, it requires Unity Editor to import the file before it can be registered in the bridge system.

## Files Created

- `BridgeStatusCommandHandler.cs` - Main command handler implementation
- `BridgeStatusCommandHandler.cs.meta` - Unity metadata file for proper asset management
- `BridgeStatusCommandHandler_ACTIVATION.md` - This file

## Activation Steps

Once Unity Editor is opened and imports the new file, follow these steps:

### Step 1: Verify Import

1. Open Unity Editor for the rpg.game project
2. Wait for Unity to detect and import the new files
3. Check the Console for any import errors
4. Verify `BridgeStatusCommandHandler` appears in the Project window under:
   `Assets/Scripts/Editor/ClaudeCodeBridge/BridgeStatusCommandHandler.cs`

### Step 2: Enable Registration

1. Open `Assets/Scripts/Editor/ClaudeCodeBridge/ClaudeUnityBridge.cs`
2. Find the line (approximately line 82):
   ```csharp
   // RegisterHandler(new BridgeStatusCommandHandler()); // TODO: Enable after Unity imports the file
   ```
3. Uncomment it to:
   ```csharp
   RegisterHandler(new BridgeStatusCommandHandler());
   ```
4. Save the file
5. Wait for Unity to recompile

### Step 3: Verify Registration

Check the Console after Unity recompiles. You should see:
```
[ClaudeUnityBridge] Registered X command handlers: run-tests, query-hierarchy, ..., bridge-status, ...
```

### Step 4: Test the Handler

Run the bridge-status command from PowerShell:
```powershell
& ".claude\unity\send-command.ps1" -CommandType "bridge-status"
```

Expected response in `.claude/unity/responses/{guid}-bridge-status.json`:
```json
{
  "commandId": "...",
  "commandType": "bridge-status",
  "status": "success",
  "timestamp": "...",
  "dataJson": "{
    \"unityVersion\": \"6000.2.0f1\",
    \"isInitialized\": true,
    \"registeredHandlers\": [...],
    \"commandsProcessed\": 0,
    \"commandsPath\": \"C:/Projects/rpg.game/.claude/unity/commands\",
    \"responsesPath\": \"C:/Projects/rpg.game/.claude/unity/responses\",
    \"currentScene\": \"...\",
    \"playModeState\": \"Stopped\"
  }"
}
```

## What This Handler Does

The `BridgeStatusCommandHandler` provides diagnostic information about the Claude Unity Bridge system:

- **Unity Version**: Current Unity Editor version
- **Initialization Status**: Whether bridge is running
- **Registered Handlers**: List of all available command types
- **Commands Processed**: Total commands executed since Unity started
- **File Paths**: Locations where commands and responses are stored
- **Current Scene**: Active scene in Unity Editor
- **Play Mode State**: Whether Unity is Stopped, Playing, or Paused

## Use Cases

1. **Health Check**: Verify bridge connectivity before running automation
2. **Debug**: Troubleshoot command routing issues
3. **Discovery**: Find which commands are available
4. **Context Awareness**: Check Unity state before sending commands

## Implementation Details

- **Namespace**: `BWS.Editor.ClaudeCodeBridge`
- **Command Type**: `"bridge-status"`
- **Parameters**: None required (`BridgeStatusParams` is empty)
- **Response**: `BridgeStatusResult` with comprehensive status data
- **Reflection**: Uses reflection to access private bridge fields for accurate metrics
- **Coding Style**: Follows project conventions (Allman braces, extensive comments, XML docs)

## Troubleshooting

If the handler doesn't work after activation:

1. Check Unity Console for compilation errors
2. Verify the file was imported (check .meta file exists)
3. Confirm registration line is uncommented in `ClaudeUnityBridge.cs`
4. Restart Unity Editor to force full recompilation
5. Check `.claude/unity/responses/` for error messages

## Related Files

- `BridgeModels.cs` - Contains `BridgeStatusParams` and `BridgeStatusResult` (already present)
- `ClaudeUnityBridge.cs` - Main bridge system where handlers are registered
- `ReadConsoleCommandHandler.cs` - Similar handler used as pattern reference
