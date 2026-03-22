using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
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
            return CreateAssetByType(typeName, null);
        }

        private static UnityEngine.Object CreateAssetByType(
            string typeName, AssetExtendedOperationParams parameters)
        {
            switch (typeName.ToLower())
            {
                case "scriptableobject":
                    return ScriptableObject.CreateInstance<ScriptableObject>();
                case "material":
                    return new Material(Shader.Find("Standard"));
                case "animatorcontroller":
                    return new UnityEditor.Animations.AnimatorController();
                case "physicsmaterial":
                case "physicmaterial":
                    return new PhysicMaterial();
                case "physicsmaterial2d":
                case "physicmaterial2d":
                    return new PhysicsMaterial2D();
                case "animationclip":
                    return new AnimationClip();
                case "rendertexture":
                    int w = (parameters?.renderTextureWidth > 0) ? parameters.renderTextureWidth : 256;
                    int h = (parameters?.renderTextureHeight > 0) ? parameters.renderTextureHeight : 256;
                    int d = (parameters?.renderTextureDepth >= 0 && parameters != null) ? parameters.renderTextureDepth : 0;
                    return new RenderTexture(w, h, d);
                default:
                    return TryCreateScriptableObjectSubtype(typeName);
            }
        }

        private static UnityEngine.Object TryCreateScriptableObjectSubtype(string typeName)
        {
            var type = ResolveType(typeName);
            if (type is null) return null;
            if (!typeof(ScriptableObject).IsAssignableFrom(type)) return null;
            return ScriptableObject.CreateInstance(type);
        }

        private static Type ResolveType(string typeName)
        {
            var type = Type.GetType(typeName);
            if (type is not null) return type;
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                type = asm.GetType(typeName);
                if (type is not null) return type;
            }
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                type = asm.GetTypes().FirstOrDefault(
                    t => t.Name == typeName || t.FullName == typeName);
                if (type is not null) return type;
            }
            return null;
        }

        private static bool TryCreateFileBasedAsset(
            AssetExtendedOperationParams parameters,
            AssetExtendedOperationResult result)
        {
            var typeLower = parameters.assetType.ToLower();
            string content;
            switch (typeLower)
            {
                case "textasset":
                    content = parameters.initialContent ?? "";
                    File.WriteAllText(parameters.assetPath, content);
                    AssetDatabase.ImportAsset(parameters.assetPath);
                    PopulateResult(parameters, result);
                    return true;
                case "shader":
                    var name = Path.GetFileNameWithoutExtension(parameters.assetPath);
                    content = $"Shader \"Custom/{name}\"\n{{\n    SubShader {{}}\n}}\n";
                    File.WriteAllText(parameters.assetPath, content);
                    AssetDatabase.ImportAsset(parameters.assetPath);
                    PopulateResult(parameters, result);
                    return true;
                case "assemblydefinition":
                case "asmdef":
                    var asmName = Path.GetFileNameWithoutExtension(parameters.assetPath);
                    content = $"{{\n    \"name\": \"{asmName}\",\n    \"references\": []\n}}\n";
                    File.WriteAllText(parameters.assetPath, content);
                    AssetDatabase.ImportAsset(parameters.assetPath);
                    PopulateResult(parameters, result);
                    return true;
                case "assemblydefinitionreference":
                case "asmref":
                    content = "{\n    \"reference\": \"\"\n}\n";
                    File.WriteAllText(parameters.assetPath, content);
                    AssetDatabase.ImportAsset(parameters.assetPath);
                    PopulateResult(parameters, result);
                    return true;
                default:
                    return false;
            }
        }

        private static void PopulateResult(
            AssetExtendedOperationParams p, AssetExtendedOperationResult r)
        {
            AssetDatabase.SaveAssets();
            string guid = AssetDatabase.AssetPathToGUID(p.assetPath);
            r.asset = CreateAssetInfo(p.assetPath, guid);
            r.success = true;
            r.message = $"Created asset: {p.assetPath}";
        }

        private static void EnsureDirectoryExists(string assetPath)
        {
            string directory = Path.GetDirectoryName(assetPath);
            if (!string.IsNullOrEmpty(directory) && !Directory.Exists(directory))
            {
                Directory.CreateDirectory(directory);
            }
        }

        private AssetExtendedOperationResult ExecuteReserialize(
            AssetExtendedOperationParams parameters)
        {
            var result = new AssetExtendedOperationResult
            {
                operation = "reserialize",
                success = false,
            };

            try
            {
                var options = ForceReserializeAssetsOptions.ReserializeAssetsAndMetadata;
                var mode = parameters.reserializeMode?.ToLower();
                if (mode == "assets")
                    options = ForceReserializeAssetsOptions.ReserializeAssets;
                else if (mode == "metadata")
                    options = ForceReserializeAssetsOptions.ReserializeMetadata;

                if (parameters.assetPaths != null && parameters.assetPaths.Count > 0)
                {
                    var missing = new List<string>();
                    foreach (var path in parameters.assetPaths)
                    {
                        if (!File.Exists(path) && !Directory.Exists(path))
                            missing.Add(path);
                    }
                    if (missing.Count > 0)
                    {
                        result.message = $"Assets not found: {string.Join(", ", missing)}";
                        return result;
                    }

                    AssetDatabase.ForceReserializeAssets(parameters.assetPaths, options);
                    result.totalCount = parameters.assetPaths.Count;
                    result.message = $"Reserialized {result.totalCount} assets (mode: {options})";
                }
                else
                {
                    AssetDatabase.ForceReserializeAssets();
                    result.message = $"Reserialized all project assets (mode: {options})";
                }

                result.success = true;
                BridgeLogger.LogInfo(result.message);
                return result;
            }
            catch (Exception ex)
            {
                result.message = $"Reserialize failed: {ex.Message}";
                BridgeLogger.LogError(result.message);
                return result;
            }
        }
    }
}
