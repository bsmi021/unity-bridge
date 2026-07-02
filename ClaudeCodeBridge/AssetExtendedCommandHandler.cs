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
    /// Command handler for extended asset operations via AssetDatabase.
    /// Supports: create, delete, copy, move, deps, guid, folder-create, folder-list, export,
    /// import-package, import-model.
    /// Helper methods in AssetExtendedHelpers.cs (partial class).
    /// </summary>
    public partial class AssetExtendedCommandHandler : ICommandHandler
    {
        public string CommandType => "asset-extended-operation";

        private static readonly HashSet<string> MUTATING_OPERATIONS = new HashSet<string>(
            StringComparer.OrdinalIgnoreCase)
        {
            "create", "delete", "copy", "move",
            "folder-create", "export", "import-package", "import-model", "reserialize"
        };

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, CommandType,
                        "Unity is compiling. Wait for compilation to finish before sending commands.");
                }

                var parameters = JsonUtility.FromJson<AssetExtendedOperationParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new AssetExtendedOperationParams();

                if (EditorApplication.isPlaying &&
                    MUTATING_OPERATIONS.Contains(parameters.operation ?? ""))
                {
                    return BridgeResponse.Error(command.commandId, CommandType,
                        "Cannot perform mutating operations during play mode. Exit play mode first.");
                }

                BridgeLogger.LogDebug($"Asset extended operation: {parameters.operation}");

                AssetExtendedOperationResult result;
                switch (parameters.operation?.ToLower())
                {
                    case "create":
                        result = ExecuteCreate(parameters);
                        break;
                    case "delete":
                        result = ExecuteDelete(parameters);
                        break;
                    case "copy":
                        result = ExecuteCopy(parameters);
                        break;
                    case "move":
                        result = ExecuteMove(parameters);
                        break;
                    case "deps":
                        result = ExecuteDeps(parameters);
                        break;
                    case "guid":
                        result = ExecuteGuid(parameters);
                        break;
                    case "hash":
                        result = ExecuteHash(parameters);
                        break;
                    case "folder-create":
                        result = ExecuteFolderCreate(parameters);
                        break;
                    case "folder-list":
                        result = ExecuteFolderList(parameters);
                        break;
                    case "export":
                        result = ExecuteExport(parameters);
                        break;
                    case "import-package":
                        result = ExecuteImportPackage(parameters);
                        break;
                    case "import-model":
                        result = ExecuteImportModel(parameters);
                        break;
                    case "reserialize":
                        result = ExecuteReserialize(parameters);
                        break;
                    default:
                        result = new AssetExtendedOperationResult
                        {
                            operation = parameters.operation,
                            success = false,
                            message = $"Unknown operation: {parameters.operation}. " +
                                "Supported: create, delete, copy, move, deps, guid, hash, " +
                                "folder-create, folder-list, export, import-package, import-model, " +
                                "reserialize"
                        };
                        break;
                }

                var resultJson = JsonUtility.ToJson(result);
                BridgeLogger.LogInfo($"Asset extended completed: {parameters.operation}, success={result.success}");
                return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Asset extended error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private AssetExtendedOperationResult ExecuteCreate(AssetExtendedOperationParams parameters)
        {
            var result = new AssetExtendedOperationResult { operation = "create", success = false };

            if (string.IsNullOrEmpty(parameters.assetPath))
            {
                result.message = "assetPath is required for create operation";
                return result;
            }

            if (!parameters.assetPath.StartsWith("Assets/"))
            {
                result.message = $"Invalid asset path: '{parameters.assetPath}'. Must start with 'Assets/'.";
                return result;
            }

            if (string.IsNullOrEmpty(parameters.assetType))
            {
                result.message = "assetType is required for create operation";
                return result;
            }

            if (parameters.assetType.ToLower().Contains("prefab"))
            {
                result.message = "CreateAsset cannot create prefabs. " +
                    "Use the prefab command group with PrefabUtility.SaveAsPrefabAsset() instead.";
                return result;
            }

            EnsureDirectoryExists(parameters.assetPath);

            // File-based types (TextAsset, Shader, asmdef, asmref)
            if (TryCreateFileBasedAsset(parameters, result))
                return result;

            var asset = CreateAssetByType(parameters.assetType, parameters);
            if (asset == null)
            {
                result.message = $"Unsupported asset type: {parameters.assetType}";
                return result;
            }

            AssetDatabase.CreateAsset(asset, parameters.assetPath);
            AssetDatabase.SaveAssets();

            string guid = AssetDatabase.AssetPathToGUID(parameters.assetPath);
            result.asset = CreateAssetInfo(parameters.assetPath, guid);
            result.success = true;
            result.message = $"Created asset: {parameters.assetPath}";
            return result;
        }

        private AssetExtendedOperationResult ExecuteDelete(AssetExtendedOperationParams parameters)
        {
            var result = new AssetExtendedOperationResult { operation = "delete", success = false };

            if (string.IsNullOrEmpty(parameters.assetPath))
            {
                result.message = "assetPath is required for delete operation";
                return result;
            }

            if (!parameters.assetPath.StartsWith("Assets/"))
            {
                result.message = $"Invalid asset path: '{parameters.assetPath}'. Must start with 'Assets/'.";
                return result;
            }

            if (!File.Exists(parameters.assetPath) && !Directory.Exists(parameters.assetPath))
            {
                result.message = $"Asset does not exist: {parameters.assetPath}";
                return result;
            }

            result.assetPath = parameters.assetPath;
            result.usedTrash = parameters.useTrash;

            bool deleted;
            if (parameters.useTrash)
            {
                deleted = AssetDatabase.MoveAssetToTrash(parameters.assetPath);
                result.message = deleted
                    ? $"Moved to trash: {parameters.assetPath}"
                    : $"Failed to move to trash: {parameters.assetPath}";
            }
            else
            {
                deleted = AssetDatabase.DeleteAsset(parameters.assetPath);
                result.message = deleted
                    ? $"Deleted: {parameters.assetPath}"
                    : $"Failed to delete: {parameters.assetPath}";
            }

            result.success = deleted;
            return result;
        }

        private AssetExtendedOperationResult ExecuteCopy(AssetExtendedOperationParams parameters)
        {
            var result = new AssetExtendedOperationResult { operation = "copy", success = false };

            if (string.IsNullOrEmpty(parameters.sourcePath))
            {
                result.message = "sourcePath is required for copy operation";
                return result;
            }

            if (string.IsNullOrEmpty(parameters.destinationPath))
            {
                result.message = "destinationPath is required for copy operation";
                return result;
            }

            if (!parameters.sourcePath.StartsWith("Assets/"))
            {
                result.message = $"Invalid source path: '{parameters.sourcePath}'. Must start with 'Assets/'.";
                return result;
            }

            if (!parameters.destinationPath.StartsWith("Assets/"))
            {
                result.message = $"Invalid destination path: '{parameters.destinationPath}'. Must start with 'Assets/'.";
                return result;
            }

            EnsureDirectoryExists(parameters.destinationPath);
            bool copied = AssetDatabase.CopyAsset(parameters.sourcePath, parameters.destinationPath);

            result.sourcePath = parameters.sourcePath;
            result.destinationPath = parameters.destinationPath;

            if (copied)
            {
                string guid = AssetDatabase.AssetPathToGUID(parameters.destinationPath);
                result.asset = CreateAssetInfo(parameters.destinationPath, guid);
                result.success = true;
                result.message = $"Copied to {parameters.destinationPath}";
            }
            else
            {
                result.message = $"Failed to copy {parameters.sourcePath} to {parameters.destinationPath}";
            }

            return result;
        }

        private AssetExtendedOperationResult ExecuteMove(AssetExtendedOperationParams parameters)
        {
            var result = new AssetExtendedOperationResult { operation = "move", success = false };

            if (string.IsNullOrEmpty(parameters.sourcePath))
            {
                result.message = "sourcePath is required for move operation";
                return result;
            }

            if (string.IsNullOrEmpty(parameters.destinationPath))
            {
                result.message = "destinationPath is required for move operation";
                return result;
            }

            if (!parameters.sourcePath.StartsWith("Assets/"))
            {
                result.message = $"Invalid source path: '{parameters.sourcePath}'. Must start with 'Assets/'.";
                return result;
            }

            if (!parameters.destinationPath.StartsWith("Assets/"))
            {
                result.message = $"Invalid destination path: '{parameters.destinationPath}'. Must start with 'Assets/'.";
                return result;
            }

            result.sourcePath = parameters.sourcePath;
            result.destinationPath = parameters.destinationPath;

            // MoveAsset returns "" on success, error message on failure
            string error = AssetDatabase.MoveAsset(parameters.sourcePath, parameters.destinationPath);
            result.errorDetail = error;

            if (string.IsNullOrEmpty(error))
            {
                result.success = true;
                result.message = $"Moved to {parameters.destinationPath}";
            }
            else
            {
                result.success = false;
                result.message = $"Move failed: {error}";
            }

            return result;
        }

        private AssetExtendedOperationResult ExecuteDeps(AssetExtendedOperationParams parameters)
        {
            var result = new AssetExtendedOperationResult { operation = "deps", success = false };

            if (string.IsNullOrEmpty(parameters.assetPath))
            {
                result.message = "assetPath is required for deps operation";
                return result;
            }

            if (!parameters.assetPath.StartsWith("Assets/"))
            {
                result.message = $"Invalid asset path: '{parameters.assetPath}'. Must start with 'Assets/'.";
                return result;
            }

            if (!File.Exists(parameters.assetPath))
            {
                result.message = $"Asset does not exist: {parameters.assetPath}";
                return result;
            }

            result.assetPath = parameters.assetPath;
            string[] depPaths = AssetDatabase.GetDependencies(parameters.assetPath, parameters.recursive);

            foreach (var depPath in depPaths)
            {
                if (depPath == parameters.assetPath)
                    continue;

                string depGuid = AssetDatabase.AssetPathToGUID(depPath);
                var info = CreateAssetInfo(depPath, depGuid);
                if (info is not null)
                {
                    result.dependencies.Add(info);
                }
            }

            result.totalCount = result.dependencies.Count;
            result.success = true;
            result.message = $"Found {result.totalCount} dependencies for {parameters.assetPath}";
            return result;
        }

        private AssetExtendedOperationResult ExecuteGuid(AssetExtendedOperationParams parameters)
        {
            var result = new AssetExtendedOperationResult { operation = "guid", success = false };

            if (string.IsNullOrEmpty(parameters.input))
            {
                result.message = "input is required for guid operation";
                return result;
            }

            result.input = parameters.input;

            // Detect if input is a GUID (32 hex characters) or a path
            if (IsGuid(parameters.input))
            {
                string assetPath = AssetDatabase.GUIDToAssetPath(parameters.input);
                if (string.IsNullOrEmpty(assetPath))
                {
                    result.message = $"No asset found for GUID: {parameters.input}";
                    return result;
                }
                result.path = assetPath;
                result.guid = parameters.input;
                result.success = true;
                result.message = $"Path: {assetPath}";
            }
            else
            {
                string guid = AssetDatabase.AssetPathToGUID(parameters.input);
                if (string.IsNullOrEmpty(guid))
                {
                    result.message = $"No GUID found for path: {parameters.input}";
                    return result;
                }
                result.path = parameters.input;
                result.guid = guid;
                result.success = true;
                result.message = $"GUID: {guid}";
            }

            return result;
        }

        private AssetExtendedOperationResult ExecuteFolderCreate(AssetExtendedOperationParams parameters)
        {
            var result = new AssetExtendedOperationResult { operation = "folder-create", success = false };

            if (string.IsNullOrEmpty(parameters.folderPath))
            {
                result.message = "folderPath is required for folder-create operation";
                return result;
            }

            if (!parameters.folderPath.StartsWith("Assets/"))
            {
                result.message = $"Invalid folder path: '{parameters.folderPath}'. Must start with 'Assets/'.";
                return result;
            }

            result.folderPath = parameters.folderPath;

            string parentFolder = Path.GetDirectoryName(parameters.folderPath).Replace("\\", "/");
            string folderName = Path.GetFileName(parameters.folderPath);

            string guid = AssetDatabase.CreateFolder(parentFolder, folderName);
            if (string.IsNullOrEmpty(guid))
            {
                result.message = $"Failed to create folder: {parameters.folderPath}";
                return result;
            }

            result.guid = guid;
            result.success = true;
            result.message = $"Created folder: {parameters.folderPath}";
            return result;
        }

        private AssetExtendedOperationResult ExecuteFolderList(AssetExtendedOperationParams parameters)
        {
            var result = new AssetExtendedOperationResult { operation = "folder-list", success = false };

            if (string.IsNullOrEmpty(parameters.folderPath))
            {
                result.message = "folderPath is required for folder-list operation";
                return result;
            }

            if (!parameters.folderPath.StartsWith("Assets/"))
            {
                result.message = $"Invalid folder path: '{parameters.folderPath}'. Must start with 'Assets/'.";
                return result;
            }

            result.folderPath = parameters.folderPath;
            string[] subfolders = AssetDatabase.GetSubFolders(parameters.folderPath);
            result.subfolders = new List<string>(subfolders);
            result.totalCount = subfolders.Length;
            result.success = true;
            result.message = $"Found {result.totalCount} subfolders";
            return result;
        }

        // ExecuteExport, ExecuteImportPackage, ExecuteImportModel, and utility helpers are in
        // AssetExtendedHelpers.cs (partial class).
    }
}
