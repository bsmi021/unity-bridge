using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Partial class: property helpers for MaterialOperationCommandHandler.
    /// </summary>
    public partial class MaterialOperationCommandHandler
    {
        /// <summary>
        /// Applies a list of properties to a material.
        /// Supports Color, Float, Texture, and Vector property types.
        /// </summary>
        private void ApplyProperties(Material material, List<MaterialProperty> properties)
        {
            foreach (var prop in properties)
            {
                try
                {
                    if (!material.HasProperty(prop.name))
                    {
                        BridgeLogger.LogWarning(
                            $"Property '{prop.name}' does not exist on shader '{material.shader.name}'");
                        continue;
                    }

                    switch (prop.type.ToLower())
                    {
                        case "color":
                            var color = JsonUtility.FromJson<Color>(prop.valueJson);
                            material.SetColor(prop.name, color);
                            BridgeLogger.LogDebug($"Set color '{prop.name}' to {color}");
                            break;

                        case "float":
                            var floatValue = float.Parse(prop.valueJson);
                            material.SetFloat(prop.name, floatValue);
                            BridgeLogger.LogDebug($"Set float '{prop.name}' to {floatValue}");
                            break;

                        case "texture":
                            var texture = AssetDatabase.LoadAssetAtPath<Texture>(prop.valueJson);
                            if (texture != null)
                            {
                                material.SetTexture(prop.name, texture);
                                BridgeLogger.LogDebug($"Set texture '{prop.name}' to {prop.valueJson}");
                            }
                            else
                            {
                                BridgeLogger.LogWarning($"Texture not found: {prop.valueJson}");
                            }
                            break;

                        case "vector":
                            var vector = JsonUtility.FromJson<Vector4>(prop.valueJson);
                            material.SetVector(prop.name, vector);
                            BridgeLogger.LogDebug($"Set vector '{prop.name}' to {vector}");
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
        /// Retrieves all properties from a material with current values.
        /// </summary>
        private List<MaterialProperty> GetMaterialProperties(Material material)
        {
            var properties = new List<MaterialProperty>();

            if (material == null || material.shader == null)
                return properties;

            int propertyCount = ShaderUtil.GetPropertyCount(material.shader);
            for (int i = 0; i < propertyCount; i++)
            {
                var propName = ShaderUtil.GetPropertyName(material.shader, i);
                var propType = ShaderUtil.GetPropertyType(material.shader, i);

                var materialProp = new MaterialProperty { name = propName };

                try
                {
                    switch (propType)
                    {
                        case ShaderUtil.ShaderPropertyType.Color:
                            materialProp.type = "Color";
                            materialProp.valueJson = JsonUtility.ToJson(material.GetColor(propName));
                            break;

                        case ShaderUtil.ShaderPropertyType.Float:
                        case ShaderUtil.ShaderPropertyType.Range:
                            materialProp.type = "Float";
                            materialProp.valueJson = material.GetFloat(propName).ToString();
                            break;

                        case ShaderUtil.ShaderPropertyType.TexEnv:
                            materialProp.type = "Texture";
                            var tex = material.GetTexture(propName);
                            materialProp.valueJson = tex != null
                                ? AssetDatabase.GetAssetPath(tex) : "null";
                            break;

                        case ShaderUtil.ShaderPropertyType.Vector:
                            materialProp.type = "Vector";
                            materialProp.valueJson = JsonUtility.ToJson(material.GetVector(propName));
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
    }
}
