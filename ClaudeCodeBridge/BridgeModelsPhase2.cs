using System;
using System.Collections.Generic;

namespace BWS.Editor.ClaudeCodeBridge
{
    // -----------------------------------------------------------------------
    // Phase 2 models — split from BridgeModels.cs to stay under 500 LOC each.
    // All types are in the same namespace for seamless handler access.
    // -----------------------------------------------------------------------

    #region Undo Operation

    /// <summary>
    /// Parameters for the undo-operation command.
    /// </summary>
    [Serializable]
    public class UndoOperationParams
    {
        public string operation;
        public int limit = 20;
        public int groupIndex;
        public string name;
    }

    /// <summary>
    /// Result data for the undo-operation command.
    /// </summary>
    [Serializable]
    public class UndoOperationResult
    {
        public bool success;
        public bool undone;
        public bool redone;
        public bool cleared;
        public bool collapsed;
        public string groupName;
        public string currentGroupName;
        public List<UndoGroupInfo> recentOperations = new List<UndoGroupInfo>();
        public int count;
        public int groupIndex;
        public string name;
        public string warning;
        public string note;
    }

    /// <summary>
    /// Information about an undo group entry.
    /// </summary>
    [Serializable]
    public class UndoGroupInfo
    {
        public string name;
        public int id;
    }

    #endregion

    #region Compilation Pipeline

    /// <summary>
    /// Parameters for the compilation-pipeline command.
    /// </summary>
    [Serializable]
    public class CompilationPipelineParams
    {
        public string operation;
        public string assemblyName;
        public string scriptPath;
        public string mode;
    }

    /// <summary>
    /// Result data for the compilation-pipeline command.
    /// </summary>
    [Serializable]
    public class CompilationPipelineResult
    {
        public bool success;
        public string operation;
        public List<AssemblyInfoResult> assemblies = new List<AssemblyInfoResult>();
        public string assembly;
        public string assemblyPath;
        public string scriptPath;
        public List<string> defines = new List<string>();
        public string mode;
        public bool changed;
    }

    /// <summary>
    /// Information about a compiled assembly.
    /// </summary>
    [Serializable]
    public class AssemblyInfoResult
    {
        public string name;
        public string path;
        public int sourceFileCount;
        public List<string> defines = new List<string>();
        public List<string> references = new List<string>();
    }

    #endregion

    #region Prefab Override

    /// <summary>
    /// Parameters for the prefab-override command.
    /// </summary>
    [Serializable]
    public class PrefabOverrideParams
    {
        public string operation;
        public string instancePath;
        public string assetPath;
        public string target;
        public bool completely = false;
        public bool includeDefaultOverrides = false;
    }

    /// <summary>
    /// Result data for the prefab-override command.
    /// </summary>
    [Serializable]
    public class PrefabOverrideResult
    {
        public bool success;
        public string operation;
        public bool hasOverrides;
        public int count;
        public List<PrefabOverrideInfo> overrides = new List<PrefabOverrideInfo>();
        public bool applied;
        public bool reverted;
        public bool unpacked;
        public string mode;
        public string prefabType;
        public string instanceStatus;
        public string assetPath;
        public bool isVariant;
        public bool isPartOfPrefab;
        public string path;
        public List<PrefabInstanceInfo> instances = new List<PrefabInstanceInfo>();
    }

    /// <summary>
    /// Information about a single prefab override.
    /// </summary>
    [Serializable]
    public class PrefabOverrideInfo
    {
        public string type;
        public string objectPath;
        public string componentType;
        public string propertyPath;
        public string originalValue;
        public string currentValue;
        public string details;
    }

    /// <summary>
    /// Information about a prefab instance in the scene.
    /// </summary>
    [Serializable]
    public class PrefabInstanceInfo
    {
        public string path;
        public string scene;
        public bool hasOverrides;
    }

    #endregion

    #region Test Listing

    /// <summary>
    /// Parameters for the list-tests command.
    /// </summary>
    [Serializable]
    public class ListTestsParams
    {
        public string mode = "tests";
        public string testPlatform;
        public string filter;
    }

    /// <summary>
    /// Result data for the list-tests command.
    /// </summary>
    [Serializable]
    public class ListTestsResult
    {
        public bool success;
        public List<TestInfoEntry> tests = new List<TestInfoEntry>();
        public List<string> categories = new List<string>();
        public List<TestAssemblyInfoEntry> assemblies = new List<TestAssemblyInfoEntry>();
        public int count;
    }

    /// <summary>
    /// Information about an individual test method.
    /// </summary>
    [Serializable]
    public class TestInfoEntry
    {
        public string fullName;
        public string className;
        public string methodName;
        public List<string> categories = new List<string>();
        public string assembly;
    }

    /// <summary>
    /// Information about a test assembly and its test count.
    /// </summary>
    [Serializable]
    public class TestAssemblyInfoEntry
    {
        public string name;
        public int testCount;
    }

    #endregion

    #region GameObject Utility

    /// <summary>
    /// Parameters for the gameobject-utility command.
    /// </summary>
    [Serializable]
    public class GameObjectUtilityParams
    {
        public string operation;
        public string gameObjectPath;
        public bool fix = false;
        public List<string> flags = new List<string>();
        public int layer;
        public string tag;
        public bool recursive = false;
    }

    /// <summary>
    /// Result data for the gameobject-utility command.
    /// </summary>
    [Serializable]
    public class GameObjectUtilityResult
    {
        public bool success;
        public string operation;
        public string path;
        public List<MissingScriptInfo> found = new List<MissingScriptInfo>();
        public int totalCount;
        public int removed;
        public List<string> flags = new List<string>();
        public int rawValue;
        public int layer;
        public string tag;
        public int affectedCount;
        public bool changed;
    }

    /// <summary>
    /// Information about missing scripts on a GameObject.
    /// </summary>
    [Serializable]
    public class MissingScriptInfo
    {
        public string path;
        public int count;
    }

    #endregion
}
