using System;
using System.Collections.Generic;

namespace BWS.Editor.ClaudeCodeBridge
{
    // -----------------------------------------------------------------------
    // Phase 3 models — split from BridgeModels.cs to stay under 500 LOC each.
    // Contains: Animator, Prefab, Material, Read Console, and GameObject
    // operation models.
    // -----------------------------------------------------------------------

    #region Animator Operation Command

    /// <summary>
    /// Parameters for the animator-operation command.
    /// </summary>
    [Serializable]
    public class AnimatorOperationParams
    {
        public string operation;
        public string controllerPath;
        public string layerName = "Base Layer";
        public int layerIndex = 0;
        public float weight = 1.0f;
        public string blendingMode = "Override";
        public string stateName;
        public string sourceState;
        public string destinationState;
        public string animationClipPath;
        public float speed = 1.0f;
        public string parameterName;
        public string parameterType;
        public string defaultValue;
        public List<TransitionCondition> conditions = new List<TransitionCondition>();
        public float duration = 0.25f;
        public bool hasExitTime = true;
        public float exitTime = 0.75f;
        public bool iKPass = false;
        public string avatarMaskPath;
    }

    [Serializable]
    public class TransitionCondition
    {
        public string parameter;
        public string mode;
        public float threshold;
    }

    [Serializable]
    public class AnimatorOperationResult
    {
        public string operation;
        public string controllerPath;
        public List<AnimatorLayerInfo> layers = new List<AnimatorLayerInfo>();
        public List<AnimatorStateInfo> states = new List<AnimatorStateInfo>();
        public List<AnimatorParameterInfo> parameters = new List<AnimatorParameterInfo>();
        public List<AnimatorTransitionInfo> transitions = new List<AnimatorTransitionInfo>();
        public bool success;
        public string message;
    }

    [Serializable]
    public class AnimatorLayerInfo
    {
        public string name;
        public float weight;
        public string blendingMode;
        public int stateCount;
        public bool iKPass;
        public string avatarMask;
    }

    [Serializable]
    public class AnimatorStateInfo
    {
        public string name;
        public string layerName;
        public string motionPath;
        public float speed;
        public bool isDefaultState;
        public string tag;
    }

    [Serializable]
    public class AnimatorParameterInfo
    {
        public string name;
        public string type;
        public string defaultValue;
    }

    [Serializable]
    public class AnimatorTransitionInfo
    {
        public string sourceState;
        public string destinationState;
        public float duration;
        public bool hasExitTime;
        public float exitTime;
        public int conditionCount;
        public List<TransitionCondition> conditions = new List<TransitionCondition>();
    }

    #endregion

    #region Read Console Command

    [Serializable]
    public class ReadConsoleParams
    {
        public List<string> logTypes = new List<string>();
        public int maxEntries = 100;
        public bool clearAfterRead = false;
        public bool includeStackTrace = true;
        public int maxStackTraceLines = 5;
        public int maxMessageLength = 500;
    }

    [Serializable]
    public class ReadConsoleResult
    {
        public List<ConsoleEntry> entries = new List<ConsoleEntry>();
        public int totalCount;
    }

    [Serializable]
    public class ConsoleEntry
    {
        public string logType;
        public string message;
        public string stackTrace;
        public string timestamp;
    }

    #endregion

    #region Prefab Operation Command

    [Serializable]
    public class PrefabOperationParams
    {
        public string operation;
        public string prefabPath;
        public string gameObjectPath;
        public bool applyToAll = false;
    }

    [Serializable]
    public class PrefabOperationResult
    {
        public string operation;
        public string prefabPath;
        public string gameObjectPath;
        public bool isPrefabInstance;
        public bool hasModifications;
        public List<string> modifications = new List<string>();
        public bool success;
        public string message;
    }

    #endregion

    #region Material Operation Command

    [Serializable]
    public class MaterialOperationParams
    {
        public string operation;
        public string materialPath;
        public string shader;
        public List<MaterialProperty> properties = new List<MaterialProperty>();
    }

    [Serializable]
    public class MaterialProperty
    {
        public string name;
        public string type;
        public string valueJson;
    }

    [Serializable]
    public class MaterialOperationResult
    {
        public string operation;
        public string materialPath;
        public string shaderName;
        public List<MaterialProperty> properties = new List<MaterialProperty>();
        public bool success;
        public string message;
    }

    #endregion

    #region GameObject Operation Command

    [Serializable]
    public class GameObjectOperationParams
    {
        public string operation;
        public string gameObjectName;
        public string gameObjectPath;
        public string parentPath;
        public string newName;
        public string primitiveType;
        public bool active = true;
    }

    [Serializable]
    public class GameObjectOperationResult
    {
        public string operation;
        public string gameObjectPath;
        public bool success;
        public string message;
    }

    #endregion

    #region Bridge Status Command

    [Serializable]
    public class BridgeStatusParams
    {
    }

    [Serializable]
    public class BridgeStatusResult
    {
        public string unityVersion;
        public bool isInitialized;
        public List<string> registeredHandlers = new List<string>();
        public int commandsProcessed;
        public string commandsPath;
        public string responsesPath;
        public string currentScene;
        public string playModeState;
    }

    #endregion
}
