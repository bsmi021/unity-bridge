using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for Unity Scene Template operations.
    /// Requires com.unity.scene-template package; operations wrapped in try/catch.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "list" - List available scene templates
    /// 2. "create-from-scene" - Create a template from a scene file
    /// 3. "instantiate" - Create a new scene from a template
    /// </summary>
    public class SceneTemplateCommandHandler : ICommandHandler
    {
        public string CommandType => "scene-template";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<SceneTemplateParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new SceneTemplateParams();

                var operation = parameters.operation?.ToLower();
                BridgeLogger.LogDebug($"Executing scene-template: {operation}");

                if (EditorApplication.isCompiling)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Cannot execute while scripts are compiling.");
                }

                switch (operation)
                {
                    case "list":
                        return HandleList(command);
                    case "create-from-scene":
                        return HandleCreateFromScene(command, parameters);
                    case "instantiate":
                        return HandleInstantiate(command, parameters);
                    default:
                        return BridgeResponse.Error(command.commandId, command.commandType,
                            $"Unknown operation: {parameters.operation}. " +
                            "Supported: list, create-from-scene, instantiate");
                }
            }
            catch (Exception ex)
            {
                if (IsPackageMissing(ex))
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Scene Template operations require the com.unity.scene-template " +
                        "package. Install it via Package Manager.");
                }
                BridgeLogger.LogError($"Scene template error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse HandleList(BridgeCommand command)
        {
            var templates = FindAllSceneTemplates();
            var result = new SceneTemplateResult
            {
                success = true,
                operation = "list",
                templates = templates,
                message = $"Found {templates.Count} scene templates",
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleCreateFromScene(
            BridgeCommand command, SceneTemplateParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.scenePath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "scenePath is required for create-from-scene operation.");
            }
            if (string.IsNullOrEmpty(parameters.outputPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "outputPath is required for create-from-scene operation.");
            }

            if (!File.Exists(parameters.scenePath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Scene file not found: {parameters.scenePath}");
            }

            return CreateTemplateFromScene(command, parameters);
        }

        private BridgeResponse CreateTemplateFromScene(
            BridgeCommand command, SceneTemplateParams parameters)
        {
            // Use SceneTemplateAsset via reflection to stay compatible
            // when the package is or isn't installed.
            try
            {
                var templateType = FindSceneTemplateAssetType();
                if (templateType == null)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "SceneTemplateAsset type not found. " +
                        "Ensure com.unity.scene-template package is installed.");
                }

                var template = ScriptableObject.CreateInstance(templateType);
                var sceneProp = templateType.GetProperty("templateScene");
                if (sceneProp is not null)
                {
                    var sceneAsset = AssetDatabase.LoadAssetAtPath<SceneAsset>(
                        parameters.scenePath);
                    sceneProp.SetValue(template, sceneAsset);
                }

                EnsureDirectory(parameters.outputPath);
                AssetDatabase.CreateAsset(template, parameters.outputPath);
                AssetDatabase.SaveAssets();

                var result = new SceneTemplateResult
                {
                    success = true,
                    operation = "create-from-scene",
                    templatePath = parameters.outputPath,
                    scenePath = parameters.scenePath,
                    message = $"Created scene template from {parameters.scenePath}",
                };
                return BridgeResponse.Success(command.commandId, command.commandType,
                    JsonUtility.ToJson(result));
            }
            catch (Exception ex)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Failed to create scene template: {ex.Message}");
            }
        }

        private BridgeResponse HandleInstantiate(
            BridgeCommand command, SceneTemplateParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.templatePath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "templatePath is required for instantiate operation.");
            }

            try
            {
                var serviceType = FindSceneTemplateServiceType();
                if (serviceType == null)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "SceneTemplateService type not found. " +
                        "Ensure com.unity.scene-template package is installed.");
                }

                var templateAsset = AssetDatabase.LoadMainAssetAtPath(
                    parameters.templatePath);
                if (templateAsset == null)
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        $"Template not found: {parameters.templatePath}");
                }

                var outputPath = parameters.outputPath ?? "";
                var instantiate = serviceType.GetMethod("Instantiate",
                    new[] { templateAsset.GetType(), typeof(bool), typeof(string) });

                if (instantiate is not null)
                {
                    instantiate.Invoke(null, new object[]
                    {
                        templateAsset,
                        !string.IsNullOrEmpty(outputPath), // loadAdditively
                        outputPath,
                    });
                }
                else
                {
                    // Fallback: try simpler overload
                    var simple = serviceType.GetMethod("Instantiate",
                        new[] { templateAsset.GetType() });
                    if (simple is not null)
                        simple.Invoke(null, new object[] { templateAsset });
                    else
                        return BridgeResponse.Error(command.commandId, command.commandType,
                            "Could not find suitable Instantiate method.");
                }

                var result = new SceneTemplateResult
                {
                    success = true,
                    operation = "instantiate",
                    templatePath = parameters.templatePath,
                    message = $"Instantiated scene from template: {parameters.templatePath}",
                };
                return BridgeResponse.Success(command.commandId, command.commandType,
                    JsonUtility.ToJson(result));
            }
            catch (Exception ex)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"Failed to instantiate template: {ex.Message}");
            }
        }

        private static List<SceneTemplateInfo> FindAllSceneTemplates()
        {
            var results = new List<SceneTemplateInfo>();
            var guids = AssetDatabase.FindAssets("t:SceneTemplateAsset");

            foreach (var guid in guids)
            {
                var path = AssetDatabase.GUIDToAssetPath(guid);
                results.Add(new SceneTemplateInfo
                {
                    path = path,
                    name = Path.GetFileNameWithoutExtension(path),
                    guid = guid,
                });
            }
            return results;
        }

        private static Type FindSceneTemplateAssetType()
        {
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                var type = asm.GetType("UnityEditor.SceneTemplate.SceneTemplateAsset");
                if (type is not null) return type;
            }
            return null;
        }

        private static Type FindSceneTemplateServiceType()
        {
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                var type = asm.GetType("UnityEditor.SceneTemplate.SceneTemplateService");
                if (type is not null) return type;
            }
            return null;
        }

        private static bool IsPackageMissing(Exception ex)
        {
            var msg = ex.ToString();
            return msg.Contains("SceneTemplate") && msg.Contains("not found");
        }

        private static void EnsureDirectory(string assetPath)
        {
            string dir = Path.GetDirectoryName(assetPath);
            if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
                Directory.CreateDirectory(dir);
        }
    }

    #region Scene Template Models

    [Serializable]
    public class SceneTemplateParams
    {
        public string operation;
        public string scenePath;      // For create-from-scene
        public string outputPath;     // For create-from-scene, instantiate
        public string templatePath;   // For instantiate
    }

    [Serializable]
    public class SceneTemplateResult
    {
        public bool success;
        public string operation;
        public string templatePath;
        public string scenePath;
        public List<SceneTemplateInfo> templates = new List<SceneTemplateInfo>();
        public string message;
    }

    [Serializable]
    public class SceneTemplateInfo
    {
        public string path;
        public string name;
        public string guid;
    }

    #endregion
}
