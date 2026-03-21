using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace BWS.Editor.ClaudeCodeBridge
{
    /// <summary>
    /// Command handler for managing script execution order.
    ///
    /// PURPOSE:
    /// Get and set MonoScript execution order via MonoImporter API.
    /// Useful for ensuring initialization order between scripts.
    ///
    /// SUPPORTED OPERATIONS:
    /// 1. "get" - List all MonoScripts with their execution orders
    /// 2. "set" - Set execution order for a specific script
    ///
    /// COMMAND JSON:
    /// {
    ///   "commandId": "guid",
    ///   "commandType": "script-execution-order",
    ///   "parametersJson": "{\"operation\":\"set\",\"scriptPath\":\"Assets/Scripts/MyScript.cs\",\"order\":100}"
    /// }
    /// </summary>
    public class ScriptExecutionOrderCommandHandler : ICommandHandler
    {
        public string CommandType => "script-execution-order";

        public BridgeResponse Execute(BridgeCommand command)
        {
            try
            {
                var parameters = JsonUtility.FromJson<ScriptExecutionOrderParams>(
                    command.parametersJson ?? "{}");
                if (parameters == null)
                    parameters = new ScriptExecutionOrderParams();

                var operation = parameters.operation?.ToLower();
                BridgeLogger.LogDebug($"Execution order operation: {operation}");

                switch (operation)
                {
                    case "get":
                        return HandleGet(command, parameters);
                    case "set":
                        return HandleSet(command, parameters);
                    default:
                        return BridgeResponse.Error(command.commandId, command.commandType,
                            $"Unknown operation: {parameters.operation}. Supported: get, set");
                }
            }
            catch (Exception ex)
            {
                BridgeLogger.LogError($"Execution order error: {ex}");
                return BridgeResponse.Error(command.commandId, command.commandType, ex.ToString());
            }
        }

        private BridgeResponse HandleGet(BridgeCommand command, ScriptExecutionOrderParams parameters)
        {
            var result = new ScriptExecutionOrderResult
            {
                operation = "get",
                success = true,
            };

            // Find all MonoScript assets
            var guids = AssetDatabase.FindAssets("t:MonoScript");
            bool filterNonDefault = parameters.nonDefaultOnly;

            foreach (var guid in guids)
            {
                var path = AssetDatabase.GUIDToAssetPath(guid);
                var script = AssetDatabase.LoadAssetAtPath<MonoScript>(path);
                if (script == null) continue;

                var importer = AssetImporter.GetAtPath(path) as MonoImporter;
                if (importer == null) continue;

                int order = MonoImporter.GetExecutionOrder(script);

                // Optionally filter to only non-default orders
                if (filterNonDefault && order == 0)
                    continue;

                result.scripts.Add(new ScriptOrderEntry
                {
                    scriptPath = path,
                    className = script.GetClass()?.Name ?? script.name,
                    executionOrder = order,
                });
            }

            // Sort by execution order
            result.scripts.Sort((a, b) => a.executionOrder.CompareTo(b.executionOrder));
            result.message = $"Found {result.scripts.Count} scripts" +
                (filterNonDefault ? " with non-default execution order" : "");

            BridgeLogger.LogInfo(result.message);
            return BridgeResponse.Success(
                command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }

        private BridgeResponse HandleSet(BridgeCommand command, ScriptExecutionOrderParams parameters)
        {
            if (string.IsNullOrEmpty(parameters.scriptPath))
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "scriptPath is required for set operation.");
            }

            if (EditorApplication.isCompiling)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    "Cannot set execution order while scripts are compiling.");
            }

            var script = AssetDatabase.LoadAssetAtPath<MonoScript>(parameters.scriptPath);
            if (script == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"MonoScript not found at: {parameters.scriptPath}");
            }

            var importer = AssetImporter.GetAtPath(parameters.scriptPath) as MonoImporter;
            if (importer == null)
            {
                return BridgeResponse.Error(command.commandId, command.commandType,
                    $"MonoImporter not available for: {parameters.scriptPath}");
            }

            int previousOrder = MonoImporter.GetExecutionOrder(script);
            MonoImporter.SetExecutionOrder(script, parameters.order);

            var result = new ScriptExecutionOrderResult
            {
                operation = "set",
                success = true,
                message = $"Set execution order for {script.name}: {previousOrder} -> {parameters.order}",
            };
            result.scripts.Add(new ScriptOrderEntry
            {
                scriptPath = parameters.scriptPath,
                className = script.GetClass()?.Name ?? script.name,
                executionOrder = parameters.order,
            });

            BridgeLogger.LogInfo(result.message);
            return BridgeResponse.Success(
                command.commandId, command.commandType,
                JsonUtility.ToJson(result));
        }
    }

    #region Script Execution Order Models

    [Serializable]
    public class ScriptExecutionOrderParams
    {
        public string operation; // "get", "set"
        public string scriptPath; // Asset path for set
        public int order; // Execution order value for set
        public bool nonDefaultOnly = false; // For get: filter to non-zero only
    }

    [Serializable]
    public class ScriptExecutionOrderResult
    {
        public string operation;
        public bool success;
        public string message;
        public List<ScriptOrderEntry> scripts = new List<ScriptOrderEntry>();
    }

    [Serializable]
    public class ScriptOrderEntry
    {
        public string scriptPath;
        public string className;
        public int executionOrder;
    }

    #endregion
}
