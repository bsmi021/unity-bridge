using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
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

        private AssetExtendedOperationResult ExecuteImportModel(AssetExtendedOperationParams parameters)
        {
            var result = new AssetExtendedOperationResult { operation = "import-model", success = false };
            var validationError = ValidateModelImport(parameters, out var fullDestinationPath);
            if (!string.IsNullOrEmpty(validationError))
            {
                result.message = validationError;
                return result;
            }

            var fullSourcePath = Path.GetFullPath(parameters.sourcePath);
            var destinationDir = Path.GetDirectoryName(fullDestinationPath);
            if (!string.IsNullOrEmpty(destinationDir))
                Directory.CreateDirectory(destinationDir);

            if (!AssetFileMutationScope.TryBegin(
                fullDestinationPath,
                parameters.overwrite,
                out var mutation,
                out var mutationError))
            {
                result.message = mutationError;
                return result;
            }

            using (mutation)
                return ExecuteModelImportTransaction(
                    parameters, result, fullSourcePath, mutation);
        }

        private static AssetExtendedOperationResult ExecuteModelImportTransaction(
            AssetExtendedOperationParams parameters,
            AssetExtendedOperationResult result,
            string fullSourcePath,
            AssetFileMutationScope mutation)
        {
            try
            {
                mutation.CopyFrom(fullSourcePath);
                ImportModelAsset(parameters.destinationPath);
                PopulateModelImportResult(parameters, result, fullSourcePath);
                if (IsGltfExtension(parameters.destinationPath)
                    && IsDefaultImporter(AssetDatabase.GetImporterType(parameters.destinationPath)))
                {
                    var rollbackError = RollbackModelImport(parameters.destinationPath, mutation);
                    result.asset = null;
                    result.guid = "";
                    result.message = "glTF/glb import requires a ScriptedImporter package."
                        + rollbackError;
                    return result;
                }

                mutation.Commit();
                result.success = true;
                result.message = $"Imported model: {parameters.destinationPath}";
                return result;
            }
            catch (Exception ex)
            {
                var rollbackError = RollbackModelImport(parameters.destinationPath, mutation);
                result.asset = null;
                result.guid = "";
                result.message = $"Model import failed: {ex.Message}{rollbackError}";
                return result;
            }
        }

        private static string ValidateModelImport(
            AssetExtendedOperationParams parameters, out string fullDestinationPath)
        {
            fullDestinationPath = "";
            if (string.IsNullOrEmpty(parameters.sourcePath))
                return "sourcePath is required for import-model operation";
            if (string.IsNullOrEmpty(parameters.destinationPath))
                return "destinationPath is required for import-model operation";
            if (!ProjectAssetPath.TryResolve(
                Application.dataPath,
                parameters.destinationPath,
                out fullDestinationPath,
                out var pathError))
            {
                return pathError;
            }
            if (!File.Exists(parameters.sourcePath))
                return $"Source model file does not exist: {parameters.sourcePath}";
            if (!IsSupportedModelExtension(parameters.destinationPath))
                return $"Unsupported model extension: {Path.GetExtension(parameters.destinationPath)}";
            return null;
        }

        private static void ImportModelAsset(string assetPath)
        {
            AssetDatabase.ImportAsset(
                assetPath,
                ImportAssetOptions.ForceSynchronousImport | ImportAssetOptions.ForceUpdate);
        }

        private static void PopulateModelImportResult(
            AssetExtendedOperationParams parameters,
            AssetExtendedOperationResult result,
            string fullSourcePath)
        {
            var importerType = AssetDatabase.GetImporterType(parameters.destinationPath);
            result.sourcePath = fullSourcePath;
            result.destinationPath = parameters.destinationPath;
            result.assetPath = parameters.destinationPath;
            result.importerType = importerType?.Name ?? "";
            result.guid = AssetDatabase.AssetPathToGUID(parameters.destinationPath);
            result.asset = CreateAssetInfo(parameters.destinationPath, result.guid);
        }

        private static string RollbackModelImport(
            string assetPath, AssetFileMutationScope mutation)
        {
            try
            {
                if (!mutation.DestinationExisted)
                    AssetDatabase.DeleteAsset(assetPath);
                mutation.Rollback();
                if (mutation.DestinationExisted)
                    ImportModelAsset(assetPath);
                else
                    AssetDatabase.Refresh();
                return "";
            }
            catch (Exception ex)
            {
                return $" Rollback failed: {ex.Message}";
            }
        }

        private static bool IsSupportedModelExtension(string path)
        {
            var ext = Path.GetExtension(path).ToLowerInvariant();
            return ext == ".fbx" || ext == ".obj" || ext == ".dae" ||
                ext == ".3ds" || ext == ".dxf" || ext == ".blend" ||
                ext == ".gltf" || ext == ".glb";
        }

        private static bool IsGltfExtension(string path)
        {
            var ext = Path.GetExtension(path).ToLowerInvariant();
            return ext == ".gltf" || ext == ".glb";
        }

        private static bool IsDefaultImporter(Type importerType)
        {
            return importerType == null
                || importerType == typeof(AssetImporter)
                || importerType.Name == "DefaultImporter";
        }

        private AssetExtendedOperationResult ExecuteHash(AssetExtendedOperationParams parameters)
        {
            var result = new AssetExtendedOperationResult { operation = "hash", success = false };

            if (string.IsNullOrEmpty(parameters.assetPath))
            {
                result.message = "assetPath is required for hash operation";
                return result;
            }

            if (!ProjectAssetPath.TryResolve(
                Application.dataPath,
                parameters.assetPath,
                out var fullPath,
                out var pathError))
            {
                result.message = pathError;
                return result;
            }

            if (!File.Exists(fullPath))
            {
                result.message = $"Asset does not exist: {parameters.assetPath}";
                return result;
            }

            result.assetPath = parameters.assetPath;
            result.sha256 = ComputeSha256(fullPath);
            result.fileSizeBytes = new FileInfo(fullPath).Length;
            result.success = true;
            result.message = $"SHA256 computed for {parameters.assetPath}";
            return result;
        }

        private static string ComputeSha256(string fullPath)
        {
            using (var sha = SHA256.Create())
            using (var stream = File.OpenRead(fullPath))
            {
                var hash = sha.ComputeHash(stream);
                return BitConverter.ToString(hash).Replace("-", "").ToLowerInvariant();
            }
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
                    return new PhysicsMaterial();
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
