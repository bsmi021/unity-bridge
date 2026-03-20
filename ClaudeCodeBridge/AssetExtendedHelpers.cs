using System;
using System.IO;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Partial class: export, import-package, and utility helpers for AssetExtendedCommandHandler.
    /// </summary>
    public partial class AssetExtendedCommandHandler
    {
        private AssetExtendedOperationResult ExecuteExport(AssetExtendedOperationParams parameters)
        {
            var result = new AssetExtendedOperationResult { operation = "export", success = false };

            if (parameters.assetPaths == null || parameters.assetPaths.Count == 0)
            {
                result.message = "assetPaths is required for export operation";
                return result;
            }

            if (string.IsNullOrEmpty(parameters.outputPath))
            {
                result.message = "outputPath is required for export operation";
                return result;
            }

            var flags = ExportPackageOptions.Default;
            if (parameters.includeDependencies)
                flags |= ExportPackageOptions.IncludeDependencies;

            AssetDatabase.ExportPackage(
                parameters.assetPaths.ToArray(), parameters.outputPath, flags);

            result.outputPath = parameters.outputPath;
            result.exportedAssets = parameters.assetPaths.Count;

            if (File.Exists(parameters.outputPath))
            {
                result.fileSizeBytes = new FileInfo(parameters.outputPath).Length;
            }

            result.success = true;
            result.message = $"Exported {result.exportedAssets} assets to {parameters.outputPath}";
            return result;
        }

        private AssetExtendedOperationResult ExecuteImportPackage(AssetExtendedOperationParams parameters)
        {
            var result = new AssetExtendedOperationResult { operation = "import-package", success = false };

            if (string.IsNullOrEmpty(parameters.packagePath))
            {
                result.message = "packagePath is required for import-package operation";
                return result;
            }

            if (!File.Exists(parameters.packagePath))
            {
                result.message = $"Package file does not exist: {parameters.packagePath}";
                return result;
            }

            AssetDatabase.ImportPackage(parameters.packagePath, parameters.interactive);
            result.outputPath = parameters.packagePath;
            result.success = true;
            result.message = $"Imported package: {parameters.packagePath}";
            return result;
        }

        private static bool IsGuid(string input)
        {
            return input.Length == 32 && Regex.IsMatch(input, "^[0-9a-fA-F]{32}$");
        }

        private static AssetInfo CreateAssetInfo(string assetPath, string guid)
        {
            try
            {
                var assetType = AssetDatabase.GetMainAssetTypeAtPath(assetPath);
                long fileSize = 0;
                if (File.Exists(assetPath))
                {
                    fileSize = new FileInfo(assetPath).Length;
                }

                return new AssetInfo
                {
                    path = assetPath,
                    guid = guid,
                    type = assetType?.Name ?? "Unknown",
                    fileSize = fileSize
                };
            }
            catch (Exception ex)
            {
                BridgeLogger.LogWarning($"Failed to create asset info for {assetPath}: {ex.Message}");
                return null;
            }
        }

        private static UnityEngine.Object CreateAssetByType(string typeName)
        {
            switch (typeName.ToLower())
            {
                case "scriptableobject":
                    return ScriptableObject.CreateInstance<ScriptableObject>();
                case "material":
                    return new Material(Shader.Find("Standard"));
                case "animatorcontroller":
                    return new UnityEditor.Animations.AnimatorController();
                default:
                    return null;
            }
        }

        private static void EnsureDirectoryExists(string assetPath)
        {
            string directory = Path.GetDirectoryName(assetPath);
            if (!string.IsNullOrEmpty(directory) && !Directory.Exists(directory))
            {
                Directory.CreateDirectory(directory);
            }
        }
    }
}
