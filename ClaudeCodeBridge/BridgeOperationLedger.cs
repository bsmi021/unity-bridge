using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Durable operation ledger for bridge command lifecycle state.
    /// One JSON file stores current state; a JSONL file records transitions.
    /// </summary>
    public static class BridgeOperationLedger
    {
        private const int SCHEMA_VERSION = 1;
        private const string StateQueued = "queued";
        private const string StateAccepted = "accepted";
        private const string StateRunning = "running";
        private const string StateRecovering = "recovering_after_reload";
        private const string StateCompleted = "completed";
        private const string StateFailed = "failed";
        private const string StateInterrupted = "interrupted";
        private const string StateAbandoned = "abandoned";
        private const int AtomicWriteMaxAttempts = 5;
        private const int AtomicWriteInitialDelayMs = 25;

        private static readonly UTF8Encoding Utf8NoBom = new UTF8Encoding(false, true);
        private static readonly string ProjectRoot = Directory.GetParent(Application.dataPath).FullName;
        private static readonly string OperationsPath =
            Path.Combine(ProjectRoot, ".claude", "unity", "operations");
        private static readonly string ResponsesPath =
            Path.Combine(ProjectRoot, ".claude", "unity", "responses");

        public static void EnsureInitialized()
        {
            Directory.CreateDirectory(OperationsPath);
            Directory.CreateDirectory(ResponsesPath);
        }

        public static bool IsTerminalWithResponse(string commandId)
        {
            var record = Load(commandId);
            return record != null && IsTerminal(record.state) && ResponseExists(record);
        }

        public static void MarkAccepted(BridgeCommand command, string commandFilePath)
        {
            EnsureInitialized();
            var record = Load(command.commandId) ?? CreateRecord(command, commandFilePath);
            Transition(record, StateAccepted, "accepted", null);
        }

        public static void MarkResponse(BridgeResponse response)
        {
            EnsureInitialized();
            var record = Load(response.commandId);
            if (record == null || IsTerminal(record.state)) return;

            if (response.status == "running")
            {
                Transition(record, StateRunning, "running_response", null);
                return;
            }

            if (response.status == "success")
            {
                Transition(record, StateCompleted, "success_response", null);
                return;
            }

            if (response.status == "error")
            {
                Transition(record, StateFailed, "error_response", response.errorMessage);
            }
        }

        public static void RecoverAfterReload()
        {
            EnsureInitialized();
            foreach (var path in Directory.GetFiles(OperationsPath, "*.json"))
            {
                var record = LoadFromPath(path);
                if (record == null || !ShouldInterruptAfterReload(record)) continue;

                var message = "Command interrupted by Unity domain reload before final response.";
                Transition(record, StateInterrupted, "domain_reload_recovery", message);
                ClaudeUnityBridge.WriteResponseStatic(
                    BridgeResponse.Error(record.commandId, record.commandType, message));
            }
        }

        private static OperationRecord CreateRecord(BridgeCommand command, string commandFilePath)
        {
            var now = UtcNow();
            var record = new OperationRecord
            {
                schemaVersion = SCHEMA_VERSION,
                commandId = command.commandId,
                commandType = command.commandType,
                state = StateQueued,
                parametersHash = HashParameters(command.parametersJson),
                retryPolicy = "non_idempotent",
                domainGeneration = HeartbeatGenerator.DomainGeneration,
                commandPath = commandFilePath,
                responsePath = ResponsePath(command.commandId, command.commandType),
                createdAt = now,
                lastProgressAt = now
            };
            Write(record);
            AppendEvent(record, null, StateQueued, "created", null);
            return record;
        }

        private static void Transition(
            OperationRecord record,
            string toState,
            string eventType,
            string reason)
        {
            if (record.state != toState && !CanTransition(record.state, toState))
            {
                BridgeLogger.LogWarning($"Invalid operation transition {record.state} -> {toState}");
                return;
            }

            string fromState = record.state;
            string now = UtcNow();
            record.state = toState;
            record.lastProgressAt = now;
            if (toState == StateAccepted && string.IsNullOrEmpty(record.acceptedAt))
                record.acceptedAt = now;
            if (toState == StateRunning && string.IsNullOrEmpty(record.startedAt))
                record.startedAt = now;
            if (IsTerminal(toState) && string.IsNullOrEmpty(record.terminalAt))
                record.terminalAt = now;
            if (!string.IsNullOrEmpty(reason))
                record.lastError = reason;
            record.domainGeneration = HeartbeatGenerator.DomainGeneration;

            Write(record);
            AppendEvent(record, fromState, toState, eventType, reason);
        }

        private static bool CanTransition(string fromState, string toState)
        {
            if (fromState == StateQueued)
                return toState == StateAccepted || IsTerminal(toState) || toState == StateRunning;
            if (fromState == StateAccepted)
                return toState == StateRunning || toState == StateRecovering || IsTerminal(toState);
            if (fromState == StateRunning)
                return toState == StateRecovering || IsTerminal(toState);
            if (fromState == StateRecovering)
                return toState == StateRunning || IsTerminal(toState);
            return false;
        }

        private static bool ShouldInterruptAfterReload(OperationRecord record)
        {
            if (ResponseExists(record)) return false;
            // Commands that intentionally span a domain reload (a PlayMode test
            // run, or a compile that triggered the reload) own their own
            // completion and must not be force-interrupted here, or the caller
            // would receive a spurious "interrupted" before the real result.
            if (IsDeferredAcrossReload(record.commandId)) return false;
            return record.state == StateAccepted
                || record.state == StateRunning
                || record.state == StateRecovering;
        }

        private static bool IsDeferredAcrossReload(string commandId)
        {
            if (string.IsNullOrEmpty(commandId)) return false;
            return commandId == SessionState.GetString(BridgeTestRunReporter.CommandIdKey, "")
                || commandId == SessionState.GetString(CompileCommandHandler.PendingCommandIdKey, "");
        }

        private static bool ResponseExists(OperationRecord record)
        {
            return !string.IsNullOrEmpty(record.responsePath) && File.Exists(record.responsePath);
        }

        private static OperationRecord Load(string commandId)
        {
            return LoadFromPath(Path.Combine(OperationsPath, commandId + ".json"));
        }

        private static OperationRecord LoadFromPath(string path)
        {
            try
            {
                if (!File.Exists(path)) return null;
                return JsonUtility.FromJson<OperationRecord>(File.ReadAllText(path));
            }
            catch (Exception ex)
            {
                BridgeLogger.LogWarning($"Failed to read operation record '{path}': {ex.Message}");
                return null;
            }
        }

        private static void Write(OperationRecord record)
        {
            EnsureInitialized();
            string path = Path.Combine(OperationsPath, record.commandId + ".json");
            WriteAtomic(path, JsonUtility.ToJson(record, true));
        }

        private static void AppendEvent(
            OperationRecord record,
            string fromState,
            string toState,
            string eventType,
            string reason)
        {
            try
            {
                var evt = new OperationEvent
                {
                    schemaVersion = SCHEMA_VERSION,
                    timestamp = UtcNow(),
                    commandId = record.commandId,
                    commandType = record.commandType,
                    fromState = fromState,
                    toState = toState,
                    eventType = eventType,
                    reason = reason,
                    domainGeneration = record.domainGeneration
                };
                string path = Path.Combine(OperationsPath, record.commandId + ".events.jsonl");
                File.AppendAllText(
                    path,
                    JsonUtility.ToJson(evt, false) + Environment.NewLine,
                    Utf8NoBom);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogWarning($"Failed to append operation event: {ex.Message}");
            }
        }

        public static void WriteAtomic(string path, string content)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            Exception lastException = null;

            for (int attempt = 1; attempt <= AtomicWriteMaxAttempts; attempt++)
            {
                string tempPath = CreateTempPath(path);
                try
                {
                    WriteTempFile(tempPath, content);
                    ReplaceOrMove(tempPath, path);
                    return;
                }
                catch (Exception ex) when (ex is IOException || ex is UnauthorizedAccessException)
                {
                    lastException = ex;
                    TryDeleteTemp(tempPath);
                    if (attempt >= AtomicWriteMaxAttempts)
                        break;

                    BridgeLogger.LogDebug(
                        $"Atomic write attempt {attempt}/{AtomicWriteMaxAttempts} failed for '{path}': {ex.Message}");
                    Thread.Sleep(RetryDelayMs(attempt));
                }
            }

            throw new IOException(
                $"Atomic write failed for '{path}' after {AtomicWriteMaxAttempts} attempts: {lastException?.Message}",
                lastException);
        }

        private static string CreateTempPath(string path)
        {
            return $"{path}.{Guid.NewGuid():N}.tmp";
        }

        private static void WriteTempFile(string tempPath, string content)
        {
            using var stream = new FileStream(tempPath, FileMode.CreateNew, FileAccess.Write, FileShare.Read);
            using var writer = new StreamWriter(stream, Utf8NoBom);
            writer.Write(content);
            writer.Flush();
            stream.Flush(true);
        }

        private static void ReplaceOrMove(string tempPath, string path)
        {
            if (File.Exists(path))
            {
                File.Replace(tempPath, path, null);
                return;
            }

            File.Move(tempPath, path);
        }

        private static void TryDeleteTemp(string tempPath)
        {
            try
            {
                if (File.Exists(tempPath))
                    File.Delete(tempPath);
            }
            catch
            {
                // Best-effort cleanup; stale temp files are pruned by the CLI clean command.
            }
        }

        private static int RetryDelayMs(int attempt)
        {
            return AtomicWriteInitialDelayMs * (1 << Math.Min(attempt - 1, 4));
        }

        private static string ResponsePath(string commandId, string commandType)
        {
            return Path.Combine(ResponsesPath, $"{commandId}-{commandType}.json");
        }

        private static bool IsTerminal(string state)
        {
            return state == StateCompleted
                || state == StateFailed
                || state == StateInterrupted
                || state == StateAbandoned;
        }

        private static string HashParameters(string parametersJson)
        {
            using var sha = SHA256.Create();
            byte[] bytes = Encoding.UTF8.GetBytes(parametersJson ?? "{}");
            byte[] hash = sha.ComputeHash(bytes);
            return BitConverter.ToString(hash).Replace("-", "").ToLowerInvariant();
        }

        private static string UtcNow()
        {
            return DateTime.UtcNow.ToString("o");
        }

        [Serializable]
        private class OperationRecord
        {
            public int schemaVersion;
            public string commandId;
            public string commandType;
            public string state;
            public string parametersHash;
            public string retryPolicy;
            public int domainGeneration;
            public string idempotencyKey;
            public string commandPath;
            public string responsePath;
            public string createdAt;
            public string acceptedAt;
            public string startedAt;
            public string lastProgressAt;
            public string terminalAt;
            public string lastBusyReason;
            public string lastError;
        }

        [Serializable]
        private class OperationEvent
        {
            public int schemaVersion;
            public string timestamp;
            public string commandId;
            public string commandType;
            public string fromState;
            public string toState;
            public string eventType;
            public string reason;
            public int domainGeneration;
        }
    }
}
