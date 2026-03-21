using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for editor configuration operations.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "get" - Read current editor settings
    /// 2. "set" - Modify a specific editor setting by key
    ///
    /// GUARDS:
    /// - EditorApplication.isCompiling: blocks all operations
    /// - EditorApplication.isPlaying: blocks set operations
    /// </summary>
    public class EditorConfigCommandHandler : ICommandHandler
    {
        public string CommandType => "editor-config";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot access editor config while scripts are compiling.");
                }

                var parameters = JsonUtility.FromJson<EditorConfigParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new EditorConfigParams();

                EditorConfigResult result;
                switch (parameters.operation?.ToLower())
                {
                    case "get":
                        result = ExecuteGet();
                        break;
                    case "set":
                        result = ExecuteSet(parameters);
                        break;
                    default:
                        result = new EditorConfigResult
                        {
                            success = false,
                            operation = parameters.operation,
                            message = $"Unknown operation: {parameters.operation}. "
                                + "Supported: get, set"
                        };
                        break;
                }

                var resultJson = JsonUtility.ToJson(result);
                return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"EditorConfig error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private EditorConfigResult ExecuteGet()
        {
            var settings = EditorSettings.serializationMode.ToString();
            return new EditorConfigResult
            {
                success = true,
                operation = "get",
                enterPlayModeOptionsEnabled = EditorSettings.enterPlayModeOptionsEnabled,
                enterPlayModeOptions = EditorSettings.enterPlayModeOptions.ToString(),
                serializationMode = EditorSettings.serializationMode.ToString(),
                asyncShaderCompilation = EditorSettings.asyncShaderCompilation,
                lineEndingsForNewScripts = EditorSettings.lineEndingsForNewScripts.ToString(),
                projectGenerationRootNamespace = EditorSettings.projectGenerationRootNamespace,
                message = "Editor settings retrieved"
            };
        }

        private EditorConfigResult ExecuteSet(EditorConfigParams p)
        {
            if (EditorApplication.isPlaying)
            {
                return new EditorConfigResult
                {
                    success = false,
                    operation = "set",
                    message = "Cannot modify editor settings in play mode."
                };
            }

            if (string.IsNullOrEmpty(p.key))
            {
                return new EditorConfigResult
                {
                    success = false,
                    operation = "set",
                    message = "key is required for set operation"
                };
            }

            bool applied = ApplySetting(p.key, p.value, out string applyMsg);
            if (!applied)
            {
                return new EditorConfigResult
                {
                    success = false,
                    operation = "set",
                    message = applyMsg
                };
            }

            var result = ExecuteGet();
            result.message = $"Setting '{p.key}' updated. {applyMsg}";
            return result;
        }

        private bool ApplySetting(string key, string value, out string message)
        {
            try
            {
                switch (key.ToLower())
                {
                    case "enterplaymodeoptionsenabled":
                        EditorSettings.enterPlayModeOptionsEnabled = bool.Parse(value);
                        message = $"enterPlayModeOptionsEnabled = {value}";
                        return true;

                    case "enterplaymodeoptions":
                        return ParseEnterPlayModeOptions(value, out message);

                    case "serializationmode":
                        return ParseSerializationMode(value, out message);

                    case "asyncshadercompilation":
                        EditorSettings.asyncShaderCompilation = bool.Parse(value);
                        message = $"asyncShaderCompilation = {value}";
                        return true;

                    case "lineendingsfornewscripts":
                        return ParseLineEndings(value, out message);

                    case "projectgenerationrootnamespace":
                        EditorSettings.projectGenerationRootNamespace = value;
                        message = $"projectGenerationRootNamespace = {value}";
                        return true;

                    default:
                        message = $"Unknown setting key: {key}. Supported: "
                            + "enterPlayModeOptionsEnabled, enterPlayModeOptions, "
                            + "serializationMode, asyncShaderCompilation, "
                            + "lineEndingsForNewScripts, projectGenerationRootNamespace";
                        return false;
                }
            }
            catch (Exception ex)
            {
                message = $"Failed to set '{key}': {ex.Message}";
                return false;
            }
        }

        private bool ParseEnterPlayModeOptions(string value, out string message)
        {
            // Accept: "None", "DisableDomainReload", "DisableSceneReload",
            //         "DisableDomainReload, DisableSceneReload"
            if (Enum.TryParse<EnterPlayModeOptions>(value, true, out var options))
            {
                EditorSettings.enterPlayModeOptions = options;
                message = $"enterPlayModeOptions = {options}";
                return true;
            }
            message = $"Invalid enterPlayModeOptions value: {value}. "
                + "Valid: None, DisableDomainReload, DisableSceneReload";
            return false;
        }

        private bool ParseSerializationMode(string value, out string message)
        {
            if (Enum.TryParse<SerializationMode>(value, true, out var mode))
            {
                EditorSettings.serializationMode = mode;
                message = $"serializationMode = {mode}";
                return true;
            }
            message = $"Invalid serializationMode: {value}. "
                + "Valid: Mixed, ForceText, ForceBinary";
            return false;
        }

        private bool ParseLineEndings(string value, out string message)
        {
            if (Enum.TryParse<LineEndingsMode>(value, true, out var mode))
            {
                EditorSettings.lineEndingsForNewScripts = mode;
                message = $"lineEndingsForNewScripts = {mode}";
                return true;
            }
            message = $"Invalid lineEndingsForNewScripts: {value}. "
                + "Valid: OSNative, Unix, Windows";
            return false;
        }
    }

    // -----------------------------------------------------------------
    // Models
    // -----------------------------------------------------------------

    [Serializable]
    public class EditorConfigParams
    {
        public string operation;
        public string key;
        public string value;
    }

    [Serializable]
    public class EditorConfigResult
    {
        public bool success;
        public string operation;
        public string message;
        public bool enterPlayModeOptionsEnabled;
        public string enterPlayModeOptions;
        public string serializationMode;
        public bool asyncShaderCompilation;
        public string lineEndingsForNewScripts;
        public string projectGenerationRootNamespace;
    }
}
