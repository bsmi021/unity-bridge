using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Main bridge system that allows Claude Code to communicate with Unity Editor.
    ///
    /// Architecture:
    /// 1. Watches .claude/unity/commands/ for JSON command files
    /// 2. Processes commands on EditorApplication.update (runs even when Unity is in background)
    /// 3. Writes JSON response files to .claude/unity/responses/
    /// 4. Supports extensible command handlers
    ///
    /// Usage from Claude Code:
    /// 1. Write command JSON to .claude/unity/commands/{guid}-{command-type}.json
    /// 2. Poll/watch .claude/unity/responses/{guid}-{command-type}.json for response
    /// 3. Parse response and continue workflow
    /// </summary>
    [InitializeOnLoad]
    public class ClaudeUnityBridge
    {
        private static ClaudeUnityBridge _instance;
        private static readonly string PROJECT_ROOT = Directory.GetParent(Application.dataPath).FullName;
        private static readonly string COMMANDS_PATH = Path.Combine(PROJECT_ROOT, ".claude", "unity", "commands");
        private static readonly string RESPONSES_PATH = Path.Combine(PROJECT_ROOT, ".claude", "unity", "responses");
    private static readonly string DIAGNOSTICS_PATH = Path.Combine(PROJECT_ROOT, ".claude", "unity", "diagnostics");
    private static readonly string DIAGNOSTICS_LOG = Path.Combine(DIAGNOSTICS_PATH, "bridge-log.jsonl");

    // Robust file read constants (kept small to avoid editor stalls)
    private const int READ_MAX_ATTEMPTS = 12;            // Total attempts before giving up
    private const int READ_RETRY_DELAY_MS = 50;           // Delay between attempts
    private const int STABILITY_WAIT_MS = 25;             // Wait to ensure file size/timestamp stability

        private Dictionary<string, ICommandHandler> _commandHandlers = new Dictionary<string, ICommandHandler>();
        private HashSet<string> _processedCommandFiles = new HashSet<string>();
        private FileSystemWatcher _commandWatcher;
        private PlayModeStateChange _lastPlayModeState = PlayModeStateChange.EnteredEditMode;
        private bool _isInitialized = false;

        /// <summary>
        /// Static constructor - runs when Unity loads the editor.
        /// Subscribes to EditorApplication.update for background processing.
        /// IMPORTANT: Also subscribes to playModeStateChanged to maintain state across domain reloads.
        /// </summary>
        static ClaudeUnityBridge()
        {
            EditorApplication.update += Update;
            EditorApplication.playModeStateChanged += OnPlayModeStateChanged;
            BridgeLogger.LogDebug("Static constructor - subscribed to EditorApplication events");
        }

        /// <summary>
        /// Singleton instance initialization.
        /// Recreates instance if null (resilience against domain reloads).
        /// </summary>
        private static ClaudeUnityBridge Instance
        {
            get
            {
                if (_instance == null)
                {
                    _instance = new ClaudeUnityBridge();
                    BridgeLogger.LogDebug("Creating new instance");
                }
                return _instance;
            }
        }

        /// <summary>
        /// Destructor - logs when instance is being garbage collected.
        /// Helps diagnose unexpected instance destruction.
        /// </summary>
        ~ClaudeUnityBridge()
        {
            BridgeLogger.LogWarning($"Instance being destroyed. PlayMode: {_lastPlayModeState}, Initialized: {_isInitialized}");
            Cleanup();
        }

        /// <summary>
        /// Initialize the bridge system.
        /// Sets up directories and registers command handlers.
        /// Safe to call multiple times (idempotent).
        /// </summary>
        private void Initialize()
        {
            if (_isInitialized)
            {
                BridgeLogger.LogDebug("Already initialized, skipping");
                return;
            }

            // Ensure directories exist
            Directory.CreateDirectory(COMMANDS_PATH);
            Directory.CreateDirectory(RESPONSES_PATH);
            Directory.CreateDirectory(DIAGNOSTICS_PATH);

            // Register command handlers (only if not already registered)
            if (_commandHandlers.Count == 0)
            {
                RegisterHandler(new RunTestsCommandHandler());
                RegisterHandler(new QueryHierarchyCommandHandler());
                RegisterHandler(new GetComponentDataCommandHandler());
                RegisterHandler(new SetComponentDataCommandHandler());
                RegisterHandler(new AddComponentCommandHandler());
                RegisterHandler(new ValidatePrefabCommandHandler());
                RegisterHandler(new ProfilerSampleCommandHandler());
                RegisterHandler(new ReadConsoleCommandHandler());
                RegisterHandler(new GameObjectOperationCommandHandler());
                RegisterHandler(new BridgeStatusCommandHandler());

                // Phase 1 new handlers
                RegisterHandler(new ClearConsoleCommandHandler());
                RegisterHandler(new GetSelectionCommandHandler());
                RegisterHandler(new RefreshAssetsCommandHandler());
                RegisterHandler(new FocusObjectCommandHandler());

                // Phase 2 handlers
                RegisterHandler(new CompileCommandHandler());
                RegisterHandler(new ExecuteMenuItemCommandHandler());

                // RegisterHandler(new AnimatorOperationCommandHandler()); // TODO: Enable after Unity import
                // RegisterHandler(new MaterialOperationCommandHandler()); // TODO: Enable after Unity import

                // NOTE: The following handlers will be registered after Unity imports their .meta files
                // After opening Unity Editor to import these files, uncomment these lines:
                // RegisterHandler(new AnimatorOperationCommandHandler());
                // RegisterHandler(new BuildOperationCommandHandler());
                // RegisterHandler(new SceneOperationCommandHandler());
                // RegisterHandler(new PrefabOperationCommandHandler());
            }

            // Set up file watcher for commands
            SetupFileWatcher();

            _isInitialized = true;
            BridgeLogger.LogInfo($"Initialized with {_commandHandlers.Count} command handlers");
        }

        /// <summary>
        /// Ensure bridge is initialized.
        /// Called from Update() to recover from domain reloads.
        /// </summary>
        private static void EnsureInitialized()
        {
            if (Instance != null && !Instance._isInitialized)
            {
                Instance.Initialize();
            }
        }

        /// <summary>
        /// Register a command handler.
        /// </summary>
        private void RegisterHandler(ICommandHandler handler)
        {
            _commandHandlers[handler.CommandType] = handler;
        }

        /// <summary>
        /// Set up file watcher to detect new command files.
        /// Disposes existing watcher before creating new one.
        /// </summary>
        private void SetupFileWatcher()
        {
            try
            {
                // Dispose existing watcher if present
                if (_commandWatcher != null)
                {
                    _commandWatcher.EnableRaisingEvents = false;
                    _commandWatcher.Created -= OnCommandFileCreated;
                    _commandWatcher.Dispose();
                    _commandWatcher = null;
                    BridgeLogger.LogDebug("Disposed existing file watcher");
                }

                // Create new watcher
                _commandWatcher = new FileSystemWatcher(COMMANDS_PATH)
                {
                    Filter = "*.json",
                    NotifyFilter = NotifyFilters.FileName | NotifyFilters.CreationTime
                };
                _commandWatcher.Created += OnCommandFileCreated;
                _commandWatcher.EnableRaisingEvents = true;
                BridgeLogger.LogDebug("File watcher enabled");
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Failed to setup file watcher: {ex.Message}");
            }
        }

        /// <summary>
        /// Clean up resources (file watcher, etc).
        /// Safe to call multiple times.
        /// </summary>
        private void Cleanup()
        {
            if (_commandWatcher != null)
            {
                try
                {
                    // Try to disable raising events (may already be disposed)
                    try
                    {
                        _commandWatcher.EnableRaisingEvents = false;
                    }
                    catch (ObjectDisposedException)
                    {
                        // Already disposed, ignore
                    }

                    // Try to unsubscribe from events
                    try
                    {
                        _commandWatcher.Created -= OnCommandFileCreated;
                    }
                    catch (ObjectDisposedException)
                    {
                        // Already disposed, ignore
                    }

                    // Try to dispose (safe to call even if already disposed)
                    _commandWatcher.Dispose();

                    BridgeLogger.LogDebug("Cleaned up file watcher");
                }
                catch (Exception ex)
                {
                    // Log error but don't fail cleanup
                    BridgeLogger.LogWarning($"Non-critical error during cleanup: {ex.Message}");
                }
                finally
                {
                    // Always null out the reference
                    _commandWatcher = null;
                }
            }
        }

        /// <summary>
        /// File watcher callback when a new command file is created.
        /// </summary>
        private void OnCommandFileCreated(object sender, FileSystemEventArgs e)
        {
            // File watcher callback - actual processing happens on main thread in Update()
            BridgeLogger.LogDebug($"Detected command file: {Path.GetFileName(e.FullPath)}");
        }

        /// <summary>
        /// Main update loop - runs every editor frame.
        /// Processes pending command files on the main Unity thread.
        /// Ensures initialization and recovery from domain reloads.
        /// </summary>
        private static void Update()
        {
            // Ensure instance exists (resilience against GC/domain reload)
            if (_instance == null)
            {
                // Just access Instance to trigger creation
                _ = Instance;
            }

            // Ensure initialized (recovery mechanism)
            EnsureInitialized();

            // Process pending commands if directories exist
            if (Directory.Exists(COMMANDS_PATH))
            {
                Instance.ProcessPendingCommands();
            }
        }

        /// <summary>
        /// Handle play mode state changes.
        /// Maintains bridge state across domain reloads.
        /// </summary>
        private static void OnPlayModeStateChanged(PlayModeStateChange state)
        {
            BridgeLogger.LogDebug($"Play mode state changed: {state}");

            if (_instance != null)
            {
                _instance._lastPlayModeState = state;
            }

            switch (state)
            {
                case PlayModeStateChange.EnteredEditMode:
                    // Re-initialize after exiting play mode (domain may have reloaded)
                    EnsureInitialized();
                    break;

                case PlayModeStateChange.ExitingEditMode:
                    // About to enter play mode - ensure we're ready
                    EnsureInitialized();
                    break;

                case PlayModeStateChange.EnteredPlayMode:
                    // Now in play mode - ensure initialized
                    EnsureInitialized();
                    break;

                case PlayModeStateChange.ExitingPlayMode:
                    // About to exit play mode - nothing to do
                    break;
            }
        }

        /// <summary>
        /// Process all pending command files.
        /// </summary>
        private void ProcessPendingCommands()
        {
            try
            {
                var commandFiles = Directory.GetFiles(COMMANDS_PATH, "*.json")
                    .Where(f => !_processedCommandFiles.Contains(f))
                    .ToList();

                foreach (var commandFile in commandFiles)
                {
                    ProcessCommandFile(commandFile);
                    _processedCommandFiles.Add(commandFile);
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error processing commands: {ex.Message}");
            }
        }

        /// <summary>
        /// Process a single command file.
        /// </summary>
        private void ProcessCommandFile(string commandFilePath)
        {
            string commandId = null;
            string commandType = null;
            string fileBaseName = Path.GetFileName(commandFilePath);

            try
            {
                // Attempt robust read of command JSON with retries and stability detection
                if (!TryReadCommandJson(commandFilePath, out var commandJson, out var readDiag))
                {
                    // Could not read the file contents. Try to recover metadata from filename and emit a diagnostic error response.
                    TryExtractMetadataFromFilename(fileBaseName, out commandId, out commandType);

                    var reason = $"Failed to read command file after {READ_MAX_ATTEMPTS} attempts. Details: {readDiag}";
                    WriteDiagnostic("read-failed", reason, commandFilePath, null);

                    var errorResponse = BridgeResponse.Error(
                        string.IsNullOrEmpty(commandId) ? $"filename-{fileBaseName}" : commandId,
                        string.IsNullOrEmpty(commandType) ? "unknown" : commandType,
                        reason
                    );
                    WriteResponse(errorResponse);
                    // Do not attempt to delete file here; it may not exist or may be mid-write.
                    return;
                }
                var command = JsonUtility.FromJson<BridgeCommand>(commandJson);

                commandId = command.commandId;
                commandType = command.commandType;

                // Validate parsed JSON; JsonUtility returns default instance on malformed JSON rather than throwing
                if (string.IsNullOrEmpty(commandId) || string.IsNullOrEmpty(commandType))
                {
                    // Fallback to filename metadata extraction when possible
                    string fallbackId, fallbackType;
                    TryExtractMetadataFromFilename(fileBaseName, out fallbackId, out fallbackType);

                    var parseMsg = $"Invalid or incomplete command JSON. Parsed commandId='{commandId ?? "<null>"}', commandType='{commandType ?? "<null>"}'. Fallback from filename: id='{fallbackId ?? "<none>"}', type='{fallbackType ?? "<none>"}'.";
                    WriteDiagnostic("json-invalid", parseMsg, commandFilePath, null);

                    var errorResponse = BridgeResponse.Error(
                        string.IsNullOrEmpty(commandId) ? (string.IsNullOrEmpty(fallbackId) ? $"filename-{fileBaseName}" : fallbackId) : commandId,
                        string.IsNullOrEmpty(commandType) ? (string.IsNullOrEmpty(fallbackType) ? "unknown" : fallbackType) : commandType,
                        parseMsg
                    );
                    WriteResponse(errorResponse);
                    SafeDelete(commandFilePath);
                    return;
                }

                BridgeLogger.LogDebug($"Processing command: {commandType} (ID: {commandId})");

                // Find handler
                if (!_commandHandlers.TryGetValue(commandType, out var handler))
                {
                    var errorResponse = BridgeResponse.Error(
                        commandId,
                        commandType,
                        $"Unknown command type: {commandType}"
                    );
                    WriteDiagnostic("unknown-command", $"No handler registered for '{commandType}'", commandFilePath, null);
                    WriteResponse(errorResponse);
                    return;
                }

                // Execute command
                var response = handler.Execute(command);
                WriteResponse(response);

                // Track command execution for heartbeat monitoring
                HeartbeatGenerator.IncrementCommandCount();

                // Clean up command file
                SafeDelete(commandFilePath);
                BridgeLogger.LogDebug($"Completed command: {commandType} (ID: {commandId})");
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error executing command: {ex}");
                WriteDiagnostic("execute-exception", "Unhandled exception during command execution", commandFilePath, ex);

                if (commandId != null && commandType != null)
                {
                    var errorResponse = BridgeResponse.Error(commandId, commandType, ex.ToString());
                    WriteResponse(errorResponse);
                }
                else
                {
                    // Last resort: emit a filename-scoped error so the other side has breadcrumbs
                    TryExtractMetadataFromFilename(fileBaseName, out var fallbackId, out var fallbackType);
                    var errorResponse = BridgeResponse.Error(
                        string.IsNullOrEmpty(fallbackId) ? $"filename-{fileBaseName}" : fallbackId,
                        string.IsNullOrEmpty(fallbackType) ? "unknown" : fallbackType,
                        ex.ToString()
                    );
                    WriteResponse(errorResponse);
                }
            }
        }

        /// <summary>
        /// Attempt to robustly read a command JSON file, handling transient writer races and partial writes.
        /// Returns false with a diagnostic summary if reading fails after retries.
        /// </summary>
        private bool TryReadCommandJson(string path, out string json, out string diagnosticSummary)
        {
            json = null;
            diagnosticSummary = null;

            var attempts = 0;
            int missingCount = 0;
            int ioExceptions = 0;
            int emptyReads = 0;

            while (attempts < READ_MAX_ATTEMPTS)
            {
                attempts++;

                try
                {
                    if (!File.Exists(path))
                    {
                        missingCount++;
                        Thread.Sleep(READ_RETRY_DELAY_MS);
                        continue;
                    }

                    if (!IsFileStable(path))
                    {
                        Thread.Sleep(READ_RETRY_DELAY_MS);
                        continue;
                    }

                    if (TryReadAllTextShared(path, out json) && !string.IsNullOrWhiteSpace(json))
                    {
                        diagnosticSummary = "ok";
                        return true;
                    }

                    emptyReads++;
                    Thread.Sleep(READ_RETRY_DELAY_MS);
                }
                catch (IOException)
                {
                    ioExceptions++;
                    Thread.Sleep(READ_RETRY_DELAY_MS);
                }
                catch (UnauthorizedAccessException)
                {
                    ioExceptions++;
                    Thread.Sleep(READ_RETRY_DELAY_MS);
                }
            }

            diagnosticSummary = $"attempts={attempts}; missingChecks={missingCount}; ioErrors={ioExceptions}; emptyReads={emptyReads}";
            return false;
        }

        /// <summary>
        /// Returns true when file size and last write time are stable across a short interval.
        /// </summary>
        private bool IsFileStable(string path)
        {
            try
            {
                var info1 = new FileInfo(path);
                var size1 = info1.Length;
                var time1 = info1.LastWriteTimeUtc;
                Thread.Sleep(STABILITY_WAIT_MS);
                if (!File.Exists(path)) return false;
                var info2 = new FileInfo(path);
                return info2.Length == size1 && info2.LastWriteTimeUtc == time1;
            }
            catch
            {
                return false;
            }
        }

        /// <summary>
        /// Read all text from a file allowing the writer to keep the handle open.
        /// </summary>
        private bool TryReadAllTextShared(string path, out string content)
        {
            content = null;
            try
            {
                using (var fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
                using (var reader = new StreamReader(fs))
                {
                    content = reader.ReadToEnd();
                    return true;
                }
            }
            catch
            {
                return false;
            }
        }

        /// <summary>
        /// Try to extract commandId and commandType from the filename pattern "{guid}-{commandType}.json".
        /// Falls back to nulls when pattern doesn't match.
        /// </summary>
        private void TryExtractMetadataFromFilename(string fileName, out string commandId, out string commandType)
        {
            commandId = null;
            commandType = null;

            try
            {
                var baseName = Path.GetFileNameWithoutExtension(fileName);
                // GUID-at-start pattern: 8-4-4-4-12 hex digits, then a dash, then type (which may include dashes)
                var match = Regex.Match(baseName, "^(?<id>[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})-(?<type>.+)$");
                if (match.Success)
                {
                    commandId = match.Groups["id"].Value;
                    commandType = match.Groups["type"].Value;
                }
            }
            catch (Exception ex)
            {
                WriteDiagnostic("filename-parse-failed", $"Failed to parse filename metadata for '{fileName}'", fileName, ex);
            }
        }

        /// <summary>
        /// Attempt to delete a file and swallow non-critical exceptions, with diagnostics.
        /// </summary>
        private void SafeDelete(string path)
        {
            try
            {
                if (File.Exists(path))
                {
                    File.Delete(path);
                }
            }
            catch (Exception ex)
            {
                WriteDiagnostic("delete-failed", $"Failed to delete command file '{path}'", path, ex);
            }
        }

        [Serializable]
        private class BridgeDiagnosticEvent
        {
            public string timestamp;
            public string level;
            public string eventType;
            public string message;
            public string file;
            public string exception;
        }

        /// <summary>
        /// Write a structured diagnostic event to the diagnostics log for offline analysis.
        /// </summary>
        private void WriteDiagnostic(string eventType, string message, string file, Exception ex)
        {
            try
            {
                var evt = new BridgeDiagnosticEvent
                {
                    timestamp = DateTime.UtcNow.ToString("o"),
                    level = ex == null ? "Warn" : "Error",
                    eventType = eventType,
                    message = message,
                    file = file,
                    exception = ex?.ToString()
                };

                var json = JsonUtility.ToJson(evt, false);
                File.AppendAllText(DIAGNOSTICS_LOG, json + Environment.NewLine);
            }
            catch
            {
                // Best-effort diagnostics; never throw from logging
            }
        }

        /// <summary>
        /// Write a response to the responses directory.
        /// </summary>
        private void WriteResponse(BridgeResponse response)
        {
            WriteResponseStatic(response);
        }

        /// <summary>
        /// Static method to write a response (for use by command handlers).
        /// </summary>
        public static void WriteResponseStatic(BridgeResponse response)
        {
            try
            {
                var responseJson = JsonUtility.ToJson(response, true);
                var responseFilePath = Path.Combine(RESPONSES_PATH, $"{response.commandId}-{response.commandType}.json");
                File.WriteAllText(responseFilePath, responseJson);
                BridgeLogger.LogDebug($"Wrote response: {Path.GetFileName(responseFilePath)}");
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error writing response: {ex}");
            }
        }

        #region Context Menu Items

        /// <summary>
        /// Test bridge connection by querying bridge status.
        /// </summary>
        [MenuItem("Assets/Claude Code Bridge/Test Connection", false, 100)]
        public static void TestConnection()
        {
            // Menu items always log (user explicitly requested output)
            Debug.Log("[ClaudeUnityBridge] Testing bridge connection...");

            try
            {
                if (Instance._isInitialized && Instance._commandWatcher != null && Instance._commandWatcher.EnableRaisingEvents)
                {
                    Debug.Log($"[ClaudeUnityBridge] Connection successful!\n" +
                             $"- Bridge initialized: {Instance._isInitialized}\n" +
                             $"- File watcher active: {Instance._commandWatcher.EnableRaisingEvents}\n" +
                             $"- Registered handlers: {Instance._commandHandlers.Count}\n" +
                             $"- Commands processed: {Instance._processedCommandFiles.Count}");
                }
                else
                {
                    Debug.LogWarning("[ClaudeUnityBridge] Bridge is not fully operational. Attempting to reinitialize...");
                    EnsureInitialized();

                    if (Instance._isInitialized)
                    {
                        Debug.Log("[ClaudeUnityBridge] Bridge reinitialized successfully!");
                    }
                    else
                    {
                        Debug.LogError("[ClaudeUnityBridge] Failed to initialize bridge. Check console for errors.");
                    }
                }
            }
            catch (Exception ex)
            {
                Debug.LogError($"[ClaudeUnityBridge] Connection test failed: {ex}");
            }
        }

        /// <summary>
        /// Show detailed bridge status.
        /// </summary>
        [MenuItem("Assets/Claude Code Bridge/Show Status", false, 101)]
        public static void ShowStatusFromAssetsMenu()
        {
            ShowStatus();
        }

        /// <summary>
        /// Clean up old response files (older than 1 hour).
        /// </summary>
        [MenuItem("Assets/Claude Code Bridge/Clean Old Responses", false, 200)]
        public static void CleanOldResponsesFromAssetsMenu()
        {
            CleanOldResponses();
        }

        /// <summary>
        /// Clean up old command files (older than 1 hour).
        /// Useful if commands get stuck or orphaned.
        /// </summary>
        [MenuItem("Assets/Claude Code Bridge/Clean Old Commands", false, 201)]
        public static void CleanOldCommands()
        {
            try
            {
                var cutoffTime = DateTime.UtcNow.AddHours(-1);
                var files = Directory.GetFiles(COMMANDS_PATH, "*.json");
                int cleaned = 0;

                foreach (var file in files)
                {
                    if (File.GetCreationTimeUtc(file) < cutoffTime)
                    {
                        File.Delete(file);
                        cleaned++;
                    }
                }

                // Menu items always log (user explicitly requested output)
                Debug.Log($"[ClaudeUnityBridge] Cleaned {cleaned} old command files");
            }
            catch (Exception ex)
            {
                Debug.LogError($"[ClaudeUnityBridge] Error cleaning commands: {ex}");
            }
        }

        /// <summary>
        /// Manually reset and reinitialize the bridge.
        /// </summary>
        [MenuItem("Assets/Claude Code Bridge/Reset Bridge", false, 300)]
        public static void ResetBridgeFromAssetsMenu()
        {
            ResetBridge();
        }

        /// <summary>
        /// Open Claude Unity Bridge documentation in browser.
        /// </summary>
        [MenuItem("Assets/Claude Code Bridge/Open Documentation", false, 400)]
        public static void OpenDocumentation()
        {
            Application.OpenURL("https://github.com/anthropics/claude-code");
            Debug.Log("[ClaudeUnityBridge] Opening documentation in browser...");
        }

        /// <summary>
        /// Show bridge file system paths in console.
        /// </summary>
        [MenuItem("Assets/Claude Code Bridge/Show File Paths", false, 401)]
        public static void ShowFilePaths()
        {
            Debug.Log($"[ClaudeUnityBridge] File System Paths:\n" +
                     $"Commands: {COMMANDS_PATH}\n" +
                     $"Responses: {RESPONSES_PATH}\n" +
                     $"Project Root: {PROJECT_ROOT}");
        }

        #endregion

        #region Tools Menu Items

        /// <summary>
        /// Clean up old response files (older than 1 hour).
        /// Called from menu item for manual cleanup.
        /// </summary>
        [MenuItem("Tools/Claude Code Bridge/Clean Old Responses")]
        public static void CleanOldResponses()
        {
            try
            {
                var cutoffTime = DateTime.UtcNow.AddHours(-1);
                var files = Directory.GetFiles(RESPONSES_PATH, "*.json");
                int cleaned = 0;

                foreach (var file in files)
                {
                    if (File.GetCreationTimeUtc(file) < cutoffTime)
                    {
                        File.Delete(file);
                        cleaned++;
                    }
                }

                Debug.Log($"[ClaudeUnityBridge] Cleaned {cleaned} old response files");
            }
            catch (Exception ex)
            {
                Debug.LogError($"[ClaudeUnityBridge] Error cleaning responses: {ex}");
            }
        }

        /// <summary>
        /// Show bridge status in console.
        /// </summary>
        [MenuItem("Tools/Claude Code Bridge/Show Status")]
        public static void ShowStatus()
        {
            Debug.Log($"[ClaudeUnityBridge] Status:\n" +
                     $"Initialized: {Instance._isInitialized}\n" +
                     $"Play Mode State: {Instance._lastPlayModeState}\n" +
                     $"File Watcher Active: {Instance._commandWatcher != null && Instance._commandWatcher.EnableRaisingEvents}\n" +
                     $"Commands Path: {COMMANDS_PATH}\n" +
                     $"Responses Path: {RESPONSES_PATH}\n" +
                     $"Registered Handlers: {string.Join(", ", Instance._commandHandlers.Keys)}\n" +
                     $"Processed Commands: {Instance._processedCommandFiles.Count}");
        }

        /// <summary>
        /// Manually reset and reinitialize the bridge.
        /// Useful for debugging or recovering from errors.
        /// </summary>
        [MenuItem("Tools/Claude Code Bridge/Reset Bridge")]
        public static void ResetBridge()
        {
            Debug.Log("[ClaudeUnityBridge] Manual reset requested");

            if (_instance != null)
            {
                _instance.Cleanup();
                _instance._isInitialized = false;
                _instance._processedCommandFiles.Clear();
            }

            EnsureInitialized();
            Debug.Log("[ClaudeUnityBridge] Reset complete - bridge reinitialized");
        }

        #endregion
    }
}
