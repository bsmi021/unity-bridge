using System;
using System.Collections.Generic;
using System.Reflection;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for reading Unity Console logs.
    ///
    /// PURPOSE:
    /// Accesses the Unity Editor Console to retrieve error, warning, and log messages.
    /// This enables Claude Code to programmatically inspect console output for debugging
    /// and validation purposes without manual inspection.
    ///
    /// USE CASES:
    /// - Read compilation errors after code changes
    /// - Check for runtime errors during PlayMode tests
    /// - Monitor warning messages for code quality issues
    /// - Capture logs for automated validation workflows
    /// - Debug issues by programmatically inspecting console state
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "read-console",
    ///   "timestamp": "2025-10-06T18:00:00Z",
    ///   "parametersJson": "{\"logTypes\":[\"Error\",\"Warning\"],\"maxEntries\":50,\"clearAfterRead\":false}"
    /// }
    ///
    /// TECHNICAL DETAILS:
    /// Uses reflection to access Unity's internal LogEntries API since it's not publicly exposed.
    /// LogEntries.GetEntryInternal() provides access to individual console entries with their
    /// message, stack trace, mode (error/warning/log), and other metadata.
    ///
    /// USAGE EXAMPLES:
    ///
    /// 1. Read all console errors:
    ///    Parameters: { "logTypes": ["Error"], "maxEntries": 100 }
    ///
    /// 2. Read last 50 entries of all types:
    ///    Parameters: { "maxEntries": 50 }
    ///
    /// 3. Read and clear console:
    ///    Parameters: { "clearAfterRead": true }
    /// </summary>
    public class ReadConsoleCommandHandler : ICommandHandler
    {
        public string CommandType => "read-console";

        // Reflection types and methods for accessing Unity's internal LogEntries API
        private static Type _logEntriesType;
        private static Type _logEntryType;
        private static MethodInfo _startGettingEntriesMethod;
        private static MethodInfo _getEntryInternalMethod;
        private static MethodInfo _endGettingEntriesMethod;
        private static MethodInfo _getCountMethod;
        private static MethodInfo _clearMethod;

        // LogEntry field accessors
        private static FieldInfo _messageField;
        private static FieldInfo _fileField;
        private static FieldInfo _lineField;
        private static FieldInfo _modeField;
        private static FieldInfo _instanceIDField;
        private static FieldInfo _identifierField;

        // Log mode constants (from Unity's internal ConsoleFlags enum)
        private const int LOG_MODE_ERROR = 1 << 0;        // Error flag
        private const int LOG_MODE_ASSERT = 1 << 1;       // Assert flag
        private const int LOG_MODE_LOG = 1 << 2;          // Log flag
        private const int LOG_MODE_FATAL = 1 << 4;        // Fatal error flag
        private const int LOG_MODE_DONT_PREPROCESS = 1 << 5; // Don't preprocess flag
        private const int LOG_MODE_ASSET_IMPORT_ERROR = 1 << 6; // Asset import error flag
        private const int LOG_MODE_ASSET_IMPORT_WARNING = 1 << 7; // Asset import warning flag
        private const int LOG_MODE_SCRIPT_COMPILE_ERROR = 1 << 8; // Script compile error flag
        private const int LOG_MODE_SCRIPT_COMPILE_WARNING = 1 << 9; // Script compile warning flag
        private const int LOG_MODE_STICKY_ERROR = 1 << 10; // Sticky error flag
        private const int LOG_MODE_MAY_IGNORE_LINE_NUMBER = 1 << 11; // May ignore line number flag
        private const int LOG_MODE_REPORT_BUG = 1 << 12;  // Report bug flag
        private const int LOG_MODE_DISPLAY_FRAME_COUNT = 1 << 13; // Display frame count flag
        private const int LOG_MODE_SUPPRESS_STACK_TRACE = 1 << 14; // Suppress stack trace flag

        /// <summary>
        /// Static constructor to initialize reflection types and methods.
        /// This setup happens once when the class is first loaded.
        /// </summary>
        static ReadConsoleCommandHandler()
        {
            try
            {
                // Get LogEntries type from UnityEditor assembly
                _logEntriesType = Type.GetType("UnityEditor.LogEntries,UnityEditor");
                if (_logEntriesType == null)
                {
                    BridgeLogger.LogError("Failed to find LogEntries type");
                    return;
                }

                // Get LogEntry type from UnityEditor assembly
                _logEntryType = Type.GetType("UnityEditor.LogEntry,UnityEditor");
                if (_logEntryType == null)
                {
                    BridgeLogger.LogError("Failed to find LogEntry type");
                    return;
                }

                // Get methods from LogEntries API
                _startGettingEntriesMethod = _logEntriesType.GetMethod("StartGettingEntries", BindingFlags.Static | BindingFlags.Public);
                _getEntryInternalMethod = _logEntriesType.GetMethod("GetEntryInternal", BindingFlags.Static | BindingFlags.Public);
                _endGettingEntriesMethod = _logEntriesType.GetMethod("EndGettingEntries", BindingFlags.Static | BindingFlags.Public);
                _getCountMethod = _logEntriesType.GetMethod("GetCount", BindingFlags.Static | BindingFlags.Public);
                _clearMethod = _logEntriesType.GetMethod("Clear", BindingFlags.Static | BindingFlags.Public);

                // Get fields from LogEntry structure
                _messageField = _logEntryType.GetField("message");
                _fileField = _logEntryType.GetField("file");
                _lineField = _logEntryType.GetField("line");
                _modeField = _logEntryType.GetField("mode");
                _instanceIDField = _logEntryType.GetField("instanceID");
                _identifierField = _logEntryType.GetField("identifier");

                // Validate all reflection members were found
                if (_startGettingEntriesMethod == null || _getEntryInternalMethod == null ||
                    _endGettingEntriesMethod == null || _getCountMethod == null || _clearMethod == null)
                {
                    BridgeLogger.LogError("Failed to find one or more LogEntries methods");
                    return;
                }

                if (_messageField == null || _modeField == null)
                {
                    BridgeLogger.LogError("Failed to find required LogEntry fields");
                    return;
                }

                BridgeLogger.LogInfo("Successfully initialized reflection for Unity Console access");
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Reflection initialization failed: {ex}");
            }
        }

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                // Validate reflection was initialized successfully
                if (_logEntriesType == null || _logEntryType == null)
                {
                    return BridgeResponse.Error(
                        command.commandId,
                        command.commandType,
                        "Failed to initialize reflection for Unity Console access. LogEntries API not available."
                    );
                }

                // Parse parameters
                var parameters = JsonUtility.FromJson<ReadConsoleParams>(command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new ReadConsoleParams();

                // Normalize log types to handle case variations
                var normalizedLogTypes = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                foreach (var logType in parameters.logTypes)
                {
                    normalizedLogTypes.Add(logType);
                }

                Regex filterRegex = null;
                if (!string.IsNullOrEmpty(parameters.filterPattern))
                {
                    try
                    {
                        filterRegex = new Regex(
                            parameters.filterPattern,
                            RegexOptions.None,
                            TimeSpan.FromSeconds(1));
                    }
                    catch (ArgumentException ex)
                    {
                        return BridgeResponse.Error(command.commandId, command.commandType,
                            $"Invalid filterPattern regex: {ex.Message}");
                    }
                }

                BridgeLogger.LogDebug($"Reading console: logTypes={string.Join(",", parameters.logTypes)}, maxEntries={parameters.maxEntries}, clearAfterRead={parameters.clearAfterRead}, includeStackTrace={parameters.includeStackTrace}, maxStackTraceLines={parameters.maxStackTraceLines}, filterPattern={parameters.filterPattern}");

                // Read console entries with stack trace control
                var result = ReadConsoleEntries(
                    normalizedLogTypes,
                    parameters.maxEntries,
                    parameters.includeStackTrace,
                    parameters.maxStackTraceLines,
                    parameters.maxMessageLength,
                    filterRegex
                );

                // Clear console if requested
                if (parameters.clearAfterRead)
                {
                    ClearConsole();
                    BridgeLogger.LogInfo("Console cleared after read");
                }

                var resultJson = JsonUtility.ToJson(result);
                BridgeLogger.LogInfo($"Read {result.entries.Count} console entries (total count: {result.totalCount})");

                return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        /// <summary>
        /// Reads console entries using Unity's internal LogEntries API via reflection.
        /// Filters by log type and respects maxEntries limit.
        /// Applies stack trace truncation based on parameters.
        /// </summary>
        private ReadConsoleResult ReadConsoleEntries(
            HashSet<string> logTypes,
            int maxEntries,
            bool includeStackTrace,
            int maxStackTraceLines,
            int maxMessageLength,
            Regex filterRegex)
        {
            var result = new ReadConsoleResult();

            try
            {
                // Get total count of console entries
                int totalCount = (int)_getCountMethod.Invoke(null, null);
                result.totalCount = totalCount;

                if (totalCount == 0)
                {
                    BridgeLogger.LogDebug("Console is empty");
                    return result;
                }

                // Start getting entries (required before reading individual entries)
                _startGettingEntriesMethod.Invoke(null, null);

                // Create LogEntry instance for reading data
                object logEntry = Activator.CreateInstance(_logEntryType);

                // Read entries (newest first by default in Unity console)
                int entriesRead = 0;
                for (int i = 0; i < totalCount && entriesRead < maxEntries; i++)
                {
                    // GetEntryInternal(int row, LogEntry outputEntry)
                    bool success = (bool)_getEntryInternalMethod.Invoke(null, new object[] { i, logEntry });

                    if (!success)
                        continue;

                    // Extract log entry data using reflection
                    string rawMessage = _messageField.GetValue(logEntry) as string ?? "";
                    int mode = (int)_modeField.GetValue(logEntry);

                    // Determine log type from mode flags
                    string logType = DetermineLogType(mode);

                    // Filter by log type if specified
                    if (logTypes.Count > 0 && !logTypes.Contains(logType))
                        continue;

                    // Get additional info (file/line for stack trace)
                    string file = _fileField?.GetValue(logEntry) as string ?? "";
                    int line = _lineField != null ? (int)_lineField.GetValue(logEntry) : 0;

                    // Parse and truncate message/stack trace
                    var (processedMessage, stackTrace) = ProcessMessageAndStackTrace(
                        rawMessage,
                        file,
                        line,
                        includeStackTrace,
                        maxStackTraceLines,
                        maxMessageLength
                    );

                    if (filterRegex != null && !filterRegex.IsMatch(processedMessage))
                        continue;

                    // Create console entry
                    var entry = new ConsoleEntry
                    {
                        logType = logType,
                        message = processedMessage,
                        stackTrace = stackTrace,
                        timestamp = DateTime.UtcNow.ToString("o")
                    };

                    result.entries.Add(entry);
                    entriesRead++;
                }

                // End getting entries (cleanup)
                _endGettingEntriesMethod.Invoke(null, null);

                BridgeLogger.LogDebug($"Successfully read {entriesRead} entries from console (filtered from {totalCount} total)");
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error reading console entries: {ex}");
                throw;
            }

            return result;
        }

        /// <summary>
        /// Processes a raw Unity log message to separate the main message from the stack trace,
        /// applying truncation based on the provided parameters.
        ///
        /// Unity log messages typically contain the error/warning message followed by a stack trace.
        /// Stack trace lines usually start with whitespace and contain method signatures like:
        /// "  at MyClass.MyMethod () [0x00000] in /path/file.cs:42"
        /// or Unity format: "UnityEngine.Debug:Log (object)"
        /// </summary>
        private (string message, string stackTrace) ProcessMessageAndStackTrace(
            string rawMessage,
            string file,
            int line,
            bool includeStackTrace,
            int maxStackTraceLines,
            int maxMessageLength)
        {
            if (string.IsNullOrEmpty(rawMessage))
            {
                return ("", "");
            }

            // Split message into lines
            var lines = rawMessage.Split(new[] { '\n', '\r' }, StringSplitOptions.RemoveEmptyEntries);

            if (lines.Length == 0)
            {
                return ("", "");
            }

            // Find where the stack trace begins
            var messageLines = new List<string>();
            var stackTraceLines = new List<string>();
            bool inStackTrace = false;

            foreach (var rawLine in lines)
            {
                string trimmedLine = rawLine.TrimStart();

                // Detect stack trace patterns:
                // - Lines starting with "at " (standard .NET stack trace)
                // - Lines containing " (at " (Unity format with file path)
                // - Lines matching "Namespace.Class:Method" pattern (Unity debug format)
                // - Lines starting with "UnityEngine." or "System." (common stack trace prefixes)
                bool isStackTraceLine = IsStackTraceLine(trimmedLine);

                if (isStackTraceLine && !inStackTrace)
                {
                    inStackTrace = true;
                }

                if (inStackTrace)
                {
                    stackTraceLines.Add(rawLine);
                }
                else
                {
                    messageLines.Add(rawLine);
                }
            }

            // Build the processed message
            string processedMessage = string.Join("\n", messageLines);

            // Apply message length limit
            if (maxMessageLength > 0 && processedMessage.Length > maxMessageLength)
            {
                processedMessage = processedMessage.Substring(0, maxMessageLength) + "...";
            }

            // Build the stack trace
            string stackTrace = "";

            if (includeStackTrace && maxStackTraceLines != -1)
            {
                // If we have extracted stack trace lines from the message
                if (stackTraceLines.Count > 0)
                {
                    // Apply line limit (0 = unlimited)
                    var limitedLines = maxStackTraceLines > 0 && stackTraceLines.Count > maxStackTraceLines
                        ? stackTraceLines.GetRange(0, maxStackTraceLines)
                        : stackTraceLines;

                    stackTrace = string.Join("\n", limitedLines);

                    // Add truncation indicator if we trimmed lines
                    if (maxStackTraceLines > 0 && stackTraceLines.Count > maxStackTraceLines)
                    {
                        stackTrace += $"\n  ... ({stackTraceLines.Count - maxStackTraceLines} more lines)";
                    }
                }
                else if (!string.IsNullOrEmpty(file))
                {
                    // Fallback to file:line info if no stack trace was extracted
                    stackTrace = $"{file}:{line}";
                }
            }

            return (processedMessage, stackTrace);
        }

        /// <summary>
        /// Determines if a line is part of a stack trace based on common patterns.
        /// </summary>
        private bool IsStackTraceLine(string trimmedLine)
        {
            if (string.IsNullOrWhiteSpace(trimmedLine))
                return false;

            // Standard .NET stack trace format
            if (trimmedLine.StartsWith("at "))
                return true;

            // Unity format with file reference
            if (trimmedLine.Contains(" (at ") && trimmedLine.Contains(":"))
                return true;

            // Unity debug log format: "Namespace.Class:Method (args)"
            if (trimmedLine.Contains(":") && trimmedLine.Contains("(") &&
                !trimmedLine.StartsWith("//") && !trimmedLine.Contains("="))
            {
                // Check for common Unity/System prefixes
                if (trimmedLine.StartsWith("UnityEngine.") ||
                    trimmedLine.StartsWith("UnityEditor.") ||
                    trimmedLine.StartsWith("System.") ||
                    System.Text.RegularExpressions.Regex.IsMatch(trimmedLine, @"^[A-Z][a-zA-Z0-9_]*(\.[A-Z][a-zA-Z0-9_]*)*:[A-Z]"))
                {
                    return true;
                }
            }

            // Rethrow marker
            if (trimmedLine.StartsWith("Rethrow as "))
                return true;

            return false;
        }

        /// <summary>
        /// Determines the log type (Error, Warning, or Log) from Unity's console mode flags.
        /// Unity uses bitflags to represent different log types and metadata.
        /// </summary>
        private string DetermineLogType(int mode)
        {
            // Check error flags first (highest priority)
            if ((mode & LOG_MODE_ERROR) != 0 ||
                (mode & LOG_MODE_FATAL) != 0 ||
                (mode & LOG_MODE_ASSERT) != 0 ||
                (mode & LOG_MODE_SCRIPT_COMPILE_ERROR) != 0 ||
                (mode & LOG_MODE_ASSET_IMPORT_ERROR) != 0)
            {
                return "Error";
            }

            // Check warning flags
            if ((mode & LOG_MODE_SCRIPT_COMPILE_WARNING) != 0 ||
                (mode & LOG_MODE_ASSET_IMPORT_WARNING) != 0)
            {
                return "Warning";
            }

            // Check log flag
            if ((mode & LOG_MODE_LOG) != 0)
            {
                return "Log";
            }

            // Default to Log if no specific flag is set
            return "Log";
        }

        /// <summary>
        /// Clears all entries from the Unity Console.
        /// </summary>
        private void ClearConsole()
        {
            try
            {
                _clearMethod.Invoke(null, null);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error clearing console: {ex}");
                throw;
            }
        }
    }
}
