using System;
using System.Collections.Generic;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Parameters for the transform-operation command.
    /// Operations: get, set, parent, sibling-index
    /// </summary>
    [Serializable]
    public class TransformParams
    {
        public string operation;
        public string gameObjectPath;

        // set operation fields
        public SerializableVector3 position;
        public SerializableVector3 localPosition;
        public SerializableVector3 rotation;
        public SerializableVector3 scale;
        public bool useLocal = false;

        // parent operation fields
        public string parentPath;
        public bool worldPositionStays = true;

        // sibling-index operation
        public int siblingIndex = -1;
    }

    /// <summary>
    /// Nullable vector3 wrapper — null means "not specified" so we
    /// only apply fields the caller explicitly provides.
    /// </summary>
    [Serializable]
    public class SerializableVector3
    {
        public float x;
        public float y;
        public float z;
        public bool isSet = false;
    }

    /// <summary>
    /// Result data for the transform-operation command.
    /// </summary>
    [Serializable]
    public class TransformResult
    {
        public bool success;
        public string operation;
        public string gameObjectPath;
        public SerializableVector3Data position;
        public SerializableVector3Data localPosition;
        public SerializableVector3Data rotation;
        public SerializableVector3Data localEulerAngles;
        public SerializableVector3Data localScale;
        public string parentPath;
        public int siblingIndex;
        public string message;
    }

    /// <summary>
    /// Simple vector3 data for JSON serialization in results.
    /// </summary>
    [Serializable]
    public class SerializableVector3Data
    {
        public float x;
        public float y;
        public float z;

        public static SerializableVector3Data FromVector3(UnityEngine.Vector3 v)
        {
            return new SerializableVector3Data { x = v.x, y = v.y, z = v.z };
        }
    }
}
