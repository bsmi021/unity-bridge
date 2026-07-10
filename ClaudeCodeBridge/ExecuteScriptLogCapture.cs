using System;
using System.Collections.Generic;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    internal sealed class ExecuteScriptLogCapture : IDisposable
    {
        public List<ExecuteScriptLogEntry> Entries { get; } =
            new List<ExecuteScriptLogEntry>();

        public ExecuteScriptLogCapture()
        {
            Application.logMessageReceived += OnLogMessage;
        }

        public void Dispose()
        {
            Application.logMessageReceived -= OnLogMessage;
        }

        private void OnLogMessage(string message, string stackTrace, LogType logType)
        {
            Entries.Add(new ExecuteScriptLogEntry
            {
                message = message,
                stackTrace = stackTrace,
                logType = logType.ToString(),
            });
        }
    }
}
