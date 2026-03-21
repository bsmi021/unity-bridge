using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Partial class: keyword and render queue helpers for MaterialOperationCommandHandler.
    /// </summary>
    public partial class MaterialOperationCommandHandler
    {
        /// <summary>
        /// Enable a shader keyword on a material.
        /// </summary>
        private MaterialOperationResult EnableKeyword(MaterialOperationParams parameters)
        {
            var result = new MaterialOperationResult
            {
                operation = "enable-keyword",
                materialPath = parameters.materialPath
            };

            try
            {
                var material = LoadMaterial(parameters.materialPath);
                if (material == null)
                {
                    result.success = false;
                    result.message = $"Material not found: {parameters.materialPath}";
                    return result;
                }

                if (string.IsNullOrEmpty(parameters.keyword))
                {
                    result.success = false;
                    result.message = "keyword is required for enable-keyword operation";
                    return result;
                }

                material.EnableKeyword(parameters.keyword);
                EditorUtility.SetDirty(material);
                AssetDatabase.SaveAssets();

                result.success = true;
                result.shaderName = material.shader.name;
                result.keywords = GetActiveKeywords(material);
                result.message = $"Enabled keyword: {parameters.keyword}";
                BridgeLogger.LogInfo(result.message);
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to enable keyword: {ex.Message}";
                BridgeLogger.LogError($"Enable keyword failed: {ex}");
            }

            return result;
        }

        /// <summary>
        /// Disable a shader keyword on a material.
        /// </summary>
        private MaterialOperationResult DisableKeyword(MaterialOperationParams parameters)
        {
            var result = new MaterialOperationResult
            {
                operation = "disable-keyword",
                materialPath = parameters.materialPath
            };

            try
            {
                var material = LoadMaterial(parameters.materialPath);
                if (material == null)
                {
                    result.success = false;
                    result.message = $"Material not found: {parameters.materialPath}";
                    return result;
                }

                if (string.IsNullOrEmpty(parameters.keyword))
                {
                    result.success = false;
                    result.message = "keyword is required for disable-keyword operation";
                    return result;
                }

                material.DisableKeyword(parameters.keyword);
                EditorUtility.SetDirty(material);
                AssetDatabase.SaveAssets();

                result.success = true;
                result.shaderName = material.shader.name;
                result.keywords = GetActiveKeywords(material);
                result.message = $"Disabled keyword: {parameters.keyword}";
                BridgeLogger.LogInfo(result.message);
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to disable keyword: {ex.Message}";
                BridgeLogger.LogError($"Disable keyword failed: {ex}");
            }

            return result;
        }

        /// <summary>
        /// Get all active shader keywords on a material.
        /// </summary>
        private MaterialOperationResult GetKeywords(MaterialOperationParams parameters)
        {
            var result = new MaterialOperationResult
            {
                operation = "get-keywords",
                materialPath = parameters.materialPath
            };

            try
            {
                var material = LoadMaterial(parameters.materialPath);
                if (material == null)
                {
                    result.success = false;
                    result.message = $"Material not found: {parameters.materialPath}";
                    return result;
                }

                result.success = true;
                result.shaderName = material.shader.name;
                result.renderQueue = material.renderQueue;
                result.keywords = GetActiveKeywords(material);
                result.message = $"Found {result.keywords.Count} active keywords";
                BridgeLogger.LogDebug(result.message);
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to get keywords: {ex.Message}";
                BridgeLogger.LogError($"Get keywords failed: {ex}");
            }

            return result;
        }

        /// <summary>
        /// Set the render queue value on a material.
        /// </summary>
        private MaterialOperationResult SetRenderQueue(MaterialOperationParams parameters)
        {
            var result = new MaterialOperationResult
            {
                operation = "set-render-queue",
                materialPath = parameters.materialPath
            };

            try
            {
                var material = LoadMaterial(parameters.materialPath);
                if (material == null)
                {
                    result.success = false;
                    result.message = $"Material not found: {parameters.materialPath}";
                    return result;
                }

                if (parameters.renderQueue < 0)
                {
                    result.success = false;
                    result.message = "renderQueue must be >= 0";
                    return result;
                }

                material.renderQueue = parameters.renderQueue;
                EditorUtility.SetDirty(material);
                AssetDatabase.SaveAssets();

                result.success = true;
                result.shaderName = material.shader.name;
                result.renderQueue = material.renderQueue;
                result.message = $"Set render queue to {parameters.renderQueue}";
                BridgeLogger.LogInfo(result.message);
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to set render queue: {ex.Message}";
                BridgeLogger.LogError($"Set render queue failed: {ex}");
            }

            return result;
        }

        /// <summary>
        /// Copy all properties from a source material to the target material.
        /// Both materials must use the same shader.
        /// </summary>
        private MaterialOperationResult CopyProperties(MaterialOperationParams parameters)
        {
            var result = new MaterialOperationResult
            {
                operation = "copy-properties",
                materialPath = parameters.materialPath
            };

            try
            {
                var target = LoadMaterial(parameters.materialPath);
                if (target == null)
                {
                    result.success = false;
                    result.message = $"Target material not found: {parameters.materialPath}";
                    return result;
                }

                if (string.IsNullOrEmpty(parameters.sourceMaterialPath))
                {
                    result.success = false;
                    result.message = "sourceMaterialPath is required for copy-properties";
                    return result;
                }

                var source = LoadMaterial(parameters.sourceMaterialPath);
                if (source == null)
                {
                    result.success = false;
                    result.message = $"Source material not found: {parameters.sourceMaterialPath}";
                    return result;
                }

                target.CopyPropertiesFromMaterial(source);
                EditorUtility.SetDirty(target);
                AssetDatabase.SaveAssets();

                result.success = true;
                result.shaderName = target.shader.name;
                result.renderQueue = target.renderQueue;
                result.keywords = GetActiveKeywords(target);
                result.properties = GetMaterialProperties(target);
                result.message = $"Copied properties from {parameters.sourceMaterialPath}";
                BridgeLogger.LogInfo(result.message);
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to copy properties: {ex.Message}";
                BridgeLogger.LogError($"Copy properties failed: {ex}");
            }

            return result;
        }

        /// <summary>
        /// Extract active shader keywords from a material.
        /// </summary>
        private List<string> GetActiveKeywords(Material material)
        {
            return material.shaderKeywords != null
                ? material.shaderKeywords.ToList()
                : new List<string>();
        }
    }
}
