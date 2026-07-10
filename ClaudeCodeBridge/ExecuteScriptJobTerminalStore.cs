using System;
using System.IO;
using System.Text;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Durable first-writer-wins terminal envelopes for cooperative script jobs.
    /// </summary>
    internal static class ExecuteScriptJobTerminalStore
    {
        private const string TerminalSuffix = ".terminal.json";
        private const string MaterializedSuffix = ".materialized";

        public static bool TryCommitAndMaterialize(
            BridgeResponse proposed,
            out BridgeResponse committed,
            out string message)
        {
            committed = null;
            if (!IsTerminal(proposed))
                return Fail("Only terminal responses can be committed.", out message);
            if (!TryPaths(proposed.commandId, out var terminalPath, out var markerPath, out message))
                return false;
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(terminalPath));
                if (!File.Exists(terminalPath))
                    TryCreateClaim(terminalPath, proposed);
                committed = ReadResponse(terminalPath);
                if (committed == null)
                    return Fail("Committed execute-job terminal envelope is invalid.", out message);
                if (File.Exists(markerPath))
                {
                    message = "";
                    return true;
                }
                if (!ClaudeUnityBridge.WriteResponseStatic(committed))
                    return Fail("Could not materialize committed execute-job response.", out message);
                BridgeOperationLedger.WriteAtomic(markerPath, DateTime.UtcNow.ToString("o"));
                message = "";
                return true;
            }
            catch (Exception ex)
            {
                return Fail($"Could not commit execute-job terminal response: {ex.Message}", out message);
            }
        }

        public static void ReplayPending()
        {
            var directory = StorePath();
            if (!Directory.Exists(directory))
                return;
            foreach (var terminalPath in Directory.GetFiles(directory, $"*{TerminalSuffix}"))
            {
                var commandId = Path.GetFileName(terminalPath)
                    .Substring(0, Path.GetFileName(terminalPath).Length - TerminalSuffix.Length);
                if (!TryPaths(commandId, out _, out var markerPath, out _) || File.Exists(markerPath))
                    continue;
                var response = ReadResponse(terminalPath);
                if (response == null || !ClaudeUnityBridge.WriteResponseStatic(response))
                    continue;
                BridgeOperationLedger.WriteAtomic(markerPath, DateTime.UtcNow.ToString("o"));
            }
        }

        private static void TryCreateClaim(string path, BridgeResponse response)
        {
            try
            {
                var bytes = Encoding.UTF8.GetBytes(JsonUtility.ToJson(response, true));
                using (var stream = new FileStream(
                    path, FileMode.CreateNew, FileAccess.Write, FileShare.Read))
                {
                    stream.Write(bytes, 0, bytes.Length);
                    stream.Flush(true);
                }
            }
            catch (IOException) when (File.Exists(path))
            {
                // Another terminal path won the durable first-writer claim.
            }
        }

        private static BridgeResponse ReadResponse(string path)
        {
            try
            {
                return JsonUtility.FromJson<BridgeResponse>(File.ReadAllText(path));
            }
            catch
            {
                return null;
            }
        }

        private static bool TryPaths(
            string commandId,
            out string terminalPath,
            out string markerPath,
            out string message)
        {
            terminalPath = "";
            markerPath = "";
            if (string.IsNullOrWhiteSpace(commandId)
                || Path.GetFileName(commandId) != commandId)
            {
                return Fail("Execute-job command id is invalid.", out message);
            }
            terminalPath = Path.Combine(StorePath(), commandId + TerminalSuffix);
            markerPath = Path.Combine(StorePath(), commandId + MaterializedSuffix);
            message = "";
            return true;
        }

        private static string StorePath()
        {
            var root = Directory.GetParent(Application.dataPath)?.FullName
                ?? Application.dataPath;
            return Path.Combine(root, ".claude", "unity", "job-terminals");
        }

        private static bool IsTerminal(BridgeResponse response)
        {
            return response != null
                && (response.status == "success" || response.status == "error");
        }

        private static bool Fail(string error, out string message)
        {
            message = error;
            return false;
        }
    }
}
