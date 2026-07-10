using System;
using System.Collections.Generic;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Tracks one in-flight, non-blocking compile wait.
    /// </summary>
    internal class CompileWaitContext
    {
        public string CommandId;
        public string CommandType;
        public DateTime StartTime;
        public int TimeoutSeconds;
        public bool CompilationStarted;
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
        public bool triggered;
        public bool hasErrors;
        public bool hasWarnings;
        public int errorCount;
        public int warningCount;
        public double durationSeconds;
        public List<CompilationMessage> messages = new List<CompilationMessage>();
        public string message;
    }

    /// <summary>
    /// Represents a single compilation message (error or warning).
    /// </summary>
    [Serializable]
    public class CompilationMessage
    {
        public string type;
        public string message;
        public string file;
        public int line;
        public int column;
    }
}
