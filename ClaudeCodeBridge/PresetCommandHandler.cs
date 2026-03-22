using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.Presets;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for Unity Preset management.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "create" - Create a preset from an existing asset
    /// 2. "apply" - Apply a preset to a target asset
    /// 3. "can-apply" - Check if a preset can be applied to a target
    /// 4. "list-defaults" - List all default presets
    /// </summary>
    public class PresetCommandHandler : ICommandHandler
    {
        public string CommandType => "preset-operation";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<PresetOperationParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new PresetOperationParams();

                var operation = parameters.operation?.ToLower();
                BridgeLogger.LogDebug($"Executing preset-operation: {operation}");

                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot execute while scripts are compiling.");
                }

                switch (operation)
                {
                    case "create":
                        return HandleCreate(command, parameters);
                    case "apply":
                        return HandleApply(command, parameters);
                    case "can-apply":
                        return HandleCanApply(command, parameters);
                    case "list-defaults":
                        return HandleListDefaults(command);
                    default:
                        return BridgeResponse.Error(command.commandId, command.commandType,
                            $"Unknown operation: {parameters.operation}. " +
                            "Supported: create, apply, can-apply, list-defaults");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Preset operation error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse HandleCreate(BridgeCommand command, PresetOperationParams p)
        {
            if (string.IsNullOrEmpty(p.sourcePath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "sourcePath is required for create operation.");
            }
            if (string.IsNullOrEmpty(p.outputPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "outputPath is required for create operation.");
            }

            var source = AssetDatabase.LoadMainAssetAtPath(p.sourcePath);
            if (source == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Source asset not found: {p.sourcePath}");
            }

            var preset = new Preset(source);
            EnsureDirectory(p.outputPath);
            AssetDatabase.CreateAsset(preset, p.outputPath);
            AssetDatabase.SaveAssets();

            var result = new PresetOperationResult
            {
                success = true,
                operation = "create",
                presetPath = p.outputPath,
                sourceType = source.GetType().FullName,
                message = $"Created preset from {p.sourcePath} at {p.outputPath}",
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleApply(BridgeCommand command, PresetOperationParams p)
        {
            if (string.IsNullOrEmpty(p.presetPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "presetPath is required for apply operation.");
            }
            if (string.IsNullOrEmpty(p.targetPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "targetPath is required for apply operation.");
            }

            var preset = AssetDatabase.LoadAssetAtPath<Preset>(p.presetPath);
            if (preset == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Preset not found: {p.presetPath}");
            }

            var target = AssetDatabase.LoadMainAssetAtPath(p.targetPath);
            if (target == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Target asset not found: {p.targetPath}");
            }

            bool applied = preset.ApplyTo(target);
            AssetDatabase.SaveAssets();

            var result = new PresetOperationResult
            {
                success = applied,
                operation = "apply",
                presetPath = p.presetPath,
                targetPath = p.targetPath,
                message = applied
                    ? $"Applied preset to {p.targetPath}"
                    : $"Failed to apply preset to {p.targetPath}",
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleCanApply(BridgeCommand command, PresetOperationParams p)
        {
            if (string.IsNullOrEmpty(p.presetPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "presetPath is required for can-apply operation.");
            }
            if (string.IsNullOrEmpty(p.targetPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "targetPath is required for can-apply operation.");
            }

            var preset = AssetDatabase.LoadAssetAtPath<Preset>(p.presetPath);
            if (preset == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Preset not found: {p.presetPath}");
            }

            var target = AssetDatabase.LoadMainAssetAtPath(p.targetPath);
            if (target == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Target asset not found: {p.targetPath}");
            }

            bool canApply = preset.CanBeAppliedTo(target);
            var result = new PresetOperationResult
            {
                success = true,
                operation = "can-apply",
                presetPath = p.presetPath,
                targetPath = p.targetPath,
                canApply = canApply,
                sourceType = preset.GetTargetFullTypeName(),
                targetType = target.GetType().FullName,
                message = canApply
                    ? $"Preset can be applied to {p.targetPath}"
                    : $"Preset cannot be applied to {p.targetPath}",
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleListDefaults(BridgeCommand command)
        {
            // Find all Preset assets in the project
            var guids = AssetDatabase.FindAssets("t:Preset");
            var items = new List<PresetDefaultInfo>();

            foreach (var guid in guids)
            {
                var path = AssetDatabase.GUIDToAssetPath(guid);
                var preset = AssetDatabase.LoadAssetAtPath<Preset>(path);
                if (preset == null) continue;

                items.Add(new PresetDefaultInfo
                {
                    presetPath = path,
                    targetType = preset.GetTargetFullTypeName(),
                });
            }

            var result = new PresetOperationResult
            {
                success = true,
                operation = "list-defaults",
                defaults = items,
                message = $"Found {items.Count} default presets",
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private static void EnsureDirectory(string assetPath)
        {
            string dir = System.IO.Path.GetDirectoryName(assetPath);
            if (!string.IsNullOrEmpty(dir) && !System.IO.Directory.Exists(dir))
                System.IO.Directory.CreateDirectory(dir);
        }
    }

    #region Preset Models

    [Serializable]
    public class PresetOperationParams
    {
        public string operation;
        public string sourcePath;     // For create: asset to create preset from
        public string outputPath;     // For create: where to save preset
        public string presetPath;     // For apply/can-apply
        public string targetPath;     // For apply/can-apply
    }

    [Serializable]
    public class PresetOperationResult
    {
        public bool success;
        public string operation;
        public string presetPath;
        public string targetPath;
        public string sourceType;
        public string targetType;
        public bool canApply;
        public List<PresetDefaultInfo> defaults = new List<PresetDefaultInfo>();
        public string message;
    }

    [Serializable]
    public class PresetDefaultInfo
    {
        public string presetPath;
        public string targetType;
    }

    #endregion
}
