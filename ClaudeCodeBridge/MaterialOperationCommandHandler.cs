using System;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for material operations.
    /// Supports: create, modify, get-properties, set-shader.
    /// Property helpers in MaterialOperationHelpers.cs (partial class).
    /// </summary>
    public partial class MaterialOperationCommandHandler : ICommandHandler
    {
        public string CommandType => "material-operation";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                // Parse parameters
                var parameters = JsonUtility.FromJson<MaterialOperationParams>(command.parametersJson ?? "{}");
                if (parameters == null || string.IsNullOrEmpty(parameters.operation))
                {
                    return BridgeResponse.Error(command.commandId, command.commandType, "Missing required parameter: operation");
                }

                BridgeLogger.LogDebug($"Executing operation: {parameters.operation} on {parameters.materialPath}");

                // Route to appropriate operation handler
                MaterialOperationResult result;
                switch (parameters.operation.ToLower())
                {
                    case "create":
                        result = CreateMaterial(parameters);
                        break;

                    case "modify":
                        result = ModifyMaterial(parameters);
                        break;

                    case "get-properties":
                        result = GetProperties(parameters);
                        break;

                    case "set-shader":
                        result = SetShader(parameters);
                        break;

                    default:
                        return BridgeResponse.Error(
                            command.commandId,
                            command.commandType,
                            $"Unknown operation: {parameters.operation}. Supported operations: create, modify, get-properties, set-shader"
                        );
                }

                // Serialize result and return response
                var resultJson = JsonUtility.ToJson(result);
                if (result.success)
                {
                    BridgeLogger.LogInfo($"Operation '{parameters.operation}' completed successfully");
                    return BridgeResponse.Success(command.commandId, command.commandType, resultJson);
                }
                else
                {
                    BridgeLogger.LogWarning($"Operation '{parameters.operation}' failed: {result.message}");
                    return BridgeResponse.Error(command.commandId, command.commandType, result.message);
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        #region Operation Handlers

        /// <summary>
        /// Creates a new material asset with the specified shader.
        /// The directory path must already exist.
        /// </summary>
        private MaterialOperationResult CreateMaterial(MaterialOperationParams parameters)
        {
            var result = new MaterialOperationResult
            {
                operation = "create",
                materialPath = parameters.materialPath
            };

            try
            {
                // Validate material path
                if (string.IsNullOrEmpty(parameters.materialPath))
                {
                    result.success = false;
                    result.message = "Material path is required for create operation";
                    return result;
                }

                // Check if material already exists
                if (File.Exists(Path.Combine(Application.dataPath, "..", parameters.materialPath)))
                {
                    result.success = false;
                    result.message = $"Material already exists at path: {parameters.materialPath}";
                    return result;
                }

                // Ensure directory exists
                var directory = Path.GetDirectoryName(parameters.materialPath);
                var fullDirectoryPath = Path.Combine(Application.dataPath, "..", directory);
                if (!Directory.Exists(fullDirectoryPath))
                {
                    Directory.CreateDirectory(fullDirectoryPath);
                    AssetDatabase.Refresh();
                }

                // Find shader (default to URP Lit if not specified)
                var shaderName = string.IsNullOrEmpty(parameters.shader) ? "Universal Render Pipeline/Lit" : parameters.shader;
                var shader = Shader.Find(shaderName);
                if (shader == null)
                {
                    result.success = false;
                    result.message = $"Shader not found: {shaderName}";
                    return result;
                }

                // Create material
                var material = new Material(shader);

                // Apply any initial properties
                if (parameters.properties != null && parameters.properties.Count > 0)
                {
                    ApplyProperties(material, parameters.properties);
                }

                // Save asset
                AssetDatabase.CreateAsset(material, parameters.materialPath);
                AssetDatabase.SaveAssets();
                AssetDatabase.Refresh();

                result.success = true;
                result.shaderName = material.shader.name;
                result.message = $"Material created successfully at {parameters.materialPath}";
                result.properties = GetMaterialProperties(material);

                BridgeLogger.LogDebug($"Created material: {parameters.materialPath} with shader {shaderName}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to create material: {ex.Message}";
                BridgeLogger.LogError($"Create failed: {ex}");
            }

            return result;
        }

        /// <summary>
        /// Modifies properties on an existing material.
        /// Supports Color, Float, Texture, and Vector properties.
        /// </summary>
        private MaterialOperationResult ModifyMaterial(MaterialOperationParams parameters)
        {
            var result = new MaterialOperationResult
            {
                operation = "modify",
                materialPath = parameters.materialPath
            };

            try
            {
                // Load material
                var material = LoadMaterial(parameters.materialPath);
                if (material == null)
                {
                    result.success = false;
                    result.message = $"Material not found at path: {parameters.materialPath}";
                    return result;
                }

                // Apply properties
                if (parameters.properties == null || parameters.properties.Count == 0)
                {
                    result.success = false;
                    result.message = "No properties specified for modify operation";
                    return result;
                }

                ApplyProperties(material, parameters.properties);

                // Mark dirty and save
                EditorUtility.SetDirty(material);
                AssetDatabase.SaveAssets();

                result.success = true;
                result.shaderName = material.shader.name;
                result.message = $"Modified {parameters.properties.Count} properties";
                result.properties = GetMaterialProperties(material);

                BridgeLogger.LogDebug($"Modified material: {parameters.materialPath}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to modify material: {ex.Message}";
                BridgeLogger.LogError($"Modify failed: {ex}");
            }

            return result;
        }

        /// <summary>
        /// Retrieves all properties from a material.
        /// Returns property names, types, and current values.
        /// </summary>
        private MaterialOperationResult GetProperties(MaterialOperationParams parameters)
        {
            var result = new MaterialOperationResult
            {
                operation = "get-properties",
                materialPath = parameters.materialPath
            };

            try
            {
                // Load material
                var material = LoadMaterial(parameters.materialPath);
                if (material == null)
                {
                    result.success = false;
                    result.message = $"Material not found at path: {parameters.materialPath}";
                    return result;
                }

                // Get properties
                result.properties = GetMaterialProperties(material);
                result.shaderName = material.shader.name;
                result.success = true;
                result.message = $"Retrieved {result.properties.Count} properties";

                BridgeLogger.LogDebug($"Retrieved properties from: {parameters.materialPath}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to get properties: {ex.Message}";
                BridgeLogger.LogError($"Get properties failed: {ex}");
            }

            return result;
        }

        /// <summary>
        /// Changes the shader on a material.
        /// Note: This may reset some properties if they don't exist on the new shader.
        /// </summary>
        private MaterialOperationResult SetShader(MaterialOperationParams parameters)
        {
            var result = new MaterialOperationResult
            {
                operation = "set-shader",
                materialPath = parameters.materialPath
            };

            try
            {
                // Load material
                var material = LoadMaterial(parameters.materialPath);
                if (material == null)
                {
                    result.success = false;
                    result.message = $"Material not found at path: {parameters.materialPath}";
                    return result;
                }

                // Validate shader parameter
                if (string.IsNullOrEmpty(parameters.shader))
                {
                    result.success = false;
                    result.message = "Shader name is required for set-shader operation";
                    return result;
                }

                // Find shader
                var shader = Shader.Find(parameters.shader);
                if (shader == null)
                {
                    result.success = false;
                    result.message = $"Shader not found: {parameters.shader}";
                    return result;
                }

                // Set shader
                material.shader = shader;

                // Apply any properties
                if (parameters.properties != null && parameters.properties.Count > 0)
                {
                    ApplyProperties(material, parameters.properties);
                }

                // Mark dirty and save
                EditorUtility.SetDirty(material);
                AssetDatabase.SaveAssets();

                result.success = true;
                result.shaderName = material.shader.name;
                result.message = $"Shader changed to {parameters.shader}";
                result.properties = GetMaterialProperties(material);

                BridgeLogger.LogDebug($"Changed shader on {parameters.materialPath} to {parameters.shader}");
            }
            catch (Exception ex)
            {
                result.success = false;
                result.message = $"Failed to set shader: {ex.Message}";
                BridgeLogger.LogError($"Set shader failed: {ex}");
            }

            return result;
        }

        #endregion

        #region Helper Methods

        /// <summary>
        /// Loads a material from the AssetDatabase.
        /// </summary>
        private Material LoadMaterial(string materialPath)
        {
            if (string.IsNullOrEmpty(materialPath))
                return null;

            return AssetDatabase.LoadAssetAtPath<Material>(materialPath);
        }

        // ApplyProperties and GetMaterialProperties are in
        // MaterialOperationHelpers.cs (partial class).

        #endregion
    }
}
