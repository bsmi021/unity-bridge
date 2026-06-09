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
    /// 2. Processes commands on EditorApplication.update
    /// 3. Writes JSON response files to .claude/unity/responses/
    /// 4. Command registry and menu items extracted to separate files
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

        private const int READ_MAX_ATTEMPTS = 12;
        private const int READ_RETRY_DELAY_MS = 50;
        private const int STABILITY_WAIT_MS = 25;

        private Dictionary<string, ICommandHandler> _commandHandlers = new Dictionary<string, ICommandHandler>();
        private HashSet<string> _processedCommandFiles = new HashSet<string>();
        private FileSystemWatcher _commandWatcher;
        private PlayModeStateChange _lastPlayModeState = PlayModeStateChange.EnteredEditMode;
        private bool _isInitialized = false;
        private bool _recoveryScanned = false;

        static ClaudeUnityBridge()
        {
            EditorApplication.update += Update;
            EditorApplication.playModeStateChanged += OnPlayModeStateChanged;
            BridgeLogger.LogDebug("Static constructor - subscribed to EditorApplication events");
        }

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

        ~ClaudeUnityBridge()
        {
            BridgeLogger.LogWarning(
                $"Instance being destroyed. PlayMode: {_lastPlayModeState}, Initialized: {_isInitialized}");
            Cleanup();
        }

        private void Initialize()
        {
            if (_isInitialized)
            {
                BridgeLogger.LogDebug("Already initialized, skipping");
                return;
            }

            Directory.CreateDirectory(COMMANDS_PATH);
            Directory.CreateDirectory(RESPONSES_PATH);
            Directory.CreateDirectory(DIAGNOSTICS_PATH);
            BridgeOperationLedger.EnsureInitialized();

            if (_commandHandlers.Count == 0)
            {
                BridgeCommandRegistry.RegisterAll(RegisterHandler);
            }

            SetupFileWatcher();
            if (!_recoveryScanned)
            {
                BridgeOperationLedger.RecoverAfterReload();
                _recoveryScanned = true;
            }
            _isInitialized = true;
            BridgeLogger.LogInfo($"Initialized with {_commandHandlers.Count} command handlers");
        }

        private static void EnsureInitialized()
        {
            if (Instance != null && !Instance._isInitialized)
            {
                Instance.Initialize();
            }
        }

        private void RegisterHandler(ICommandHandler handler)
        {
            _commandHandlers[handler.CommandType] = handler;
        }

        #region Public API for Menu Items

        /// <summary>
        /// Status snapshot for menu item queries.
        /// </summary>
        public struct BridgeStatusSnapshot
        {
            public bool isInitialized;
            public bool isWatcherActive;
            public bool isHealthy;
            public int handlerCount;
            public int processedCount;
            public string playModeState;
            public string handlerNames;
        }

        public static BridgeStatusSnapshot GetBridgeStatus()
        {
            var inst = Instance;
            return new BridgeStatusSnapshot
            {
                isInitialized = inst._isInitialized,
                isWatcherActive = inst._commandWatcher != null && inst._commandWatcher.EnableRaisingEvents,
                // Health reflects the poll-driven processing loop, not the file
                // watcher (which only logs — all processing happens in Update).
                isHealthy = inst._isInitialized,
                handlerCount = inst._commandHandlers.Count,
                processedCount = inst._processedCommandFiles.Count,
                playModeState = inst._lastPlayModeState.ToString(),
                handlerNames = string.Join(", ", inst._commandHandlers.Keys)
            };
        }

        public static void ForceReinitialize()
        {
            EnsureInitialized();
        }

        public static void ResetBridge()
        {
            if (_instance != null)
            {
                _instance.Cleanup();
                _instance._isInitialized = false;
                _instance._processedCommandFiles.Clear();
            }
            EnsureInitialized();
        }

        #endregion

        #region File Watcher

        private void SetupFileWatcher()
        {
            try
            {
                if (_commandWatcher != null)
                {
                    _commandWatcher.EnableRaisingEvents = false;
                    _commandWatcher.Created -= OnCommandFileCreated;
                    _commandWatcher.Dispose();
                    _commandWatcher = null;
                    BridgeLogger.LogDebug("Disposed existing file watcher");
                }

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

        private void Cleanup()
        {
            if (_commandWatcher != null)
            {
                try
                {
                    try { _commandWatcher.EnableRaisingEvents = false; }
                    catch (ObjectDisposedException) { }
                    try { _commandWatcher.Created -= OnCommandFileCreated; }
                    catch (ObjectDisposedException) { }
                    _commandWatcher.Dispose();
                    BridgeLogger.LogDebug("Cleaned up file watcher");
                }
                catch (Exception ex)
                {
                    BridgeLogger.LogWarning($"Non-critical error during cleanup: {ex.Message}");
                }
                finally
                {
                    _commandWatcher = null;
                }
            }
        }

        private void OnCommandFileCreated(object sender, FileSystemEventArgs e)
        {
            BridgeLogger.LogDebug($"Detected command file: {Path.GetFileName(e.FullPath)}");
        }

        #endregion

        #region Update Loop and Command Processing

        private static void Update()
        {
            if (_instance == null) { _ = Instance; }
            EnsureInitialized();

            if (Directory.Exists(COMMANDS_PATH))
            {
                Instance.ProcessPendingCommands();
            }
        }

        private static void OnPlayModeStateChanged(PlayModeStateChange state)
        {
            BridgeLogger.LogDebug($"Play mode state changed: {state}");
            if (_instance != null) { _instance._lastPlayModeState = state; }

            switch (state)
            {
                case PlayModeStateChange.EnteredEditMode:
                case PlayModeStateChange.ExitingEditMode:
                case PlayModeStateChange.EnteredPlayMode:
                    EnsureInitialized();
                    break;
            }
        }

        private void ProcessPendingCommands()
        {
            try
            {
                var present = Directory.GetFiles(COMMANDS_PATH, "*.json");

                // Bound memory: a processed command file is deleted immediately,
                // so drop tracking entries whose files no longer exist instead of
                // letting the set grow unbounded for the editor session.
                if (_processedCommandFiles.Count > 0)
                {
                    _processedCommandFiles.IntersectWith(present);
                }

                // Process in submission order (creation time), not the
                // unspecified order Directory.GetFiles returns, so ordered
                // sequences (e.g. add-component then set-component-data) run FIFO.
                var commandFiles = present
                    .Where(f => !_processedCommandFiles.Contains(f))
                    .OrderBy(GetCommandFileOrderKey)
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

        private static DateTime GetCommandFileOrderKey(string path)
        {
            try { return File.GetCreationTimeUtc(path); }
            catch { return DateTime.UtcNow; }
        }

        private void ProcessCommandFile(string commandFilePath)
        {
            string commandId = null;
            string commandType = null;
            string fileBaseName = Path.GetFileName(commandFilePath);

            try
            {
                if (!TryReadCommandJson(commandFilePath, out var commandJson, out var readDiag))
                {
                    TryExtractMetadataFromFilename(fileBaseName, out commandId, out commandType);
                    var reason = $"Failed to read command file after {READ_MAX_ATTEMPTS} attempts. Details: {readDiag}";
                    WriteDiagnostic("read-failed", reason, commandFilePath, null);
                    WriteResponse(BridgeResponse.Error(
                        string.IsNullOrEmpty(commandId) ? $"filename-{fileBaseName}" : commandId,
                        string.IsNullOrEmpty(commandType) ? "unknown" : commandType, reason));
                    SafeDelete(commandFilePath);
                    return;
                }
                var command = JsonUtility.FromJson<BridgeCommand>(commandJson);
                commandId = command.commandId;
                commandType = command.commandType;

                if (string.IsNullOrEmpty(commandId) || string.IsNullOrEmpty(commandType))
                {
                    TryExtractMetadataFromFilename(fileBaseName, out var fallbackId, out var fallbackType);
                    var parseMsg = $"Invalid or incomplete command JSON. Parsed commandId='{commandId ?? "<null>"}', " +
                        $"commandType='{commandType ?? "<null>"}'.";
                    WriteDiagnostic("json-invalid", parseMsg, commandFilePath, null);
                    WriteResponse(BridgeResponse.Error(
                        string.IsNullOrEmpty(commandId) ? (fallbackId ?? $"filename-{fileBaseName}") : commandId,
                        string.IsNullOrEmpty(commandType) ? (fallbackType ?? "unknown") : commandType, parseMsg));
                    SafeDelete(commandFilePath);
                    return;
                }

                BridgeLogger.LogDebug($"Processing command: {commandType} (ID: {commandId})");

                if (BridgeOperationLedger.IsTerminalWithResponse(commandId))
                {
                    SafeDelete(commandFilePath);
                    BridgeLogger.LogDebug($"Skipped terminal command file: {commandId}");
                    return;
                }

                if (!_commandHandlers.TryGetValue(commandType, out var handler))
                {
                    WriteDiagnostic("unknown-command", $"No handler for '{commandType}'", commandFilePath, null);
                    WriteResponse(BridgeResponse.Error(commandId, commandType, $"Unknown command type: {commandType}"));
                    SafeDelete(commandFilePath);
                    return;
                }

                TryMarkAccepted(command, commandFilePath);
                var response = handler.Execute(command);
                WriteResponse(response);
                HeartbeatGenerator.IncrementCommandCount();
                SafeDelete(commandFilePath);
                BridgeLogger.LogDebug($"Completed command: {commandType} (ID: {commandId})");
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error executing command: {ex}");
                WriteDiagnostic("execute-exception", "Unhandled exception", commandFilePath, ex);
                TryExtractMetadataFromFilename(fileBaseName, out var fbId, out var fbType);
                WriteResponse(BridgeResponse.Error(
                    commandId ?? fbId ?? $"filename-{fileBaseName}",
                    commandType ?? fbType ?? "unknown", ex.ToString()));
                SafeDelete(commandFilePath);
            }
        }

        private void TryMarkAccepted(BridgeCommand command, string commandFilePath)
        {
            try
            {
                BridgeOperationLedger.MarkAccepted(command, commandFilePath);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError(
                    $"Operation ledger accepted-state update failed for command {command.commandId}: {ex}");
                WriteDiagnostic("ledger-accepted-failed",
                    "Operation ledger accepted-state update failed", commandFilePath, ex);
            }
        }

        #endregion

        #region File I/O Helpers

        private bool TryReadCommandJson(string path, out string json, out string diagnosticSummary)
        {
            json = null;
            diagnosticSummary = null;
            int attempts = 0, missingCount = 0, ioExceptions = 0, emptyReads = 0;

            while (attempts < READ_MAX_ATTEMPTS)
            {
                attempts++;
                try
                {
                    if (!File.Exists(path)) { missingCount++; Thread.Sleep(READ_RETRY_DELAY_MS); continue; }
                    if (!IsFileStable(path)) { Thread.Sleep(READ_RETRY_DELAY_MS); continue; }
                    if (TryReadAllTextShared(path, out json) && !string.IsNullOrWhiteSpace(json))
                    {
                        diagnosticSummary = "ok";
                        return true;
                    }
                    emptyReads++;
                    Thread.Sleep(READ_RETRY_DELAY_MS);
                }
                catch (IOException) { ioExceptions++; Thread.Sleep(READ_RETRY_DELAY_MS); }
                catch (UnauthorizedAccessException) { ioExceptions++; Thread.Sleep(READ_RETRY_DELAY_MS); }
            }

            diagnosticSummary = $"attempts={attempts}; missing={missingCount}; io={ioExceptions}; empty={emptyReads}";
            return false;
        }

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
            catch { return false; }
        }

        private bool TryReadAllTextShared(string path, out string content)
        {
            content = null;
            try
            {
                using var fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
                using var reader = new StreamReader(fs);
                content = reader.ReadToEnd();
                return true;
            }
            catch { return false; }
        }

        private void TryExtractMetadataFromFilename(
            string fileName, out string commandId, out string commandType)
        {
            commandId = null;
            commandType = null;
            try
            {
                var baseName = Path.GetFileNameWithoutExtension(fileName);
                var match = Regex.Match(baseName,
                    "^(?<id>[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})-(?<type>.+)$");
                if (match.Success)
                {
                    commandId = match.Groups["id"].Value;
                    commandType = match.Groups["type"].Value;
                }
            }
            catch (Exception ex)
            {
                WriteDiagnostic("filename-parse-failed", $"Parse failed for '{fileName}'", fileName, ex);
            }
        }

        private void SafeDelete(string path)
        {
            try { if (File.Exists(path)) File.Delete(path); }
            catch (Exception ex)
            {
                WriteDiagnostic("delete-failed", $"Failed to delete '{path}'", path, ex);
            }
        }

        #endregion

        #region Response and Diagnostics

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
                RotateDiagnosticsLogIfNeeded();
                File.AppendAllText(DIAGNOSTICS_LOG, JsonUtility.ToJson(evt, false) + Environment.NewLine);
            }
            catch { }
        }

        private const long DIAGNOSTICS_LOG_MAX_BYTES = 5 * 1024 * 1024; // 5 MB

        private static void RotateDiagnosticsLogIfNeeded()
        {
            try
            {
                var info = new FileInfo(DIAGNOSTICS_LOG);
                if (!info.Exists || info.Length < DIAGNOSTICS_LOG_MAX_BYTES)
                    return;
                var rotated = DIAGNOSTICS_LOG + ".1";
                if (File.Exists(rotated))
                    File.Delete(rotated);
                File.Move(DIAGNOSTICS_LOG, rotated);
            }
            catch { }
        }

        private void WriteResponse(BridgeResponse response)
        {
            WriteResponseStatic(response);
        }

        public static void WriteResponseStatic(BridgeResponse response)
        {
            var filePath = Path.Combine(RESPONSES_PATH,
                $"{response.commandId}-{response.commandType}.json");
            try
            {
                var responseJson = JsonUtility.ToJson(response, true);
                BridgeOperationLedger.WriteAtomic(filePath, responseJson);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error writing response file '{filePath}': {ex}");
                return;
            }

            try
            {
                BridgeOperationLedger.MarkResponse(response);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError(
                    $"Operation ledger terminal-state update failed for command {response.commandId}: {ex}");
            }

            BridgeLogger.LogDebug($"Wrote response: {Path.GetFileName(filePath)}");
        }

        #endregion
    }
}
