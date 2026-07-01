using System;
using System.Collections.Generic;

namespace BWS.Editor.ClaudeCodeBridge
{
    [Serializable]
    public class TimelineParams
    {
        public string operation;
        public string timelineAssetPath;
        public string trackType;
        public string trackName;
        public int trackIndex = -1;
        public string clipAssetPath;
        public int clipIndex = -1;
        public string directorPath;
        public float time = float.NaN; // NaN sentinel means "not provided" (JsonUtility
                                        // preserves this default for absent JSON keys,
                                        // same idiom as NavMeshParams' -1f sentinels).
    }

    [Serializable]
    public class TimelineResult
    {
        public string operation;
        public bool success;
        public string message;
    }

    [Serializable]
    public class TimelineTrackInfo
    {
        public int trackIndex;
        public string name;
        public string typeName;
        public int clipCount;
    }

    [Serializable]
    public class TimelineTrackResult
    {
        public string operation;
        public bool success;
        public string message;
        public int trackIndex;
        public string name;
        public string typeName;
    }

    [Serializable]
    public class TimelineInfoResult
    {
        public string operation;
        public bool success;
        public string message;
        public string timelineAssetPath;
        public List<TimelineTrackInfo> tracks = new List<TimelineTrackInfo>();
    }

    [Serializable]
    public class TimelineClipInfo
    {
        public int trackIndex;
        public int clipIndex;
        public string displayName;
        public double start;
        public double duration;
    }

    [Serializable]
    public class TimelineClipResult
    {
        public string operation;
        public bool success;
        public string message;
        public int trackIndex;
        public int clipIndex;
        public string displayName;
        public double start;
        public double duration;
    }

    [Serializable]
    public class TimelineClipsResult
    {
        public string operation;
        public bool success;
        public string message;
        public int trackIndex;
        public List<TimelineClipInfo> clips = new List<TimelineClipInfo>();
    }
}
