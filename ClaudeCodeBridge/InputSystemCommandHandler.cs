using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for Input System configuration.
    /// Requires com.unity.inputsystem package. Returns error if not installed.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "list-actions" - List all InputActionAssets and their action maps
    /// 2. "get-action-map" - Get details of a specific action map
    /// 3. "export" - Export InputActionAsset as JSON
    /// 4. "import" - Import JSON into an InputActionAsset
    /// 5. Authoring operations: create asset, add maps/actions/bindings/control schemes
    /// </summary>
    public class InputSystemCommandHandler : ICommandHandler
    {
        public string CommandType => "input-system";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                if (!IsInputSystemAvailable())
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        "Input System package (com.unity.inputsystem) is not installed. " +
                        "Install it via Package Manager.");
                }

                var parameters = JsonUtility.FromJson<InputSystemParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new InputSystemParams();

                var operation = parameters.operation?.ToLower();
                BridgeLogger.LogDebug($"Executing input-system: {operation}");

                switch (operation)
                {
                    case "list-actions":
                        return HandleListActions(command);
                    case "get-action-map":
                        return HandleGetActionMap(command, parameters);
                    case "export":
                        return HandleExport(command, parameters);
                    case "import":
                        return HandleImport(command, parameters);
                    case "create-asset":
                    case "add-action-map":
                    case "add-action":
                    case "add-binding":
                    case "add-control-scheme":
                    case "list-control-schemes":
                        return InputSystemAuthoringHelpers.Handle(command, parameters);
                    default:
                        return BridgeResponse.Error(command.commandId, command.commandType,
                            $"Unknown operation: {parameters.operation}. " +
                            "Supported: list-actions, get-action-map, export, import, " +
                            "create-asset, add-action-map, add-action, add-binding, " +
                            "add-control-scheme, list-control-schemes");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Input system error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse HandleListActions(BridgeCommand command)
        {
            var guids = AssetDatabase.FindAssets("t:InputActionAsset");
            var assets = new List<InputActionAssetInfo>();

            foreach (var guid in guids)
            {
                var path = AssetDatabase.GUIDToAssetPath(guid);
                var info = GetAssetInfo(path);
                if (info is not null) assets.Add(info);
            }

            var result = new InputSystemResult
            {
                success = true,
                operation = "list-actions",
                assets = assets,
                message = $"Found {assets.Count} InputActionAssets",
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleGetActionMap(
            BridgeCommand command, InputSystemParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.assetPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "assetPath is required for get-action-map operation.");
            }

            var asset = LoadInputActionAsset(parameters.assetPath);
            if (asset == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"InputActionAsset not found: {parameters.assetPath}");
            }

            // Use ToJson to get full details
            string json = InvokeToJson(asset);
            var result = new InputSystemResult
            {
                success = true,
                operation = "get-action-map",
                json = json,
                message = $"Retrieved action map from {parameters.assetPath}",
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleExport(
            BridgeCommand command, InputSystemParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.assetPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "assetPath is required for export operation.");
            }

            var asset = LoadInputActionAsset(parameters.assetPath);
            if (asset == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"InputActionAsset not found: {parameters.assetPath}");
            }

            string json = InvokeToJson(asset);

            if (!string.IsNullOrEmpty(parameters.outputPath))
            {
                File.WriteAllText(parameters.outputPath, json);
            }

            var result = new InputSystemResult
            {
                success = true,
                operation = "export",
                json = json,
                outputPath = parameters.outputPath ?? "",
                message = !string.IsNullOrEmpty(parameters.outputPath)
                    ? $"Exported to {parameters.outputPath}"
                    : "Exported InputActionAsset as JSON",
            };
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleImport(
            BridgeCommand command, InputSystemParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.assetPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "assetPath is required for import operation.");
            }
            if (string.IsNullOrEmpty(parameters.json) &&
                string.IsNullOrEmpty(parameters.inputPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "json or inputPath is required for import operation.");
            }

            if (EditorApplication.isPlaying)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "Cannot import during play mode.");
            }

            string json = parameters.json;
            if (string.IsNullOrEmpty(json) && !string.IsNullOrEmpty(parameters.inputPath))
            {
                if (!File.Exists(parameters.inputPath))
                {
                    return BridgeResponse.Error(command.commandId, command.commandType,
                        $"Input file not found: {parameters.inputPath}");
                }
                json = File.ReadAllText(parameters.inputPath);
            }

            // InputActionAsset files are just JSON — write directly
            File.WriteAllText(ToFullPath(parameters.assetPath), json);
            AssetDatabase.ImportAsset(parameters.assetPath);
            AssetDatabase.SaveAssets();

            var result = new InputSystemResult
            {
                success = true,
                operation = "import",
                message = $"Imported InputActionAsset to {parameters.assetPath}",
            };
            BridgeLogger.LogInfo($"Input system import: {parameters.assetPath}");
            return BridgeResponse.Success(command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private static bool IsInputSystemAvailable()
        {
            return GetInputActionAssetType() is not null;
        }

        private static Type GetInputActionAssetType()
        {
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                var type = asm.GetType("UnityEngine.InputSystem.InputActionAsset");
                if (type is not null) return type;
            }
            return null;
        }

        private static UnityEngine.Object LoadInputActionAsset(string path)
        {
            var type = GetInputActionAssetType();
            if (type == null) return null;
            return AssetDatabase.LoadAssetAtPath(path, type);
        }

        private static InputActionAssetInfo GetAssetInfo(string path)
        {
            var asset = LoadInputActionAsset(path);
            if (asset == null) return null;

            var info = new InputActionAssetInfo
            {
                path = path,
                name = asset.name,
            };

            // Try to read action map names via ToJson
            try
            {
                string json = InvokeToJson(asset);
                if (!string.IsNullOrEmpty(json))
                    info.jsonLength = json.Length;
            }
            catch { /* ignore */ }

            return info;
        }

        private static string InvokeToJson(UnityEngine.Object asset)
        {
            var type = asset.GetType();
            var method = type.GetMethod("ToJson",
                System.Reflection.BindingFlags.Public |
                System.Reflection.BindingFlags.Instance);
            if (method is not null)
                return method.Invoke(asset, null) as string ?? "";

            // Fallback to EditorJsonUtility
            return EditorJsonUtility.ToJson(asset, true);
        }

        private static string ToFullPath(string assetPath)
        {
            if (Path.IsPathRooted(assetPath)) return assetPath;
            var projectRoot = Directory.GetParent(Application.dataPath).FullName;
            return Path.Combine(projectRoot, assetPath.Replace('/', Path.DirectorySeparatorChar));
        }
    }

    #region Input System Models

    [Serializable]
    public class InputSystemParams
    {
        public string operation;
        public string assetPath;
        public string outputPath;     // For export
        public string inputPath;      // For import: read JSON from file
        public string json;           // For import: inline JSON
        public string actionMap;
        public string actionName;
        public string actionType;
        public string bindingPath;
        public string interactions;
        public string processors;
        public string groups;
        public string expectedControlType;
        public string controlScheme;
        public string bindingGroup;
        public List<string> devicePaths = new List<string>();
        public bool overwrite;
    }

    [Serializable]
    public class InputSystemResult
    {
        public bool success;
        public string operation;
        public string assetPath;
        public string actionMap;
        public string actionName;
        public string bindingPath;
        public string controlScheme;
        public string json;
        public string outputPath;
        public List<string> controlSchemes = new List<string>();
        public List<InputActionAssetInfo> assets = new List<InputActionAssetInfo>();
        public string message;
    }

    [Serializable]
    public class InputActionAssetInfo
    {
        public string path;
        public string name;
        public int jsonLength;
    }

    #endregion
}
