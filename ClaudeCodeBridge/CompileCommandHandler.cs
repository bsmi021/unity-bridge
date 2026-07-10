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

        // Non-blocking wait state. Handlers run synchronously from
        // EditorApplication.update, so we must NOT block the main thread while
        // EditorApplication.isCompiling — Unity drives compilation on that same
        // thread, so a blocking wait freezes the whole editor and the flag never
        // clears. Instead we return "running" and finish from a per-frame poll.
        private static readonly Dictionary<string, CompileWaitContext> _pendingCompiles =
            new Dictionary<string, CompileWaitContext>();
        private static bool _pollRegistered = false;

        // Grace period for compilation to *begin* after a refresh before we
        // conclude there was nothing to compile and complete immediately.
        private const double CompileStartGraceSeconds = 1.0;

        // SessionState markers so a compile that triggers a domain reload (which
        // wipes the in-memory poll) is still completed after the reload.
        internal const string PendingCommandIdKey = "UnityBridge.Compile.CommandId";
        private const string PendingStartTicksKey = "UnityBridge.Compile.StartTicks";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<CompileParams>(command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new CompileParams();

                BridgeLogger.LogDebug(
                    $"Triggering compilation (waitForCompletion={parameters.waitForCompletion}, " +
                    $"timeout={parameters.timeout}s)");
                var startTime = DateTime.UtcNow;
                if (!parameters.waitForCompletion)
                    return TriggerWithoutWait(command);
                return TriggerAndWait(command, parameters.timeout, startTime);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private static BridgeResponse TriggerWithoutWait(BridgeCommand command)
        {
            AssetDatabase.Refresh(ImportAssetOptions.ForceUpdate);
            BridgeLogger.LogInfo("Compilation triggered, returning immediately");
            var result = new CompilationResult
            {
                success = true,
                triggered = true,
                message = "Compilation triggered"
            };
            return BridgeResponse.Success(
                command.commandId, command.commandType, JsonUtility.ToJson(result));
        }

        private static BridgeResponse TriggerAndWait(
            BridgeCommand command, int timeoutSeconds, DateTime startTime)
        {
            _pendingCompiles[command.commandId] = new CompileWaitContext
            {
                CommandId = command.commandId,
                CommandType = command.commandType,
                StartTime = startTime,
                TimeoutSeconds = timeoutSeconds,
                CompilationStarted = false,
            };
            SessionState.SetString(PendingCommandIdKey, command.commandId);
            SessionState.SetString(PendingStartTicksKey, startTime.Ticks.ToString());
            EnsurePollRegistered();

            try
            {
                AssetDatabase.Refresh(ImportAssetOptions.ForceUpdate);
            }
            catch
            {
                RemovePendingWait(command.commandId);
                throw;
            }

            return BridgeResponse.Running(
                command.commandId,
                command.commandType,
                $"{{\"message\":\"Compilation requested at {startTime:O}\"}}");
        }

        private static void RemovePendingWait(string commandId)
        {
            _pendingCompiles.Remove(commandId);
            ClearPendingMarker(commandId);
            if (_pendingCompiles.Count == 0 && _pollRegistered)
            {
                EditorApplication.update -= PollPendingCompiles;
                _pollRegistered = false;
            }
        }

        private static void EnsurePollRegistered()
        {
            if (_pollRegistered)
                return;
            EditorApplication.update += PollPendingCompiles;
            _pollRegistered = true;
        }

        /// <summary>
        /// Per-frame, non-blocking check of in-flight compile waits. Writes the
        /// terminal response when compilation finishes (or never started) or on
        /// timeout, then unregisters itself once no waits remain.
        /// </summary>
        private static void PollPendingCompiles()
        {
            if (_pendingCompiles.Count == 0)
            {
                EditorApplication.update -= PollPendingCompiles;
                _pollRegistered = false;
                return;
            }

            var compiling = EditorApplication.isCompiling;
            var completed = new List<string>();

            foreach (var kvp in _pendingCompiles)
            {
                var ctx = kvp.Value;
                var elapsed = (DateTime.UtcNow - ctx.StartTime).TotalSeconds;

                if (compiling)
                {
                    ctx.CompilationStarted = true;
                }

                if (elapsed > ctx.TimeoutSeconds)
                {
                    WriteTimeout(ctx, elapsed);
                    completed.Add(kvp.Key);
                    continue;
                }

                // Done when compilation has finished, or when it never started
                // within the grace window (nothing to compile).
                if (!compiling && (ctx.CompilationStarted || elapsed >= CompileStartGraceSeconds))
                {
                    WriteCompleted(ctx, elapsed);
                    completed.Add(kvp.Key);
                }
            }

            foreach (var id in completed)
            {
                _pendingCompiles.Remove(id);
            }
        }

        private static void WriteCompleted(CompileWaitContext ctx, double elapsedSeconds)
        {
            var messages = GetCompilationMessages();
            var result = CreateSuccessResult(messages, elapsedSeconds);
            BridgeLogger.LogInfo($"Compilation complete in {result.durationSeconds:F2}s " +
                     $"(errors={result.errorCount}, warnings={result.warningCount})");
            ClaudeUnityBridge.WriteResponseStatic(
                BridgeResponse.Success(ctx.CommandId, ctx.CommandType, JsonUtility.ToJson(result)));
            ClearPendingMarker(ctx.CommandId);
        }

        private static void WriteTimeout(CompileWaitContext ctx, double elapsedSeconds)
        {
            BridgeLogger.LogError($"Compilation timeout after {ctx.TimeoutSeconds}s");
            var timeoutResult = new CompilationResult
            {
                success = false,
                hasErrors = true,
                errorCount = 1,
                durationSeconds = elapsedSeconds,
                messages = new List<CompilationMessage>
                {
                    new CompilationMessage
                    {
                        type = "error",
                        message = $"Compilation timeout after {ctx.TimeoutSeconds} seconds"
                    }
                }
            };
            ClaudeUnityBridge.WriteResponseStatic(
                BridgeResponse.Success(ctx.CommandId, ctx.CommandType, JsonUtility.ToJson(timeoutResult)));
            ClearPendingMarker(ctx.CommandId);
        }

        private static void ClearPendingMarker(string commandId)
        {
            if (SessionState.GetString(PendingCommandIdKey, "") == commandId)
            {
                SessionState.EraseString(PendingCommandIdKey);
                SessionState.EraseString(PendingStartTicksKey);
            }
        }

        /// <summary>
        /// Called once on domain load (before ledger reload recovery). If a
        /// compile was in flight when the reload occurred, the reload itself
        /// means compilation finished, so collect results and write the terminal
        /// response now. No-op if no compile was pending.
        /// </summary>
        public static void CompletePendingCompileAfterReload()
        {
            var commandId = SessionState.GetString(PendingCommandIdKey, "");
            if (string.IsNullOrEmpty(commandId))
                return;

            double elapsed = 0.0;
            if (long.TryParse(SessionState.GetString(PendingStartTicksKey, ""), out var ticks))
                elapsed = (DateTime.UtcNow - new DateTime(ticks, DateTimeKind.Utc)).TotalSeconds;

            try
            {
                var messages = GetCompilationMessages();
                var result = CreateSuccessResult(messages, elapsed);
                BridgeLogger.LogInfo(
                    $"Compilation completed across reload (errors={result.errorCount}, warnings={result.warningCount})");
                ClaudeUnityBridge.WriteResponseStatic(
                    BridgeResponse.Success(commandId, "compile", JsonUtility.ToJson(result)));
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error completing compile after reload: {ex}");
                ClaudeUnityBridge.WriteResponseStatic(
                    BridgeResponse.Error(commandId, "compile", ex.ToString()));
            }
            finally
            {
                SessionState.EraseString(PendingCommandIdKey);
                SessionState.EraseString(PendingStartTicksKey);
            }
        }

        /// <summary>
        /// Creates a successful result from compilation messages.
        /// </summary>
        private static CompilationResult CreateSuccessResult(List<CompilationMessage> messages, double elapsedSeconds)
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
                durationSeconds = elapsedSeconds,
                messages = messages
            };
        }

        /// <summary>
        /// Retrieves compilation messages from Unity's LogEntries using reflection.
        /// This accesses the editor console logs that were generated during compilation.
        /// </summary>
        private static List<CompilationMessage> GetCompilationMessages()
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
        private static CompilationMessage ExtractLogEntry(Type logEntriesType, MethodInfo getEntryMethod, int index)
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
        private static string DetermineMessageType(object mode)
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

}
