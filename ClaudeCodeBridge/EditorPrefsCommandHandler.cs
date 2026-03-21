using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for reading/writing EditorPrefs and SessionState.
    ///
    /// PURPOSE:
    /// Allows external tools to get, set, delete, and check editor preferences
    /// and session-scoped state. Supports string, int, float, and bool types.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "get" - Read a preference value
    /// 2. "set" - Write a preference value
    /// 3. "delete" - Remove a preference key
    /// 4. "has" - Check if a key exists
    /// </summary>
    public class EditorPrefsCommandHandler : ICommandHandler
    {
        public string CommandType => "editor-prefs";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<EditorPrefsParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new EditorPrefsParams();

                var operation = parameters.operation?.ToLower();
                BridgeLogger.LogDebug($"Executing editor-prefs: {operation}");

                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot execute while scripts are compiling.");
                }

                switch (operation)
                {
                    case "get":
                        return HandleGet(command, parameters);
                    case "set":
                        return HandleSet(command, parameters);
                    case "delete":
                        return HandleDelete(command, parameters);
                    case "has":
                        return HandleHas(command, parameters);
                    default:
                        return BridgeResponse.Error(command.commandId, command.commandType,
                            $"Unknown operation: {parameters.operation}. " +
                            "Supported: get, set, delete, has");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Editor-prefs error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse HandleGet(BridgeCommand command, EditorPrefsParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.key))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "key is required for get operation.");
            }

            var useSession = parameters.scope == "session";
            var valueType = string.IsNullOrEmpty(parameters.valueType)
                ? "string" : parameters.valueType.ToLower();
            string value;

            if (useSession)
                value = GetSessionValue(parameters.key, valueType);
            else
                value = GetPrefsValue(parameters.key, valueType);

            var result = new EditorPrefsResult
            {
                success = true,
                operation = "get",
                key = parameters.key,
                value = value,
                valueType = valueType,
                scope = useSession ? "session" : "prefs",
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleSet(BridgeCommand command, EditorPrefsParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.key))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "key is required for set operation.");
            }

            var useSession = parameters.scope == "session";
            var valueType = string.IsNullOrEmpty(parameters.valueType)
                ? "string" : parameters.valueType.ToLower();

            if (useSession)
                SetSessionValue(parameters.key, parameters.value, valueType);
            else
                SetPrefsValue(parameters.key, parameters.value, valueType);

            var result = new EditorPrefsResult
            {
                success = true,
                operation = "set",
                key = parameters.key,
                value = parameters.value,
                valueType = valueType,
                scope = useSession ? "session" : "prefs",
            };
            BridgeLogger.LogInfo($"EditorPrefs set: {parameters.key} = {parameters.value}");
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleDelete(BridgeCommand command, EditorPrefsParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.key))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "key is required for delete operation.");
            }

            var useSession = parameters.scope == "session";

            if (useSession)
                SessionState.EraseString(parameters.key);
            else
                EditorPrefs.DeleteKey(parameters.key);

            var result = new EditorPrefsResult
            {
                success = true,
                operation = "delete",
                key = parameters.key,
                scope = useSession ? "session" : "prefs",
            };
            BridgeLogger.LogInfo($"EditorPrefs deleted: {parameters.key}");
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleHas(BridgeCommand command, EditorPrefsParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.key))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "key is required for has operation.");
            }

            var useSession = parameters.scope == "session";
            bool exists;

            if (useSession)
            {
                // SessionState does not expose HasKey; check for default sentinel
                var sentinel = "__bridge_sentinel_" + Guid.NewGuid();
                exists = SessionState.GetString(parameters.key, sentinel) != sentinel;
            }
            else
            {
                exists = EditorPrefs.HasKey(parameters.key);
            }

            var result = new EditorPrefsResult
            {
                success = true,
                operation = "has",
                key = parameters.key,
                exists = exists,
                scope = useSession ? "session" : "prefs",
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        // ---------------------------------------------------------------
        // EditorPrefs helpers
        // ---------------------------------------------------------------

        private static string GetPrefsValue(string key, string valueType)
        {
            switch (valueType)
            {
                case "int":
                    return EditorPrefs.GetInt(key, 0).ToString();
                case "float":
                    return EditorPrefs.GetFloat(key, 0f).ToString();
                case "bool":
                    return EditorPrefs.GetBool(key, false).ToString().ToLower();
                default:
                    return EditorPrefs.GetString(key, "");
            }
        }

        private static void SetPrefsValue(string key, string value, string valueType)
        {
            switch (valueType)
            {
                case "int":
                    EditorPrefs.SetInt(key, int.Parse(value));
                    break;
                case "float":
                    EditorPrefs.SetFloat(key, float.Parse(value));
                    break;
                case "bool":
                    EditorPrefs.SetBool(key, ParseBool(value));
                    break;
                default:
                    EditorPrefs.SetString(key, value);
                    break;
            }
        }

        // ---------------------------------------------------------------
        // SessionState helpers
        // ---------------------------------------------------------------

        private static string GetSessionValue(string key, string valueType)
        {
            switch (valueType)
            {
                case "int":
                    return SessionState.GetInt(key, 0).ToString();
                case "float":
                    return SessionState.GetFloat(key, 0f).ToString();
                case "bool":
                    return SessionState.GetBool(key, false).ToString().ToLower();
                default:
                    return SessionState.GetString(key, "");
            }
        }

        private static void SetSessionValue(string key, string value, string valueType)
        {
            switch (valueType)
            {
                case "int":
                    SessionState.SetInt(key, int.Parse(value));
                    break;
                case "float":
                    SessionState.SetFloat(key, float.Parse(value));
                    break;
                case "bool":
                    SessionState.SetBool(key, ParseBool(value));
                    break;
                default:
                    SessionState.SetString(key, value);
                    break;
            }
        }

        private static bool ParseBool(string value)
        {
            var lower = value?.ToLower();
            return lower == "true" || lower == "1" || lower == "yes";
        }
    }

    #region EditorPrefs Models

    [Serializable]
    public class EditorPrefsParams
    {
        public string operation;
        public string key;
        public string value;
        public string valueType = "string";
        public string scope = "prefs";
    }

    [Serializable]
    public class EditorPrefsResult
    {
        public bool success;
        public string operation;
        public string key;
        public string value;
        public string valueType;
        public string scope;
        public bool exists;
    }

    #endregion
}
