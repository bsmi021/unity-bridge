using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for triggering and monitoring C# script compilation in Unity.
    ///
    /// PURPOSE:
    /// Allows Claude Code to trigger script compilation and optionally wait for completion,
    /// gathering compilation errors and warnings from the editor logs. This enables automation
    /// of build validation workflows without requiring manual editor interaction.
    ///
    /// USE CASES:
    /// - Verify scripts compile after code generation or modifications
    /// - Collect compilation errors for CI/CD pipelines
    /// - Monitor compilation health during automated testing
    /// - Ensure asset changes don't break existing code
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "compile",
    ///   "timestamp": "2025-10-07T18:00:00Z",
    ///   "parametersJson": "{\"waitForCompletion\":true,\"timeout\":120}"
    /// }
    ///
    /// RESPONSE JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "compile",
    ///   "status": "success",
    ///   "timestamp": "2025-10-07T18:00:05Z",
    ///   "dataJson": "{
    ///     \"success\": true,
    ///     \"hasErrors\": false,
    ///     \"hasWarnings\": true,
    ///     \"errorCount\": 0,
    ///     \"warningCount\": 1,
    ///     \"durationSeconds\": 4.5,
    ///     \"messages\": [
    ///       {
    ///         \"type\": \"warning\",
    ///         \"message\": \"Function not used\",
    ///         \"file\": \"Assets/Scripts/MyScript.cs\",
    ///         \"line\": 42,
    ///         \"column\": 5
    ///       }
    ///     ]
    ///   }"
    /// }
    ///
    /// TECHNICAL DETAILS:
    /// Uses EditorApplication.isCompiling to monitor compilation state. For waitForCompletion=true,
    /// polls the compilation flag with a small delay (100ms) to avoid busy-waiting. After compilation
    /// completes, uses reflection to access LogEntries to retrieve compilation-related messages.
    /// This provides a complete picture of compilation health without blocking the entire editor.
    ///
    /// PARAMETERS:
    /// - waitForCompletion (bool, default true): If true, waits for compilation to finish before returning.
    ///   If false, triggers compilation and returns immediately.
    /// - timeout (int, default 120): Maximum seconds to wait for compilation (only used if waitForCompletion=true).
    ///
    /// USAGE EXAMPLES:
    ///
    /// 1. Trigger compilation and wait for results:
    ///    & ".claude\unity\send-command.ps1" -CommandType "compile" -Parameters @{waitForCompletion=$true}
    ///
    /// 2. Trigger compilation without waiting:
    ///    & ".claude\unity\send-command.ps1" -CommandType "compile" -Parameters @{waitForCompletion=$false}
    ///
    /// 3. Check for compilation errors with short timeout:
    ///    $result = & ".claude\unity\send-command.ps1" -CommandType "compile" -Parameters @{waitForCompletion=$true;timeout=30}
    ///    if ($result.hasErrors) { Write-Error "Compilation failed!" }
    /// </summary>
    public class CompileCommandHandler : ICommandHandler
    {
        public string CommandType => "compile";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                // Parse parameters
                var parameters = JsonUtility.FromJson<CompileParams>(command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new CompileParams();

                BridgeLogger.LogDebug($"Triggering compilation (waitForCompletion={parameters.waitForCompletion}, timeout={parameters.timeout}s)");

                // Record start time
                var startTime = DateTime.UtcNow;

                // Trigger compilation
                AssetDatabase.Refresh(ImportAssetOptions.ForceUpdate);

                // If not waiting for completion, return immediately
                if (!parameters.waitForCompletion)
                {
                    BridgeLogger.LogInfo("Compilation triggered, returning immediately");
                    var quickResult = new CompilationResult
                    {
                        success = true,
                        triggered = true,
                        message = "Compilation triggered"
                    };
                    return BridgeResponse.Success(command.commandId, command.commandType, JsonUtility.ToJson(quickResult));
                }

                // Wait for compilation to complete
                return HandleWaitForCompletion(command, parameters, startTime);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        /// <summary>
        /// Waits for compilation to complete and collects results.
        /// </summary>
        private BridgeResponse HandleWaitForCompletion(BridgeCommand command, CompileParams parameters, DateTime startTime)
        {
            var sw = System.Diagnostics.Stopwatch.StartNew();
            var timeoutMs = parameters.timeout * 1000;

            // Wait for compilation to finish
            if (!WaitForCompilationComplete(timeoutMs))
            {
                sw.Stop();
                return CreateTimeoutResponse(command, parameters, sw);
            }

            sw.Stop();

            // Collect and analyze results
            var messages = GetCompilationMessages();
            var result = CreateSuccessResult(messages, sw);

            BridgeLogger.LogInfo($"Compilation complete in {result.durationSeconds:F2}s " +
                     $"(errors={result.errorCount}, warnings={result.warningCount})");

            return BridgeResponse.Success(command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        /// <summary>
        /// Waits for compilation to finish, respecting timeout.
        /// Returns true if compilation finished, false if timeout occurred.
        /// </summary>
        private bool WaitForCompilationComplete(int timeoutMs)
        {
            var sw = System.Diagnostics.Stopwatch.StartNew();

            while (EditorApplication.isCompiling)
            {
                if (sw.ElapsedMilliseconds > timeoutMs)
                {
                    BridgeLogger.LogError($"Compilation timeout after {timeoutMs}ms");
                    return false;
                }

                System.Threading.Thread.Sleep(100);
            }

            return true;
        }

        /// <summary>
        /// Creates a timeout result response.
        /// </summary>
        private BridgeResponse CreateTimeoutResponse(BridgeCommand command, CompileParams parameters, System.Diagnostics.Stopwatch sw)
        {
            var timeoutResult = new CompilationResult
            {
                success = false,
                hasErrors = true,
                errorCount = 1,
                durationSeconds = sw.Elapsed.TotalSeconds,
                messages = new List<CompilationMessage>
                {
                    new CompilationMessage
                    {
                        type = "error",
                        message = $"Compilation timeout after {parameters.timeout} seconds"
                    }
                }
            };
            return BridgeResponse.Success(command.commandId, command.commandType, JsonUtility.ToJson(timeoutResult));
        }

        /// <summary>
        /// Creates a successful result from compilation messages.
        /// </summary>
        private CompilationResult CreateSuccessResult(List<CompilationMessage> messages, System.Diagnostics.Stopwatch sw)
        {
            var hasErrors = messages.Any(m => m.type == "error");
            var hasWarnings = messages.Any(m => m.type == "warning");

            return new CompilationResult
            {
                success = !hasErrors,
                hasErrors = hasErrors,
                hasWarnings = hasWarnings,
                errorCount = messages.Count(m => m.type == "error"),
                warningCount = messages.Count(m => m.type == "warning"),
                durationSeconds = sw.Elapsed.TotalSeconds,
                messages = messages
            };
        }

        /// <summary>
        /// Retrieves compilation messages from Unity's LogEntries using reflection.
        /// This accesses the editor console logs that were generated during compilation.
        /// </summary>
        private List<CompilationMessage> GetCompilationMessages()
        {
            var messages = new List<CompilationMessage>();

            try
            {
                // Access UnityEditor.Logging.LogEntries using reflection
                var logEntriesType = Type.GetType("UnityEditor.Logging.LogEntries,UnityEditor.CoreModule");
                if (logEntriesType == null)
                {
                    BridgeLogger.LogWarning("Could not find LogEntries type");
                    return messages;
                }

                // Get count of log entries
                var getCountMethod = logEntriesType.GetMethod("GetCount", BindingFlags.Static | BindingFlags.Public);
                if (getCountMethod == null)
                {
                    BridgeLogger.LogWarning("Could not find GetCount method");
                    return messages;
                }

                var countObj = getCountMethod.Invoke(null, null);
                if (countObj == null || !(countObj is int count))
                {
                    BridgeLogger.LogWarning("Could not get log entry count");
                    return messages;
                }

                // Process each log entry
                var getEntryMethod = logEntriesType.GetMethod("GetEntryInternal",
                    BindingFlags.Static | BindingFlags.Public);
                if (getEntryMethod == null)
                {
                    BridgeLogger.LogWarning("Could not find GetEntryInternal method");
                    return messages;
                }

                // Iterate through log entries
                for (int i = 0; i < count; i++)
                {
                    try
                    {
                        var logEntry = ExtractLogEntry(logEntriesType, getEntryMethod, i);
                        if (logEntry != null)
                        {
                            messages.Add(logEntry);
                        }
                    }
                    catch (Exception ex)
                    {
                        BridgeLogger.LogWarning($"Error processing log entry {i}: {ex.Message}");
                    }
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error getting compilation messages: {ex}");
            }

            return messages;
        }

        /// <summary>
        /// Extracts a single log entry using reflection.
        /// </summary>
        private CompilationMessage ExtractLogEntry(Type logEntriesType, MethodInfo getEntryMethod, int index)
        {
            // Create output parameters for GetEntryInternal
            // Signature: GetEntryInternal(int index, LogEntry& entry)
            var logEntryType = Type.GetType("UnityEditor.Logging.LogEntry,UnityEditor.CoreModule");
            if (logEntryType == null)
                return null;

            var outParam = System.Activator.CreateInstance(logEntryType);
            var parameters = new object[] { index, outParam };

            // Call the method
            getEntryMethod.Invoke(null, parameters);
            outParam = parameters[1];

            // Extract properties from the LogEntry
            var messageField = logEntryType?.GetProperty("message", BindingFlags.Instance | BindingFlags.Public);
            var fileField = logEntryType?.GetProperty("file", BindingFlags.Instance | BindingFlags.Public);
            var lineField = logEntryType?.GetProperty("line", BindingFlags.Instance | BindingFlags.Public);
            var modeField = logEntryType?.GetProperty("mode", BindingFlags.Instance | BindingFlags.Public);

            // Extract values
            var messageText = (string)messageField?.GetValue(outParam) ?? "";
            var filePath = (string)fileField?.GetValue(outParam) ?? "";
            var lineNum = (int?)lineField?.GetValue(outParam) ?? 0;
            var mode = modeField?.GetValue(outParam);

            // Determine error type from mode (0=log, 1=warning, 2=error)
            string messageType = DetermineMessageType(mode);

            // Only include errors and warnings
            if (messageType == "log")
                return null;

            return new CompilationMessage
            {
                type = messageType,
                message = messageText,
                file = filePath,
                line = lineNum,
                column = 0  // LogEntry doesn't provide column info
            };
        }

        /// <summary>
        /// Determines message type from LogEntry mode value.
        /// </summary>
        private string DetermineMessageType(object mode)
        {
            if (mode is int modeInt)
            {
                return modeInt switch
                {
                    0 => "log",
                    1 => "warning",
                    2 => "error",
                    _ => "log"
                };
            }

            return "log";
        }
    }

    /// <summary>
    /// Parameters for the compile command.
    /// </summary>
    [Serializable]
    public class CompileParams
    {
        public bool waitForCompletion = true;
        public int timeout = 120;
    }

    /// <summary>
    /// Result data for the compile command.
    /// </summary>
    [Serializable]
    public class CompilationResult
    {
        public bool success;
        public bool triggered; // Used when returning immediately
        public bool hasErrors;
        public bool hasWarnings;
        public int errorCount;
        public int warningCount;
        public double durationSeconds;
        public List<CompilationMessage> messages = new List<CompilationMessage>();
        public string message; // General message for triggered=true case
    }

    /// <summary>
    /// Represents a single compilation message (error or warning).
    /// </summary>
    [Serializable]
    public class CompilationMessage
    {
        public string type; // "error" or "warning"
        public string message;
        public string file;
        public int line;
        public int column;
    }
}
