using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for quality settings operations.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "list" - List all quality levels with names
    /// 2. "get" - Get current quality level and all settings
    /// 3. "set-level" - Switch active quality level
    ///
    /// GUARDS:
    /// - EditorApplication.isCompiling: blocks all operations
    /// - EditorApplication.isPlaying: blocks set-level
    /// </summary>
    public class QualitySettingsCommandHandler : ICommandHandler
    {
        public string CommandType => "quality-settings";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot access quality settings while scripts are compiling.");
                }

                var parameters = JsonUtility.FromJson<QualitySettingsParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new QualitySettingsParams();

                QualitySettingsResult result;
                switch (parameters.operation?.ToLower())
                {
                    case "list":
                        result = ExecuteList();
                        break;
                    case "get":
                        result = ExecuteGet();
                        break;
                    case "set-level":
                        result = ExecuteSetLevel(parameters);
                        break;
                    default:
                        result = new QualitySettingsResult
                        {
                            success = false,
                            operation = parameters.operation,
                            message = $"Unknown operation: {parameters.operation}. "
                                + "Supported: list, get, set-level"
                        };
                        break;
                }

                var resultJson = JsonUtility.ToJson(result);
                return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"QualitySettings error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private QualitySettingsResult ExecuteList()
        {
            var names = QualitySettings.names;
            var result = new QualitySettingsResult
            {
                success = true,
                operation = "list",
                currentLevel = QualitySettings.GetQualityLevel()
            };

            for (int i = 0; i < names.Length; i++)
            {
                result.levels.Add(new QualityLevelInfo
                {
                    index = i,
                    name = names[i],
                    isActive = i == QualitySettings.GetQualityLevel()
                });
            }

            result.message = $"Found {names.Length} quality levels";
            return result;
        }

        private QualitySettingsResult ExecuteGet()
        {
            var result = new QualitySettingsResult
            {
                success = true,
                operation = "get",
                currentLevel = QualitySettings.GetQualityLevel(),
                currentLevelName = QualitySettings.names[QualitySettings.GetQualityLevel()],
                shadowQuality = QualitySettings.shadows.ToString(),
                shadowResolution = QualitySettings.shadowResolution.ToString(),
                shadowDistance = QualitySettings.shadowDistance,
                antiAliasing = QualitySettings.antiAliasing,
                softParticles = QualitySettings.softParticles,
                vSyncCount = QualitySettings.vSyncCount,
                lodBias = QualitySettings.lodBias,
                maximumLodLevel = QualitySettings.maximumLODLevel,
                particleRaycastBudget = QualitySettings.particleRaycastBudget,
                anisotropicFiltering = QualitySettings.anisotropicFiltering.ToString(),
                globalTextureMipmapLimit = QualitySettings.globalTextureMipmapLimit,
                pixelLightCount = QualitySettings.pixelLightCount,
                realtimeReflectionProbes = QualitySettings.realtimeReflectionProbes,
                billboardsFaceCameraPosition = QualitySettings.billboardsFaceCameraPosition,
                streamingMipmapsActive = QualitySettings.streamingMipmapsActive,
                message = "Quality settings retrieved"
            };

            return result;
        }

        private QualitySettingsResult ExecuteSetLevel(QualitySettingsParams parameters)
        {
            if (EditorApplication.isPlaying)
            {
                return new QualitySettingsResult
                {
                    success = false,
                    operation = "set-level",
                    message = "Cannot change quality level in play mode."
                };
            }

            var names = QualitySettings.names;
            if (parameters.level < 0 || parameters.level >= names.Length)
            {
                return new QualitySettingsResult
                {
                    success = false,
                    operation = "set-level",
                    message = $"Invalid level {parameters.level}. "
                        + $"Valid range: 0-{names.Length - 1}"
                };
            }

            QualitySettings.SetQualityLevel(parameters.level, true);

            return new QualitySettingsResult
            {
                success = true,
                operation = "set-level",
                currentLevel = QualitySettings.GetQualityLevel(),
                currentLevelName = QualitySettings.names[QualitySettings.GetQualityLevel()],
                message = $"Quality level set to {parameters.level} "
                    + $"({QualitySettings.names[parameters.level]})"
            };
        }
    }

    // -----------------------------------------------------------------
    // Models
    // -----------------------------------------------------------------

    [Serializable]
    public class QualitySettingsParams
    {
        public string operation;
        public int level = -1;
    }

    [Serializable]
    public class QualitySettingsResult
    {
        public bool success;
        public string operation;
        public string message;
        public int currentLevel;
        public string currentLevelName;

        // list
        public List<QualityLevelInfo> levels = new List<QualityLevelInfo>();

        // get detail
        public string shadowQuality;
        public string shadowResolution;
        public float shadowDistance;
        public int antiAliasing;
        public bool softParticles;
        public int vSyncCount;
        public float lodBias;
        public int maximumLodLevel;
        public int particleRaycastBudget;
        public string anisotropicFiltering;
        public int globalTextureMipmapLimit;
        public int pixelLightCount;
        public bool realtimeReflectionProbes;
        public bool billboardsFaceCameraPosition;
        public bool streamingMipmapsActive;
    }

    [Serializable]
    public class QualityLevelInfo
    {
        public int index;
        public string name;
        public bool isActive;
    }
}
