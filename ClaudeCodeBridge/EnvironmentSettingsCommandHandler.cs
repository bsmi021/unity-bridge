using System;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for environment lighting, fog, and reflection settings.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "get" - Read current environment/rendering settings
    /// 2. "set" - Modify environment settings
    ///
    /// GUARDS:
    /// - EditorApplication.isCompiling: blocks all operations
    /// - EditorApplication.isPlaying: blocks set operation
    /// </summary>
    public class EnvironmentSettingsCommandHandler : ICommandHandler
    {
        public string CommandType => "environment-settings";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot access environment settings while compiling.");
                }

                var parameters = JsonUtility.FromJson<EnvironmentSettingsParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new EnvironmentSettingsParams();

                EnvironmentSettingsResult result;
                switch (parameters.operation?.ToLower())
                {
                    case "get":
                        result = ExecuteGet();
                        break;
                    case "set":
                        result = ExecuteSet(parameters);
                        break;
                    default:
                        result = new EnvironmentSettingsResult
                        {
                            success = false,
                            operation = parameters.operation,
                            message = $"Unknown operation: {parameters.operation}. "
                                + "Supported: get, set"
                        };
                        break;
                }

                var resultJson = JsonUtility.ToJson(result);
                return BridgeResponse.Success(
                    command.commandId, command.commandType, resultJson);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"EnvironmentSettings error: {ex}");
                return BridgeResponse.Error(
                    command.commandId, command.commandType, ex.ToString());
            }
        }

        private EnvironmentSettingsResult ExecuteGet()
        {
            var skybox = RenderSettings.skybox;
            var ambientColor = RenderSettings.ambientLight;
            var skyColor = RenderSettings.ambientSkyColor;
            var equatorColor = RenderSettings.ambientEquatorColor;
            var groundColor = RenderSettings.ambientGroundColor;
            var fogColor = RenderSettings.fogColor;

            return new EnvironmentSettingsResult
            {
                success = true,
                operation = "get",
                // Skybox
                skyboxMaterial = skybox is not null
                    ? AssetDatabase.GetAssetPath(skybox) : "",
                // Ambient
                ambientMode = RenderSettings.ambientMode.ToString(),
                ambientIntensity = RenderSettings.ambientIntensity,
                ambientLightR = ambientColor.r,
                ambientLightG = ambientColor.g,
                ambientLightB = ambientColor.b,
                ambientSkyColorR = skyColor.r,
                ambientSkyColorG = skyColor.g,
                ambientSkyColorB = skyColor.b,
                ambientEquatorColorR = equatorColor.r,
                ambientEquatorColorG = equatorColor.g,
                ambientEquatorColorB = equatorColor.b,
                ambientGroundColorR = groundColor.r,
                ambientGroundColorG = groundColor.g,
                ambientGroundColorB = groundColor.b,
                // Fog
                fog = RenderSettings.fog,
                fogMode = RenderSettings.fogMode.ToString(),
                fogColorR = fogColor.r,
                fogColorG = fogColor.g,
                fogColorB = fogColor.b,
                fogDensity = RenderSettings.fogDensity,
                fogStartDistance = RenderSettings.fogStartDistance,
                fogEndDistance = RenderSettings.fogEndDistance,
                // Reflection
                defaultReflectionMode =
                    RenderSettings.defaultReflectionMode.ToString(),
                defaultReflectionResolution =
                    RenderSettings.defaultReflectionResolution,
                reflectionBounces = RenderSettings.reflectionBounces,
                reflectionIntensity = RenderSettings.reflectionIntensity,
                message = "Environment settings retrieved"
            };
        }

        private EnvironmentSettingsResult ExecuteSet(
            EnvironmentSettingsParams p)
        {
            if (EditorApplication.isPlaying)
            {
                return new EnvironmentSettingsResult
                {
                    success = false,
                    operation = "set",
                    message = "Cannot modify environment settings in play mode."
                };
            }

            EnvironmentSetHelpers.Apply(p);

            var result = ExecuteGet();
            result.operation = "set";
            result.message = "Environment settings updated";
            return result;
        }
    }
}
