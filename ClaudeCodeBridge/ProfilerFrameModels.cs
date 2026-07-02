using System;
using System.Collections.Generic;

namespace BWS.Editor.ClaudeCodeBridge
{
    [Serializable]
    public class ProfilerFrameParams
    {
        public string operation;
        public int frameIndex = -1;
        public int frameIndexStart = -1;
        public int frameIndexEnd = -1;
        public int threadIndex = 0;
        public int count = 10;
        public int depth = 8;
        public int frameCount;
        public string markerName;
        public string logFile;
    }

    [Serializable]
    public class ProfilerFrameResult
    {
        public string operation;
        public bool success;
        public string message;
        public int firstFrameIndex;
        public int lastFrameIndex;
        public int frameIndex;
        public long totalGcBytes;
        public List<ProfilerFrameSampleInfo> samples = new List<ProfilerFrameSampleInfo>();
        public List<ProfilerFrameSummaryInfo> summaries = new List<ProfilerFrameSummaryInfo>();
        public List<ProfilerFrameTreeInfo> tree = new List<ProfilerFrameTreeInfo>();
    }

    [Serializable]
    public class ProfilerFrameSampleInfo
    {
        public string markerName;
        public int markerId;
        public double totalTimeMs;
        public double selfTimeMs;
        public long gcBytes;
        public int callCount;
    }

    [Serializable]
    public class ProfilerFrameSummaryInfo
    {
        public string markerName;
        public double totalTimeMs;
        public double selfTimeMs;
        public long gcBytes;
        public int callCount;
    }

    [Serializable]
    public class ProfilerFrameTreeInfo
    {
        public int depth;
        public string markerName;
        public double totalTimeMs;
        public double selfTimeMs;
        public long gcBytes;
        public int callCount;
    }
}
