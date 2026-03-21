using System;
using System.Collections.Generic;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Parameters for the serialized-property command.
    /// Operations: get, set, list
    /// </summary>
    [Serializable]
    public class SerializedPropertyParams
    {
        public string operation;
        public string gameObjectPath;
        public string componentType;
        public string propertyPath;
        public string valueJson;
    }

    /// <summary>
    /// Result data for the serialized-property command.
    /// </summary>
    [Serializable]
    public class SerializedPropertyResult
    {
        public bool success;
        public string operation;
        public string gameObjectPath;
        public string componentType;
        public List<SerializedPropertyInfo> properties = new List<SerializedPropertyInfo>();
        public string message;
    }

    /// <summary>
    /// Information about a single serialized property.
    /// </summary>
    [Serializable]
    public class SerializedPropertyInfo
    {
        public string name;
        public string path;
        public string displayName;
        public string type;
        public string value;
        public int depth;
        public bool isExpanded;
        public int arraySize;
        public bool isArray;
    }
}
