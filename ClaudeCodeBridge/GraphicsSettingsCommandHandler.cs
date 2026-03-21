using System;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for graphics and render pipeline settings.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "get" - Read current graphics settings
    /// 2. "set" - Modify graphics settings
    ///
    /// GUARDS:
    /// - EditorApplication.isCompiling: blocks all operations
    /// - EditorApplication.isPlaying: blocks set operation
    /// </summary>
    public class GraphicsSettingsCommandHandler : ICommandHandler
    {
        public string CommandType => "graphics-settings";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot access graphics settings while scripts are compiling.");
                }

                var parameters = JsonUtility.FromJson<GraphicsSettingsParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new GraphicsSettingsParams();

                GraphicsSettingsResult result;
                switch (parameters.operation?.ToLower())
                {
                    case "get":
                        result = ExecuteGet();
                        break;
                    case "set":
                        result = ExecuteSet(parameters);
                        break;
                    default:
                        result = new GraphicsSettingsResult
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
                BridgeLogger.LogError($"GraphicsSettings error: {ex}");
                return BridgeResponse.Error(
                    command.commandId, command.commandType, ex.ToString());
            }
        }

        private GraphicsSettingsResult ExecuteGet()
        {
            var defaultRP = GraphicsSettings.defaultRenderPipeline;
            var currentRP = GraphicsSettings.currentRenderPipeline;

            return new GraphicsSettingsResult
            {
                success = true,
                operation = "get",
                defaultRenderPipeline = defaultRP is not null
                    ? AssetDatabase.GetAssetPath(defaultRP) : "",
                defaultRenderPipelineName = defaultRP is not null
                    ? defaultRP.name : "Built-in",
                currentRenderPipeline = currentRP is not null
                    ? AssetDatabase.GetAssetPath(currentRP) : "",
                currentRenderPipelineName = currentRP is not null
                    ? currentRP.name : "Built-in",
                transparencySortMode =
                    GraphicsSettings.transparencySortMode.ToString(),
                transparencySortAxisX =
                    GraphicsSettings.transparencySortAxis.x,
                transparencySortAxisY =
                    GraphicsSettings.transparencySortAxis.y,
                transparencySortAxisZ =
                    GraphicsSettings.transparencySortAxis.z,
                useScriptableRenderPipelineBatching =
                    GraphicsSettings.useScriptableRenderPipelineBatching,
                logWhenShaderIsCompiled =
                    GraphicsSettings.logWhenShaderIsCompiled,
                qualityRenderPipeline = GetQualityRenderPipeline(),
                message = "Graphics settings retrieved"
            };
        }

        private GraphicsSettingsResult ExecuteSet(GraphicsSettingsParams p)
        {
            if (EditorApplication.isPlaying)
            {
                return new GraphicsSettingsResult
                {
                    success = false,
                    operation = "set",
                    message = "Cannot modify graphics settings in play mode."
                };
            }

            if (!string.IsNullOrEmpty(p.defaultRenderPipeline))
            {
                SetDefaultRenderPipeline(p.defaultRenderPipeline);
            }

            if (p.setTransparencySortMode)
            {
                GraphicsSettings.transparencySortMode =
                    (TransparencySortMode)Enum.Parse(
                        typeof(TransparencySortMode),
                        p.transparencySortMode, true);
            }

            if (p.setTransparencySortAxis)
            {
                GraphicsSettings.transparencySortAxis = new Vector3(
                    p.transparencySortAxisX,
                    p.transparencySortAxisY,
                    p.transparencySortAxisZ);
            }

            if (p.setSrpBatching)
            {
                GraphicsSettings.useScriptableRenderPipelineBatching =
                    p.useScriptableRenderPipelineBatching;
            }

            if (p.setLogShaderCompilation)
            {
                GraphicsSettings.logWhenShaderIsCompiled =
                    p.logWhenShaderIsCompiled;
            }

            var result = ExecuteGet();
            result.operation = "set";
            result.message = "Graphics settings updated";
            return result;
        }

        private static string GetQualityRenderPipeline()
        {
            var rp = QualitySettings.renderPipeline;
            if (rp is not null)
                return AssetDatabase.GetAssetPath(rp);
            return "";
        }

        private static void SetDefaultRenderPipeline(string assetPath)
        {
            if (assetPath == "none" || assetPath == "builtin")
            {
                GraphicsSettings.defaultRenderPipeline = null;
                return;
            }

            var asset = AssetDatabase.LoadAssetAtPath<RenderPipelineAsset>(
                assetPath);
            if (asset is null)
            {
                throw new ArgumentException(
                    $"No RenderPipelineAsset found at: {assetPath}");
            }
            GraphicsSettings.defaultRenderPipeline = asset;
        }
    }

    // -----------------------------------------------------------------
    // Models
    // -----------------------------------------------------------------

    [Serializable]
    public class GraphicsSettingsParams
    {
        public string operation;

        // set: render pipeline
        public string defaultRenderPipeline;

        // set: transparency sort
        public string transparencySortMode;
        public bool setTransparencySortMode;
        public float transparencySortAxisX;
        public float transparencySortAxisY;
        public float transparencySortAxisZ;
        public bool setTransparencySortAxis;

        // set: SRP batching
        public bool useScriptableRenderPipelineBatching;
        public bool setSrpBatching;

        // set: shader log
        public bool logWhenShaderIsCompiled;
        public bool setLogShaderCompilation;
    }

    [Serializable]
    public class GraphicsSettingsResult
    {
        public bool success;
        public string operation;
        public string message;

        public string defaultRenderPipeline;
        public string defaultRenderPipelineName;
        public string currentRenderPipeline;
        public string currentRenderPipelineName;
        public string transparencySortMode;
        public float transparencySortAxisX;
        public float transparencySortAxisY;
        public float transparencySortAxisZ;
        public bool useScriptableRenderPipelineBatching;
        public bool logWhenShaderIsCompiled;
        public string qualityRenderPipeline;
    }
}
