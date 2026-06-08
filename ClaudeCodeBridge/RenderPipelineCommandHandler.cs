using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for focused render pipeline asset and project setting operations.
    /// </summary>
    public class RenderPipelineCommandHandler : ICommandHandler
    {
        private const string GraphicsSettingsPath = "ProjectSettings/GraphicsSettings.asset";
        private const string QualitySettingsPath = "ProjectSettings/QualitySettings.asset";

        public string CommandType => "render-pipeline";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot access render pipeline settings while scripts are compiling.");
                }

                var parameters = JsonUtility.FromJson<RenderPipelineParams>(
                    command.parametersJson ?? "{}") ?? new RenderPipelineParams();

                RenderPipelineResult result;
                switch (parameters.operation?.ToLowerInvariant())
                {
                    case "list-assets":
                        result = ExecuteListAssets();
                        break;
                    case "get-current":
                        result = ExecuteGetCurrent();
                        break;
                    case "set-default":
                        result = ExecuteSetDefault(parameters);
                        break;
                    case "set-quality":
                        result = ExecuteSetQuality(parameters);
                        break;
                    case "inspect":
                        result = ExecuteInspect(parameters);
                        break;
                    default:
                        result = ErrorResult(parameters.operation,
                            "Supported: list-assets, get-current, set-default, "
                            + "set-quality, inspect");
                        break;
                }

                return BridgeResponse.Success(command.commandId, command.commandType,
                    JsonUtility.ToJson(result));
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"RenderPipeline error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.Message);
            }
        }

        private RenderPipelineResult ExecuteListAssets()
        {
            var result = SuccessResult("list-assets", "Render pipeline assets listed");
            foreach (var path in FindRenderPipelineAssetPaths())
                result.assets.Add(CreateAssetInfo(LoadRenderPipelineAsset(path), path));

            result.message = $"Found {result.assets.Count} render pipeline assets";
            return result;
        }

        private RenderPipelineResult ExecuteGetCurrent()
        {
            return new RenderPipelineResult
            {
                success = true,
                operation = "get-current",
                current = CreateCurrentState(),
                message = "Render pipeline state retrieved"
            };
        }

        private RenderPipelineResult ExecuteSetDefault(RenderPipelineParams p)
        {
            if (!CanMutate("set-default", out var error))
                return error;

            if (!TryResolveAssetPath(p.assetPath, "set-default", out var asset, out error))
                return error;

            var settings = BeginSettingsChange(GraphicsSettingsPath, "Set Default Render Pipeline");
            GraphicsSettings.defaultRenderPipeline = asset;
            EndSettingsChange(settings);

            var result = ExecuteGetCurrent();
            result.operation = "set-default";
            result.asset = CreateAssetInfo(asset, GetAssetPath(asset));
            result.message = asset == null
                ? "Default render pipeline cleared"
                : $"Default render pipeline set to {result.asset.assetPath}";
            return result;
        }

        private RenderPipelineResult ExecuteSetQuality(RenderPipelineParams p)
        {
            if (!CanMutate("set-quality", out var error))
                return error;

            if (!TryResolveQualityLevel(p.qualityLevel, out var level, out var levelMessage))
                return ErrorResult("set-quality", levelMessage);

            if (!TryResolveAssetPath(p.assetPath, "set-quality", out var asset, out error))
                return error;

            var settings = BeginSettingsChange(QualitySettingsPath, "Set Quality Render Pipeline");
            if (!string.IsNullOrWhiteSpace(p.qualityLevel)
                && level != QualitySettings.GetQualityLevel())
            {
                QualitySettings.SetQualityLevel(level, true);
            }
            QualitySettings.renderPipeline = asset;
            EndSettingsChange(settings);

            var result = ExecuteGetCurrent();
            result.operation = "set-quality";
            result.asset = CreateAssetInfo(asset, GetAssetPath(asset), level);
            result.message = asset == null
                ? $"Quality render pipeline cleared for {QualitySettings.names[level]}"
                : $"Quality render pipeline set to {result.asset.assetPath}";
            return result;
        }

        private RenderPipelineResult ExecuteInspect(RenderPipelineParams p)
        {
            if (!TryResolveAssetPath(p.assetPath, "inspect", out var asset, out var error)
                || asset == null)
            {
                return error ?? ErrorResult("inspect", "assetPath is required");
            }

            return new RenderPipelineResult
            {
                success = true,
                operation = "inspect",
                asset = CreateAssetInfo(asset, p.assetPath),
                message = $"Render pipeline asset inspected: {p.assetPath}"
            };
        }

        private static bool CanMutate(string operation, out RenderPipelineResult error)
        {
            if (EditorApplication.isPlaying)
            {
                error = ErrorResult(operation,
                    "Cannot modify render pipeline settings in play mode.");
                return false;
            }

            error = null;
            return true;
        }

        private static bool TryResolveAssetPath(
            string assetPath,
            string operation,
            out RenderPipelineAsset asset,
            out RenderPipelineResult error)
        {
            asset = null;
            error = null;
            if (IsBuiltInValue(assetPath))
                return true;

            if (string.IsNullOrWhiteSpace(assetPath))
            {
                error = ErrorResult(operation, "assetPath is required");
                return false;
            }

            asset = LoadRenderPipelineAsset(assetPath);
            if (asset != null)
                return true;

            error = ErrorResult(operation,
                $"No RenderPipelineAsset found at assetPath: {assetPath}");
            return false;
        }

        private static bool TryResolveQualityLevel(
            string qualityLevel,
            out int level,
            out string message)
        {
            level = QualitySettings.GetQualityLevel();
            message = null;
            if (string.IsNullOrWhiteSpace(qualityLevel))
                return true;

            var names = QualitySettings.names;
            if (int.TryParse(qualityLevel, out var parsed))
                return ValidateQualityLevel(parsed, names, out level, out message);

            for (var i = 0; i < names.Length; i++)
            {
                if (!string.Equals(names[i], qualityLevel, StringComparison.OrdinalIgnoreCase))
                    continue;
                level = i;
                return true;
            }

            message = $"Unknown qualityLevel '{qualityLevel}'. Use a quality level name or index.";
            return false;
        }

        private static bool ValidateQualityLevel(
            int parsed,
            string[] names,
            out int level,
            out string message)
        {
            level = parsed;
            message = null;
            if (parsed >= 0 && parsed < names.Length)
                return true;

            message = $"Invalid qualityLevel {parsed}. Valid range: 0-{names.Length - 1}";
            return false;
        }

        private static RenderPipelineCurrentState CreateCurrentState()
        {
            var state = new RenderPipelineCurrentState
            {
                defaultRenderPipeline = GetAssetPath(GraphicsSettings.defaultRenderPipeline),
                currentRenderPipeline = GetAssetPath(GraphicsSettings.currentRenderPipeline),
                currentRenderPipelineAssetType = GetCurrentPipelineAssetType(),
                qualityRenderPipeline = GetAssetPath(QualitySettings.renderPipeline),
                qualityLevel = QualitySettings.GetQualityLevel().ToString(),
                qualityLevelName = GetActiveQualityName()
            };

            var configured = GraphicsSettings.allConfiguredRenderPipelines;
            if (configured == null)
                return state;

            foreach (var asset in configured)
                state.allConfiguredRenderPipelines.Add(CreateAssetInfo(asset, GetAssetPath(asset)));

            return state;
        }

        private static RenderPipelineAssetInfo CreateAssetInfo(
            RenderPipelineAsset asset,
            string assetPath,
            int qualityLevel = -1)
        {
            var activeQualityLevel = QualitySettings.GetQualityLevel();
            var qualityOverride = QualitySettings.renderPipeline;
            return new RenderPipelineAssetInfo
            {
                assetPath = assetPath ?? "",
                name = asset != null ? asset.name : "Built-in",
                typeName = asset != null ? asset.GetType().FullName : "Built-in",
                isDefault = asset != null && asset == GraphicsSettings.defaultRenderPipeline,
                isCurrent = asset != null && asset == GraphicsSettings.currentRenderPipeline,
                isQualityOverride = asset != null && asset == qualityOverride,
                qualityLevel = ResolveAssetQualityLevel(asset, qualityLevel, activeQualityLevel)
            };
        }

        private static string ResolveAssetQualityLevel(
            RenderPipelineAsset asset,
            int qualityLevel,
            int activeQualityLevel)
        {
            if (qualityLevel >= 0)
                return qualityLevel.ToString();
            return asset != null && asset == QualitySettings.renderPipeline
                ? activeQualityLevel.ToString()
                : "";
        }

        private static UnityEngine.Object BeginSettingsChange(string assetPath, string undoName)
        {
            var settings = AssetDatabase.LoadMainAssetAtPath(assetPath);
            if (settings != null)
                Undo.RecordObject(settings, undoName);
            return settings;
        }

        private static void EndSettingsChange(UnityEngine.Object settings)
        {
            if (settings != null)
                EditorUtility.SetDirty(settings);
            AssetDatabase.SaveAssets();
        }

        private static string[] FindRenderPipelineAssetPaths()
        {
            var guids = AssetDatabase.FindAssets("t:RenderPipelineAsset");
            var paths = new List<string>();
            foreach (var guid in guids)
                paths.Add(AssetDatabase.GUIDToAssetPath(guid));
            paths.Sort(StringComparer.OrdinalIgnoreCase);
            return paths.ToArray();
        }

        private static RenderPipelineAsset LoadRenderPipelineAsset(string assetPath)
        {
            return AssetDatabase.LoadAssetAtPath<RenderPipelineAsset>(assetPath);
        }

        private static string GetAssetPath(RenderPipelineAsset asset)
        {
            return asset != null ? AssetDatabase.GetAssetPath(asset) : "";
        }

        private static string GetCurrentPipelineAssetType()
        {
            var type = GraphicsSettings.currentRenderPipelineAssetType;
            return type != null ? type.FullName : "Built-in";
        }

        private static string GetActiveQualityName()
        {
            var level = QualitySettings.GetQualityLevel();
            var names = QualitySettings.names;
            return level >= 0 && level < names.Length ? names[level] : "";
        }

        private static bool IsBuiltInValue(string value)
        {
            return string.Equals(value, "none", StringComparison.OrdinalIgnoreCase)
                || string.Equals(value, "builtin", StringComparison.OrdinalIgnoreCase);
        }

        private static RenderPipelineResult SuccessResult(string operation, string message)
        {
            return new RenderPipelineResult
            {
                success = true,
                operation = operation,
                message = message
            };
        }

        private static RenderPipelineResult ErrorResult(string operation, string message)
        {
            return new RenderPipelineResult
            {
                success = false,
                operation = operation,
                message = message
            };
        }
    }

    [Serializable]
    public class RenderPipelineParams
    {
        public string operation;
        public string assetPath;
        public string qualityLevel;
    }

    [Serializable]
    public class RenderPipelineResult
    {
        public bool success;
        public string operation;
        public RenderPipelineCurrentState current;
        public List<RenderPipelineAssetInfo> assets = new List<RenderPipelineAssetInfo>();
        public RenderPipelineAssetInfo asset;
        public string message;
    }

    [Serializable]
    public class RenderPipelineCurrentState
    {
        public string defaultRenderPipeline;
        public string currentRenderPipeline;
        public string qualityRenderPipeline;
        public string currentRenderPipelineAssetType;
        public string qualityLevel;
        public string qualityLevelName;
        public List<RenderPipelineAssetInfo> allConfiguredRenderPipelines =
            new List<RenderPipelineAssetInfo>();
    }

    [Serializable]
    public class RenderPipelineAssetInfo
    {
        public string assetPath;
        public string name;
        public string typeName;
        public bool isDefault;
        public bool isCurrent;
        public bool isQualityOverride;
        public string qualityLevel;
    }
}
