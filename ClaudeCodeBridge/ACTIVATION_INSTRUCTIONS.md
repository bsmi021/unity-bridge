# Command Handlers Activation Instructions

## Current Status
✅ **6 new command handler files created** but not yet activated
✅ **run-tests handler** is working

## New Handler Files Created
- `QueryHierarchyCommandHandler.cs` - Inspect GameObject hierarchy
- `GetComponentDataCommandHandler.cs` - Read component field values
- `SetComponentDataCommandHandler.cs` - Modify component field values
- `AddComponentCommandHandler.cs` - Add components to GameObjects
- `ValidatePrefabCommandHandler.cs` - Validate prefab integrity
- `ProfilerSampleCommandHandler.cs` - Capture performance snapshots

## Why They're Not Active Yet
Unity hasn't imported the new .cs files into its compilation yet. This is a Unity Editor behavior where newly created files need to be detected and imported.

## Activation Steps

### Option 1: Close and Reopen Unity (Recommended)
1. **Save your scene** (Ctrl+S)
2. **Close Unity Editor completely**
3. **Reopen the project**
4. Unity will detect all new files and reimport them
5. Check Console for: `[ClaudeUnityBridge] Registered 7 command handlers...`
6. Uncomment lines 76-81 in `ClaudeUnityBridge.cs`
7. Save and wait for recompilation

### Option 2: Force Reimport
1. In Unity: **Assets > Refresh** (Ctrl+R)
2. Wait for asset database refresh
3. In Unity: **Assets > Reimport All**
4. Wait for full project reimport (may take a few minutes)
5. Check Console for successful compilation
6. Uncomment lines 76-81 in `ClaudeUnityBridge.cs`
7. Save and wait for recompilation

### Option 3: Manual Verification
1. Open Unity's **Project window**
2. Navigate to `Assets/Scripts/Editor/ClaudeCodeBridge/`
3. Verify you see all 6 new handler files with Unity icons (not question marks)
4. If files show as imported, uncomment lines 76-81 in `ClaudeUnityBridge.cs`
5. Save and Unity will recompile with all handlers

## Verifying Activation

Once activated, test with:
```powershell
.\.claude\unity\send-command.ps1 -CommandType "query-hierarchy" -Parameters @{maxDepth=2}
```

Should see: 7 command handlers registered in Unity Console

## If Still Having Issues

If Unity still won't detect the files after the above steps:
1. Ensure all .meta files were generated (each .cs file should have a .cs.meta)
2. Check for Unity Console errors during import
3. Try deleting `Library/ScriptAssemblies/BWS.Editor.dll` and let Unity rebuild
4. As last resort: Manually create one handler in Unity (Right-click > Create > C# Script) and copy content

## Current Code Location

The commented-out handler registrations are in:
- File: `Assets/Scripts/Editor/ClaudeCodeBridge/ClaudeUnityBridge.cs`
- Lines: 76-81
- Simply remove the `//` comment markers and save
