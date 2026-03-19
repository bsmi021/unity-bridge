using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for performing operations on Unity assets via AssetDatabase.
    ///
    /// PURPOSE:
    /// Provides Claude Code with the ability to query, inspect, and manage Unity assets
    /// without opening the Unity Editor UI. Enables asset discovery, dependency analysis,
    /// and database operations through the bridge system.
    ///
    /// USE CASES:
    /// - Find assets by path pattern and type (e.g., all prefabs in a folder)
    /// - Analyze asset dependencies to understand what references what
    /// - Trigger asset imports or reimports programmatically
    /// - Refresh the AssetDatabase after external file changes
    /// - Get detailed metadata about specific assets
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "find" - Search for assets matching path patterns and types
    /// 2. "get-dependencies" - Get all dependencies for a specific asset
    /// 3. "import" - Import or reimport an asset
    /// 4. "refresh" - Refresh the entire AssetDatabase
    /// 5. "get-info" - Get detailed information about a specific asset
    ///
    /// COMMAND JSON EXAMPLES:
    ///
    /// Find all prefabs in Assets/Prefabs/:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "asset-operation",
    ///   "timestamp": "2025-10-06T18:00:00Z",
    ///   "parametersJson": "{\"operation\":\"find\",\"assetPath\":\"Assets/Prefabs/\",\"assetType\":\"Prefab\",\"recursive\":true}"
    /// }
    ///
    /// Get dependencies for a specific prefab:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "asset-operation",
    ///   "timestamp": "2025-10-06T18:00:00Z",
    ///   "parametersJson": "{\"operation\":\"get-dependencies\",\"assetPath\":\"Assets/Prefabs/Player.prefab\"}"
    /// }
    ///
    /// Refresh AssetDatabase:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "asset-operation",
    ///   "timestamp": "2025-10-06T18:00:00Z",
    ///   "parametersJson": "{\"operation\":\"refresh\"}"
    /// }
    /// </summary>
    public class AssetOperationCommandHandler : ICommandHandler
    {
        public string CommandType => "asset-operation";

        // Mapping of friendly type names to AssetDatabase filter strings
        private static readonly Dictionary<string, string> TYPE_FILTERS = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
        {
            { "Prefab", "t:Prefab" },
            { "Material", "t:Material" },
            { "Texture", "t:Texture" },
            { "Texture2D", "t:Texture2D" },
            { "ScriptableObject", "t:ScriptableObject" },
            { "Scene", "t:Scene" },
            { "AnimationClip", "t:AnimationClip" },
            { "AudioClip", "t:AudioClip" },
            { "Shader", "t:Shader" },
            { "Mesh", "t:Mesh" },
            { "Font", "t:Font" },
            { "Sprite", "t:Sprite" },
            { "Model", "t:Model" },
            { "GameObject", "t:GameObject" }
        };

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<AssetOperationParams>(command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new AssetOperationParams();

                BridgeLogger.LogDebug($"Executing operation: {parameters.operation}");

                AssetOperationResult result;

                switch (parameters.operation?.ToLower())
                {
                    case "find":
                        result = ExecuteFind(parameters);
                        break;

                    case "get-dependencies":
                        result = ExecuteGetDependencies(parameters);
                        break;

                    case "import":
                        result = ExecuteImport(parameters);
                        break;

                    case "refresh":
                        result = ExecuteRefresh(parameters);
                        break;

                    case "get-info":
                        result = ExecuteGetInfo(parameters);
                        break;

                    default:
                        result = new AssetOperationResult
                        {
                            operation = parameters.operation,
                            success = false,
                            message = $"Unknown operation: {parameters.operation}. Supported operations: find, get-dependencies, import, refresh, get-info"
                        };
                        break;
                }

                var resultJson = JsonUtility.ToJson(result);
                BridgeLogger.LogInfo($"Operation completed: {parameters.operation}, success={result.success}");

                return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        /// <summary>
        /// Find assets matching the specified criteria.
        /// Uses AssetDatabase.FindAssets() with type filtering and path constraints.
        /// </summary>
        private AssetOperationResult ExecuteFind(AssetOperationParams parameters)
        {
            var result = new AssetOperationResult
            {
                operation = "find",
                success = false
            };

            // Validate asset path if provided
            if (!string.IsNullOrEmpty(parameters.assetPath))
            {
                if (!Directory.Exists(parameters.assetPath) && !File.Exists(parameters.assetPath))
                {
                    result.message = $"Asset path does not exist: {parameters.assetPath}";
                    return result;
                }
            }

            // Build search filter
            string searchFilter = "";

            // Add type filter if specified
            if (!string.IsNullOrEmpty(parameters.assetType))
            {
                if (TYPE_FILTERS.TryGetValue(parameters.assetType, out string typeFilter))
                {
                    searchFilter = typeFilter;
                }
                else
                {
                    // Try as a direct type filter
                    searchFilter = $"t:{parameters.assetType}";
                }
            }

            // Add search pattern if specified
            if (!string.IsNullOrEmpty(parameters.searchPattern))
            {
                if (!string.IsNullOrEmpty(searchFilter))
                    searchFilter += " ";
                searchFilter += parameters.searchPattern;
            }

            // Determine search folders
            string[] searchInFolders = null;
            if (!string.IsNullOrEmpty(parameters.assetPath))
            {
                // If assetPath is a file, search in its directory
                if (File.Exists(parameters.assetPath))
                {
                    searchInFolders = new[] { Path.GetDirectoryName(parameters.assetPath) };
                }
                else
                {
                    searchInFolders = new[] { parameters.assetPath };
                }
            }

            // Execute search
            string[] assetGuids;
            if (searchInFolders != null)
            {
                assetGuids = AssetDatabase.FindAssets(searchFilter, searchInFolders);
            }
            else
            {
                assetGuids = AssetDatabase.FindAssets(searchFilter);
            }

            // Build asset info list
            foreach (var guid in assetGuids)
            {
                string assetPath = AssetDatabase.GUIDToAssetPath(guid);

                // Filter by recursive setting
                if (!parameters.recursive && !string.IsNullOrEmpty(parameters.assetPath))
                {
                    string assetDir = Path.GetDirectoryName(assetPath);
                    string searchDir = parameters.assetPath.TrimEnd('/', '\\');
                    if (!string.Equals(assetDir, searchDir, StringComparison.OrdinalIgnoreCase))
                    {
                        continue;
                    }
                }

                var assetInfo = CreateAssetInfo(assetPath, guid);
                if (assetInfo != null)
                {
                    result.assets.Add(assetInfo);
                }
            }

            result.success = true;
            result.message = $"Found {result.assets.Count} assets";
            return result;
        }

        /// <summary>
        /// Get all dependencies for a specific asset.
        /// Uses AssetDatabase.GetDependencies() to analyze references.
        /// </summary>
        private AssetOperationResult ExecuteGetDependencies(AssetOperationParams parameters)
        {
            var result = new AssetOperationResult
            {
                operation = "get-dependencies",
                success = false
            };

            // Validate asset path
            if (string.IsNullOrEmpty(parameters.assetPath))
            {
                result.message = "Asset path is required for get-dependencies operation";
                return result;
            }

            if (!File.Exists(parameters.assetPath))
            {
                result.message = $"Asset file does not exist: {parameters.assetPath}";
                return result;
            }

            // Get dependencies (recursive by default)
            string[] dependencies = AssetDatabase.GetDependencies(parameters.assetPath, recursive: parameters.recursive);

            // Build result
            foreach (var depPath in dependencies)
            {
                // Skip the asset itself
                if (depPath == parameters.assetPath)
                    continue;

                result.dependencies.Add(depPath);

                // Also add to assets list with full info
                string guid = AssetDatabase.AssetPathToGUID(depPath);
                var assetInfo = CreateAssetInfo(depPath, guid);
                if (assetInfo != null)
                {
                    result.assets.Add(assetInfo);
                }
            }

            result.success = true;
            result.message = $"Found {result.dependencies.Count} dependencies";
            return result;
        }

        /// <summary>
        /// Import or reimport a specific asset.
        /// Uses AssetDatabase.ImportAsset() to trigger the import pipeline.
        /// </summary>
        private AssetOperationResult ExecuteImport(AssetOperationParams parameters)
        {
            var result = new AssetOperationResult
            {
                operation = "import",
                success = false
            };

            // Validate asset path
            if (string.IsNullOrEmpty(parameters.assetPath))
            {
                result.message = "Asset path is required for import operation";
                return result;
            }

            if (!File.Exists(parameters.assetPath))
            {
                result.message = $"Asset file does not exist: {parameters.assetPath}";
                return result;
            }

            // Import the asset
            AssetDatabase.ImportAsset(parameters.assetPath, ImportAssetOptions.ForceUpdate);

            // Get asset info after import
            string guid = AssetDatabase.AssetPathToGUID(parameters.assetPath);
            var assetInfo = CreateAssetInfo(parameters.assetPath, guid);
            if (assetInfo != null)
            {
                result.assets.Add(assetInfo);
            }

            result.success = true;
            result.message = $"Successfully imported: {parameters.assetPath}";
            return result;
        }

        /// <summary>
        /// Refresh the entire AssetDatabase.
        /// Uses AssetDatabase.Refresh() to detect external file changes.
        /// </summary>
        private AssetOperationResult ExecuteRefresh(AssetOperationParams parameters)
        {
            var result = new AssetOperationResult
            {
                operation = "refresh",
                success = false
            };

            BridgeLogger.LogDebug("Refreshing AssetDatabase...");

            // Refresh the database
            AssetDatabase.Refresh();

            result.success = true;
            result.message = "AssetDatabase refreshed successfully";
            return result;
        }

        /// <summary>
        /// Get detailed information about a specific asset.
        /// Retrieves metadata including type, GUID, and file size.
        /// </summary>
        private AssetOperationResult ExecuteGetInfo(AssetOperationParams parameters)
        {
            var result = new AssetOperationResult
            {
                operation = "get-info",
                success = false
            };

            // Validate asset path
            if (string.IsNullOrEmpty(parameters.assetPath))
            {
                result.message = "Asset path is required for get-info operation";
                return result;
            }

            if (!File.Exists(parameters.assetPath))
            {
                result.message = $"Asset file does not exist: {parameters.assetPath}";
                return result;
            }

            // Get asset info
            string guid = AssetDatabase.AssetPathToGUID(parameters.assetPath);
            var assetInfo = CreateAssetInfo(parameters.assetPath, guid);

            if (assetInfo != null)
            {
                result.assets.Add(assetInfo);
                result.success = true;
                result.message = $"Retrieved info for: {parameters.assetPath}";
            }
            else
            {
                result.message = $"Failed to retrieve info for: {parameters.assetPath}";
            }

            return result;
        }

        /// <summary>
        /// Create an AssetInfo object for a given asset path and GUID.
        /// Includes path, GUID, type, and file size information.
        /// </summary>
        private AssetInfo CreateAssetInfo(string assetPath, string guid)
        {
            try
            {
                // Get asset type
                var assetType = AssetDatabase.GetMainAssetTypeAtPath(assetPath);
                if (assetType == null)
                    return null;

                // Get file size
                long fileSize = 0;
                if (File.Exists(assetPath))
                {
                    var fileInfo = new FileInfo(assetPath);
                    fileSize = fileInfo.Length;
                }

                return new AssetInfo
                {
                    path = assetPath,
                    guid = guid,
                    type = assetType.Name,
                    fileSize = fileSize
                };
            }
            catch (Exception ex)
            {
                BridgeLogger.LogWarning($"Failed to create asset info for {assetPath}: {ex.Message}");
                return null;
            }
        }
    }
}
