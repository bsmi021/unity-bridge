using System;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Parameters for the memory-profiler command.
    /// </summary>
    [Serializable]
    public class MemoryProfilerParams
    {
        public string operation;
        public string path;
        public string captureFlags;
    }

    /// <summary>
    /// Result payload written on completion of a memory-profiler operation.
    /// </summary>
    [Serializable]
    public class MemoryProfilerResult
    {
        public string operation;
        public string path;
        public bool success;
        public string message;
    }
}
