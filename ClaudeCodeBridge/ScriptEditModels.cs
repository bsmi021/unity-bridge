using System;

namespace BWS.Editor.ClaudeCodeBridge
{
    [Serializable]
    public class ScriptEditParams
    {
        public string operation;
        public string assetPath;
        public int startLine;
        public int endLine;
        public string anchor;
        public int occurrence = 1;
        public string replacement;
        public string ifMatch;
    }

    [Serializable]
    public class ScriptEditResult
    {
        public string operation;
        public string assetPath;
        public bool success;
        public string message;
        public string sha256Before;
        public string sha256After;
        public bool imported;
        public bool compileRequested;
        public string compileFeedback;
    }
}
