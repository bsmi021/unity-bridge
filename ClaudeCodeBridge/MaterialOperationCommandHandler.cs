using System;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for material operations.
    ///
    /// PURPOSE:
    /// Manages Unity material assets through programmatic operations including creation,
    /// modification of properties (colors, floats, textures, vectors), shader assignment,
    /// and property inspection. This enables automated material workflows, testing, and
    /// configuration management without manual Inspector interaction.
    ///
    /// USE CASES:
    /// - Create materials programmatically for procedural content pipelines
    /// - Modify material properties for automated testing and validation
    /// - Batch update materials during art asset integration
    /// - Inspect material configurations for documentation or analysis
    /// - Change shaders during build-time optimization passes
    /// - Automate material variations for character customization systems
    ///
    /// SUPPORTED OPERATIONS:
    /// - "create" - Create new material asset with specified shader
    /// - "modify" - Update material properties (color, float, texture, vector)
    /// - "get-properties" - Read all properties from existing material
    /// - "set-shader" - Change material's shader and update properties
    ///
    /// COMMAND JSON EXAMPLES:
    ///
    /// 1. Create Material:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "material-operation",
    ///   "timestamp": "2025-10-06T00:00:00Z",
    ///   "parametersJson": "{\"operation\":\"create\",\"materialPath\":\"Assets/Materials/NewMat.mat\",\"shader\":\"Universal Render Pipeline/Lit\"}"
    /// }
    ///
    /// 2. Get Properties:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "material-operation",
    ///   "parametersJson": "{\"operation\":\"get-properties\",\"materialPath\":\"Assets/Materials/Character.mat\"}"
    /// }
    ///
    /// 3. Modify Color:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "material-operation",
    ///   "parametersJson": "{\"operation\":\"modify\",\"materialPath\":\"Assets/Materials/Character.mat\",\"properties\":[{\"name\":\"_Color\",\"type\":\"Color\",\"valueJson\":\"{\\\"r\\\":1.0,\\\"g\\\":0.0,\\\"b\\\":0.0,\\\"a\\\":1.0}\"}]}"
    /// }
    ///
    /// 4. Set Shader:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "material-operation",
    ///   "parametersJson": "{\"operation\":\"set-shader\",\"materialPath\":\"Assets/Materials/Character.mat\",\"shader\":\"Universal Render Pipeline/Unlit\"}"
    /// }
    ///
    /// USAGE FROM POWERSHELL:
    /// See .claude/unity/test-material-operation.ps1 for examples
    /// </summary>
    public class MaterialOperationCommandHandler : ICommandHandler
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

        /// <summary>
        /// Applies a list of properties to a material.
        /// Supports Color, Float, Texture, and Vector property types.
        /// </summary>
        private void ApplyProperties(Material material, System.Collections.Generic.List<MaterialProperty> properties)
        {
            foreach (var prop in properties)
            {
                try
                {
                    // Check if property exists on material
                    if (!material.HasProperty(prop.name))
                    {
                        BridgeLogger.LogWarning($"Property '{prop.name}' does not exist on material with shader '{material.shader.name}'");
                        continue;
                    }

                    // Apply property based on type
                    switch (prop.type.ToLower())
                    {
                        case "color":
                            var color = JsonUtility.FromJson<Color>(prop.valueJson);
                            material.SetColor(prop.name, color);
                            BridgeLogger.LogDebug($"Set color property '{prop.name}' to {color}");
                            break;

                        case "float":
                            var floatValue = float.Parse(prop.valueJson);
                            material.SetFloat(prop.name, floatValue);
                            BridgeLogger.LogDebug($"Set float property '{prop.name}' to {floatValue}");
                            break;

                        case "texture":
                            // For textures, valueJson should be the asset path
                            var texture = AssetDatabase.LoadAssetAtPath<Texture>(prop.valueJson);
                            if (texture != null)
                            {
                                material.SetTexture(prop.name, texture);
                                BridgeLogger.LogDebug($"Set texture property '{prop.name}' to {prop.valueJson}");
                            }
                            else
                            {
                                BridgeLogger.LogWarning($"Texture not found at path: {prop.valueJson}");
                            }
                            break;

                        case "vector":
                            var vector = JsonUtility.FromJson<Vector4>(prop.valueJson);
                            material.SetVector(prop.name, vector);
                            BridgeLogger.LogDebug($"Set vector property '{prop.name}' to {vector}");
                            break;

                        default:
                            BridgeLogger.LogWarning($"Unsupported property type: {prop.type}");
                            break;
                    }
                }
                catch (Exception ex)
                {
                    BridgeLogger.LogError($"Failed to apply property '{prop.name}': {ex.Message}");
                }
            }
        }

        /// <summary>
        /// Retrieves all properties from a material.
        /// Returns a list of MaterialProperty objects with current values.
        /// </summary>
        private System.Collections.Generic.List<MaterialProperty> GetMaterialProperties(Material material)
        {
            var properties = new System.Collections.Generic.List<MaterialProperty>();

            if (material == null || material.shader == null)
                return properties;

            // Iterate through all shader properties
            int propertyCount = UnityEditor.ShaderUtil.GetPropertyCount(material.shader);
            for (int i = 0; i < propertyCount; i++)
            {
                var propName = UnityEditor.ShaderUtil.GetPropertyName(material.shader, i);
                var propType = UnityEditor.ShaderUtil.GetPropertyType(material.shader, i);

                var materialProp = new MaterialProperty
                {
                    name = propName
                };

                // Get value based on type
                try
                {
                    switch (propType)
                    {
                        case UnityEditor.ShaderUtil.ShaderPropertyType.Color:
                            materialProp.type = "Color";
                            var color = material.GetColor(propName);
                            materialProp.valueJson = JsonUtility.ToJson(color);
                            break;

                        case UnityEditor.ShaderUtil.ShaderPropertyType.Float:
                        case UnityEditor.ShaderUtil.ShaderPropertyType.Range:
                            materialProp.type = "Float";
                            materialProp.valueJson = material.GetFloat(propName).ToString();
                            break;

                        case UnityEditor.ShaderUtil.ShaderPropertyType.TexEnv:
                            materialProp.type = "Texture";
                            var tex = material.GetTexture(propName);
                            materialProp.valueJson = tex != null ? AssetDatabase.GetAssetPath(tex) : "null";
                            break;

                        case UnityEditor.ShaderUtil.ShaderPropertyType.Vector:
                            materialProp.type = "Vector";
                            var vec = material.GetVector(propName);
                            materialProp.valueJson = JsonUtility.ToJson(vec);
                            break;

                        default:
                            materialProp.type = propType.ToString();
                            materialProp.valueJson = "unsupported";
                            break;
                    }

                    properties.Add(materialProp);
                }
                catch (Exception ex)
                {
                    BridgeLogger.LogWarning($"Failed to read property '{propName}': {ex.Message}");
                }
            }

            return properties;
        }

        #endregion
    }
}
