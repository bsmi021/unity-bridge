using System;
using System.Collections.Generic;

namespace BWS.Editor.ClaudeCodeBridge
{
    // -----------------------------------------------------------------------
    // Phase 3 models — Shader Inspection
    // -----------------------------------------------------------------------

    /// <summary>
    /// Parameters for the shader-inspection command.
    /// </summary>
    [Serializable]
    public class ShaderInspectionParams
    {
        public string operation;
        public string shaderName;
        public string propertyName;
        public bool errorsOnly;
        public string keywordFilter;
    }

    /// <summary>
    /// Result data for the shader list operation.
    /// </summary>
    [Serializable]
    public class ShaderListResult
    {
        public string operation;
        public List<ShaderListEntry> shaders = new List<ShaderListEntry>();
        public int totalCount;
        public bool success;
        public string message;
    }

    /// <summary>
    /// Entry in the shader list.
    /// </summary>
    [Serializable]
    public class ShaderListEntry
    {
        public string name;
        public bool supported;
        public bool hasErrors;
    }

    /// <summary>
    /// Result data for the shader info operation.
    /// </summary>
    [Serializable]
    public class ShaderInfoResult
    {
        public string operation;
        public string shaderName;
        public bool supported;
        public bool hasErrors;
        public bool isCompiling;
        public int renderQueue;
        public int passCount;
        public int propertyCount;
        public int subShaderCount;
        public bool success;
        public string message;
    }

    /// <summary>
    /// Result data for the shader errors operation.
    /// </summary>
    [Serializable]
    public class ShaderErrorsResult
    {
        public string operation;
        public string shaderName;
        public bool hasErrors;
        public List<ShaderMessageEntry> messages = new List<ShaderMessageEntry>();
        public int messageCount;
        public bool success;
        public string message;
    }

    /// <summary>
    /// A single shader compilation message (error or warning).
    /// </summary>
    [Serializable]
    public class ShaderMessageEntry
    {
        public string message;
        public string messageDetails;
        public string severity;
        public string platform;
        public int line;
        public string file;
    }

    /// <summary>
    /// Result data for the shader properties operation.
    /// </summary>
    [Serializable]
    public class ShaderPropertiesResult
    {
        public string operation;
        public string shaderName;
        public List<ShaderPropertyEntry> properties = new List<ShaderPropertyEntry>();
        public int propertyCount;
        public bool success;
        public string message;
    }

    /// <summary>
    /// A single shader property.
    /// </summary>
    [Serializable]
    public class ShaderPropertyEntry
    {
        public string name;
        public string displayName;
        public string type;
        public string description;
        public List<string> flags = new List<string>();
        public string defaultValue;
        public float rangeMin;
        public float rangeMax;
        public string textureDimension;
    }

    /// <summary>
    /// Result data for the shader find-by-property operation.
    /// </summary>
    [Serializable]
    public class ShaderFindByPropertyResult
    {
        public string operation;
        public string propertyName;
        public List<ShaderPropertyMatch> shaders = new List<ShaderPropertyMatch>();
        public int matchCount;
        public bool success;
        public string message;
    }

    /// <summary>
    /// A shader that has the searched property.
    /// </summary>
    [Serializable]
    public class ShaderPropertyMatch
    {
        public string name;
        public string propertyType;
        public string propertyDescription;
    }

    /// <summary>
    /// Result data for the shader keywords operation.
    /// </summary>
    [Serializable]
    public class ShaderKeywordsResult
    {
        public string operation;
        public string shaderName;
        public List<string> globalKeywords = new List<string>();
        public List<string> localKeywords = new List<string>();
        public int globalCount;
        public int localCount;
        public bool success;
        public string message;
    }
}
